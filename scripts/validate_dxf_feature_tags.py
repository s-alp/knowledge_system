"""`validate_dxf_feature_tags`として成果物の契約・必須項目・値の整合性を検証する補助スクリプトである。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_DXF_ROOT = ROOT / "output" / "dxf_full_audit_2026-07-28" / "dxf"
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "output"
    / "dxf_full_audit_2026-07-28"
    / "production_tag_validation.json"
)
DEFAULT_RAW_OUTPUT_ROOT = (
    ROOT
    / "output"
    / "dxf_full_audit_2026-07-28"
    / "production_tag_validation_raw"
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
        description="本体のDXF抽出・正規化・タグ生成経路で、共有サンプルDXFの特徴タグを検証します。"
    )
    parser.add_argument("--dxf-root", type=Path, default=DEFAULT_DXF_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--raw-output-root", type=Path, default=DEFAULT_RAW_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.dxf_root.is_dir():
        raise NotADirectoryError(f"DXFルートが存在しません: {args.dxf_root}")

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "knowledge_system_backend.settings",
    )
    sys.path.insert(0, str(BACKEND_ROOT))

    import django

    django.setup()

    from apps.drawing_metadata.services.generic_cad_extractor import (
        extract_generic_cad_metadata,
    )
    from apps.drawing_metadata.services.normalization import normalize_raw_extract
    from apps.drawing_metadata.services.tag_builder import build_derived_tags

    dxf_paths = sorted(args.dxf_root.rglob("*.dxf"))
    if not dxf_paths:
        raise FileNotFoundError(f"検証対象DXFがありません: {args.dxf_root}")

    results: list[dict] = []
    tag_counts: Counter[str] = Counter()
    for index, dxf_path in enumerate(dxf_paths, start=1):
        relative_path = dxf_path.relative_to(args.dxf_root)
        raw_output_path = (
            args.raw_output_root
            / relative_path.parent
            / f"{relative_path.name}.extract.json"
        )
        payload = extract_generic_cad_metadata(
            input_path=str(dxf_path),
            source_format="dxf",
            source_kind="2d",
            output_path=raw_output_path,
        )
        canonical = normalize_raw_extract(payload)
        target_tags = sorted(
            tag["tag"]
            for tag in build_derived_tags(canonical)
            if tag["tag"] in TARGET_TAGS
        )
        tag_counts.update(target_tags)
        results.append(
            {
                "index": index,
                "relativePath": str(relative_path),
                "dimensionCount": canonical["dimension_count"],
                "dimensionToleranceCount": canonical["dimension_tolerance_count"],
                "geometricToleranceCount": canonical["geometric_tolerance_count"],
                "weldInstructionCount": canonical["weld_instruction_count"],
                "weldTypes": canonical["weld_types"],
                "hardnessSpecValues": canonical["hardness_spec_values"],
                "targetTags": target_tags,
                "rawExtractPath": str(raw_output_path),
            }
        )
        print(
            f"{index:03d}/{len(dxf_paths):03d} {relative_path.name}: "
            f"{', '.join(target_tags) if target_tags else '-'}",
            flush=True,
        )

    report = {
        "dxfRoot": str(args.dxf_root),
        "fileCount": len(dxf_paths),
        "targetTagFileCounts": dict(sorted(tag_counts.items())),
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
