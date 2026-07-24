from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone


HEARTBEAT_SCHEMA_VERSION = "drawing_metadata_worker_heartbeat.v1"


def _heartbeat_path() -> Path:
    return settings.DRAWING_METADATA_STORAGE_ROOT / "worker_heartbeat.json"


def write_worker_heartbeat(
    *,
    worker_name: str,
    mode: str,
    state: str,
    job_id: str | None = None,
    runner_mode: str = "loop",
    process_id: int | None = None,
    batch_size: int | None = None,
) -> None:
    """Worker の常駐状態をフロントから確認できるように小さなJSONへ記録する。"""

    path = _heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = timezone.now()
    payload = {
        "schemaVersion": HEARTBEAT_SCHEMA_VERSION,
        "workerName": worker_name,
        "mode": mode,
        "state": state,
        "jobId": job_id or "",
        "runnerMode": runner_mode,
        "processId": process_id if process_id is not None else os.getpid(),
        "batchSize": batch_size,
        "updatedAt": now.isoformat(),
        "staleAfterSeconds": settings.DRAWING_METADATA_WORKER_HEARTBEAT_STALE_SECONDS,
    }
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return timezone.make_aware(parsed, timezone.utc)
    return parsed


def build_worker_status_payload() -> dict:
    path = _heartbeat_path()
    stale_seconds = settings.DRAWING_METADATA_WORKER_HEARTBEAT_STALE_SECONDS
    if not path.exists():
        return {
            "schemaVersion": HEARTBEAT_SCHEMA_VERSION,
            "status": "missing",
            "label": "未起動",
            "message": "抽出workerのheartbeatがありません。ジョブは待機中のまま残ります。",
            "workerName": "",
            "mode": "",
            "state": "",
            "jobId": "",
            "runnerMode": "",
            "processId": None,
            "batchSize": None,
            "updatedAt": "",
            "ageSeconds": None,
            "staleAfterSeconds": stale_seconds,
        }

    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schemaVersion": HEARTBEAT_SCHEMA_VERSION,
            "status": "unreadable",
            "label": "確認不可",
            "message": "抽出workerのheartbeatを読み取れません。workerログを確認してください。",
            "workerName": "",
            "mode": "",
            "state": "",
            "jobId": "",
            "runnerMode": "",
            "processId": None,
            "batchSize": None,
            "updatedAt": "",
            "ageSeconds": None,
            "staleAfterSeconds": stale_seconds,
        }

    updated_at = _parse_datetime(str(raw_payload.get("updatedAt") or ""))
    age_seconds = int((timezone.now() - updated_at).total_seconds()) if updated_at else None
    is_fresh = age_seconds is not None and age_seconds <= stale_seconds
    state = str(raw_payload.get("state") or "")
    runner_mode = str(raw_payload.get("runnerMode") or "")
    is_loop_worker = runner_mode == "loop"
    is_running = is_fresh and is_loop_worker
    status = "running" if is_running else "stale"
    label = "稼働中" if is_running else "停止または未確認"
    message = (
        "抽出workerが定期的にheartbeatを更新しています。"
        if is_running
        else "抽出workerのheartbeat更新が途切れています。起票済みジョブが残る場合はworkerを起動してください。"
    )
    if is_fresh and not is_loop_worker:
        status = "not_looping"
        label = "未常駐"
        message = "直近の実行は単発処理のため、常駐workerは稼働していません。"
    if is_running and state == "processing":
        message = "抽出workerがジョブを処理中です。"
    elif is_running and state == "idle":
        message = "抽出workerは起動済みで、次のジョブを待機しています。"

    return {
        "schemaVersion": HEARTBEAT_SCHEMA_VERSION,
        "status": status,
        "label": label,
        "message": message,
        "workerName": str(raw_payload.get("workerName") or ""),
        "mode": str(raw_payload.get("mode") or ""),
        "state": state,
        "jobId": str(raw_payload.get("jobId") or ""),
        "runnerMode": runner_mode,
        "processId": raw_payload.get("processId"),
        "batchSize": raw_payload.get("batchSize"),
        "updatedAt": str(raw_payload.get("updatedAt") or ""),
        "ageSeconds": age_seconds,
        "staleAfterSeconds": stale_seconds,
    }
