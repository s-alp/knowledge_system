from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def main() -> None:
    import django

    django.setup()

    from apps.drawing_metadata.models import RegisteredDrawing
    from apps.drawing_metadata.services.icad_entities import build_icad_entity_catalog

    counter: Counter[str] = Counter()
    total = 0
    catalog = build_icad_entity_catalog(RegisteredDrawing.objects.prefetch_related("snapshots"), target_key="part")
    for entity in catalog["items"]:
        if entity.get("targetKey") != "part":
            continue
        total += 1
        counter[str(entity.get("name") or "")] += 1

    print(f"part_total={total}")
    for name, count in counter.most_common(30):
        print(f"{count}\t{name}")


if __name__ == "__main__":
    main()
