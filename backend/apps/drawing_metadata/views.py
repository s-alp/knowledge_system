from __future__ import annotations

import json

from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.drawing_metadata.api.serializers import RegisteredDrawingDetailSerializer
from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.display import (
    build_2d_snapshot_display,
    build_3d_snapshot_display,
    build_composed_display_payload,
    build_integration_handoff_display_payload,
    build_tag_review_display_payload,
)
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview
from apps.drawing_metadata.services.persistence import apply_manual_overrides, enqueue_extraction_job
from apps.drawing_metadata.services.rag_payload import build_rag_payload


class RegistrationListPageView(View):
    template_name = "drawing_metadata/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        drawings = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            "jobs",
        ).all()
        return render(request, self.template_name, {"drawings": drawings})


class RegistrationDetailPageView(View):
    template_name = "drawing_metadata/detail.html"

    def get(self, request: HttpRequest, drawing_id) -> HttpResponse:
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        jobs = drawing.jobs.all()[:50]
        snapshots_by_mode = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}
        snapshot_2d = snapshots_by_mode.get("2d")
        snapshot_3d = snapshots_by_mode.get("3d")
        composed_metadata = compose_drawing_metadata(drawing)
        detail_api_payload = RegisteredDrawingDetailSerializer(drawing).data
        viewer_bootstrap = detail_api_payload.get("viewerBootstrap", {})
        knowledge_payload_preview = detail_api_payload.get("knowledgeSystemPayloadPreview", {})
        rag_payload = build_rag_payload(drawing)
        api_links = {
            "detail_api": request.build_absolute_uri(f"/api/v1/drawing-metadata/registrations/{drawing.id}/"),
            "rag_payload_api": request.build_absolute_uri(
                f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload/"
            ),
            "tag_review_page": request.build_absolute_uri(f"/drawing-metadata/{drawing.id}/tags/"),
        }

        return render(
            request,
            self.template_name,
            {
                "drawing": drawing,
                "jobs": jobs,
                "snapshots_by_mode": snapshots_by_mode,
                "snapshot_2d": snapshot_2d,
                "snapshot_3d": snapshot_3d,
                "composed_metadata": composed_metadata,
                "composed_display": build_composed_display_payload(composed_metadata),
                "handoff_display": build_integration_handoff_display_payload(
                    viewer_bootstrap=viewer_bootstrap,
                    rag_payload=rag_payload,
                    knowledge_payload_preview=knowledge_payload_preview,
                    api_links=api_links,
                ),
                "snapshot_2d_display": (
                    build_2d_snapshot_display(
                        raw_extract=snapshot_2d.raw_extract_json,
                        canonical_attributes=snapshot_2d.canonical_attributes_json,
                    )
                    if snapshot_2d
                    else None
                ),
                "snapshot_3d_display": (
                    build_3d_snapshot_display(
                        raw_extract=snapshot_3d.raw_extract_json,
                        canonical_attributes=snapshot_3d.canonical_attributes_json,
                    )
                    if snapshot_3d
                    else None
                ),
                "manual_overrides_pretty_2d": json.dumps(
                    snapshot_2d.manual_overrides_json if snapshot_2d else {},
                    ensure_ascii=False,
                    indent=2,
                ),
                "manual_overrides_pretty_3d": json.dumps(
                    snapshot_3d.manual_overrides_json if snapshot_3d else {},
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        )

    def post(self, request: HttpRequest, drawing_id) -> HttpResponse:
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        action = request.POST.get("action", "").strip()
        extraction_mode = request.POST.get("extraction_mode", "").strip()

        if action == "extract":
            job = enqueue_extraction_job(
                drawing=drawing,
                extraction_mode=extraction_mode,
                reason="HTML detail page re-extract",
                executed_by="html-ui",
            )
            messages.success(request, f"{extraction_mode} 再抽出ジョブ {job.id} を起票しました。")
            return redirect("drawing-metadata-job-page", job_id=job.id)

        if action == "override":
            raw_payload = request.POST.get("manual_overrides_json", "").strip() or "{}"
            payload = json.loads(raw_payload)
            apply_manual_overrides(
                drawing=drawing,
                extraction_mode=extraction_mode,
                payload=payload,
                reason=request.POST.get("reason", "").strip(),
                executed_by="html-ui",
            )
            messages.success(request, f"{extraction_mode} 手動補正を保存しました。")
            return redirect("drawing-metadata-detail-page", drawing_id=drawing.id)

        messages.error(request, "未対応の操作です。")
        return redirect("drawing-metadata-detail-page", drawing_id=drawing.id)


class TagReviewPageView(View):
    template_name = "drawing_metadata/tag_review.html"

    def get(self, request: HttpRequest, drawing_id) -> HttpResponse:
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        snapshots_by_mode = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}
        composed_metadata = compose_drawing_metadata(drawing)
        knowledge_payload_preview = build_knowledge_system_payload_preview(
            drawing=drawing,
            composed_metadata=composed_metadata,
        )
        return render(
            request,
            self.template_name,
            {
                "drawing": drawing,
                "tag_review_display": build_tag_review_display_payload(
                    composed_metadata=composed_metadata,
                    snapshots_by_mode=snapshots_by_mode,
                    knowledge_payload_preview=knowledge_payload_preview,
                ),
            },
        )


class JobDetailPageView(View):
    template_name = "drawing_metadata/job_detail.html"

    def get(self, request: HttpRequest, job_id) -> HttpResponse:
        job = get_object_or_404(DrawingMetadataExtractionJob.objects.select_related("drawing"), pk=job_id)
        return render(request, self.template_name, {"job": job})
