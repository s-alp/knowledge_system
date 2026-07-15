import subprocess

import pytest

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.extraction_runner import (
    ExtractionRunnerError,
    build_extractor_command,
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
def test_build_extractor_command_uses_extraction_mode_and_icad_options(settings):
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

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="2d",
        output_path="C:\\temp\\out.json",
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
