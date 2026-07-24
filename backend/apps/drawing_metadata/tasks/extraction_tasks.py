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
from apps.drawing_metadata.services.extraction_runner import ExtractionRunnerError, run_extractor, run_extractor_batch
from apps.drawing_metadata.services.failure_diagnostics import build_job_failure_diagnostics, build_source_preflight
from apps.drawing_metadata.services.llm_title_block_classifier import (
    GeminiConfigurationError,
    GeminiResponseError,
    apply_title_block_classifications,
    classify_title_block_candidates,
    filter_classifiable_title_block_candidates_with_stats,
    remap_title_block_classification_indexes,
)
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.persistence import save_extraction_snapshot
from apps.drawing_metadata.services.source_formats import uses_generic_cad_extractor, uses_sxnet_extractor
from apps.drawing_metadata.services.tag_builder import build_derived_tags


def _resolve_mode_filter(mode: str) -> list[str]:
    if mode == "all":
        return [EXTRACTION_MODE_2D, EXTRACTION_MODE_3D]
    return [mode]


def _processing_lease_seconds(batch_size: int = 1) -> int:
    return max(
        settings.DRAWING_METADATA_JOB_LEASE_SECONDS,
        settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS * max(batch_size, 1)
        + settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS
        + 60,
    )


def _refresh_processing_lease(job: DrawingMetadataExtractionJob, *, batch_size: int = 1) -> None:
    job.lease_expires_at = timezone.now() + timedelta(seconds=_processing_lease_seconds(batch_size))
    job.save(update_fields=["lease_expires_at", "updated_at"])


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


def claim_next_jobs(worker_name: str, mode: str, limit: int) -> list[DrawingMetadataExtractionJob]:
    jobs: list[DrawingMetadataExtractionJob] = []
    for _index in range(max(limit, 1)):
        job = claim_next_job(worker_name=worker_name, mode=mode)
        if not job:
            break
        jobs.append(job)
    return jobs


def _classify_2d_title_block_candidates(canonical_attributes: dict, warnings: list[dict]) -> None:
    provider = settings.DRAWING_METADATA_LLM_PROVIDER.lower()
    if provider != "gemini" or not settings.GEMINI_API_KEY:
        return

    candidates = canonical_attributes.get("title_block_candidates") or []
    if not candidates:
        return

    classifiable_candidates, original_indexes, skip_stats = filter_classifiable_title_block_candidates_with_stats(candidates)
    replacement_count = int(skip_stats.get("replacement_character") or 0)
    if replacement_count:
        warnings.append(
            {
                "code": "title_block_llm_skipped_replacement_characters",
                "message": f"Replacement-character title-block candidates were skipped before Gemini classification: {replacement_count}",
                "source": "gemini_title_block_classifier",
                "count": replacement_count,
            }
        )
    unusable_count = int(skip_stats.get("unusable_value") or 0)
    if unusable_count:
        warnings.append(
            {
                "code": "title_block_llm_skipped_unusable_values",
                "message": f"Value-less or unusable title-block candidates were skipped before Gemini classification: {unusable_count}",
                "source": "gemini_title_block_classifier",
                "count": unusable_count,
            }
        )
    if not classifiable_candidates:
        return

    try:
        classifications = classify_title_block_candidates(classifiable_candidates)
    except (GeminiConfigurationError, GeminiResponseError) as exc:
        warnings.append(
            {
                "code": "title_block_llm_classification_failed",
                "message": str(exc),
                "source": "gemini_title_block_classifier",
            }
        )
        return

    classifications = remap_title_block_classification_indexes(classifications, original_indexes)
    apply_title_block_classifications(canonical_attributes, classifications)


def _prepare_job_for_processing(job: DrawingMetadataExtractionJob, *, batch_size: int = 1) -> dict:
    _refresh_processing_lease(job, batch_size=batch_size)
    diagnostics = dict(job.diagnostics_json or {})
    diagnostics["activeExtractionProfile"] = job.extraction_profile or "default"
    diagnostics["activeExtractionOptions"] = job.extraction_options_json or {}
    diagnostics["sourcePreflight"] = build_source_preflight(job.drawing)
    job.diagnostics_json = diagnostics
    job.save(update_fields=["diagnostics_json", "updated_at"])
    return diagnostics


def _complete_job_from_payload(
    job: DrawingMetadataExtractionJob,
    payload: dict,
    *,
    diagnostics: dict,
    executed_by: str,
) -> DrawingMetadataExtractionJob:
    warnings = list(payload.get("warnings", []))
    canonical_attributes = normalize_raw_extract(payload)
    if job.extraction_mode == EXTRACTION_MODE_2D:
        _classify_2d_title_block_candidates(canonical_attributes, warnings)
    derived_tags = build_derived_tags(canonical_attributes)
    raw_extract = dict(payload.get("raw_extract", {}))
    if payload.get("source_file"):
        raw_extract["_source_file"] = payload["source_file"]
    save_extraction_snapshot(
        drawing=job.drawing,
        extraction_mode=job.extraction_mode,
        job=job,
        raw_extract=raw_extract,
        canonical_attributes=canonical_attributes,
        derived_tags=derived_tags,
        executed_by=executed_by,
    )
    compose_drawing_metadata(job.drawing)
    job.status = DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    job.finished_at = timezone.now()
    job.elapsed_ms = int(payload.get("elapsed_ms") or 0)
    job.error_message = ""
    job.warnings_json = warnings
    diagnostics["resultWarningCount"] = len(warnings)
    job.diagnostics_json = diagnostics
    job.extractor_name = payload.get("extractor_name", "")
    job.extractor_version = payload.get("extractor_version", "")
    job.schema_version = settings.DRAWING_METADATA_SCHEMA_VERSION
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "finished_at",
            "elapsed_ms",
            "error_message",
            "warnings_json",
            "diagnostics_json",
            "extractor_name",
            "extractor_version",
            "schema_version",
            "lease_expires_at",
            "updated_at",
        ]
    )
    return job


def _fail_job(job: DrawingMetadataExtractionJob, message: str) -> DrawingMetadataExtractionJob:
    job.status = DrawingMetadataExtractionJob.STATUS_FAILED
    job.finished_at = timezone.now()
    job.error_message = message
    job.lease_expires_at = None
    diagnostics = dict(job.diagnostics_json or {})
    diagnostics["failure"] = build_job_failure_diagnostics(job)
    job.diagnostics_json = diagnostics
    job.save(
        update_fields=[
            "status",
            "finished_at",
            "error_message",
            "diagnostics_json",
            "lease_expires_at",
            "updated_at",
        ]
    )
    return job


def process_job(job_id) -> DrawingMetadataExtractionJob:
    job = DrawingMetadataExtractionJob.objects.select_related("drawing").get(pk=job_id)
    executed_by = f"worker:{job.worker_name or 'unknown'}"
    try:
        diagnostics = _prepare_job_for_processing(job)
        result = run_extractor(
            drawing=job.drawing,
            extraction_mode=job.extraction_mode,
            job_id=job.id,
            extraction_profile=job.extraction_profile or "default",
            extraction_options=job.extraction_options_json or {},
        )
        _complete_job_from_payload(job, result.payload, diagnostics=diagnostics, executed_by=executed_by)
    except (ExtractionRunnerError, FileNotFoundError, ValueError) as exc:
        _fail_job(job, str(exc))
    return job


def process_jobs(jobs: list[DrawingMetadataExtractionJob]) -> list[DrawingMetadataExtractionJob]:
    job_list = list(jobs)
    if not job_list:
        return []

    completed_jobs: list[DrawingMetadataExtractionJob] = []
    generic_jobs = [job for job in job_list if uses_generic_cad_extractor(job.drawing.source_format)]
    sxnet_jobs = [job for job in job_list if uses_sxnet_extractor(job.drawing.source_format)]
    unsupported_jobs = [
        job
        for job in job_list
        if job not in generic_jobs and job not in sxnet_jobs
    ]

    for job in generic_jobs:
        completed_jobs.append(process_job(job.id))

    for job in unsupported_jobs:
        completed_jobs.append(_fail_job(job, f"{job.drawing.source_format} は抽出器の対象外です。"))

    if not sxnet_jobs:
        return completed_jobs

    diagnostics_by_job_id: dict[str, dict] = {}
    batch_size = len(sxnet_jobs)
    for job in sxnet_jobs:
        diagnostics_by_job_id[str(job.id)] = _prepare_job_for_processing(job, batch_size=batch_size)

    try:
        batch_results = run_extractor_batch(sxnet_jobs)
    except (ExtractionRunnerError, FileNotFoundError, ValueError) as exc:
        for job in sxnet_jobs:
            completed_jobs.append(_fail_job(job, str(exc)))
        return completed_jobs

    jobs_by_id = {str(job.id): job for job in sxnet_jobs}
    for result in batch_results:
        job = jobs_by_id[result.job_id]
        if result.error_message or result.payload is None:
            completed_jobs.append(_fail_job(job, result.error_message or "一括抽出でジョブが失敗しました。"))
            continue
        try:
            completed_jobs.append(
                _complete_job_from_payload(
                    job,
                    result.payload,
                    diagnostics=diagnostics_by_job_id[result.job_id],
                    executed_by=f"worker:{job.worker_name or 'unknown'}",
                )
            )
        except (FileNotFoundError, ValueError) as exc:
            completed_jobs.append(_fail_job(job, str(exc)))
    return completed_jobs
