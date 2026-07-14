from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


SCHEMA_VERSION = "icad_extract_import_manifest.v1"


def _load_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _mode(payload: dict, path: Path) -> str | None:
    source_kind = str(payload.get("source_kind") or "").lower()
    if source_kind in {"2d", "3d"}:
        return source_kind
    lowered = path.name.lower()
    if "_2d" in lowered or "-2d" in lowered or ".2d" in lowered:
        return "2d"
    if "_3d" in lowered or "-3d" in lowered or ".3d" in lowered:
        return "3d"
    return None


def _source_path(payload: dict) -> str | None:
    raw_extract = payload.get("raw_extract", {}) or {}
    source_file = payload.get("source_file", {}) or raw_extract.get("_source_file", {}) or {}
    value = payload.get("input_path") or source_file.get("full_path")
    return str(value) if value else None


def _customer_hint(source_path: str) -> str:
    parts = [part for part in PureWindowsPath(source_path).parts if part not in {"\\", "/"}]
    if len(parts) >= 2 and (parts[0].endswith(":") or parts[0].endswith(":\\") or parts[0].endswith(":/")):
        return parts[1]
    if len(parts) >= 3 and parts[0].startswith("\\\\"):
        return parts[2]
    return parts[0] if parts else "unknown"


def _count_part_ex_info(parts: list[dict]) -> int:
    return len([part for part in parts if part.get("ex_info_fields")])


def _metrics(payload: dict) -> dict:
    raw_extract = payload.get("raw_extract", {}) or {}
    parts = raw_extract.get("parts", []) or []
    texts = raw_extract.get("texts", []) or []
    dimensions = raw_extract.get("dimensions", []) or []
    primitives = raw_extract.get("geometry_primitives", []) or []
    print_frames = raw_extract.get("print_frames", []) or []
    layers = raw_extract.get("layers", []) or []
    view_sheets = raw_extract.get("view_sheets", []) or []
    materials = raw_extract.get("materials", []) or []
    mass_properties = raw_extract.get("mass_properties", {}) or {}
    return {
        "partCount": len(parts),
        "partExInfoCount": _count_part_ex_info(parts),
        "textCount": len(texts),
        "dimensionCount": len(dimensions),
        "primitiveCount": len(primitives),
        "printFrameCount": len(print_frames),
        "layerCount": len(layers),
        "viewSheetCount": len(view_sheets),
        "materialCount": len(materials),
        "hasMassProperties": bool(mass_properties),
        "warningCount": len(payload.get("warnings", []) or []),
    }


def _score(mode: str, path: Path, metrics: dict) -> int:
    lowered = path.name.lower()
    if mode == "2d":
        score = (
            metrics["textCount"]
            + metrics["dimensionCount"] * 2
            + metrics["primitiveCount"] * 3
            + metrics["printFrameCount"] * 15
            + metrics["layerCount"] * 4
            + metrics["viewSheetCount"] * 6
        )
        for keyword, bonus in (("allviews", 180), ("primitives", 140), ("v2meta", 120), ("layered", 80), ("positioned", 60)):
            if keyword in lowered:
                score += bonus
        return score

    score = (
        metrics["partCount"] * 3
        + metrics["partExInfoCount"] * 80
        + metrics["materialCount"] * 50
        + (120 if metrics["hasMassProperties"] else 0)
    )
    for keyword, bonus in (("part_ex_info", 220), ("material", 120), ("mass", 100)):
        if keyword in lowered:
            score += bonus
    return score


def _candidate(path: Path, payload: dict) -> dict | None:
    if not isinstance(payload.get("raw_extract"), dict):
        return None
    mode = _mode(payload, path)
    source_path = _source_path(payload)
    if not mode or not source_path:
        return None
    metrics = _metrics(payload)
    return {
        "mode": mode,
        "path": str(path),
        "score": _score(mode, path, metrics),
        "metrics": metrics,
        "extractorVersion": payload.get("extractor_version"),
        "sourceKind": payload.get("source_kind"),
    }


def _best_by_mode(candidates: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for candidate in candidates:
        mode = candidate["mode"]
        previous = best.get(mode)
        if previous is None or (candidate["score"], candidate["path"]) > (previous["score"], previous["path"]):
            best[mode] = candidate
    return best


def _entry_sort_key(entry: dict) -> tuple:
    has_pair = entry["has2d"] and entry["has3d"]
    total_score = sum(item["score"] for item in entry["selectedFiles"])
    has_part_ex = any(item["metrics"].get("partExInfoCount", 0) > 0 for item in entry["selectedFiles"])
    has_material = any(item["metrics"].get("materialCount", 0) > 0 for item in entry["selectedFiles"])
    return (has_pair, has_part_ex, has_material, total_score, entry["sourcePath"])


def _select_entries(entries: list[dict], max_drawings: int) -> list[dict]:
    selected: list[dict] = []
    seen_customers: set[str] = set()
    sorted_entries = sorted(entries, key=_entry_sort_key, reverse=True)

    for entry in sorted_entries:
        if entry["customerHint"] in seen_customers:
            continue
        selected.append(entry)
        seen_customers.add(entry["customerHint"])
        if len(selected) >= max_drawings:
            return selected

    for entry in sorted_entries:
        if entry in selected:
            continue
        selected.append(entry)
        if len(selected) >= max_drawings:
            return selected
    return selected


def build_manifest(input_roots: list[Path], max_drawings: int) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    scanned = 0
    skipped = defaultdict(int)

    for input_root in input_roots:
        for path in sorted(input_root.rglob("*.json") if input_root.is_dir() else [input_root]):
            scanned += 1
            payload = _load_json(path)
            if payload is None:
                skipped["invalidJson"] += 1
                continue
            candidate = _candidate(path.resolve(), payload)
            if candidate is None:
                skipped["notImportableExtract"] += 1
                continue
            grouped[_source_path(payload)].append(candidate)

    entries: list[dict] = []
    for source_path, candidates in grouped.items():
        best = _best_by_mode(candidates)
        selected_files = [best[mode] for mode in ("2d", "3d") if mode in best]
        entries.append(
            {
                "sourcePath": source_path,
                "filename": PureWindowsPath(source_path).name,
                "customerHint": _customer_hint(source_path),
                "has2d": "2d" in best,
                "has3d": "3d" in best,
                "candidateFileCount": len(candidates),
                "selectedFiles": selected_files,
            }
        )

    selected_entries = _select_entries(entries, max_drawings)
    selected_paths = [
        selected_file["path"]
        for entry in selected_entries
        for selected_file in entry["selectedFiles"]
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "inputRoots": [str(path) for path in input_roots],
        "scannedJsonCount": scanned,
        "importableDrawingCount": len(entries),
        "selectedDrawingCount": len(selected_entries),
        "selectedFileCount": len(selected_paths),
        "skipped": dict(skipped),
        "selectedPaths": selected_paths,
        "entries": selected_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="共有済みICAD抽出JSONからDB取込用の代表manifestを生成します。")
    parser.add_argument("--input-root", action="append", required=True, help="抽出JSONファイルまたはディレクトリ。複数指定可。")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-drawings", type=int, default=24)
    args = parser.parse_args()

    input_roots = [Path(value).expanduser().resolve() for value in args.input_root]
    missing = [path for path in input_roots if not path.exists()]
    if missing:
        raise SystemExit(f"input-root が存在しません: {missing}")

    manifest = build_manifest(input_roots, args.max_drawings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "wrote "
        f"{args.output} selectedDrawings={manifest['selectedDrawingCount']} "
        f"selectedFiles={manifest['selectedFileCount']} scanned={manifest['scannedJsonCount']}"
    )


if __name__ == "__main__":
    main()
