from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import django

django.setup()

from apps.drawing_metadata.models import DrawingMetadataExtractionJob
from apps.drawing_metadata.services.failure_diagnostics import build_job_failure_diagnostics


def _inspect_job(job: DrawingMetadataExtractionJob) -> dict:
    drawing = job.drawing
    failure = build_job_failure_diagnostics(job)
    preflight = failure["sourcePreflight"]
    return {
        "jobId": str(job.id),
        "drawingId": str(drawing.id),
        "mode": job.extraction_mode,
        "profile": job.extraction_profile,
        "status": job.status,
        "filename": preflight["filename"],
        "sourcePath": preflight["sourcePath"],
        "sourcePathLength": preflight["sourcePathLength"],
        "sourcePathWithinSxnetLegacyLimit": preflight["sourcePathWithinSxnetLegacyLimit"],
        "requiresSxnetStagedInput": preflight["requiresSxnetStagedInput"],
        "filenameLength": preflight["filenameLength"],
        "filenameWithinWindowsLimit": preflight["filenameWithinWindowsLimit"],
        "extensionIsIcd": preflight["extensionIsIcd"],
        "sourceExistsFromCurrentMachine": preflight["sourceExistsFromCurrentMachine"],
        "errorClass": failure["errorClass"],
        "reextractCondition": failure["reextractCondition"],
        "recordedFailureDiagnostics": (job.diagnostics_json or {}).get("failure"),
        "errorMessage": job.error_message or "",
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect drawing metadata extraction job failure context.")
    parser.add_argument("job_ids", nargs="+", help="DrawingMetadataExtractionJob UUIDs to inspect.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    jobs = list(DrawingMetadataExtractionJob.objects.select_related("drawing").filter(id__in=args.job_ids))
    found_ids = {str(job.id) for job in jobs}
    missing_ids = [job_id for job_id in args.job_ids if job_id not in found_ids]
    payload = {
        "schemaVersion": "drawing_metadata_job_failure_inspection.v1",
        "requestedJobIds": args.job_ids,
        "missingJobIds": missing_ids,
        "jobs": [_inspect_job(job) for job in jobs],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if missing_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
