from datetime import timedelta

import pytest
from django.utils import timezone

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.extraction_runner import ExtractionRunResult
from apps.drawing_metadata.services.llm_title_block_classifier import GeminiResponseError
from apps.drawing_metadata.tasks import extraction_tasks
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


@pytest.mark.django_db
def test_process_job_refreshes_lease_for_extractor_timeout(monkeypatch, settings, tmp_path):
    settings.DRAWING_METADATA_JOB_LEASE_SECONDS = 120
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 300
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-lease-refresh",
        filename="sample-lease-refresh.icd",
        source_path=r"C:\temp\sample-lease-refresh.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="test-worker",
        lease_expires_at=timezone.now() + timedelta(seconds=5),
    )

    def fake_run_extractor(*, drawing, extraction_mode, job_id, extraction_profile, extraction_options):
        live_job = DrawingMetadataExtractionJob.objects.get(pk=job_id)
        assert live_job.lease_expires_at is not None
        assert live_job.lease_expires_at > timezone.now() + timedelta(seconds=300)
        assert extraction_profile == "default"
        assert extraction_options == {}
        return ExtractionRunResult(
            payload={
                "source_format": "icad",
                "source_kind": "3d",
                "source_file": {"file_name": "sample-lease-refresh.icd"},
                "raw_extract": {"parts": []},
                "warnings": [],
            },
            output_path=tmp_path / "raw.json",
        )

    monkeypatch.setattr(extraction_tasks, "run_extractor", fake_run_extractor)

    processed = extraction_tasks.process_job(job.id)

    assert processed.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert processed.lease_expires_at is None
    assert processed.diagnostics_json["activeExtractionProfile"] == "default"
    assert processed.diagnostics_json["activeExtractionOptions"] == {}
    assert processed.diagnostics_json["resultWarningCount"] == 0


@pytest.mark.django_db
def test_process_job_applies_gemini_title_block_classification(monkeypatch, settings, tmp_path):
    settings.DRAWING_METADATA_LLM_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "test-key"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-process",
        filename="sample-process.icd",
        source_path=r"C:\temp\sample-process.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="test-worker",
    )

    def fake_run_extractor(*, drawing, extraction_mode, job_id, extraction_profile, extraction_options):
        assert extraction_profile == "default"
        assert extraction_options == {}
        return ExtractionRunResult(
            payload={
                "source_format": "icad",
                "source_kind": "2d",
                "source_file": {"file_name": "sample-process.icd"},
                "raw_extract": {
                    "texts": [
                        {
                            "text_lines": ["品名 SUS304"],
                            "source_type": "text",
                            "inside_print_area": True,
                        }
                    ]
                },
                "warnings": [],
            },
            output_path=tmp_path / "raw.json",
        )

    def fake_classify_title_block_candidates(candidates):
        assert candidates[0]["value"] == "SUS304"
        return [{"index": 0, "field": "material", "confidence": "high", "reason": "材質値に見える"}]

    monkeypatch.setattr(extraction_tasks, "run_extractor", fake_run_extractor)
    monkeypatch.setattr(
        extraction_tasks,
        "classify_title_block_candidates",
        fake_classify_title_block_candidates,
    )

    processed = extraction_tasks.process_job(job.id)
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="2d")

    assert processed.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert snapshot.canonical_attributes_json["title_block_fields"]["material"] == "SUS304"
    assert snapshot.canonical_attributes_json["title_block_candidates"][0]["llm_field"] == "material"
    assert any(tag["tag"] == "材質:SUS304" for tag in snapshot.derived_tags_json)


@pytest.mark.django_db
def test_process_job_records_gemini_failure_as_warning(monkeypatch, settings, tmp_path):
    settings.DRAWING_METADATA_LLM_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "test-key"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-warning",
        filename="sample-warning.icd",
        source_path=r"C:\temp\sample-warning.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="test-worker",
    )

    def fake_run_extractor(*, drawing, extraction_mode, job_id, extraction_profile, extraction_options):
        assert extraction_profile == "default"
        assert extraction_options == {}
        return ExtractionRunResult(
            payload={
                "source_format": "icad",
                "source_kind": "2d",
                "source_file": {"file_name": "sample-warning.icd"},
                "raw_extract": {
                    "texts": [
                        {
                            "text_lines": ["品名 SUS304"],
                            "source_type": "text",
                            "inside_print_area": True,
                        }
                    ]
                },
                "warnings": [],
            },
            output_path=tmp_path / "raw.json",
        )

    def fake_classify_title_block_candidates(candidates):
        raise GeminiResponseError("Gemini API returned HTTP 500.")

    monkeypatch.setattr(extraction_tasks, "run_extractor", fake_run_extractor)
    monkeypatch.setattr(
        extraction_tasks,
        "classify_title_block_candidates",
        fake_classify_title_block_candidates,
    )

    processed = extraction_tasks.process_job(job.id)

    assert processed.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert processed.warnings_json == [
        {
            "code": "title_block_llm_classification_failed",
            "message": "Gemini API returned HTTP 500.",
            "source": "gemini_title_block_classifier",
        }
    ]


def test_classify_2d_title_block_candidates_skips_replacement_characters(monkeypatch, settings):
    settings.DRAWING_METADATA_LLM_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "test-key"
    canonical_attributes = {
        "title_block_fields": {},
        "title_block_candidates": [
            {
                "field": "material",
                "label": "材質",
                "value": "�",
                "confidence": "low",
                "evidence_text": "材質 �",
            },
            {
                "field": "material",
                "label": "材質",
                "value": "SUS304",
                "confidence": "low",
                "evidence_text": "材質 SUS304",
            },
        ],
    }
    warnings = []

    def fake_classify_title_block_candidates(candidates):
        assert candidates == [canonical_attributes["title_block_candidates"][1]]
        return [{"index": 0, "field": "material", "confidence": "high", "reason": "材質値に見える"}]

    monkeypatch.setattr(
        extraction_tasks,
        "classify_title_block_candidates",
        fake_classify_title_block_candidates,
    )

    extraction_tasks._classify_2d_title_block_candidates(canonical_attributes, warnings)

    assert warnings == [
        {
            "code": "title_block_llm_skipped_replacement_characters",
            "message": "Replacement-character title-block candidates were skipped before Gemini classification: 1",
            "source": "gemini_title_block_classifier",
            "count": 1,
        }
    ]
    assert "llm_field" not in canonical_attributes["title_block_candidates"][0]
    assert canonical_attributes["title_block_candidates"][1]["llm_field"] == "material"
    assert canonical_attributes["title_block_fields"]["material"] == "SUS304"
