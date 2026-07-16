from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import django

django.setup()

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing
from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload
from apps.drawing_metadata.services.failure_diagnostics import build_job_failure_diagnostics


REQUIRED_MODES = ("2d", "3d")
ACTIVE_STATUSES = {
    DrawingMetadataExtractionJob.STATUS_QUEUED,
    DrawingMetadataExtractionJob.STATUS_PROCESSING,
}


def _latest_jobs_by_mode(drawing: RegisteredDrawing) -> dict[str, DrawingMetadataExtractionJob | None]:
    jobs = sorted(drawing.jobs.all(), key=lambda job: job.created_at, reverse=True)
    return {mode: next((job for job in jobs if job.extraction_mode == mode), None) for mode in REQUIRED_MODES}


def _job_payload(job: DrawingMetadataExtractionJob | None) -> dict:
    if job is None:
        return {"status": "not_recorded", "jobId": None, "createdAt": None, "finishedAt": None, "errorMessage": ""}
    return {
        "status": job.status,
        "jobId": str(job.id),
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
        "errorMessage": job.error_message,
    }


def main() -> int:
    base_queryset = RegisteredDrawing.objects.prefetch_related("snapshots", "jobs").order_by("filename", "id")
    total_registration_count = base_queryset.count()
    scoped_queryset, scope = apply_active_drawing_scope(base_queryset)
    drawings = list(scoped_queryset)
    drawing_ids = [drawing.id for drawing in drawings]
    job_status_counts = Counter(
        DrawingMetadataExtractionJob.objects.filter(drawing_id__in=drawing_ids).values_list("status", flat=True)
    )
    failed_jobs = list(
        DrawingMetadataExtractionJob.objects.select_related("drawing")
        .filter(drawing_id__in=drawing_ids, status=DrawingMetadataExtractionJob.STATUS_FAILED)
        .order_by("-updated_at")
    )
    failed_jobs_missing_diagnostics = [
        job for job in failed_jobs if not (job.diagnostics_json or {}).get("failure")
    ]
    blocking_issues: list[dict] = []
    drawing_rows: list[dict] = []

    for job in failed_jobs_missing_diagnostics:
        failure = build_job_failure_diagnostics(job)
        blocking_issues.append(
            {
                "sourcePath": job.drawing.source_path,
                "filename": job.drawing.filename,
                "code": "failed_job_missing_failure_diagnostics",
                "message": "失敗済み抽出ジョブに failure diagnostics が記録されていません。",
                "modes": [job.extraction_mode],
                "jobId": str(job.id),
                "errorClass": failure["errorClass"],
                "reextractCondition": failure["reextractCondition"],
            }
        )

    for drawing in drawings:
        snapshot_modes = {snapshot.extraction_mode for snapshot in drawing.snapshots.all()}
        latest_jobs = _latest_jobs_by_mode(drawing)
        missing_modes = [mode for mode in REQUIRED_MODES if mode not in snapshot_modes]
        active_modes = [mode for mode, job in latest_jobs.items() if job is not None and job.status in ACTIVE_STATUSES]
        failed_without_snapshot = [
            mode
            for mode, job in latest_jobs.items()
            if job is not None and job.status == DrawingMetadataExtractionJob.STATUS_FAILED and mode not in snapshot_modes
        ]

        if missing_modes:
            blocking_issues.append(
                {
                    "sourcePath": drawing.source_path,
                    "filename": drawing.filename,
                    "code": "snapshot_missing",
                    "message": "登録済みICDに2D/3D snapshot欠落があります。",
                    "modes": missing_modes,
                    "reextractCondition": "欠落modeを再抽出し、失敗する場合はエラー理由と再抽出条件を記録してください。",
                }
            )
        if active_modes:
            blocking_issues.append(
                {
                    "sourcePath": drawing.source_path,
                    "filename": drawing.filename,
                    "code": "active_job_remaining",
                    "message": "待機中または実行中の抽出ジョブが残っています。",
                    "modes": active_modes,
                    "reextractCondition": "workerを起動して完了させるか、停止理由を確認してください。",
                }
            )
        if failed_without_snapshot:
            blocking_issues.append(
                {
                    "sourcePath": drawing.source_path,
                    "filename": drawing.filename,
                    "code": "latest_failed_without_snapshot",
                    "message": "最新ジョブが失敗しており、対象modeのsnapshotもありません。",
                    "modes": failed_without_snapshot,
                    "reextractCondition": "失敗理由を確認し、条件を変えて再抽出してください。",
                }
            )

        drawing_rows.append(
            {
                "sourcePath": drawing.source_path,
                "filename": drawing.filename,
                "snapshotModes": sorted(snapshot_modes),
                "latestJobs": {mode: _job_payload(job) for mode, job in latest_jobs.items()},
                "sourcePathLength": len(drawing.source_path),
            }
        )

    payload = {
        "schemaVersion": "drawing_metadata_job_state_audit.v1",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(drawings),
        ),
        "drawingCount": len(drawings),
        "jobStatusCounts": dict(sorted(job_status_counts.items())),
        "activeJobCount": sum(job_status_counts.get(status, 0) for status in ACTIVE_STATUSES),
        "failedJobCount": len(failed_jobs),
        "failedJobMissingFailureDiagnosticsCount": len(failed_jobs_missing_diagnostics),
        "blockingIssueCount": len(blocking_issues),
        "gatePassed": not blocking_issues,
        "blockingIssues": blocking_issues,
        "drawings": drawing_rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
