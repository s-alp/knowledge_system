# 図枠文字の代表payloadを正規化処理へ通し、図面名称の採用・除外規則を再現確認する。
# Djangoの正規化サービスを直接呼ぶ検証専用スクリプトで、DBや原本図面は更新しない。
# 期待結果と異なる場合は、ラベル規則、座標ペアリング条件、NFKC正規化を確認する。
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def _payload(texts: list[dict]) -> dict:
    return {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {
            "full_path": r"C:\audit\sample.icd",
            "directory_path": r"C:\audit",
            "file_name": "sample.icd",
            "file_name_without_extension": "sample",
            "extension": ".icd",
        },
        "raw_extract": {
            "texts": texts,
            "print_frames": [],
        },
    }


def main() -> None:
    import django

    django.setup()

    from apps.drawing_metadata.services.normalization import normalize_raw_extract

    cases = {
        "same_element_standard": [{"text_lines": ["品名: 開口カバー"]}],
        "same_element_spaced_label": [{"text_lines": ["品　名: 開口カバー"]}],
        "same_payload_next_line": [{"text_lines": ["品　名", "開口カバー"]}],
        "separate_text_elements": [
            {"text_lines": ["品　名"], "position_x": 10.0, "position_y": 10.0},
            {"text_lines": ["開口カバー"], "position_x": 20.0, "position_y": 10.0},
        ],
        "english_unit_label_only": [{"text_lines": ["UNIT Name"]}],
        "english_machine_label_only": [{"text_lines": ["MACHINE Name"]}],
    }
    results: dict[str, dict] = {}
    for name, texts in cases.items():
        canonical = normalize_raw_extract(_payload(texts))
        results[name] = {
            "drawingName": canonical.get("drawing_name"),
            "titleBlockFields": canonical.get("title_block_fields"),
            "titleBlockNameCandidates": [
                candidate
                for candidate in canonical.get("title_block_candidates") or []
                if candidate.get("field") == "drawing_name"
            ],
        }

    output_path = ROOT / "output" / "drawing_entity_name_audit_2026-07-29" / "normalization_probe.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
