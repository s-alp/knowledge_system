from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
    EXTRACTION_MODE_2D,
    EXTRACTION_MODE_3D,
)
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.extraction_runner import ExtractionRunnerError, run_extractor
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.persistence import save_extraction_snapshot
from apps.drawing_metadata.services.tag_builder import build_derived_tags


def _resolve_mode_filter(mode: str) -> list[str]:
    if mode == "all":
        return [EXTRACTION_MODE_2D, EXTRACTION_MODE_3D]
    return [mode]


def claim_next_job(worker_name: str, mode: str) -> DrawingMetadataExtractionJob | None:
    mode_values = _resolve_mode_filter(mode)
    now = timezone.now()
    lease_deadline = now + timedelta(seconds=settings.DRAWING_METADATA_JOB_LEASE_SECONDS)

    with transaction.atomic():
        job = (
            DrawingMetadataExtractionJob.objects.select_related("drawing")
            .filter(
                extraction_mode__in=mode_values,
            )
            .filter(
                Q(status=DrawingMetadataExtractionJob.STATUS_QUEUED)
                | Q(
                    status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
                    lease_expires_at__isnull=True,
                )
                | Q(
                    status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
                    lease_expires_at__isnull=False,
                    lease_expires_at__lte=now,
                )
            )
            .order_by("created_at")
            .first()
        )
        if not job:
            return None

        if job.status == DrawingMetadataExtractionJob.STATUS_PROCESSING:
            job.retry_count += 1

        job.status = DrawingMetadataExtractionJob.STATUS_PROCESSING
        job.worker_name = worker_name
        job.started_at = job.started_at or now
        job.lease_expires_at = lease_deadline
        job.save(
            update_fields=[
                "status",
                "worker_name",
                "retry_count",
                "started_at",
                "lease_expires_at",
                "updated_at",
            ]
        )
        return job


def process_job(job_id) -> DrawingMetadataExtractionJob:
    job = DrawingMetadataExtractionJob.objects.select_related("drawing").get(pk=job_id)
    executed_by = f"worker:{job.worker_name or 'unknown'}"
    try:
        result = run_extractor(
            drawing=job.drawing,
            extraction_mode=job.extraction_mode,
            job_id=job.id,
        )
        canonical_attributes = normalize_raw_extract(result.payload)
        derived_tags = build_derived_tags(canonical_attributes)
        save_extraction_snapshot(
            drawing=job.drawing,
            extraction_mode=job.extraction_mode,
            job=job,
            raw_extract=result.payload.get("raw_extract", {}),
            canonical_attributes=canonical_attributes,
            derived_tags=derived_tags,
            executed_by=executed_by,
        )
        compose_drawing_metadata(job.drawing)
        job.status = DrawingMetadataExtractionJob.STATUS_SUCCEEDED
        job.finished_at = timezone.now()
        job.elapsed_ms = int(result.payload.get("elapsed_ms") or 0)
        job.error_message = ""
        job.warnings_json = result.payload.get("warnings", [])
        job.extractor_name = result.payload.get("extractor_name", "")
        job.extractor_version = result.payload.get("extractor_version", "")
        job.schema_version = settings.DRAWING_METADATA_SCHEMA_VERSION
        job.lease_expires_at = None
        job.save(
            update_fields=[
                "status",
                "finished_at",
                "elapsed_ms",
                "error_message",
                "warnings_json",
                "extractor_name",
                "extractor_version",
                "schema_version",
                "lease_expires_at",
                "updated_at",
            ]
        )
    except (ExtractionRunnerError, FileNotFoundError, ValueError) as exc:
        job.status = DrawingMetadataExtractionJob.STATUS_FAILED
        job.finished_at = timezone.now()
        job.error_message = str(exc)
        job.lease_expires_at = None
        job.save(update_fields=["status", "finished_at", "error_message", "lease_expires_at", "updated_at"])
    return job
