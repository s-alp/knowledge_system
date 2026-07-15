from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("output/souya_handoff/icad_extract_import_manifest_reextract_2026-07-15.json")
DEFAULT_OUTPUT_ROOT = Path("output/live_extracts/preview_asset_probe_2026-07-15")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_backend_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _selected_3d_sources(manifest: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if not entry.get("has3d"):
            continue
        selected.append(
            {
                "sourcePath": entry.get("sourcePath"),
                "filename": entry.get("filename"),
                "customerHint": entry.get("customerHint"),
                "has2d": bool(entry.get("has2d")),
                "has3d": bool(entry.get("has3d")),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _safe_name(index: int, filename: str | None) -> str:
    stem = Path(filename or f"sample-{index:02d}").stem
    invalid = '<>:"/\\|?*'
    sanitized = "".join("_" if character in invalid else character for character in stem).strip(". ")
    return f"{index:02d}_{sanitized or 'sample'}"


def _run_one(
    *,
    runner: str,
    sxnet_dll: str,
    icad_executable: str,
    sample: dict[str, Any],
    index: int,
    output_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    source_path = str(sample["sourcePath"])
    safe_name = _safe_name(index, sample.get("filename"))
    asset_dir = output_root / "assets" / safe_name
    asset_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{safe_name}.3d.preview.json"
    public_base_url = f"/api/v1/drawing-metadata-preview-assets/{safe_name}"

    command = [
        runner,
        "extract",
        "--input-path",
        source_path,
        "--source-kind",
        "3d",
        "--output-path",
        str(output_path),
        "--sxnet-dll-path",
        sxnet_dll,
        "--icad-executable-path",
        icad_executable,
        "--icad-startup-wait-seconds",
        "8",
        "--shutdown-icad-if-autostarted",
        "true",
        "--extraction-profile",
        "3d_preview_asset_probe",
        "--preview-output-dir",
        str(asset_dir),
        "--preview-public-base-url",
        public_base_url,
        "--preview-file-name-prefix",
        safe_name,
    ]

    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    asset_files = [
        {"name": path.name, "sizeBytes": path.stat().st_size}
        for path in sorted(asset_dir.glob("*"))
        if path.is_file()
    ]

    payload: dict[str, Any] = {}
    viewer_assets: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if output_path.exists():
        payload = _load_json(output_path)
        raw_extract = payload.get("raw_extract", {}) or {}
        viewer_assets = (raw_extract.get("viewer_assets", {}) or {}).get("3d", []) or []
        warnings = payload.get("warnings", []) or []

    return {
        "sourcePath": source_path,
        "filename": sample.get("filename"),
        "customerHint": sample.get("customerHint"),
        "exitCode": completed.returncode,
        "elapsedMs": elapsed_ms,
        "outputPath": str(output_path),
        "outputExists": output_path.exists(),
        "assetDir": str(asset_dir),
        "assetFiles": asset_files,
        "viewerAssets": viewer_assets,
        "warnings": warnings,
        "stdoutTail": completed.stdout[-2000:],
        "stderrTail": completed.stderr[-2000:],
    }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    ready = 0
    failed = 0
    for result in results:
        assets = result.get("viewerAssets") or []
        if any(asset.get("status") == "ready" for asset in assets):
            ready += 1
        else:
            failed += 1
    return {
        "total": len(results),
        "ready": ready,
        "failed": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe SXNET STL preview asset export across real ICAD 3D samples.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--runner")
    parser.add_argument("--sxnet-dll")
    parser.add_argument("--icad-executable")
    args = parser.parse_args()

    backend_env = _load_backend_env(Path("backend/.env"))
    runner = args.runner or backend_env.get("DRAWING_METADATA_EXTRACTOR_EXECUTABLE")
    sxnet_dll = args.sxnet_dll or backend_env.get("DRAWING_METADATA_SXNET_DLL_PATH")
    icad_executable = args.icad_executable or backend_env.get("DRAWING_METADATA_ICAD_EXECUTABLE")
    missing = [
        name
        for name, value in (
            ("runner", runner),
            ("sxnet_dll", sxnet_dll),
            ("icad_executable", icad_executable),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"missing required settings: {', '.join(missing)}")

    manifest = _load_json(args.manifest)
    samples = _selected_3d_sources(manifest, args.limit)
    args.output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for index, sample in enumerate(samples, start=1):
        result = _run_one(
            runner=str(runner),
            sxnet_dll=str(sxnet_dll),
            icad_executable=str(icad_executable),
            sample=sample,
            index=index,
            output_root=args.output_root,
            timeout_seconds=args.timeout_seconds,
        )
        results.append(result)
        status = "ready" if any(asset.get("status") == "ready" for asset in result.get("viewerAssets", [])) else "failed"
        print(f"{index:02d} {status} {result['filename']} assets={len(result['assetFiles'])} exit={result['exitCode']}")

    report = {
        "schemaVersion": "icad_3d_preview_asset_probe.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "runner": str(runner),
        "sxnetDll": str(sxnet_dll),
        "icadExecutable": str(icad_executable),
        "summary": _summary(results),
        "results": results,
    }
    summary_path = args.output_root / "summary.json"
    summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
