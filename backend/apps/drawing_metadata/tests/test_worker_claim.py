"""test_worker_claimの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.extraction_runner import ExtractionRunnerError, ExtractionRunResult
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
def test_process_job_extracts_step_and_saves_tags_without_sxnet(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    source_path = tmp_path / "gantry.step"
    source_path.write_text(
        """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('SUS304'),'2;1');
FILE_NAME('コマツ小山 ガントリー','2026-07-23',('SMC'),('system'),'preprocessor','system','');
ENDSEC;
DATA;
#10=PRODUCT('GANTRY HAND','SMC CYLINDER','',(#1));
ENDSEC;
END-ISO-10303-21;
""",
        encoding="utf-8",
    )
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="step-process",
        filename="gantry.step",
        source_path=str(source_path),
        source_format="step",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="test-worker",
    )

    processed = extraction_tasks.process_job(job.id)
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="3d")
    tags = [tag["tag"] for tag in snapshot.derived_tags_json]

    assert processed.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert processed.extractor_name == "generic-cad-text-extractor"
    assert snapshot.canonical_attributes_json["source_format"] == "step"
    assert "客先:コマツ小山" in tags
    assert "装置:ガントリー" in tags
    assert "材質:SUS304" in tags


@pytest.mark.django_db
def test_process_job_records_failure_diagnostics_for_sxnet_open_error(monkeypatch):
    long_source_path = "C:\\" + "\\".join(["segment"] * 40) + "\\sample.icd"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-failure-diagnostics",
        filename="sample.icd",
        source_path=long_source_path,
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
        worker_name="test-worker",
    )

    def fake_run_extractor(*, drawing, extraction_mode, job_id, extraction_profile, extraction_options):
        raise ExtractionRunnerError("sxnet.SxException: 指定したファイルは図面ファイルではありません。")

    monkeypatch.setattr(extraction_tasks, "run_extractor", fake_run_extractor)

    processed = extraction_tasks.process_job(job.id)

    failure = processed.diagnostics_json["failure"]
    assert processed.status == DrawingMetadataExtractionJob.STATUS_FAILED
    assert failure["errorClass"] == "sxnet_rejected_as_not_drawing_file"
    assert failure["sourcePreflight"]["requiresSxnetStagedInput"] is True
    assert failure["sourcePreflight"]["sourcePathWithinSxnetLegacyLimit"] is False
    assert "短い一時パス" in failure["reextractCondition"]


@pytest.mark.django_db
def test_process_job_reclassifies_formal_material_by_dictionary_without_external_ai(monkeypatch, tmp_path):
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

    monkeypatch.setattr(extraction_tasks, "run_extractor", fake_run_extractor)

    processed = extraction_tasks.process_job(job.id)
    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="2d")

    assert processed.status == DrawingMetadataExtractionJob.STATUS_SUCCEEDED
    assert snapshot.canonical_attributes_json["title_block_fields"]["material"] == "SUS304"
    assert any(tag["tag"] == "材質:SUS304" for tag in snapshot.derived_tags_json)
