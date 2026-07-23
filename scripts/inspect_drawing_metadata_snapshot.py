from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_drawing_metadata_snapshot.py <filename-fragment>")

    import django

    django.setup()

    from apps.drawing_metadata.models import DrawingMetadataSnapshot

    fragment = sys.argv[1]
    snapshot = (
        DrawingMetadataSnapshot.objects.select_related("drawing")
        .filter(drawing__filename__icontains=fragment, extraction_mode="2d")
        .order_by("-updated_at")
        .first()
    )
    if snapshot is None:
        raise SystemExit(f"2d snapshot not found: {fragment}")

    raw_extract = snapshot.raw_extract_json or {}
    canonical = snapshot.canonical_attributes_json or {}
    print(f"filename={snapshot.drawing.filename}")
    print(f"raw texts={len(raw_extract.get('texts') or [])}")
    print(f"raw views={len(raw_extract.get('view_sheets') or [])}")
    print("canonical keys=" + ", ".join(sorted(canonical.keys())))
    for key in (
        "drawing_name",
        "part_name",
        "part_name_candidates",
        "part_names",
        "title_block_fields",
        "title_block_candidates",
    ):
        print(key)
        print(json.dumps(canonical.get(key), ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
