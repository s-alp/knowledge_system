from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def main() -> None:
    """指定済みの1ジョブだけを通常の抽出・保存経路で処理する。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("job_id")
    args = parser.parse_args()

    import django

    django.setup()

    from apps.drawing_metadata.models import DrawingMetadataExtractionJob
    from apps.drawing_metadata.tasks.extraction_tasks import process_job

    job = DrawingMetadataExtractionJob.objects.get(pk=args.job_id)
    if job.status != DrawingMetadataExtractionJob.STATUS_QUEUED:
        raise RuntimeError(f"queuedジョブだけ処理できます: status={job.status}")

    process_job(job.id)
    job.refresh_from_db()
    print(
        json.dumps(
            {
                "jobId": str(job.id),
                "drawing": job.drawing.filename,
                "status": job.status,
                "error": job.error_message,
                "warnings": job.warnings_json,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
