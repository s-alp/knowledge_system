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
    build_viewer_tag_panel_display_payload,
)
from apps.drawing_metadata.services.failure_diagnostics import summarize_error_message, truncate_error_message_for_api
from apps.drawing_metadata.services.handoff_dashboard import build_handoff_dashboard_payload
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview
from apps.drawing_metadata.services.persistence import apply_manual_overrides, enqueue_extraction_job
from apps.drawing_metadata.services.rag_payload import build_rag_payload
from apps.drawing_metadata.services.tag_automation_settings import build_tag_automation_settings_payload

JOB_DETAIL_WARNING_DISPLAY_LIMIT = 50


class HandoffDashboardPageView(View):
    template_name = "drawing_metadata/handoff.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        drawings = list(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ).all()
        )
        return render(
            request,
            self.template_name,
            {
                "dashboard": build_handoff_dashboard_payload(drawings),
            },
        )


class RegistrationListPageView(View):
    template_name = "drawing_metadata/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        drawings = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            "jobs",
        ).all()
        return render(request, self.template_name, {"drawings": drawings})


class TagAutomationSettingsPageView(View):
    template_name = "drawing_metadata/tag_automation_settings.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                "settings_display": build_tag_automation_settings_payload(),
            },
        )


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
            "tag_review_page": request.build_absolute_uri(f"/internal/drawing-metadata/{drawing.id}/tags/"),
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
                "viewer_tag_panel": build_viewer_tag_panel_display_payload(viewer_bootstrap=viewer_bootstrap),
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

        messages.error(request, "操作を実行できません。対応している操作は「再抽出」と「手動補正の保存」です。")
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


class KnowledgeTargetTagPageView(View):
    template_name = "drawing_metadata/knowledge_target_tags.html"
    target_key = ""

    def get(self, request: HttpRequest, drawing_id) -> HttpResponse:
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        composed_metadata = compose_drawing_metadata(drawing)
        knowledge_payload_preview = build_knowledge_system_payload_preview(
            drawing=drawing,
            composed_metadata=composed_metadata,
        )
        target = _target_payload_or_404(knowledge_payload_preview, self.target_key)
        return render(
            request,
            self.template_name,
            {
                "drawing": drawing,
                "target": target,
                "source": knowledge_payload_preview.get("source", {}),
                "contract_evidence": knowledge_payload_preview.get("contractEvidence", {}),
            },
        )


class ProductUnitTagPageView(KnowledgeTargetTagPageView):
    target_key = "product"


class PartTagPageView(KnowledgeTargetTagPageView):
    target_key = "part"


class JobDetailPageView(View):
    template_name = "drawing_metadata/job_detail.html"

    def get(self, request: HttpRequest, job_id) -> HttpResponse:
        job = get_object_or_404(DrawingMetadataExtractionJob.objects.select_related("drawing"), pk=job_id)
        raw_error_message = job.error_message or ""
        error_message_display = truncate_error_message_for_api(raw_error_message)
        warnings = job.warnings_json or []
        return render(
            request,
            self.template_name,
            {
                "job": job,
                "warnings_display": warnings[:JOB_DETAIL_WARNING_DISPLAY_LIMIT],
                "warnings_count": len(warnings),
                "warnings_truncated": len(warnings) > JOB_DETAIL_WARNING_DISPLAY_LIMIT,
                "error_message_summary": summarize_error_message(raw_error_message),
                "error_message_display": error_message_display,
                "error_message_length": len(raw_error_message),
                "error_message_truncated": raw_error_message != error_message_display,
            },
        )


def _target_payload_or_404(knowledge_payload_preview: dict, target_key: str) -> dict:
    for target in knowledge_payload_preview.get("targets", []) or []:
        if isinstance(target, dict) and target.get("targetKey") == target_key:
            return target
    from django.http import Http404

    raise Http404(f"{target_key} target payload is missing")
