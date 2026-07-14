from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"


def _setup_django() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

    import django

    django.setup()


def _source_kinds(drawing) -> set[str]:
    return {snapshot.extraction_mode for snapshot in drawing.snapshots.all()}


def _target_counts(targets: list[dict]) -> list[dict]:
    return [
        {
            "targetKey": target["targetKey"],
            "attributeCount": len(target.get("attributes") or []),
            "tagCount": len(target.get("tags") or []),
            "tagApiStatus": target.get("tagApiStatus"),
        }
        for target in targets
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ICAD抽出結果から本番タグ・属性payloadプレビュー候補が多い図面を一覧化します。"
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="JSON形式で出力します。")
    args = parser.parse_args()

    _setup_django()

    from apps.drawing_metadata.models import RegisteredDrawing
    from apps.drawing_metadata.services.composition import compose_drawing_metadata
    from apps.drawing_metadata.services.knowledge_payload_preview import (
        build_knowledge_system_payload_preview,
    )

    rows: list[dict] = []
    drawings = RegisteredDrawing.objects.prefetch_related("snapshots").order_by("filename")
    for drawing in drawings:
        composed = compose_drawing_metadata(drawing)
        preview = build_knowledge_system_payload_preview(drawing=drawing, composed_metadata=composed)
        targets = preview.get("targets") or []
        target_counts = _target_counts(targets)
        source_kinds = _source_kinds(drawing)
        rows.append(
            {
                "candidateScore": sum(
                    target["attributeCount"] + target["tagCount"] for target in target_counts
                ),
                "drawingId": str(drawing.id),
                "filename": drawing.filename,
                "sourcePath": drawing.source_path,
                "has2d": "2d" in source_kinds,
                "has3d": "3d" in source_kinds,
                "sourceKinds": sorted(source_kinds),
                "targetCounts": target_counts,
            }
        )

    rows.sort(key=lambda row: (row["has2d"] and row["has3d"], row["candidateScore"]), reverse=True)
    selected = rows[: args.limit]

    if args.json:
        print(json.dumps(selected, ensure_ascii=False, indent=2))
        return 0

    print("score\thas2d\thas3d\tdrawingId\tfilename\ttargetCounts")
    for row in selected:
        print(
            "\t".join(
                [
                    str(row["candidateScore"]),
                    str(row["has2d"]),
                    str(row["has3d"]),
                    row["drawingId"],
                    row["filename"],
                    json.dumps(row["targetCounts"], ensure_ascii=False),
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
