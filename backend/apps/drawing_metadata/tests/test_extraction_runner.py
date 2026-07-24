import json
import subprocess
from pathlib import Path

import pytest

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.models import DrawingMetadataExtractionJob
from apps.drawing_metadata.services.extraction_runner import (
    ExtractionRunnerError,
    build_extractor_command,
    _decode_runner_output,
    run_extractor,
    run_extractor_batch,
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
def test_build_extractor_command_rejects_non_icad_source_for_sxnet_command(settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-step",
        filename="sample.step",
        source_path=r"C:\temp\sample.step",
        source_format="step",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"

    with pytest.raises(ExtractionRunnerError, match="汎用CAD抽出器"):
        build_extractor_command(
            drawing=drawing,
            extraction_mode="3d",
            output_path=Path(r"C:\temp\out.json"),
        )


@pytest.mark.django_db
def test_run_extractor_extracts_step_metadata_without_sxnet(settings, tmp_path):
    source_path = tmp_path / "GANTRY_HAND.step"
    source_path.write_text(
        """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('SUS304 浸炭 HRC58-62'),'2;1');
FILE_NAME('GANTRY_HAND','2026-07-23',('SMC'),('コマツ小山'),'preprocessor','system','');
ENDSEC;
DATA;
#10=PRODUCT('GANTRY HAND','SMC CYLINDER','',(#1));
ENDSEC;
END-ISO-10303-21;
""",
        encoding="utf-8",
    )
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-step",
        filename="GANTRY_HAND.step",
        source_path=str(source_path),
        source_format="step",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"

    result = run_extractor(drawing=drawing, extraction_mode="3d", job_id="step-job")

    assert result.output_path.exists()
    assert result.payload["source_format"] == "step"
    assert result.payload["source_kind"] == "3d"
    assert result.payload["extractor_name"] == "generic-cad-text-extractor"
    assert result.payload["raw_extract"]["materials"] == ["SUS304"]
    assert any(part["name"] == "GANTRY HAND" for part in result.payload["raw_extract"]["parts"])


@pytest.mark.django_db
def test_run_extractor_extracts_dxf_text_metadata_without_sxnet(settings, tmp_path):
    source_path = tmp_path / "layout.dxf"
    source_path.write_text(
        "0\nSECTION\n2\nENTITIES\n"
        "0\nTEXT\n8\nTITLE\n10\n1.0\n20\n2.0\n1\n材質 SS400\n"
        "0\nMTEXT\n8\nNOTE\n10\n3.0\n20\n4.0\n1\nPRFX RAA4844\\PSES\n"
        "0\nCIRCLE\n8\nHOLE\n10\n5.0\n20\n6.0\n40\n3.0\n"
        "0\nENDSEC\n0\nEOF\n",
        encoding="utf-8",
    )
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-dxf",
        filename="layout.dxf",
        source_path=str(source_path),
        source_format="dxf",
    )
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"

    result = run_extractor(drawing=drawing, extraction_mode="2d", job_id="dxf-job")

    texts = result.payload["raw_extract"]["texts"]
    assert result.output_path.exists()
    assert result.payload["source_format"] == "dxf"
    assert result.payload["source_kind"] == "2d"
    assert [item["joined_text"] for item in texts] == ["材質 SS400", "PRFX RAA4844 SES"]
    assert result.payload["raw_extract"]["geometry_primitives"][0]["geometry_type"] == "DxfCircle"


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
def test_build_extractor_command_forces_staged_input_for_legacy_too_long_filename(settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-long-filename",
        filename=f"{'A' * 256}.icd",
        source_path=r"C:\temp\sample.icd",
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
def test_build_extractor_command_forces_staged_input_for_2d_non_ascii_path(settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-2d-non-ascii",
        filename="sample.icd",
        source_path=r"J:\不二越5\sample.icd",
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="2d",
        output_path=Path(r"C:\temp\out.json"),
    )

    force_index = command.index("--force-sxnet-staged-input")
    assert command[force_index + 1] == "true"


@pytest.mark.django_db
def test_build_extractor_command_does_not_force_staged_input_for_3d_non_ascii_path(settings):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-3d-non-ascii",
        filename="sample.icd",
        source_path=r"J:\不二越5\sample.icd",
        source_format="icad",
    )
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode="3d",
        output_path=Path(r"C:\temp\out.json"),
    )

    assert "--force-sxnet-staged-input" not in command


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
    # パス結合はOSのセパレータに依存するため、実装と同じ Path 結合で期待値を作る
    # (Windows実機でもLinux CI/Cloud検証でも同じテストが通るようにする)。
    expected_preview_dir = str(Path(r"C:\temp\drawing_metadata_preview_assets") / "11111111-1111-1111-1111-111111111111")
    assert expected_preview_dir in command
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


@pytest.mark.django_db
def test_run_extractor_batch_invokes_batch_command_and_maps_job_results(monkeypatch, settings, tmp_path):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-batch",
        filename="sample.icd",
        source_path=r"C:\temp\sample.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(drawing=drawing, extraction_mode="3d")
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path / "metadata"
    settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT = tmp_path / "previews"
    settings.DRAWING_METADATA_PREVIEW_ASSET_BASE_URL = "/preview"
    settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE = r"C:\temp\runner.exe"
    settings.DRAWING_METADATA_SXNET_DLL_PATH = r"C:\ICADSX\bin\sxnet.dll"
    settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS = 3
    settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS = 1

    def fake_run(command, **kwargs):
        assert command[1] == "extract-batch"
        jobs_json_path = Path(command[command.index("--jobs-json") + 1])
        result_json_path = Path(command[command.index("--result-json") + 1])
        request_payload = json.loads(jobs_json_path.read_text(encoding="utf-8"))
        item = request_payload["jobs"][0]
        output_path = Path(item["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "warnings": [],
                    "raw_extract": {},
                    "elapsed_ms": 12,
                    "extractor_name": "fake-batch",
                    "extractor_version": "1.0.0",
                }
            ),
            encoding="utf-8",
        )
        result_json_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "job_id": item["job_id"],
                            "output_path": item["output_path"],
                            "succeeded": True,
                            "error_message": "",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    results = run_extractor_batch([job])

    assert len(results) == 1
    assert results[0].job_id == str(job.id)
    assert results[0].payload["extractor_name"] == "fake-batch"
    assert results[0].error_message == ""
