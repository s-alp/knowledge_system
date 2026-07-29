from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

MISSING_NAME = "名称未抽出"
EXTRACTION_PROFILE = "2d_all_views_layers_print_frame"
EXTRACTION_OPTIONS = {
    "scanAllViews": True,
    "scanAllLayers": True,
    "classifyPrintFrame": True,
    "recordOutsidePrintFrame": True,
    "recordUnknownPrintArea": True,
}


def _write_output(rows: list[dict]) -> Path:
    output_path = (
        ROOT
        / "output"
        / "drawing_entity_name_audit_2026-07-29"
        / "missing_identity_reextraction_probe.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "schemaVersion": "missing_identity_reextraction_probe.v1",
                "extractionProfile": EXTRACTION_PROFILE,
                "extractionOptions": EXTRACTION_OPTIONS,
                "count": len(rows),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    """名称未抽出図面をDB更新せず再抽出し、C#文字取得改善の実効性を確認する。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", action="append", default=[])
    args = parser.parse_args()

    import django

    django.setup()

    from apps.drawing_metadata.models import RegisteredDrawing
    from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope
    from apps.drawing_metadata.services.extraction_runner import run_extractor
    from apps.drawing_metadata.services.icad_entities import build_icad_entity_catalog
    from apps.drawing_metadata.services.normalization import normalize_raw_extract

    queryset = RegisteredDrawing.objects.prefetch_related("snapshots").order_by("filename", "id")
    scoped_queryset, _scope = apply_active_drawing_scope(queryset)
    drawings = list(scoped_queryset)
    catalog = build_icad_entity_catalog(drawings)
    missing_ids = {
        item["drawingId"]
        for item in catalog["items"]
        if item.get("name") == MISSING_NAME
    }
    targets = [drawing for drawing in drawings if str(drawing.id) in missing_ids]
    requested_filenames = set(args.filename)
    if requested_filenames:
        targets = [drawing for drawing in targets if drawing.filename in requested_filenames]

    rows: list[dict] = []
    for index, drawing in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] {drawing.filename}", flush=True)
        try:
            result = run_extractor(
                drawing=drawing,
                extraction_mode="2d",
                job_id=uuid.uuid4(),
                extraction_profile=EXTRACTION_PROFILE,
                extraction_options=EXTRACTION_OPTIONS,
            )
        except Exception as exc:
            rows.append(
                {
                    "drawingId": str(drawing.id),
                    "filename": drawing.filename,
                    "sourcePath": drawing.source_path,
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                }
            )
            _write_output(rows)
            continue
        payload = result.payload
        canonical = normalize_raw_extract(payload)
        raw_extract = payload.get("raw_extract") or {}
        rows.append(
            {
                "drawingId": str(drawing.id),
                "filename": drawing.filename,
                "sourcePath": drawing.source_path,
                "rawTextCount": len(raw_extract.get("texts") or []),
                "warningCodes": [
                    warning.get("code")
                    for warning in payload.get("warnings") or []
                    if isinstance(warning, dict)
                ],
                "drawingNumber": canonical.get("drawing_number"),
                "partName": canonical.get("part_name"),
                "drawingName": canonical.get("drawing_name"),
                "productName": canonical.get("product_name"),
                "equipmentName": canonical.get("equipment_name"),
                "unitName": canonical.get("unit_name"),
                "partNameCandidates": canonical.get("part_name_candidates") or [],
                "titleBlockIdentityCandidates": [
                    candidate
                    for candidate in canonical.get("title_block_candidates") or []
                    if candidate.get("field")
                    in {
                        "drawing_name",
                        "part_name",
                        "product_name",
                        "equipment_name",
                        "unit_name",
                    }
                ],
                "rawExtractOutputPath": str(result.output_path),
            }
        )
        _write_output(rows)

    output_path = _write_output(rows)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
