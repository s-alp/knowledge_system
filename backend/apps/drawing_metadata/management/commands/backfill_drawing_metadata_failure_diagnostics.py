from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.drawing_metadata.models import DrawingMetadataExtractionJob
from apps.drawing_metadata.services.failure_diagnostics import build_job_failure_diagnostics


class Command(BaseCommand):
    help = "既存の失敗済み抽出ジョブへ failure diagnostics を補完します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="DBを更新せず、対象件数だけ確認します。")

    def handle(self, *args, **options) -> None:
        dry_run = bool(options["dry_run"])
        jobs = DrawingMetadataExtractionJob.objects.select_related("drawing").filter(
            status=DrawingMetadataExtractionJob.STATUS_FAILED
        )
        updated = 0
        skipped = 0

        for job in jobs.iterator():
            diagnostics = dict(job.diagnostics_json or {})
            if diagnostics.get("failure"):
                skipped += 1
                continue

            diagnostics["failure"] = build_job_failure_diagnostics(job)
            if not dry_run:
                job.diagnostics_json = diagnostics
                job.save(update_fields=["diagnostics_json", "updated_at"])
            updated += 1

        action = "would_update" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"failure diagnostics backfill completed {action}={updated} skipped={skipped} dry_run={dry_run}"
            )
        )
