from datetime import timedelta

import pytest
from django.utils import timezone

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing
from apps.drawing_metadata.tasks.extraction_tasks import claim_next_job


@pytest.mark.django_db
def test_claim_next_job_filters_by_mode(settings):
    settings.DRAWING_METADATA_JOB_LEASE_SECONDS = 120
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-worker",
        filename="sample.icd",
        source_path=r"C:\temp\sample.icd",
        source_format="icad",
    )
    DrawingMetadataExtractionJob.objects.create(drawing=drawing, extraction_mode="2d", status="queued")
    DrawingMetadataExtractionJob.objects.create(drawing=drawing, extraction_mode="3d", status="queued")

    job = claim_next_job(worker_name="windows-icad-01", mode="2d")

    assert job is not None
    assert job.extraction_mode == "2d"
    assert job.worker_name == "windows-icad-01"
    assert job.status == DrawingMetadataExtractionJob.STATUS_PROCESSING


@pytest.mark.django_db
def test_claim_next_job_reclaims_stale_processing_job(settings):
    settings.DRAWING_METADATA_JOB_LEASE_SECONDS = 120
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-stale",
        filename="sample-stale.icd",
        source_path=r"C:\temp\sample-stale.icd",
        source_format="icad",
    )
    stale_job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="old-worker",
        lease_expires_at=timezone.now() - timedelta(seconds=5),
    )

    claimed = claim_next_job(worker_name="windows-icad-02", mode="all")

    assert claimed is not None
    assert claimed.id == stale_job.id
    assert claimed.worker_name == "windows-icad-02"
    assert claimed.retry_count == 1
