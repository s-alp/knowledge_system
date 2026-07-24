from apps.drawing_metadata.services.worker_status import build_worker_status_payload, write_worker_heartbeat


def test_once_heartbeat_is_not_reported_as_resident_worker(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    settings.DRAWING_METADATA_WORKER_HEARTBEAT_STALE_SECONDS = 30

    write_worker_heartbeat(
        worker_name="codex-once",
        mode="all",
        state="completed",
        runner_mode="once",
    )

    payload = build_worker_status_payload()

    assert payload["status"] == "not_looping"
    assert payload["label"] == "未常駐"
    assert payload["runnerMode"] == "once"


def test_loop_heartbeat_is_reported_as_running(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    settings.DRAWING_METADATA_WORKER_HEARTBEAT_STALE_SECONDS = 30

    write_worker_heartbeat(
        worker_name="codex-loop",
        mode="all",
        state="idle",
        runner_mode="loop",
        batch_size=8,
    )

    payload = build_worker_status_payload()

    assert payload["status"] == "running"
    assert payload["label"] == "稼働中"
    assert payload["runnerMode"] == "loop"
    assert payload["batchSize"] == 8
