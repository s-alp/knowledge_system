from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django  # noqa: E402

django.setup()

from apps.drawing_metadata.models import DrawingMetadataSnapshot  # noqa: E402


def inspect_material(value: str) -> list[dict]:
    results: list[dict] = []
    snapshots = DrawingMetadataSnapshot.objects.filter(extraction_mode="3d").select_related("drawing")
    for snapshot in snapshots.iterator():
        matches: list[dict] = []
        for part in (snapshot.raw_extract_json or {}).get("parts", []):
            if not isinstance(part, dict):
                continue
            materials = [item for item in (part.get("materials") or []) if value in str(item)]
            extended_info = {
                key: item_value
                for key, item_value in (part.get("ex_info_fields") or {}).items()
                if value in str(item_value)
            }
            if materials or extended_info:
                matches.append(
                    {
                        "partName": part.get("name"),
                        "treePath": part.get("tree_path") or [],
                        "materials": materials,
                        "extendedInfo": extended_info,
                    }
                )

        title_block = (snapshot.canonical_attributes_json or {}).get("title_block_fields") or {}
        title_block_matches = {key: item for key, item in title_block.items() if value in str(item)}
        if matches or title_block_matches:
            results.append(
                {
                    "drawing": snapshot.drawing.filename,
                    "sourcePath": snapshot.drawing.source_path,
                    "titleBlock": title_block_matches,
                    "parts": matches,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="材質値が図枠・3D材質・パーツ付加情報のどこから来たか確認します。")
    parser.add_argument("material")
    args = parser.parse_args()
    print(json.dumps(inspect_material(args.material), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
