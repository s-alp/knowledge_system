from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from django.conf import settings

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.path_constraints import requires_sxnet_staged_input


class ExtractionRunnerError(RuntimeError):
    pass


@dataclass(slots=True)
class ExtractionRunResult:
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


def build_extractor_command(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    output_path: Path,
    job_id=None,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
) -> list[str]:
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
    if _is_uploaded_icad_source(drawing.source_path) or requires_sxnet_staged_input(
        drawing.source_path,
        filename=drawing.filename,
    ):
        command.extend(["--force-sxnet-staged-input", "true"])
    if job_id is not None:
        preview_output_dir = settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)
        preview_base_url = settings.DRAWING_METADATA_PREVIEW_ASSET_BASE_URL.rstrip("/") + f"/{quote(str(job_id))}"
        command.extend(["--preview-output-dir", str(preview_output_dir)])
        command.extend(["--preview-public-base-url", preview_base_url])
        command.extend(["--preview-file-name-prefix", str(job_id)])
    return command


def _is_uploaded_icad_source(source_path: str) -> bool:
    upload_root = (settings.DRAWING_METADATA_STORAGE_ROOT / "uploads").resolve(strict=False)
    source = Path(source_path).resolve(strict=False)
    try:
        source.relative_to(upload_root)
    except ValueError:
        return False
    return True


def run_extractor(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    job_id,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
) -> ExtractionRunResult:
    output_root = settings.DRAWING_METADATA_STORAGE_ROOT / "raw_extracts"
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{job_id}.json"

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
