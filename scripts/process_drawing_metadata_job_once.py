from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: process_drawing_metadata_job_once.py <job-id>")

    import django

    django.setup()

    from apps.drawing_metadata.models import DrawingMetadataExtractionJob
    from apps.drawing_metadata.tasks.extraction_tasks import process_job

    job = DrawingMetadataExtractionJob.objects.get(pk=sys.argv[1])
    job.worker_name = "codex-direct-2d-check"
    job.save(update_fields=["worker_name", "updated_at"])
    processed = process_job(job.id)
    print(f"{processed.id}\t{processed.extraction_mode}\t{processed.status}\t{processed.drawing.filename}")
    if processed.error_message:
        print(processed.error_message)


if __name__ == "__main__":
    main()
