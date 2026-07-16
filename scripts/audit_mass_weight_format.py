from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django

django.setup()

from apps.drawing_metadata.models import DrawingMetadataSnapshot


KG_TWO_DECIMAL_PATTERN = re.compile(r"^-?\d+\.\d{2} kg$")


def _weight_strings(canonical: dict) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    title_weight = (canonical.get("title_block_fields") or {}).get("weight")
    if isinstance(title_weight, str) and title_weight.strip():
        values.append(("title_block_fields.weight", title_weight.strip()))
    weight_value = canonical.get("weight_value")
    if isinstance(weight_value, str) and weight_value.strip():
        values.append(("weight_value", weight_value.strip()))
    return values


def main() -> int:
    invalid_rows: list[dict] = []
    for snapshot in DrawingMetadataSnapshot.objects.select_related("drawing").only(
        "id",
        "drawing__filename",
        "canonical_attributes_json",
    ):
        canonical = snapshot.canonical_attributes_json or {}
        for field, value in _weight_strings(canonical):
            if not KG_TWO_DECIMAL_PATTERN.match(value):
                invalid_rows.append(
                    {
                        "snapshotId": str(snapshot.id),
                        "filename": snapshot.drawing.filename,
                        "field": field,
                        "value": value,
                    }
                )

    result = {
        "snapshotCount": DrawingMetadataSnapshot.objects.count(),
        "invalidWeightStringCount": len(invalid_rows),
        "invalidWeightStringSamples": invalid_rows[:20],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if invalid_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
