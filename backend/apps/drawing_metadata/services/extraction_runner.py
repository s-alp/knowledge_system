from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from apps.drawing_metadata.models import RegisteredDrawing


class ExtractionRunnerError(RuntimeError):
    pass


@dataclass(slots=True)
class ExtractionRunResult:
    payload: dict
    output_path: Path


def build_extractor_command(*, drawing: RegisteredDrawing, extraction_mode: str, output_path: Path) -> list[str]:
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


def run_extractor(*, drawing: RegisteredDrawing, extraction_mode: str, job_id) -> ExtractionRunResult:
    output_root = settings.DRAWING_METADATA_STORAGE_ROOT / "raw_extracts"
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{job_id}.json"

    command = build_extractor_command(drawing=drawing, extraction_mode=extraction_mode, output_path=output_path)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionRunnerError(
            f"extractor timed out after {settings.DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS} seconds: {exc.cmd}"
        ) from exc
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise ExtractionRunnerError(stderr or stdout or f"extractor failed with exit code {completed.returncode}")

    if not output_path.exists():
        raise ExtractionRunnerError(f"抽出 JSON が生成されませんでした: {output_path}")

    return ExtractionRunResult(payload=json.loads(output_path.read_text(encoding="utf-8")), output_path=output_path)
