from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-path", required=True)
    parser.add_argument("--drawing-id", required=False)
    parser.add_argument("--mark-job-failed", required=False)
    parser.add_argument("--reason", default="manual cleanup from inspection script")
    args = parser.parse_args()

    sys.path.insert(0, args.backend_path)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

    import django

    django.setup()

    from django.utils import timezone
    from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing

    if args.mark_job_failed:
        job = DrawingMetadataExtractionJob.objects.get(pk=args.mark_job_failed)
        job.status = DrawingMetadataExtractionJob.STATUS_FAILED
        job.finished_at = timezone.now()
        if not job.error_message:
            job.error_message = args.reason
        job.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
        print("MARKED_FAILED:", job.id)

    queryset = RegisteredDrawing.objects.prefetch_related("snapshots", "jobs").all()
    if args.drawing_id:
        queryset = queryset.filter(pk=args.drawing_id)

    for drawing in queryset:
        print("DRAWING:", drawing.id, drawing.filename)
        print("  SNAPSHOT_COUNT:", drawing.snapshots.count())
        for snapshot in drawing.snapshots.all():
            print("  SNAPSHOT_MODE:", snapshot.extraction_mode)
            print("    LATEST_JOB_ID:", snapshot.latest_job_id)
            print("    RAW_KEYS:", sorted((snapshot.raw_extract_json or {}).keys()))
            print("    CANONICAL_KEYS:", sorted((snapshot.canonical_attributes_json or {}).keys())[:10])
            print("    TAG_COUNT:", len(snapshot.derived_tags_json or []))
        print("  JOBS:", list(drawing.jobs.values_list("id", "extraction_mode", "status")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
