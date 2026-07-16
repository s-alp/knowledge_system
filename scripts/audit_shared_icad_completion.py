from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django

django.setup()

from apps.drawing_metadata.models import RegisteredDrawing


def _path_key(value: str) -> str:
    return value.replace("/", "\\").rstrip("\\").casefold()


def _content_count(raw: dict) -> int:
    return sum(
        len(raw.get(key) or [])
        for key in ("texts", "dimensions", "geometry_primitives", "weld_notes", "balloons", "tolerances")
    )


def _coverage_values(raw: dict, field: str) -> set[str]:
    values: set[str] = set()
    for key in ("texts", "dimensions", "geometry_primitives", "weld_notes", "balloons", "tolerances"):
        for item in raw.get(key) or []:
            if isinstance(item, dict) and item.get(field) is not None:
                values.add(str(item[field]))
    return values


def main() -> int:
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output/souya_handoff/icad_extract_import_manifest_all_shared_2026-07-15.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    drawings = {
        _path_key(drawing.source_path): drawing
        for drawing in RegisteredDrawing.objects.prefetch_related("snapshots")
    }
    rows = []
    for entry in manifest.get("entries", []):
        source_path = str(entry["sourcePath"])
        drawing = drawings.get(_path_key(source_path))
        snapshots = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()} if drawing else {}
        two_d = snapshots.get("2d")
        three_d = snapshots.get("3d")
        raw_2d = two_d.raw_extract_json or {} if two_d else {}
        raw_3d = three_d.raw_extract_json or {} if three_d else {}
        content_count = _content_count(raw_2d)
        parts = [part for part in raw_3d.get("parts") or [] if isinstance(part, dict)]
        rows.append(
            {
                "sourcePath": source_path,
                "filename": Path(source_path).name,
                "registered": drawing is not None,
                "has2dSnapshot": two_d is not None,
                "has3dSnapshot": three_d is not None,
                "twoDContentStatus": "content" if content_count else "no_2d_entities",
                "twoDContentCount": content_count,
                "viewCount": len(_coverage_values(raw_2d, "view_name")),
                "layerCount": len(_coverage_values(raw_2d, "layer_no")),
                "printFrameCount": len(raw_2d.get("print_frames") or []),
                "printFrameStatus": (
                    "defined"
                    if raw_2d.get("print_frames")
                    else "not_defined"
                    if content_count
                    else "not_applicable_no_2d_entities"
                ),
                "partOccurrenceCount": len(parts),
                "partExtendedInfoCount": sum(bool(part.get("ex_info_fields")) for part in parts),
                "materialCandidateCount": len((three_d.canonical_attributes_json or {}).get("part_material_candidates") or []) if three_d else 0,
                "massAvailable": bool((three_d.canonical_attributes_json or {}).get("mass_value") is not None) if three_d else False,
            }
        )

    result = {
        "manifest": str(manifest_path),
        "sampleCount": len(rows),
        "registeredCount": sum(row["registered"] for row in rows),
        "twoDSnapshotCount": sum(row["has2dSnapshot"] for row in rows),
        "threeDSnapshotCount": sum(row["has3dSnapshot"] for row in rows),
        "twoDContentStatusCounts": dict(Counter(row["twoDContentStatus"] for row in rows)),
        "contentWithViewCoverageCount": sum(row["twoDContentStatus"] == "content" and row["viewCount"] > 0 for row in rows),
        "contentWithLayerCoverageCount": sum(row["twoDContentStatus"] == "content" and row["layerCount"] > 0 for row in rows),
        "contentWithPrintFrameCount": sum(row["twoDContentStatus"] == "content" and row["printFrameCount"] > 0 for row in rows),
        "multiplePrintFrameDrawingCount": sum(row["printFrameCount"] > 1 for row in rows),
        "contentWithoutDefinedPrintFrameCount": sum(row["printFrameStatus"] == "not_defined" for row in rows),
        "partExtendedInfoDrawingCount": sum(row["partExtendedInfoCount"] > 0 for row in rows),
        "materialCandidateDrawingCount": sum(row["materialCandidateCount"] > 0 for row in rows),
        "massAvailableDrawingCount": sum(row["massAvailable"] for row in rows),
        "unresolved": [
            row
            for row in rows
            if not row["registered"] or not row["has2dSnapshot"] or not row["has3dSnapshot"]
        ],
        "no2dEntityRows": [row for row in rows if row["twoDContentStatus"] == "no_2d_entities"],
        "knownDataConditions": [
            {
                "sourcePath": row["sourcePath"],
                "condition": "print_frame_not_defined",
                "handling": "座標・ビュー・レイヤーは保持し、inside_print_areaは判定不明のままにする。",
            }
            for row in rows
            if row["printFrameStatus"] == "not_defined"
        ],
        "rows": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
