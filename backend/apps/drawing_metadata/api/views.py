from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drawing_metadata.api.serializers import (
    DrawingMetadataExtractionJobSerializer,
    ExtractRequestSerializer,
    ManualOverrideSerializer,
    RegisteredDrawingCreateSerializer,
    RegisteredDrawingDetailSerializer,
    RegisteredDrawingListSerializer,
)
from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.persistence import apply_manual_overrides, enqueue_extraction_job
from apps.drawing_metadata.services.rag_payload import build_rag_payload
from apps.drawing_metadata.services.viewer_preview import (
    build_2d_preview_svg,
    build_3d_preview_stl,
    resolve_actual_2d_preview_source,
    resolve_actual_3d_preview_source,
)


class RegistrationListApiView(APIView):
    def get(self, request):
        drawings = (
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            )
            .all()
        )
        return Response(RegisteredDrawingListSerializer(drawings, many=True).data)

    def post(self, request):
        serializer = RegisteredDrawingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        drawing = serializer.save()
        return Response(RegisteredDrawingDetailSerializer(drawing).data, status=status.HTTP_201_CREATED)


class RegistrationDetailApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        return Response(RegisteredDrawingDetailSerializer(drawing).data)


class DrawingViewerBootstrapApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        detail_payload = RegisteredDrawingDetailSerializer(drawing).data
        return Response(detail_payload["viewerBootstrap"])


class DrawingViewerOpenApiView(APIView):
    extraction_mode = ""
    display_mode = ""

    def post(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            ),
            pk=drawing_id,
        )
        snapshot = next(
            (snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == self.extraction_mode),
            None,
        )
        if snapshot is None:
            return Response(
                {
                    "error": {
                        "code": f"viewer_{self.extraction_mode}_snapshot_missing",
                        "message": f"{self.display_mode}の抽出snapshotがないため、プレビューを開始できません。",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if self.extraction_mode == "2d":
            actual_source = resolve_actual_2d_preview_source(drawing=drawing, snapshot=snapshot)
            if actual_source:
                return Response(
                    {
                        "sessionId": f"actual-2d-{drawing.id}",
                        "filename": actual_source.filename,
                        "extension": actual_source.extension,
                        "mimeType": actual_source.mime_type,
                        "sourceUrl": actual_source.source_url,
                        "pageCount": actual_source.page_count,
                        "pageImageUrls": actual_source.page_image_urls or [],
                        "diagnostics": {
                            "source": "drawing_metadata_snapshot",
                            "previewKind": actual_source.source_kind,
                            "note": "snapshot内の実2Dプレビュー資産URLを既存2Dビューワーadapterへ渡しています。",
                        },
                    }
                )

            return Response(
                {
                    "sessionId": f"snapshot-2d-{drawing.id}",
                    "filename": f"{drawing.filename}.preview.svg",
                    "extension": "svg",
                    "mimeType": "image/svg+xml",
                    "sourceUrl": f"/api/v1/drawings/{drawing.id}/viewer2d/preview.svg",
                    "pageCount": 1,
                    "pageImageUrls": [],
                    "diagnostics": {
                        "source": "drawing_metadata_snapshot",
                        "previewKind": "metadata_svg",
                        "note": "抽出JSONを既存2Dビューワーの画像adapterで確認するための軽量プレビューです。",
                    },
                }
            )

        actual_source = resolve_actual_3d_preview_source(drawing=drawing, snapshot=snapshot)
        if actual_source:
            return Response(
                {
                    "jobId": f"actual-3d-{drawing.id}",
                    "filename": actual_source.filename,
                    "sourceExtension": actual_source.source_extension,
                    "modelFormat": actual_source.model_format,
                    "status": "ready",
                    "modelUrl": actual_source.model_url,
                    "error": "",
                    "diagnostics": {
                        "source": "drawing_metadata_snapshot",
                        "previewKind": actual_source.source_kind,
                        "note": "snapshot内の実3Dプレビュー資産URLを既存3Dビューワーadapterへ渡しています。",
                    },
                }
            )

        return Response(
            {
                "jobId": f"snapshot-3d-{drawing.id}",
                "filename": f"{drawing.filename}.preview.stl",
                "sourceExtension": "stl",
                "modelFormat": "stl",
                "status": "ready",
                "modelUrl": f"/api/v1/drawings/{drawing.id}/viewer3d/preview.stl",
                "error": "",
                "diagnostics": {
                    "source": "drawing_metadata_snapshot",
                    "previewKind": "metadata_stl",
                    "note": "抽出JSONから作るメタデータ立体プレビューです。CAD形状そのものの変換API接続は別工程です。",
                },
            }
        )


class DrawingViewer2DOpenApiView(DrawingViewerOpenApiView):
    extraction_mode = "2d"
    display_mode = "2D"


class DrawingViewer3DOpenApiView(DrawingViewerOpenApiView):
    extraction_mode = "3d"
    display_mode = "3D"


class DrawingViewer2DPreviewApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related("snapshots"),
            pk=drawing_id,
        )
        snapshot = _get_snapshot_or_404(drawing=drawing, extraction_mode="2d")
        svg = build_2d_preview_svg(drawing=drawing, snapshot=snapshot)
        return HttpResponse(svg, content_type="image/svg+xml; charset=utf-8")


class DrawingViewer3DPreviewApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related("snapshots"),
            pk=drawing_id,
        )
        snapshot = _get_snapshot_or_404(drawing=drawing, extraction_mode="3d")
        stl = build_3d_preview_stl(drawing=drawing, snapshot=snapshot)
        return HttpResponse(stl, content_type="model/stl; charset=utf-8")


class DrawingPreviewAssetApiView(APIView):
    def get(self, request, job_id, filename):
        job_directory = (settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)).resolve()
        requested_path = (job_directory / filename).resolve()
        if not _is_relative_to(requested_path, job_directory) or not requested_path.is_file():
            raise Http404("preview asset not found")

        content_type = "model/stl" if requested_path.suffix.lower() == ".stl" else "application/octet-stream"
        return FileResponse(requested_path.open("rb"), content_type=content_type, filename=requested_path.name)


class RegistrationExtractApiView(APIView):
    def post(self, request, drawing_id):
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        serializer = ExtractRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = enqueue_extraction_job(
            drawing=drawing,
            extraction_mode=serializer.validated_data["extractionMode"],
            reason="API requested re-extract",
            executed_by="api",
            extraction_profile=serializer.validated_data.get("extractionProfile") or "default",
            extraction_options=serializer.validated_data.get("extractionOptions") or {},
        )
        return Response(DrawingMetadataExtractionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class RegistrationOverrideApiView(APIView):
    def patch(self, request, drawing_id):
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        serializer = ManualOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = apply_manual_overrides(
            drawing=drawing,
            extraction_mode=serializer.validated_data["extractionMode"],
            payload=serializer.validated_data,
            reason=serializer.validated_data.get("reason", ""),
            executed_by="api",
        )
        return Response(
            {
                "drawingId": str(drawing.id),
                "extractionMode": snapshot.extraction_mode,
                "manualOverrides": snapshot.manual_overrides_json,
                "canonicalAttributes": snapshot.canonical_attributes_json,
                "derivedTags": snapshot.derived_tags_json,
            }
        )


class RegistrationRagPayloadApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        return Response(build_rag_payload(drawing))


class JobDetailApiView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(DrawingMetadataExtractionJob.objects.select_related("drawing"), pk=job_id)
        return Response(DrawingMetadataExtractionJobSerializer(job).data)


def _get_snapshot_or_404(*, drawing: RegisteredDrawing, extraction_mode: str) -> DrawingMetadataSnapshot:
    snapshot = next(
        (snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == extraction_mode),
        None,
    )
    if snapshot is None:
        raise Http404(f"{extraction_mode} snapshot is missing")
    return snapshot


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
