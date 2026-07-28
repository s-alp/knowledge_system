from __future__ import annotations

import json
import subprocess
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.drawing_metadata.management.commands import convert_icad_cad_formats
from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing
from apps.drawing_metadata.services import extraction_runner
from apps.drawing_metadata.services.extraction_runner import CadConversionRunResult, ExtractionRunnerError


def _conversion_result(tmp_path: Path, *, autostarted: bool) -> CadConversionRunResult:
    tmp_path.mkdir(parents=True, exist_ok=True)
    converted_path = tmp_path / "converted.step"
    converted_path.write_text("ISO-10303-21;", encoding="utf-8")
    output_path = tmp_path / "conversion.json"
    warnings = [{"code": "icad_autostarted"}] if autostarted else []
    payload = {"warnings": warnings, "converted_asset": {"file_path": str(converted_path)}}
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    return CadConversionRunResult(payload=payload, output_path=output_path, converted_file_path=converted_path)


@pytest.mark.django_db
def test_conversion_command_reuses_icad_and_shuts_down_once_after_processing(monkeypatch, settings, tmp_path):
    source = tmp_path / "source.icd"
    source.write_bytes(b"icad")
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="source-host",
        filename="source.icd",
        source_path=str(source),
        source_format="icad",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    shutdown_calls: list[bool] = []
    converter_calls: list[bool | None] = []

    def fake_run_icad_converter(**kwargs):
        converter_calls.append(kwargs["shutdown_icad_if_autostarted"])
        return _conversion_result(tmp_path / kwargs["output_format"], autostarted=len(converter_calls) == 1)

    monkeypatch.setattr(convert_icad_cad_formats, "run_icad_converter", fake_run_icad_converter)
    monkeypatch.setattr(
        convert_icad_cad_formats,
        "shutdown_icad_without_saving",
        lambda: shutdown_calls.append(True),
    )

    call_command(
        "convert_icad_cad_formats",
        drawing_id=[str(drawing.id)],
        format=["dxf", "step"],
        output_root=str(tmp_path / "converted"),
        stdout=StringIO(),
    )

    assert converter_calls == [False, False]
    assert shutdown_calls == [True]


@pytest.mark.django_db
def test_conversion_command_does_not_close_preexisting_icad(monkeypatch, settings, tmp_path):
    source = tmp_path / "source.icd"
    source.write_bytes(b"icad")
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="source-host",
        filename="source.icd",
        source_path=str(source),
        source_format="icad",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    shutdown_calls: list[bool] = []

    monkeypatch.setattr(
        convert_icad_cad_formats,
        "run_icad_converter",
        lambda **kwargs: _conversion_result(tmp_path / kwargs["output_format"], autostarted=False),
    )
    monkeypatch.setattr(
        convert_icad_cad_formats,
        "shutdown_icad_without_saving",
        lambda: shutdown_calls.append(True),
    )

    call_command(
        "convert_icad_cad_formats",
        drawing_id=[str(drawing.id)],
        format=["step"],
        output_root=str(tmp_path / "converted"),
        stdout=StringIO(),
    )

    assert shutdown_calls == []


def test_converter_timeout_closes_autostarted_icad_after_result_is_written(monkeypatch, settings, tmp_path):
    source = tmp_path / "source.icd"
    source.write_bytes(b"icad")
    drawing = RegisteredDrawing(
        filename="source.icd",
        source_path=str(source),
        source_format="icad",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = "runner.exe"
    shutdown_calls: list[bool] = []

    def fake_run(command, **kwargs):
        output_path = Path(command[command.index("--output-path") + 1])
        output_dir = Path(command[command.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        converted_path = output_dir / "source.step"
        converted_path.write_text("ISO-10303-21;", encoding="utf-8")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "warnings": [{"code": "icad_autostarted"}],
                    "converted_asset": {"file_path": str(converted_path)},
                }
            ),
            encoding="utf-8",
        )
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(extraction_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        extraction_runner,
        "shutdown_icad_without_saving",
        lambda **kwargs: shutdown_calls.append(True),
    )

    result = extraction_runner.run_icad_converter(
        drawing=drawing,
        output_format="step",
        output_dir=tmp_path / "converted",
    )

    assert result.converted_file_path == tmp_path / "converted" / "source.step"
    assert shutdown_calls == [True]


def test_shutdown_icad_without_saving_raises_when_runner_fails(monkeypatch, settings):
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = "runner.exe"
    monkeypatch.setattr(
        extraction_runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b"close failed"),
    )

    with pytest.raises(ExtractionRunnerError, match="close failed"):
        extraction_runner.shutdown_icad_without_saving()


def test_converter_timeout_before_asset_closes_autostarted_icad_and_raises(monkeypatch, settings, tmp_path):
    source = tmp_path / "source.icd"
    source.write_bytes(b"icad")
    drawing = RegisteredDrawing(
        filename="source.icd",
        source_path=str(source),
        source_format="icad",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = "runner.exe"
    shutdown_calls: list[bool] = []

    def fake_run(command, **kwargs):
        output_path = Path(command[command.index("--output-path") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"icad_autostarted": True, "completed": False}),
            encoding="utf-8",
        )
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(extraction_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        extraction_runner,
        "shutdown_icad_without_saving",
        lambda **kwargs: shutdown_calls.append(True),
    )

    with pytest.raises(ExtractionRunnerError, match="ICAD CAD conversion timed out"):
        extraction_runner.run_icad_converter(
            drawing=drawing,
            output_format="step",
            output_dir=tmp_path / "converted",
            shutdown_icad_if_autostarted=False,
        )

    assert shutdown_calls == [True]


@pytest.mark.django_db
def test_extractor_batch_timeout_closes_only_autostarted_icad(monkeypatch, settings, tmp_path):
    source = tmp_path / "source.icd"
    source.write_bytes(b"icad")
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="source-host",
        filename="source.icd",
        source_path=str(source),
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_PROCESSING,
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = "runner.exe"
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 1
    settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS = 1
    shutdown_calls: list[bool] = []

    def fake_run(command, **kwargs):
        result_path = Path(command[command.index("--result-json") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps({"icad_autostarted": True, "completed": False, "results": []}),
            encoding="utf-8",
        )
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(extraction_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        extraction_runner,
        "shutdown_icad_without_saving",
        lambda **kwargs: shutdown_calls.append(True),
    )

    with pytest.raises(ExtractionRunnerError, match="extractor batch timed out"):
        extraction_runner.run_extractor_batch([job])

    assert shutdown_calls == [True]
