from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


INSPECTABLE_KEYS = (
    "texts",
    "dimensions",
    "geometry_primitives",
    "weld_notes",
    "balloons",
    "tolerances",
)
WARNING_SAMPLE_LIMIT = 20


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _raw_extract(payload: dict[str, Any]) -> dict[str, Any]:
    raw_extract = payload.get("raw_extract")
    if isinstance(raw_extract, dict):
        return raw_extract
    return payload


def _is_2d_payload(path: Path, payload: dict[str, Any], raw_extract: dict[str, Any]) -> bool:
    if payload.get("source_kind") == "2d" or payload.get("extraction_mode") == "2d":
        return True
    if path.name.lower().endswith("_2d.json") or path.name.lower().endswith(".2d.json"):
        return True
    return any(raw_extract.get(key) for key in ("view_sheets", "print_frames", "layers", *INSPECTABLE_KEYS))


def _items(raw_extract: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in INSPECTABLE_KEYS:
        for item in raw_extract.get(key, []) or []:
            if isinstance(item, dict):
                items.append(item | {"_coverage_source": key})
    return items


def _inside_counts(items: list[dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        value = item.get("inside_print_area")
        if value is True:
            counter["inside"] += 1
        elif value is False:
            counter["outside"] += 1
        else:
            counter["unknown"] += 1
    return counter


def _warning_type(message: str) -> str:
    return message.split(":", 1)[-1].strip() if ":" in message else message.strip()


def _warning_summary(warnings: list[Any]) -> dict[str, Any]:
    counter: Counter = Counter()
    samples: list[Any] = []
    for warning in warnings:
        if not isinstance(warning, dict):
            counter["non_object_warning"] += 1
            if len(samples) < WARNING_SAMPLE_LIMIT:
                samples.append(warning)
            continue
        code = str(warning.get("code") or "unknown_warning")
        message = str(warning.get("message") or "")
        if code == "unsupported_geometry":
            counter[f"{code}:{_warning_type(message)}"] += 1
        else:
            counter[code] += 1
        if len(samples) < WARNING_SAMPLE_LIMIT:
            samples.append(warning)
    return {
        "warningCount": len(warnings),
        "warningTypeCounts": dict(counter),
        "warningSamples": samples,
        "warningSamplesTruncated": len(warnings) > WARNING_SAMPLE_LIMIT,
    }


def _file_summary(path: Path, payload: dict[str, Any], raw_extract: dict[str, Any]) -> dict[str, Any]:
    view_sheets = raw_extract.get("view_sheets", []) or []
    print_frames = raw_extract.get("print_frames", []) or []
    layers = raw_extract.get("layers", []) or []
    items = _items(raw_extract)

    declared_views = {item.get("name") for item in view_sheets if isinstance(item, dict) and item.get("name")}
    item_views = {item.get("view_name") for item in items if item.get("view_name")}
    layer_numbers = {item.get("no") for item in layers if isinstance(item, dict) and item.get("no") is not None}
    item_layers = {item.get("layer_no") for item in items if item.get("layer_no") is not None}
    inside_counts = _inside_counts(items)
    warnings = payload.get("warnings") or raw_extract.get("warnings") or []

    source_counts = Counter(item.get("_coverage_source") for item in items)
    return {
        "path": str(path),
        "sourcePath": payload.get("input_path") or raw_extract.get("input_path"),
        "viewSheetCount": len(view_sheets),
        "printFrameCount": len(print_frames),
        "layerCount": len(layers),
        "inspectableItemCount": len(items),
        "textCount": source_counts["texts"],
        "dimensionCount": source_counts["dimensions"],
        "geometryPrimitiveCount": source_counts["geometry_primitives"],
        "viewsWithItems": len(item_views),
        "declaredViewsWithoutItems": sorted(str(value) for value in declared_views - item_views),
        "itemsWithoutView": len([item for item in items if not item.get("view_name")]),
        "layersWithItems": len(item_layers),
        "declaredLayersWithoutItems": sorted(str(value) for value in layer_numbers - item_layers),
        "itemsWithoutLayer": len([item for item in items if item.get("layer_no") is None]),
        "insidePrintAreaCount": inside_counts["inside"],
        "outsidePrintAreaCount": inside_counts["outside"],
        "unknownPrintAreaCount": inside_counts["unknown"],
        **_warning_summary(warnings),
    }


def _aggregate(files: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    issue_files: dict[str, list[str]] = defaultdict(list)
    for item in files:
        totals["fileCount"] += 1
        for key in (
            "viewSheetCount",
            "printFrameCount",
            "layerCount",
            "inspectableItemCount",
            "textCount",
            "dimensionCount",
            "geometryPrimitiveCount",
            "insidePrintAreaCount",
            "outsidePrintAreaCount",
            "unknownPrintAreaCount",
            "itemsWithoutView",
            "itemsWithoutLayer",
        ):
            totals[key] += int(item.get(key) or 0)
        if item["viewSheetCount"] == 0:
            issue_files["noViewSheets"].append(item["path"])
        if item["printFrameCount"] == 0:
            issue_files["noPrintFrames"].append(item["path"])
        if item["layerCount"] == 0:
            issue_files["noLayers"].append(item["path"])
        if item["itemsWithoutView"]:
            issue_files["itemsWithoutView"].append(item["path"])
        if item["itemsWithoutLayer"]:
            issue_files["itemsWithoutLayer"].append(item["path"])
        if item["unknownPrintAreaCount"]:
            issue_files["unknownPrintArea"].append(item["path"])

    return {
        "totals": dict(totals),
        "issueFileCounts": {key: len(value) for key, value in issue_files.items()},
        "issueFileSamples": {key: value[:10] for key, value in issue_files.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="共有済みICAD 2D抽出JSONのビュー/レイヤー/印刷枠カバレッジを集計します。")
    parser.add_argument("--input-root", action="append", default=[], help="探索する抽出JSONディレクトリ。複数指定可。")
    parser.add_argument("--manifest", action="append", default=[], help="selectedPaths を持つmanifest JSON。複数指定可。")
    parser.add_argument("--output", help="JSON出力先。省略時は標準出力。")
    parser.add_argument("--limit-files", type=int, default=0, help="調査用の最大ファイル数。0なら制限なし。")
    args = parser.parse_args()
    if not args.input_root and not args.manifest:
        parser.error("--input-root または --manifest を少なくとも1つ指定してください。")

    summaries: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    candidate_paths: list[Path] = []
    for manifest_value in args.manifest:
        manifest_payload = _load_json(Path(manifest_value))
        if not manifest_payload:
            continue
        for selected_path in manifest_payload.get("selectedPaths", []) or []:
            candidate_paths.append(Path(selected_path))

    for root_value in args.input_root:
        root = Path(root_value)
        for path in sorted(root.rglob("*.json")):
            candidate_paths.append(path)

    for path in candidate_paths:
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        payload = _load_json(path)
        if not payload:
            continue
        raw_extract = _raw_extract(payload)
        if not _is_2d_payload(path, payload, raw_extract):
            continue
        summaries.append(_file_summary(path, payload, raw_extract))
        if args.limit_files and len(summaries) >= args.limit_files:
            break

    result = {
        "schemaVersion": "icad_2d_extraction_coverage_summary.v1",
        "inputRoots": args.input_root,
        "manifests": args.manifest,
        "fileCount": len(summaries),
        "aggregate": _aggregate(summaries),
        "files": summaries,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
