from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.reextract_planner import enqueue_missing_or_partial_reextract_jobs


class Command(BaseCommand):
    help = "未抽出・部分抽出のICADを条件別再抽出キューへ積みます。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", action="append", default=[], help="対象 drawing id。複数指定できます。")
        parser.add_argument("--executed-by", default="queue_missing_drawing_metadata_extracts")
        parser.add_argument("--dry-run", action="store_true", help="ジョブを作らず対象とprofileだけ表示します。")

    def handle(self, *args, **options) -> None:
        queryset = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            Prefetch("jobs", queryset=DrawingMetadataExtractionJob.objects.order_by("-created_at")),
        )
        drawing_ids = options["drawing_id"]
        if drawing_ids:
            queryset = queryset.filter(id__in=drawing_ids)

        planned = 0
        queued = 0
        for drawing in queryset:
            if options["dry_run"]:
                from apps.drawing_metadata.services.reextract_planner import build_missing_or_partial_reextract_plan

                plan_items = build_missing_or_partial_reextract_plan(drawing=drawing)
                planned += len(plan_items)
                for item in plan_items:
                    self.stdout.write(f"PLAN {item.extraction_mode} {item.profile}: {drawing.filename}")
                continue

            jobs = enqueue_missing_or_partial_reextract_jobs(
                drawing=drawing,
                executed_by=options["executed_by"],
            )
            queued += len(jobs)
            for job in jobs:
                self.stdout.write(f"QUEUED {job.extraction_mode} {job.extraction_profile}: {drawing.filename} {job.id}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"completed dry-run planned={planned}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"completed queue queued={queued}"))
