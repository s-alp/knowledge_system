from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from django.conf import settings

from apps.drawing_metadata.models import DrawingMetadataExtractionJob, RegisteredDrawing
from apps.drawing_metadata.services.generic_cad_extractor import extract_generic_cad_metadata
from apps.drawing_metadata.services.path_constraints import requires_sxnet_staged_input
from apps.drawing_metadata.services.source_formats import uses_generic_cad_extractor, uses_sxnet_extractor


class ExtractionRunnerError(RuntimeError):
    pass


@dataclass(slots=True)
class ExtractionRunResult:
    payload: dict
    output_path: Path


@dataclass(slots=True)
class BatchExtractionRunResult:
    job_id: str
    payload: dict | None
    output_path: Path
    error_message: str


@dataclass(slots=True)
class CadConversionRunResult:
    payload: dict
    output_path: Path
    converted_file_path: Path | None


@dataclass(slots=True)
class CadExportTypeProbeRunResult:
    payload: dict
    output_path: Path


def _decode_runner_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    for encoding in ("utf-8", "cp932"):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("utf-8", errors="replace")


def icad_was_autostarted(payload: dict | None) -> bool:
    if not payload:
        return False
    if payload.get("icad_autostarted") is True:
        return True
    return any(
        isinstance(warning, dict) and warning.get("code") == "icad_autostarted"
        for warning in (payload.get("warnings") or [])
    )


def shutdown_icad_without_saving(*, timeout_seconds: int = 30) -> None:
    executable = settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE
    if not executable:
        raise ExtractionRunnerError(
            "DRAWING_METADATA_EXTRACTOR_EXECUTABLE が未設定のため、ICADを保存せず終了できません。"
        )
    command = [executable, "shutdown-icad", "--timeout-seconds", str(max(timeout_seconds, 1))]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=max(timeout_seconds, 1) + 15,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionRunnerError(
            f"ICADの保存なし終了が{max(timeout_seconds, 1)}秒以内に完了しませんでした: {exc.cmd}"
        ) from exc
    if completed.returncode != 0:
        stderr = _decode_runner_output(completed.stderr).strip()
        stdout = _decode_runner_output(completed.stdout).strip()
        raise ExtractionRunnerError(
            stderr or stdout or f"ICADの保存なし終了に失敗しました: exit code {completed.returncode}"
        )


def _load_json_if_available(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _shutdown_autostarted_icad_from_result(path: Path) -> None:
    if icad_was_autostarted(_load_json_if_available(path)):
        shutdown_icad_without_saving()


def build_extractor_command(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    output_path: Path,
    job_id=None,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
) -> list[str]:
    if not uses_sxnet_extractor(drawing.source_format):
        raise ExtractionRunnerError(
            f"{drawing.source_format} はSXNET抽出器の対象外です。"
            "STEP/DXFはDjango側の汎用CAD抽出器で処理してください。"
        )

    executable = settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE
    if not executable:
        raise ExtractionRunnerError(
            "DRAWING_METADATA_EXTRACTOR_EXECUTABLE が未設定です。Django 自体は Linux でも動作できますが、"
            "sxnet を使う C# 抽出器は Windows 側に分離して設定してください。"
        )
    command = [
        executable,
        "extract",
        "--input-path",
        drawing.source_path,
        "--source-kind",
        extraction_mode,
        "--output-path",
        str(output_path),
        "--extraction-profile",
        extraction_profile or "default",
        "--extraction-options-json",
        json.dumps(extraction_options or {}, ensure_ascii=False, separators=(",", ":")),
    ]
    if settings.DRAWING_METADATA_SXNET_DLL_PATH:
        command.extend(["--sxnet-dll-path", settings.DRAWING_METADATA_SXNET_DLL_PATH])
    if settings.DRAWING_METADATA_ICAD_EXECUTABLE:
        command.extend(["--icad-executable-path", settings.DRAWING_METADATA_ICAD_EXECUTABLE])
        command.extend(["--icad-startup-wait-seconds", str(settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS)])
        command.extend(
            [
                "--shutdown-icad-if-autostarted",
                "true" if settings.DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED else "false",
            ]
        )
    if (
        _is_uploaded_icad_source(drawing.source_path)
        or requires_sxnet_staged_input(
            drawing.source_path,
            filename=drawing.filename,
        )
        or _requires_2d_non_ascii_staged_input(drawing.source_path, extraction_mode=extraction_mode)
    ):
        command.extend(["--force-sxnet-staged-input", "true"])
    if job_id is not None:
        preview_output_dir = settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)
        preview_base_url = settings.DRAWING_METADATA_PREVIEW_ASSET_BASE_URL.rstrip("/") + f"/{quote(str(job_id))}"
        command.extend(["--preview-output-dir", str(preview_output_dir)])
        command.extend(["--preview-public-base-url", preview_base_url])
        command.extend(["--preview-file-name-prefix", str(job_id)])
    return command


def _raw_extract_output_path(job_id) -> Path:
    output_root = settings.DRAWING_METADATA_STORAGE_ROOT / "raw_extracts"
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / f"{job_id}.json"


def _preview_asset_options_payload(job_id) -> dict:
    preview_output_dir = settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)
    preview_base_url = settings.DRAWING_METADATA_PREVIEW_ASSET_BASE_URL.rstrip("/") + f"/{quote(str(job_id))}"
    return {
        "enabled": True,
        "output_directory": str(preview_output_dir),
        "public_base_url": preview_base_url,
        "file_name_prefix": str(job_id),
    }


def _force_sxnet_staged_input(drawing: RegisteredDrawing, extraction_mode: str) -> bool:
    return (
        _is_uploaded_icad_source(drawing.source_path)
        or requires_sxnet_staged_input(
            drawing.source_path,
            filename=drawing.filename,
        )
        or _requires_2d_non_ascii_staged_input(drawing.source_path, extraction_mode=extraction_mode)
    )


def build_batch_extractor_command(*, jobs_json_path: Path, result_json_path: Path) -> list[str]:
    executable = settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE
    if not executable:
        raise ExtractionRunnerError(
            "DRAWING_METADATA_EXTRACTOR_EXECUTABLE が未設定です。Django 自体は Linux でも動作できますが、"
            "sxnet を使う C# 抽出器は Windows 側に分離して設定してください。"
        )
    command = [
        executable,
        "extract-batch",
        "--jobs-json",
        str(jobs_json_path),
        "--result-json",
        str(result_json_path),
    ]
    if settings.DRAWING_METADATA_SXNET_DLL_PATH:
        command.extend(["--sxnet-dll-path", settings.DRAWING_METADATA_SXNET_DLL_PATH])
    if settings.DRAWING_METADATA_ICAD_EXECUTABLE:
        command.extend(["--icad-executable-path", settings.DRAWING_METADATA_ICAD_EXECUTABLE])
        command.extend(["--icad-startup-wait-seconds", str(settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS)])
        command.extend(
            [
                "--shutdown-icad-if-autostarted",
                "true" if settings.DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED else "false",
            ]
        )
    return command


def build_icad_converter_command(
    *,
    drawing: RegisteredDrawing,
    output_format: str,
    output_dir: Path,
    output_path: Path,
    output_base_name: str | None = None,
    export_file_type: int | None = None,
    step_export_file_type: int | None = None,
    dxf_export_file_type: int | None = None,
    shutdown_icad_if_autostarted: bool | None = None,
) -> list[str]:
    if not uses_sxnet_extractor(drawing.source_format):
        raise ExtractionRunnerError(f"{drawing.source_format} はICAD変換コマンドの対象外です。")

    executable = settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE
    if not executable:
        raise ExtractionRunnerError(
            "DRAWING_METADATA_EXTRACTOR_EXECUTABLE が未設定です。ICADからDXF/STEPへの変換はWindows側のC# runnerで実行してください。"
        )
    command = [
        executable,
        "convert-cad",
        "--input-path",
        drawing.source_path,
        "--output-path",
        str(output_path),
        "--output-dir",
        str(output_dir),
        "--output-format",
        output_format,
    ]
    if settings.DRAWING_METADATA_SXNET_DLL_PATH:
        command.extend(["--sxnet-dll-path", settings.DRAWING_METADATA_SXNET_DLL_PATH])
    if settings.DRAWING_METADATA_ICAD_EXECUTABLE:
        command.extend(["--icad-executable-path", settings.DRAWING_METADATA_ICAD_EXECUTABLE])
        command.extend(["--icad-startup-wait-seconds", str(settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS)])
    should_shutdown = (
        settings.DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED
        if shutdown_icad_if_autostarted is None
        else shutdown_icad_if_autostarted
    )
    command.extend(["--shutdown-icad-if-autostarted", "true" if should_shutdown else "false"])
    if _force_sxnet_staged_input(drawing, "2d" if output_format.lower().lstrip(".") == "dxf" else "3d"):
        command.extend(["--force-sxnet-staged-input", "true"])
    if output_base_name:
        command.extend(["--output-base-name", output_base_name])
    resolved_export_file_type = _resolve_cad_export_file_type(
        output_format=output_format,
        export_file_type=export_file_type,
        step_export_file_type=step_export_file_type,
        dxf_export_file_type=dxf_export_file_type,
    )
    if resolved_export_file_type is not None:
        command.extend(["--export-file-type", str(resolved_export_file_type)])
    return command


def _resolve_cad_export_file_type(
    *,
    output_format: str,
    export_file_type: int | None,
    step_export_file_type: int | None,
    dxf_export_file_type: int | None,
) -> int | None:
    normalized_format = output_format.lower().lstrip(".")
    if normalized_format == "stp":
        normalized_format = "step"
    specific_value = None
    if normalized_format == "step":
        specific_value = step_export_file_type
    elif normalized_format == "dxf":
        specific_value = dxf_export_file_type
    return specific_value if specific_value is not None else export_file_type


def build_icad_export_type_probe_command(*, output_path: Path) -> list[str]:
    executable = settings.DRAWING_METADATA_EXTRACTOR_EXECUTABLE
    if not executable:
        raise ExtractionRunnerError(
            "DRAWING_METADATA_EXTRACTOR_EXECUTABLE が未設定です。SXNET export 定数の確認はWindows側のC# runnerで実行してください。"
        )
    sxnet_dll_path = settings.DRAWING_METADATA_SXNET_DLL_PATH
    if not sxnet_dll_path:
        raise ExtractionRunnerError("DRAWING_METADATA_SXNET_DLL_PATH が未設定です。")
    return [
        executable,
        "probe-cad-export-types",
        "--sxnet-dll-path",
        sxnet_dll_path,
        "--output-path",
        str(output_path),
    ]


def _is_uploaded_icad_source(source_path: str) -> bool:
    upload_root = (settings.DRAWING_METADATA_STORAGE_ROOT / "uploads").resolve(strict=False)
    source = Path(source_path).resolve(strict=False)
    try:
        source.relative_to(upload_root)
    except ValueError:
        return False
    return True


def _requires_2d_non_ascii_staged_input(source_path: str, *, extraction_mode: str) -> bool:
    if extraction_mode != "2d":
        return False
    return any(ord(char) > 127 for char in source_path)


def run_extractor(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    job_id,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
) -> ExtractionRunResult:
    output_path = _raw_extract_output_path(job_id)

    if uses_generic_cad_extractor(drawing.source_format):
        payload = extract_generic_cad_metadata(
            input_path=drawing.source_path,
            source_format=drawing.source_format,
            source_kind=extraction_mode,
            output_path=output_path,
            extraction_profile=extraction_profile,
            extraction_options=extraction_options,
        )
        return ExtractionRunResult(payload=payload, output_path=output_path)

    command = build_extractor_command(
        drawing=drawing,
        extraction_mode=extraction_mode,
        output_path=output_path,
        job_id=job_id,
        extraction_profile=extraction_profile,
        extraction_options=extraction_options,
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        try:
            _shutdown_autostarted_icad_from_result(output_path)
        except ExtractionRunnerError as shutdown_error:
            raise ExtractionRunnerError(
                f"extractor timed out after {settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS} seconds"
                f" and ICAD cleanup failed: {shutdown_error}"
            ) from shutdown_error
        raise ExtractionRunnerError(
            f"extractor timed out after {settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS} seconds: {exc.cmd}"
        ) from exc
    if completed.returncode != 0:
        stderr = _decode_runner_output(completed.stderr).strip()
        stdout = _decode_runner_output(completed.stdout).strip()
        raise ExtractionRunnerError(stderr or stdout or f"extractor failed with exit code {completed.returncode}")

    if not output_path.exists():
        raise ExtractionRunnerError(f"抽出 JSON が生成されませんでした: {output_path}")

    return ExtractionRunResult(payload=json.loads(output_path.read_text(encoding="utf-8")), output_path=output_path)


def run_icad_converter(
    *,
    drawing: RegisteredDrawing,
    output_format: str,
    output_dir: Path,
    output_base_name: str | None = None,
    export_file_type: int | None = None,
    step_export_file_type: int | None = None,
    dxf_export_file_type: int | None = None,
    conversion_id=None,
    shutdown_icad_if_autostarted: bool | None = None,
) -> CadConversionRunResult:
    conversion_id = conversion_id or uuid.uuid4()
    output_path = settings.DRAWING_METADATA_STORAGE_ROOT / "cad_conversions" / f"{conversion_id}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_icad_converter_command(
        drawing=drawing,
        output_format=output_format,
        output_dir=output_dir,
        output_path=output_path,
        output_base_name=output_base_name,
        export_file_type=export_file_type,
        step_export_file_type=step_export_file_type,
        dxf_export_file_type=dxf_export_file_type,
        shutdown_icad_if_autostarted=shutdown_icad_if_autostarted,
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        if output_path.exists():
            result = _read_cad_conversion_result(output_path)
            if icad_was_autostarted(result.payload):
                shutdown_icad_without_saving()
            if result.converted_file_path is not None:
                return result
        raise ExtractionRunnerError(
            f"ICAD CAD conversion timed out after {settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS} seconds: {exc.cmd}"
        ) from exc
    if completed.returncode != 0:
        partial_payload = _load_json_if_available(output_path)
        if icad_was_autostarted(partial_payload):
            shutdown_icad_without_saving()
        stderr = _decode_runner_output(completed.stderr).strip()
        stdout = _decode_runner_output(completed.stdout).strip()
        raise ExtractionRunnerError(stderr or stdout or f"ICAD CAD conversion failed with exit code {completed.returncode}")
    if not output_path.exists():
        raise ExtractionRunnerError(f"変換結果 JSON が生成されませんでした: {output_path}")

    return _read_cad_conversion_result(output_path)


def _read_cad_conversion_result(output_path: Path) -> CadConversionRunResult:
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    asset = payload.get("converted_asset") or {}
    converted_file_path = Path(asset["file_path"]) if asset.get("file_path") else None
    return CadConversionRunResult(payload=payload, output_path=output_path, converted_file_path=converted_file_path)


def run_icad_export_type_probe(*, output_path: Path | None = None, probe_id=None) -> CadExportTypeProbeRunResult:
    if output_path is None:
        probe_id = probe_id or uuid.uuid4()
        output_path = settings.DRAWING_METADATA_STORAGE_ROOT / "cad_conversions" / f"export-type-probe-{probe_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_icad_export_type_probe_command(output_path=output_path)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionRunnerError(
            f"ICAD CAD export type probe timed out after {settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS} seconds: {exc.cmd}"
        ) from exc
    if completed.returncode != 0:
        stderr = _decode_runner_output(completed.stderr).strip()
        stdout = _decode_runner_output(completed.stdout).strip()
        raise ExtractionRunnerError(stderr or stdout or f"ICAD CAD export type probe failed with exit code {completed.returncode}")
    if not output_path.exists():
        raise ExtractionRunnerError(f"export type probe JSON が生成されませんでした: {output_path}")

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return CadExportTypeProbeRunResult(payload=payload, output_path=output_path)


def run_extractor_batch(jobs: Iterable[DrawingMetadataExtractionJob]) -> list[BatchExtractionRunResult]:
    job_list = list(jobs)
    if not job_list:
        return []

    for job in job_list:
        if not uses_sxnet_extractor(job.drawing.source_format):
            raise ExtractionRunnerError(
                f"{job.drawing.source_format} はSXNET抽出器の一括処理対象外です。"
                "STEP/DXFはDjango側の汎用CAD抽出器で処理してください。"
            )

    batch_root = settings.DRAWING_METADATA_STORAGE_ROOT / "batch_jobs"
    batch_root.mkdir(parents=True, exist_ok=True)
    batch_id = uuid.uuid4()
    jobs_json_path = batch_root / f"{batch_id}.jobs.json"
    result_json_path = batch_root / f"{batch_id}.result.json"
    request_payload = {
        "jobs": [
            {
                "job_id": str(job.id),
                "input_path": job.drawing.source_path,
                "source_kind": job.extraction_mode,
                "output_path": str(_raw_extract_output_path(job.id)),
                "extraction_profile": job.extraction_profile or "default",
                "extraction_options": job.extraction_options_json or {},
                "preview_asset_options": _preview_asset_options_payload(job.id),
                "force_sxnet_staged_input": _force_sxnet_staged_input(job.drawing, job.extraction_mode),
            }
            for job in job_list
        ]
    }
    jobs_json_path.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    command = build_batch_extractor_command(jobs_json_path=jobs_json_path, result_json_path=result_json_path)
    timeout_seconds = (
        settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS * len(job_list)
        + settings.DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS
        + 60
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        try:
            _shutdown_autostarted_icad_from_result(result_json_path)
        except ExtractionRunnerError as shutdown_error:
            raise ExtractionRunnerError(
                f"extractor batch timed out after {timeout_seconds} seconds"
                f" and ICAD cleanup failed: {shutdown_error}"
            ) from shutdown_error
        raise ExtractionRunnerError(f"extractor batch timed out after {timeout_seconds} seconds: {exc.cmd}") from exc

    batch_payload = _load_json_if_available(result_json_path)
    if completed.returncode != 0 and not batch_payload.get("completed"):
        stderr = _decode_runner_output(completed.stderr).strip()
        stdout = _decode_runner_output(completed.stdout).strip()
        raise ExtractionRunnerError(stderr or stdout or f"extractor batch failed with exit code {completed.returncode}")

    if not result_json_path.exists():
        raise ExtractionRunnerError(f"一括抽出の結果 JSON が生成されませんでした: {result_json_path}")

    raw_results = batch_payload.get("results") or []
    results_by_job_id = {str(item.get("job_id") or ""): item for item in raw_results}
    batch_results: list[BatchExtractionRunResult] = []
    for job in job_list:
        job_id = str(job.id)
        item = results_by_job_id.get(job_id)
        output_path = _raw_extract_output_path(job.id)
        if not item:
            batch_results.append(
                BatchExtractionRunResult(
                    job_id=job_id,
                    payload=None,
                    output_path=output_path,
                    error_message="一括抽出結果にジョブ別結果が含まれていません。",
                )
            )
            continue
        output_path = Path(str(item.get("output_path") or output_path))
        error_message = str(item.get("error_message") or "")
        if not item.get("succeeded"):
            batch_results.append(
                BatchExtractionRunResult(
                    job_id=job_id,
                    payload=None,
                    output_path=output_path,
                    error_message=error_message or "一括抽出でジョブが失敗しました。",
                )
            )
            continue
        if not output_path.exists():
            batch_results.append(
                BatchExtractionRunResult(
                    job_id=job_id,
                    payload=None,
                    output_path=output_path,
                    error_message=f"抽出 JSON が生成されませんでした: {output_path}",
                )
            )
            continue
        batch_results.append(
            BatchExtractionRunResult(
                job_id=job_id,
                payload=json.loads(output_path.read_text(encoding="utf-8")),
                output_path=output_path,
                error_message="",
            )
        )
    return batch_results
