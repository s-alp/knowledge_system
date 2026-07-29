from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.drawing_metadata.models import (
    DrawingMetadataAgentHeartbeat,
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)


CLAIM_URL = "/api/v1/drawing-metadata/agent/jobs/claim"
HEARTBEAT_URL = "/api/v1/drawing-metadata/agent/heartbeat"
TOKEN = "test-agent-token"
WORKER_NAME = "windows-agent-test"


def _client(*, authenticated: bool = True) -> APIClient:
    client = APIClient()
    if authenticated:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
    return client


def _create_job(*, source_path, source_format: str = "icad", mode: str = "3d"):
    source_bytes = source_path.read_bytes() if source_path.exists() else b""
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=f"agent-{source_format}-{mode}",
        filename=source_path.name,
        source_path=str(source_path),
        source_content_sha256=hashlib.sha256(source_bytes).hexdigest() if source_bytes else "",
        source_format=source_format,
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode=mode,
        status=DrawingMetadataExtractionJob.STATUS_QUEUED,
    )
    return drawing, job


@pytest.fixture(autouse=True)
def _agent_settings(settings, tmp_path):
    settings.DRAWING_METADATA_AGENT_TOKEN = TOKEN
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "drawing_metadata"
    settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT = settings.DRAWING_METADATA_STORAGE_ROOT / "preview_assets"
    settings.DRAWING_METADATA_AGENT_MAX_ASSET_BYTES = 1024 * 1024
    settings.DRAWING_METADATA_JOB_LEASE_SECONDS = 60
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 180


@pytest.mark.django_db
def test_agent_api_requires_bearer_token():
    response = _client(authenticated=False).post(
        CLAIM_URL,
        {"workerName": WORKER_NAME, "mode": "all"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_agent_claim_only_claims_sxnet_job(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    icad_path = settings.DRAWING_METADATA_STORAGE_ROOT / "sample.icd"
    step_path = settings.DRAWING_METADATA_STORAGE_ROOT / "sample.step"
    icad_path.write_bytes(b"icad")
    step_path.write_bytes(b"step")
    _drawing, icad_job = _create_job(source_path=icad_path)
    _create_job(source_path=step_path, source_format="step")

    response = _client().post(
        CLAIM_URL,
        {
            "workerName": WORKER_NAME,
            "mode": "all",
            "runnerVersion": "test",
            "processId": 123,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["jobId"] == str(icad_job.id)
    assert response.data["source"]["downloadAvailable"] is True
    assert response.data["source"]["sha256"] == hashlib.sha256(b"icad").hexdigest()
    icad_job.refresh_from_db()
    assert icad_job.status == DrawingMetadataExtractionJob.STATUS_PROCESSING
    assert icad_job.worker_name == WORKER_NAME
    assert DrawingMetadataAgentHeartbeat.objects.get(pk=WORKER_NAME).current_job_id == icad_job.id


@pytest.mark.django_db
def test_agent_source_download_and_asset_upload(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    source_path = settings.DRAWING_METADATA_STORAGE_ROOT / "source.icd"
    source_path.write_bytes(b"source-content")
    _drawing, job = _create_job(source_path=source_path)
    client = _client()
    claim = client.post(CLAIM_URL, {"workerName": WORKER_NAME, "mode": "all"}, format="json")

    source_response = client.get(claim.data["source"]["downloadUrl"])
    source_content = b"".join(source_response.streaming_content)
    asset_response = client.post(
        f"/api/v1/drawing-metadata/agent/jobs/{job.id}/assets",
        {
            "workerName": WORKER_NAME,
            "relativePath": "preview/model.stl",
            "file": SimpleUploadedFile("model.stl", b"solid model", content_type="model/stl"),
        },
        format="multipart",
    )

    assert source_response.status_code == 200
    assert source_content == b"source-content"
    assert asset_response.status_code == 201
    assert (
        settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT
        / str(job.id)
        / "preview"
        / "model.stl"
    ).read_bytes() == b"solid model"


@pytest.mark.django_db
def test_agent_asset_upload_rejects_path_traversal(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    source_path = settings.DRAWING_METADATA_STORAGE_ROOT / "source.icd"
    source_path.write_bytes(b"source-content")
    _drawing, job = _create_job(source_path=source_path)
    client = _client()
    client.post(CLAIM_URL, {"workerName": WORKER_NAME, "mode": "all"}, format="json")

    response = client.post(
        f"/api/v1/drawing-metadata/agent/jobs/{job.id}/assets",
        {
            "workerName": WORKER_NAME,
            "relativePath": "../outside.stl",
            "file": SimpleUploadedFile("outside.stl", b"invalid"),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert not (settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / "outside.stl").exists()


@pytest.mark.django_db
def test_agent_heartbeat_extends_job_lease(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    source_path = settings.DRAWING_METADATA_STORAGE_ROOT / "source.icd"
    source_path.write_bytes(b"source-content")
    _drawing, job = _create_job(source_path=source_path)
    client = _client()
    client.post(CLAIM_URL, {"workerName": WORKER_NAME, "mode": "all"}, format="json")
    DrawingMetadataExtractionJob.objects.filter(pk=job.id).update(
        lease_expires_at=timezone.now() + timedelta(seconds=1)
    )

    response = client.post(
        HEARTBEAT_URL,
        {
            "workerName": WORKER_NAME,
            "mode": "all",
            "state": "processing",
            "jobId": str(job.id),
            "runnerVersion": "test",
            "processId": 123,
        },
        format="json",
    )

    assert response.status_code == 200
    job.refresh_from_db()
    assert job.lease_expires_at > timezone.now() + timedelta(seconds=180)


@pytest.mark.django_db
def test_agent_complete_runs_django_normalization_and_persistence(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    source_path = settings.DRAWING_METADATA_STORAGE_ROOT / "source.icd"
    source_path.write_bytes(b"source-content")
    drawing, job = _create_job(source_path=source_path)
    client = _client()
    client.post(CLAIM_URL, {"workerName": WORKER_NAME, "mode": "all"}, format="json")

    response = client.post(
        f"/api/v1/drawing-metadata/agent/jobs/{job.id}/complete",
        {
            "workerName": WORKER_NAME,
            "result": {
                "source_format": "icad",
                "source_kind": "3d",
                "extractor_name": "icad-sxnet-extractor",
                "extractor_version": "test",
                "elapsed_ms": 25,
                "source_file": {"file_name": "source.icd"},
                "raw_extract": {"parts": []},
                "warnings": [],
            },
        },
        format="json",
    )

    assert response.status_code == 200
    job.refresh_from_db()
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="3d")
    assert job.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert snapshot.latest_job_id == job.id
    assert snapshot.canonical_attributes_json["source_format"] == "icad"


@pytest.mark.django_db
def test_agent_fail_records_error(settings):
    settings.DRAWING_METADATA_STORAGE_ROOT.mkdir(parents=True)
    source_path = settings.DRAWING_METADATA_STORAGE_ROOT / "source.icd"
    source_path.write_bytes(b"source-content")
    _drawing, job = _create_job(source_path=source_path)
    client = _client()
    client.post(CLAIM_URL, {"workerName": WORKER_NAME, "mode": "all"}, format="json")

    response = client.post(
        f"/api/v1/drawing-metadata/agent/jobs/{job.id}/fail",
        {"workerName": WORKER_NAME, "errorMessage": "SXNET open failed"},
        format="json",
    )

    assert response.status_code == 200
    job.refresh_from_db()
    heartbeat = DrawingMetadataAgentHeartbeat.objects.get(pk=WORKER_NAME)
    assert job.status == DrawingMetadataExtractionJob.STATUS_FAILED
    assert job.error_message == "SXNET open failed"
    assert heartbeat.state == "error"
    assert heartbeat.last_error == "SXNET open failed"
