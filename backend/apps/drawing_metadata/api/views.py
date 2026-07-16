from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
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
    ReviewDecisionSerializer,
)
from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload
from apps.drawing_metadata.services.handoff_dashboard import build_handoff_dashboard_payload
from apps.drawing_metadata.services.icad_entities import build_icad_entity_catalog, find_icad_entity
from apps.drawing_metadata.services.persistence import apply_manual_overrides, apply_review_decision, enqueue_extraction_job
from apps.drawing_metadata.services.rag_payload import build_rag_payload
from apps.drawing_metadata.services.tag_automation_settings import build_tag_automation_settings_payload
from apps.drawing_metadata.services.worker_status import build_worker_status_payload
from apps.drawing_metadata.services.viewer_preview import (
    build_2d_preview_svg,
    build_3d_preview_stl,
    resolve_actual_2d_preview_source,
    resolve_actual_3d_preview_source,
)


class RegistrationListApiView(APIView):
    def get(self, request):
        queryset = (
            RegisteredDrawing.objects.prefetch_related(
                Prefetch(
                    "snapshots",
                    queryset=DrawingMetadataSnapshot.objects.only(
                        "id",
                        "drawing_id",
                        "extraction_mode",
                        "latest_job_id",
                    ).select_related("latest_job"),
                ),
                Prefetch(
                    "jobs",
                    queryset=DrawingMetadataExtractionJob.objects.only(
                        "id",
                        "drawing_id",
                        "extraction_mode",
                        "status",
                        "error_message",
                        "created_at",
                        "updated_at",
                    ),
                ),
            )
            .all()
        )
        if request.query_params.get("includeAll") == "true":
            drawings = queryset
        else:
            drawings, _scope = apply_active_drawing_scope(queryset)
        return Response(RegisteredDrawingListSerializer(drawings, many=True).data)

    def post(self, request):
        serializer = RegisteredDrawingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        drawing = serializer.save()
        return Response(RegisteredDrawingDetailSerializer(drawing).data, status=status.HTTP_201_CREATED)


def _icad_entity_drawings_queryset(*, include_details: bool = False):
    drawings, _scope = apply_active_drawing_scope(
        RegisteredDrawing.objects.filter(snapshots__extraction_mode="3d").distinct()
    )
    if include_details:
        return drawings.prefetch_related(
            Prefetch(
                "snapshots",
                queryset=DrawingMetadataSnapshot.objects.filter(extraction_mode__in=("2d", "3d")).select_related(
                    "latest_job"
                ),
            ),
            "audit_logs",
        )

    snapshot_fields = (
        "id",
        "drawing_id",
        "extraction_mode",
        "canonical_attributes_json",
        "manual_overrides_json",
        "derived_tags_json",
        "review_status",
        "updated_at",
    )
    return drawings.prefetch_related(
        Prefetch(
            "snapshots",
            queryset=DrawingMetadataSnapshot.objects.filter(extraction_mode="3d").only(*snapshot_fields),
            to_attr="knowledge_3d_snapshots",
        ),
        Prefetch(
            "snapshots",
            queryset=DrawingMetadataSnapshot.objects.filter(extraction_mode="2d").only(
                "id",
                "drawing_id",
                "extraction_mode",
                "canonical_attributes_json",
                "derived_tags_json",
            ),
            to_attr="knowledge_2d_snapshots",
        ),
    )


class IcadEntityListApiView(APIView):
    def get(self, request):
        target_key = request.query_params.get("target") or None
        if target_key not in {None, "product", "part"}:
            return Response(
                {"error": {"code": "icad_entity_target", "message": "target は product または part を指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        drawings = _icad_entity_drawings_queryset()
        drawing_id = request.query_params.get("drawingId")
        if drawing_id:
            try:
                drawing_uuid = uuid.UUID(drawing_id)
            except ValueError:
                return Response(
                    {"error": {"code": "icad_entity_drawing_id", "message": "drawingId はUUIDで指定してください。"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            drawings = drawings.filter(pk=drawing_uuid)

        try:
            limit = int(request.query_params.get("limit", "50"))
            offset = int(request.query_params.get("offset", "0"))
        except ValueError:
            return Response(
                {"error": {"code": "icad_entity_pagination", "message": "limit と offset は整数で指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 1 <= limit <= 250 or offset < 0:
            return Response(
                {"error": {"code": "icad_entity_pagination", "message": "limit は1～250、offset は0以上で指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            build_icad_entity_catalog(
                drawings,
                target_key=target_key,
                query=request.query_params.get("q", ""),
                offset=offset,
                limit=limit,
            )
        )


class IcadEntityDetailApiView(APIView):
    def get(self, request, entity_id):
        drawings = _icad_entity_drawings_queryset(include_details=True)
        drawing_id = request.query_params.get("drawingId")
        if drawing_id:
            try:
                drawing_uuid = uuid.UUID(drawing_id)
            except ValueError:
                return Response(
                    {"error": {"code": "icad_entity_drawing_id", "message": "drawingId はUUIDで指定してください。"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            drawings = drawings.filter(pk=drawing_uuid)
        entity = find_icad_entity(drawings, str(entity_id))
        if entity is None:
            raise Http404("ICAD構成エンティティが見つかりません。")
        return Response(entity)


class DrawingOptionListApiView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        try:
            limit = int(request.query_params.get("limit", "100"))
        except ValueError:
            return Response(
                {"error": {"code": "drawing_option_limit", "message": "limit は整数で指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 1 <= limit <= 250:
            return Response(
                {"error": {"code": "drawing_option_limit", "message": "limit は1～250で指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        drawings, _scope = apply_active_drawing_scope(RegisteredDrawing.objects.order_by("filename", "id"))
        if query:
            from django.db.models import Q

            drawings = drawings.filter(Q(filename__icontains=query) | Q(source_path__icontains=query))
        total_count = drawings.count()
        items = [
            {
                "drawingId": str(drawing.id),
                "filename": drawing.filename,
                "sourcePath": drawing.source_path,
            }
            for drawing in drawings[:limit]
        ]
        return Response({"items": items, "totalCount": total_count})


class TagAutomationSettingsApiView(APIView):
    def get(self, request):
        return Response(build_tag_automation_settings_payload())


def _reextract_condition_for_error(error_message: str) -> str:
    normalized = (error_message or "").lower()
    if not normalized:
        return "失敗理由が記録されていません。workerログとICAD起動状態を確認してください。"
    if "timed out" in normalized or "timeout" in normalized:
        return "ICAD起動待ちまたは抽出時間が不足しています。ICAD起動状態とタイムアウト秒数を確認して再抽出します。"
    if "not drawing file" in normalized or "図面ファイル" in error_message:
        return "ICAD/SXNETが図面ファイルとして開けていません。ファイル種別、パス、アクセス権、ICAD対応版を確認して再抽出します。"
    if "sxexception" in normalized or "sxnet" in normalized:
        return "SXNETでICADファイルを開けていません。ICADの起動状態、対象ファイル、起動済みダイアログを確認して再抽出します。"
    if "file" in normalized and ("not found" in normalized or "could not find" in normalized):
        return "元ICADファイルにアクセスできません。保存パスとネットワークドライブ接続を確認して再抽出します。"
    return "失敗理由を確認し、対象ファイル・ICAD起動状態・抽出条件を修正して再抽出します。"


class HandoffSummaryApiView(APIView):
    def get(self, request):
        queryset = (
            RegisteredDrawing.objects.prefetch_related(
                Prefetch(
                    "snapshots",
                    queryset=DrawingMetadataSnapshot.objects.only(
                        "id",
                        "drawing_id",
                        "extraction_mode",
                        "canonical_attributes_json",
                        "derived_tags_json",
                        "manual_overrides_json",
                        "review_status",
                        "updated_at",
                        "latest_job_id",
                    ).select_related("latest_job"),
                ),
                Prefetch(
                    "jobs",
                    queryset=DrawingMetadataExtractionJob.objects.only(
                        "id",
                        "drawing_id",
                        "extraction_mode",
                        "status",
                        "error_message",
                        "created_at",
                        "updated_at",
                    ),
                ),
            )
            .all()
        )
        total_count = queryset.count()
        scoped_queryset, scope = apply_active_drawing_scope(queryset)
        scoped_count = scoped_queryset.count()
        scoped_drawings = list(scoped_queryset)
        payload = build_handoff_dashboard_payload(scoped_drawings)
        payload["scope"] = build_scope_payload(
            scope=scope,
            total_registration_count=total_count,
            scoped_registration_count=scoped_count,
        )
        all_jobs = DrawingMetadataExtractionJob.objects.select_related("drawing")
        payload["workerStatus"] = build_worker_status_payload()
        payload["jobStatusCounts"] = {
            row["status"]: row["count"]
            for row in all_jobs.values("status").annotate(count=Count("id")).order_by("status")
        }
        payload["recentFailedJobs"] = [
            {
                "jobId": str(job.id),
                "drawingId": str(job.drawing_id),
                "filename": job.drawing.filename,
                "extractionMode": job.extraction_mode,
                "status": job.status,
                "workerName": job.worker_name,
                "errorMessage": job.error_message,
                "reextractCondition": _reextract_condition_for_error(job.error_message),
                "updatedAt": job.updated_at.isoformat(),
            }
            for job in all_jobs.filter(status=DrawingMetadataExtractionJob.STATUS_FAILED).order_by("-updated_at")[:10]
        ]
        return Response(payload)


class RegistrationUploadApiView(APIView):
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"error": {"code": "icad_file_required", "message": "ICADファイルを指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        original_name = get_valid_filename(uploaded_file.name)
        if not original_name.lower().endswith(".icd"):
            return Response(
                {"error": {"code": "icad_file_extension", "message": ".icd ファイルを指定してください。"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload_root = settings.DRAWING_METADATA_STORAGE_ROOT / "uploads"
        upload_root.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4()}_{original_name}"
        stored_path = (upload_root / stored_name).resolve()

        with stored_path.open("wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        drawing = RegisteredDrawing.objects.create(
            host_drawing_id="",
            filename=uploaded_file.name,
            source_path=str(stored_path),
            source_format="icad",
        )
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


class RegistrationReviewApiView(APIView):
    def patch(self, request, drawing_id):
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        serializer = ReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = get_object_or_404(
            DrawingMetadataSnapshot,
            drawing=drawing,
            extraction_mode=serializer.validated_data["extractionMode"],
        )
        snapshot = apply_review_decision(
            snapshot=snapshot,
            decision=serializer.validated_data["decision"],
            reason=serializer.validated_data.get("reason", ""),
            executed_by="api",
        )
        return Response(
            {
                "drawingId": str(drawing.id),
                "extractionMode": snapshot.extraction_mode,
                "reviewStatus": snapshot.review_status,
                "reviewedAt": snapshot.reviewed_at,
                "reviewedBy": snapshot.reviewed_by,
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
