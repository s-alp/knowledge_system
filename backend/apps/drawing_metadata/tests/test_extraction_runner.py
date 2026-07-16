import subprocess
from pathlib import Path

import pytest

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.extraction_runner import (
    ExtractionRunnerError,
    build_extractor_command,
    _decode_runner_output,
    run_extractor,
)


@pytest.mark.django_db
def test_run_extractor_wraps_timeout(monkeypatch, settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-timeout",
        filename="sample.icd",
        source_path=r"C:\temp\sample.icd",
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"
    settings.DRAWING_METADATA_SXNET_DLL_PATH = r"C:\ICADSX\bin\sxnet.dll"
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 3

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", args[0]), timeout=3)

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    with pytest.raises(ExtractionRunnerError) as exc_info:
        run_extractor(drawing=drawing, extraction_mode="3d", job_id="timeout-job")

    assert "timed out" in str(exc_info.value)


@pytest.mark.django_db
def test_run_extractor_decodes_runner_stderr(monkeypatch, settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-runner-error",
        filename="sample.icd",
        source_path=r"C:\temp\sample.icd",
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"
    settings.DRAWING_METADATA_SXNET_DLL_PATH = r"C:\ICADSX\bin\sxnet.dll"
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 3

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=kwargs.get("args", args[0]),
            returncode=1,
            stderr="指定したファイルは図面ファイルではありません。".encode("utf-8"),
            stdout=b"",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExtractionRunnerError, match="図面ファイルではありません"):
        run_extractor(drawing=drawing, extraction_mode="3d", job_id="runner-error-job")


def test_decode_runner_output_accepts_cp932_stderr():
    assert _decode_runner_output("指定したファイルは図面ファイルではありません。".encode("cp932")) == (
        "指定したファイルは図面ファイルではありません。"
    )


@pytest.mark.django_db
def test_build_extractor_command_forces_staged_input_for_too_long_path(settings):
    long_source_path = "C:\\" + "\\".join(["segment"] * 40) + "\\sample.icd"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-long-path",
        filename="sample.icd",
        source_path=long_source_path,
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="3d",
        output_path=Path(r"C:\temp\out.json"),
    )

    force_index = command.index("--force-sxnet-staged-input")
    assert command[force_index + 1] == "true"


@pytest.mark.django_db
def test_build_extractor_command_uses_extraction_mode_icad_options_and_preview_assets(settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-command",
        filename="sample.icd",
        source_path=r"C:\temp\sample.icd",
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"
    settings.DRAWING_METADATA_SXNET_DLL_PATH = r"C:\ICADSX\bin\sxnet.dll"
    settings.DRAWING_METADATA_ICAD_EXECUTABLE = r"C:\ICADSX\bin\icad.exe"
    settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS = 8
    settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT = Path(r"C:\temp\drawing_metadata_preview_assets")
    settings.DRAWING_METADATA_PREVIEW_ASSET_BASE_URL = "/api/v1/drawing-metadata-preview-assets"

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="2d",
        output_path=Path(r"C:\temp\out.json"),
        job_id="11111111-1111-1111-1111-111111111111",
        extraction_profile="2d_all_views_layers_print_frame",
        extraction_options={"scanAllViews": True, "scanAllLayers": True},
    )

    assert "--source-kind" in command
    assert "2d" in command
    assert "--extraction-profile" in command
    assert "2d_all_views_layers_print_frame" in command
    assert "--extraction-options-json" in command
    assert '{"scanAllViews":true,"scanAllLayers":true}' in command
    assert "--icad-executable-path" in command
    assert "--preview-output-dir" in command
    assert r"C:\temp\drawing_metadata_preview_assets\11111111-1111-1111-1111-111111111111" in command
    assert "--preview-public-base-url" in command
    assert "/api/v1/drawing-metadata-preview-assets/11111111-1111-1111-1111-111111111111" in command
    assert "--preview-file-name-prefix" in command
    assert "11111111-1111-1111-1111-111111111111" in command
    assert "--force-sxnet-staged-input" not in command


@pytest.mark.django_db
def test_build_extractor_command_forces_staged_input_for_uploaded_icad(settings, tmp_path):
    storage_root = tmp_path / "drawing_metadata"
    uploaded_path = storage_root / "uploads" / "upload-id" / "sample.icd"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-uploaded-command",
        filename="sample.icd",
        source_path=str(uploaded_path),
        source_format="icad",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = storage_root
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="3d",
        output_path=Path(r"C:\temp\out.json"),
    )

    force_index = command.index("--force-sxnet-staged-input")
    assert command[force_index + 1] == "true"
