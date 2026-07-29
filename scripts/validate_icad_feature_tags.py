from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_MANIFEST = (
    ROOT
    / "output"
    / "souya_handoff"
    / "icad_extract_import_manifest_all_shared_2026-07-15.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "output"
    / "icad_feature_tag_validation_2026-07-28.json"
)
TARGET_TAGS = {
    "寸法あり",
    "寸法公差あり",
    "幾何公差あり",
    "溶接指示あり",
    "溶接:すみ肉",
    "溶接:全周",
    "硬度:HRC",
    "硬度:HV",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="共有ICAD抽出JSONを現行の正規化・タグ生成経路で再検証します。"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.manifest.is_file():
        raise FileNotFoundError(f"manifestが存在しません: {args.manifest}")

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "knowledge_system_backend.settings",
    )
    sys.path.insert(0, str(BACKEND_ROOT))

    import django

    django.setup()

    from apps.drawing_metadata.services.normalization import normalize_raw_extract
    from apps.drawing_metadata.services.tag_builder import build_derived_tags

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest.entriesが空です。")

    results: list[dict] = []
    tag_counts: Counter[str] = Counter()
    mode_file_counts: Counter[str] = Counter()
    for index, entry in enumerate(entries, start=1):
        mode_results: dict[str, dict] = {}
        combined_tags: set[str] = set()
        for selected_file in entry.get("selectedFiles", []):
            mode = selected_file.get("mode")
            if mode not in {"2d", "3d"}:
                continue
            extract_path = Path(selected_file["path"])
            if not extract_path.is_file():
                raise FileNotFoundError(
                    f"選択済みICAD抽出JSONが存在しません: {extract_path}"
                )
            payload = json.loads(extract_path.read_text(encoding="utf-8"))
            canonical = normalize_raw_extract(payload)
            target_tags = sorted(
                tag["tag"]
                for tag in build_derived_tags(canonical)
                if tag["tag"] in TARGET_TAGS
            )
            combined_tags.update(target_tags)
            mode_file_counts[mode] += 1
            mode_results[mode] = {
                "extractPath": str(extract_path),
                "dimensionCount": canonical["dimension_count"],
                "dimensionToleranceCount": canonical["dimension_tolerance_count"],
                "geometricToleranceCount": canonical["geometric_tolerance_count"],
                "weldInstructionCount": canonical["weld_instruction_count"],
                "weldTypes": canonical["weld_types"],
                "hardnessSpecValues": canonical["hardness_spec_values"],
                "targetTags": target_tags,
            }

        sorted_tags = sorted(combined_tags)
        tag_counts.update(sorted_tags)
        results.append(
            {
                "index": index,
                "filename": entry["filename"],
                "sourcePath": entry["sourcePath"],
                "modes": mode_results,
                "combinedTargetTags": sorted_tags,
            }
        )
        print(
            f"{index:03d}/{len(entries):03d} {entry['filename']}: "
            f"{', '.join(sorted_tags) if sorted_tags else '-'}",
            flush=True,
        )

    report = {
        "manifest": str(args.manifest),
        "drawingCount": len(entries),
        "modeFileCounts": dict(sorted(mode_file_counts.items())),
        "targetTagDrawingCounts": dict(sorted(tag_counts.items())),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"output={args.output}", flush=True)


if __name__ == "__main__":
    main()
