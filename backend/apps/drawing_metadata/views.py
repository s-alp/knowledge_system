from __future__ import annotations

import json

from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.display import (
    build_2d_snapshot_display,
    build_3d_snapshot_display,
    build_composed_display_payload,
    build_tag_review_display_payload,
)
from apps.drawing_metadata.services.persistence import apply_manual_overrides, enqueue_extraction_job


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
        return render(
            request,
            self.template_name,
            {
                "drawing": drawing,
                "tag_review_display": build_tag_review_display_payload(
                    composed_metadata=composed_metadata,
                    snapshots_by_mode=snapshots_by_mode,
                ),
            },
        )


class JobDetailPageView(View):
    template_name = "drawing_metadata/job_detail.html"

    def get(self, request: HttpRequest, job_id) -> HttpResponse:
        job = get_object_or_404(DrawingMetadataExtractionJob.objects.select_related("drawing"), pk=job_id)
        return render(request, self.template_name, {"job": job})
