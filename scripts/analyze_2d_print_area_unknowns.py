from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


INSPECTABLE_GROUPS = (
    ("texts", "text"),
    ("dimensions", "dimension"),
    ("geometry_primitives", "primitive"),
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {}
    return payload


def _iter_input_files(input_root: Path) -> list[Path]:
    if input_root.is_file():
        return [input_root]
    return sorted(input_root.rglob("*.json"))


def _has_xy(item: dict[str, Any]) -> bool:
    x = item.get("position_x")
    y = item.get("position_y")
    if x is None or y is None:
        x = item.get("center_x")
        y = item.get("center_y")
    return x is not None and y is not None


def _display_name(path: Path, payload: dict[str, Any]) -> str:
    source_file = payload.get("source_file") or {}
    raw_extract = payload.get("raw_extract") or {}
    raw_source_file = raw_extract.get("_source_file") or {}
    return (
        source_file.get("file_name")
        or raw_source_file.get("file_name")
        or payload.get("input_path")
        or path.name
    )


def analyze_file(path: Path) -> dict[str, Any] | None:
    payload = _load_json(path)
    raw_extract = payload.get("raw_extract")
    if not isinstance(raw_extract, dict):
        return None

    print_frames = raw_extract.get("print_frames") or []
    view_sheets = raw_extract.get("view_sheets") or []
    group_counts: dict[str, Counter[str]] = {}
    primitive_unknown_by_type: Counter[str] = Counter()
    primitive_missing_xy_by_type: Counter[str] = Counter()
    primitive_unknown_with_xy_by_type: Counter[str] = Counter()
    sample_unknowns: list[dict[str, Any]] = []

    total = 0
    unknown = 0
    missing_xy = 0
    unknown_with_xy = 0

    for key, group_name in INSPECTABLE_GROUPS:
        group_counter: Counter[str] = Counter()
        items = raw_extract.get(key) or []
        if not isinstance(items, list):
            items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            total += 1
            has_xy = _has_xy(item)
            if not has_xy:
                missing_xy += 1
                group_counter["missing_xy"] += 1
            if item.get("inside_print_area") is None:
                unknown += 1
                group_counter["unknown"] += 1
                if has_xy:
                    unknown_with_xy += 1
                    group_counter["unknown_with_xy"] += 1
                if len(sample_unknowns) < 10:
                    sample_unknowns.append(
                        {
                            "group": group_name,
                            "geometry_type": item.get("geometry_type"),
                            "view_name": item.get("view_name"),
                            "layer_no": item.get("layer_no"),
                            "position_x": item.get("position_x"),
                            "position_y": item.get("position_y"),
                            "center_x": item.get("center_x"),
                            "center_y": item.get("center_y"),
                            "summary": item.get("summary") or item.get("joined_text") or item.get("value_1"),
                        }
                    )
            group_counter["total"] += 1

            if group_name == "primitive":
                geometry_type = str(item.get("geometry_type") or "unknown")
                if item.get("inside_print_area") is None:
                    primitive_unknown_by_type[geometry_type] += 1
                    if has_xy:
                        primitive_unknown_with_xy_by_type[geometry_type] += 1
                if not has_xy:
                    primitive_missing_xy_by_type[geometry_type] += 1
        group_counts[group_name] = group_counter

    return {
        "path": str(path),
        "fileName": _display_name(path, payload),
        "viewSheetCount": len(view_sheets) if isinstance(view_sheets, list) else 0,
        "printFrameCount": len(print_frames) if isinstance(print_frames, list) else 0,
        "total": total,
        "unknown": unknown,
        "missingXY": missing_xy,
        "unknownWithXY": unknown_with_xy,
        "groupCounts": {name: dict(counter) for name, counter in group_counts.items()},
        "primitiveUnknownByType": dict(primitive_unknown_by_type.most_common()),
        "primitiveMissingXYByType": dict(primitive_missing_xy_by_type.most_common()),
        "primitiveUnknownWithXYByType": dict(primitive_unknown_with_xy_by_type.most_common()),
        "sampleUnknowns": sample_unknowns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="2D抽出JSONの印刷枠判定不明を種別ごとに集計します。")
    parser.add_argument("--input-root", required=True, help="対象JSONファイルまたはディレクトリ。")
    parser.add_argument("--output", help="集計JSONの出力先。")
    parser.add_argument("--top", type=int, default=10, help="ファイル別上位件数。")
    args = parser.parse_args()

    input_root = Path(args.input_root)
    file_results = [
        result
        for path in _iter_input_files(input_root)
        for result in [analyze_file(path)]
        if result is not None
    ]
    file_results.sort(key=lambda item: item["unknown"], reverse=True)

    aggregate_unknown_by_type: Counter[str] = Counter()
    aggregate_missing_xy_by_type: Counter[str] = Counter()
    for result in file_results:
        aggregate_unknown_by_type.update(result["primitiveUnknownByType"])
        aggregate_missing_xy_by_type.update(result["primitiveMissingXYByType"])

    payload = {
        "inputRoot": str(input_root),
        "fileCount": len(file_results),
        "totals": {
            "total": sum(item["total"] for item in file_results),
            "unknown": sum(item["unknown"] for item in file_results),
            "missingXY": sum(item["missingXY"] for item in file_results),
            "unknownWithXY": sum(item["unknownWithXY"] for item in file_results),
        },
        "primitiveUnknownByType": dict(aggregate_unknown_by_type.most_common()),
        "primitiveMissingXYByType": dict(aggregate_missing_xy_by_type.most_common()),
        "topFiles": file_results[: args.top],
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
