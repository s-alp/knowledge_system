from __future__ import annotations

import json
import math
import os
import sys
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

MISSING_NAME = "名称未抽出"
IDENTITY_NAME_FIELDS = {
    "drawing_name",
    "part_name",
    "product_name",
    "equipment_name",
    "unit_name",
}
NAME_LABELS = (
    "品名",
    "部品名",
    "図名",
    "図面名",
    "名称",
    "PARTNAME",
    "UNITNAME",
    "MACHINENAME",
)


def _text_lines(item: dict) -> list[str]:
    values: list[str] = []
    for key in ("text_lines", "lines"):
        raw = item.get(key)
        if isinstance(raw, list):
            values.extend(str(value).strip() for value in raw if str(value).strip())
    for key in ("joined_text", "text", "value"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            values.append(raw.strip())
    return list(dict.fromkeys(values))


def _compact_text(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).upper().split())


def _nearest_texts(label_item: dict, text_items: list[dict]) -> list[dict]:
    label_x = label_item.get("position_x")
    label_y = label_item.get("position_y")
    if not isinstance(label_x, (int, float)) or not isinstance(label_y, (int, float)):
        return []
    candidates: list[tuple[float, dict]] = []
    for item in text_items:
        if item is label_item:
            continue
        if item.get("view_name") != label_item.get("view_name"):
            continue
        item_x = item.get("position_x")
        item_y = item.get("position_y")
        if not isinstance(item_x, (int, float)) or not isinstance(item_y, (int, float)):
            continue
        joined = " / ".join(_text_lines(item))
        if not joined:
            continue
        candidates.append(
            (
                math.hypot(float(item_x) - float(label_x), float(item_y) - float(label_y)),
                {
                    "text": joined,
                    "distance": round(
                        math.hypot(float(item_x) - float(label_x), float(item_y) - float(label_y)),
                        3,
                    ),
                    "layerNo": item.get("layer_no"),
                    "positionX": item_x,
                    "positionY": item_y,
                    "insidePrintArea": item.get("inside_print_area"),
                },
            )
        )
    return [candidate for _distance, candidate in sorted(candidates, key=lambda row: row[0])[:8]]


def _label_evidence(raw_extract: dict) -> list[dict]:
    evidence: list[dict] = []
    text_items = [item for item in raw_extract.get("texts") or [] if isinstance(item, dict)]
    for item in text_items:
        lines = _text_lines(item)
        joined = " / ".join(lines)
        compact = _compact_text(joined)
        if not any(label in compact for label in NAME_LABELS):
            continue
        evidence.append(
            {
                "text": joined,
                "viewName": item.get("view_name"),
                "layerNo": item.get("layer_no"),
                "positionX": item.get("position_x"),
                "positionY": item.get("position_y"),
                "insidePrintArea": item.get("inside_print_area"),
                "nearestTexts": _nearest_texts(item, text_items),
            }
        )
    return evidence


def _snapshot_by_mode(drawing, mode: str):
    return next(
        (snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == mode),
        None,
    )


def _compact_values(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _dictionary_matches_nfkc(tokens: list[str], mapping: dict[str, list[str]]) -> list[str]:
    normalized_text = unicodedata.normalize("NFKC", " ".join(tokens)).lower()
    return [
        canonical
        for canonical, candidates in mapping.items()
        if any(
            unicodedata.normalize("NFKC", str(candidate)).lower() in normalized_text
            for candidate in candidates
        )
    ]


def main() -> None:
    import django

    django.setup()

    from apps.drawing_metadata.models import RegisteredDrawing, TagDictionaryEntry
    from apps.drawing_metadata.services.dictionaries import load_keyword_mapping
    from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload
    from apps.drawing_metadata.services.icad_entities import build_icad_entity_catalog

    part_name_mapping = load_keyword_mapping(TagDictionaryEntry.KIND_PART_NAME)
    total_registration_count = RegisteredDrawing.objects.count()
    queryset = RegisteredDrawing.objects.prefetch_related("snapshots").order_by("filename", "id")
    scoped_queryset, scope = apply_active_drawing_scope(queryset)
    drawings = list(scoped_queryset)
    catalog = build_icad_entity_catalog(drawings)
    record_by_drawing_id = {record["drawingId"]: record for record in catalog["items"]}

    rows: list[dict] = []
    for drawing in drawings:
        record = record_by_drawing_id.get(str(drawing.id))
        if record is None:
            continue
        snapshot_2d = _snapshot_by_mode(drawing, "2d")
        snapshot_3d = _snapshot_by_mode(drawing, "3d")
        canonical_2d = snapshot_2d.canonical_attributes_json if snapshot_2d else {}
        canonical_3d = snapshot_3d.canonical_attributes_json if snapshot_3d else {}
        raw_2d = snapshot_2d.raw_extract_json if snapshot_2d else {}
        raw_3d = snapshot_3d.raw_extract_json if snapshot_3d else {}
        top_part = raw_3d.get("top_part") or {}
        label_evidence = _label_evidence(raw_2d)
        entity_name = str(record.get("name") or "").strip()
        filename_stem = Path(drawing.filename).stem
        top_part_name = canonical_3d.get("top_part_name") or top_part.get("name")
        name_evidence = (
            (record.get("businessFieldSources") or {}).get("name") or {}
        ).get("evidence") or ""
        if entity_name == MISSING_NAME:
            name_resolution = "missing"
        elif name_evidence == "canonicalAttributes.part_name":
            name_resolution = "explicit_part_name"
        elif name_evidence == "canonicalAttributes.unit_name":
            name_resolution = "explicit_unit_name"
        elif name_evidence == "canonicalAttributes.equipment_name":
            name_resolution = "explicit_equipment_name"
        elif name_evidence == "canonicalAttributes.product_name":
            name_resolution = "explicit_product_name"
        elif name_evidence == "canonicalAttributes.drawing_name":
            name_resolution = "explicit_drawing_name"
        elif name_evidence == "canonicalAttributes.top_part_comment":
            name_resolution = "validated_top_part_comment"
        elif name_evidence == "registeredDrawing.filename":
            name_resolution = "filename_semantic_name"
        elif name_evidence == "canonicalAttributes.part_name_candidates":
            name_resolution = "part_dictionary"
        else:
            name_resolution = "other"
        print_area_counts = Counter(
            "inside"
            if item.get("inside_print_area") is True
            else "outside"
            if item.get("inside_print_area") is False
            else "unknown"
            for item in raw_2d.get("texts") or []
            if isinstance(item, dict)
        )
        has_print_frames = bool(raw_2d.get("print_frames"))
        trusted_text_count = (
            print_area_counts["inside"]
            if has_print_frames
            else print_area_counts["inside"] + print_area_counts["unknown"]
        )
        trusted_text_items = [
            item
            for item in raw_2d.get("texts") or []
            if isinstance(item, dict)
            and item.get("inside_print_area") is not False
            and (not has_print_frames or item.get("inside_print_area") is True)
        ]
        trusted_text_tokens = [
            value
            for item in trusted_text_items
            for value in _text_lines(item)
        ]
        nfkc_part_name_candidates = _dictionary_matches_nfkc(
            [
                *trusted_text_tokens,
                *[
                    str(value)
                    for value in (canonical_2d.get("title_block_fields") or {}).values()
                    if value
                ],
            ],
            part_name_mapping,
        )

        rows.append(
            {
                "drawingId": str(drawing.id),
                "filename": drawing.filename,
                "sourcePath": drawing.source_path,
                "targetKey": record["targetKey"],
                "entityKind": record["entityKind"],
                "entityName": entity_name,
                "entityNameMissing": entity_name == MISSING_NAME,
                "entityNameIsFilename": entity_name == filename_stem,
                "entityNameIsTopPartName": entity_name == str(top_part_name or "").strip(),
                "nameResolution": name_resolution,
                "nameEvidence": name_evidence,
                "drawingNumber": record.get("drawingNumber") or "",
                "partNumber": record.get("partNumber") or "",
                "partNumberEqualsDrawingNumber": (
                    record["targetKey"] != "part"
                    or (record.get("partNumber") or "") == (record.get("drawingNumber") or "")
                ),
                "drawingName2d": canonical_2d.get("drawing_name"),
                "partName2d": canonical_2d.get("part_name"),
                "productName2d": canonical_2d.get("product_name"),
                "equipmentName2d": canonical_2d.get("equipment_name"),
                "unitName2d": canonical_2d.get("unit_name"),
                "partNameCandidates2d": _compact_values(canonical_2d.get("part_name_candidates")),
                "partNameCandidates2dNfkcProbe": nfkc_part_name_candidates,
                "titleBlockFields2d": canonical_2d.get("title_block_fields") or {},
                "titleBlockNameCandidates2d": [
                    candidate
                    for candidate in canonical_2d.get("title_block_candidates") or []
                    if isinstance(candidate, dict) and candidate.get("field") in IDENTITY_NAME_FIELDS
                ],
                "nameLabelEvidence2d": label_evidence,
                "rawTextCount2d": len(raw_2d.get("texts") or []),
                "trustedTextCount2d": trusted_text_count,
                "filteredTextCount2d": len(raw_2d.get("texts") or []) - trusted_text_count,
                "rawTextPrintAreaCounts2d": dict(print_area_counts),
                "printFrameCount2d": len(raw_2d.get("print_frames") or []),
                "topPartName3d": top_part_name,
                "topPartComment3d": canonical_3d.get("top_part_comment") or top_part.get("comment"),
                "partNames3d": _compact_values(canonical_3d.get("part_names")),
                "partComments3d": _compact_values(canonical_3d.get("part_comments")),
            }
        )

    counts = Counter()
    # 合格条件もJSONに明示し、キー欠落を「0件」と読み替えなくてよい監査結果にする。
    for target in ("part", "product"):
        counts[f"{target}.topPartNameViolation"] = 0
        counts[f"{target}.partNumberMismatch"] = 0
        counts[f"{target}.drawingNumberMissing"] = 0
    for row in rows:
        target = row["targetKey"]
        counts[f"{target}.total"] += 1
        counts[f"{target}.resolution.{row['nameResolution']}"] += 1
        if row["entityNameMissing"]:
            counts[f"{target}.missing"] += 1
        if row["entityNameIsFilename"]:
            counts[f"{target}.filenameFallback"] += 1
        if row["entityNameIsTopPartName"]:
            counts[f"{target}.topPartNameViolation"] += 1
        if row["drawingNumber"]:
            counts[f"{target}.drawingNumberPresent"] += 1
        else:
            counts[f"{target}.drawingNumberMissing"] += 1
        if not row["partNumberEqualsDrawingNumber"]:
            counts[f"{target}.partNumberMismatch"] += 1
        if row["drawingName2d"]:
            counts[f"{target}.drawingName2d"] += 1
        if row["partNameCandidates2d"]:
            counts[f"{target}.partNameCandidates2d"] += 1
        if row["partNameCandidates2dNfkcProbe"]:
            counts[f"{target}.partNameCandidates2dNfkcProbe"] += 1
        if (
            not row["partNameCandidates2d"]
            and row["partNameCandidates2dNfkcProbe"]
        ):
            counts[f"{target}.partNameCandidatesRecoveredByNfkcProbe"] += 1
        if row["topPartName3d"]:
            counts[f"{target}.topPartName3d"] += 1
        if row["topPartComment3d"]:
            counts[f"{target}.topPartComment3d"] += 1
        if row["nameLabelEvidence2d"]:
            counts[f"{target}.nameLabelEvidence2d"] += 1
        if row["entityNameMissing"] and row["nameLabelEvidence2d"]:
            counts[f"{target}.missingWithNameLabelEvidence2d"] += 1
        if row["entityNameMissing"] and row["topPartName3d"]:
            counts[f"{target}.missingWithTopPartName3d"] += 1
        if row["entityNameMissing"] and row["topPartComment3d"]:
            counts[f"{target}.missingWithTopPartComment3d"] += 1
        if row["filteredTextCount2d"]:
            counts[f"{target}.filteredTextDrawings2d"] += 1
            counts[f"{target}.filteredTextItems2d"] += row["filteredTextCount2d"]
        if row["rawTextCount2d"] and not row["trustedTextCount2d"]:
            counts[f"{target}.rawTextPresentButAllFiltered2d"] += 1

    part_name_db_entries = list(
        TagDictionaryEntry.objects.filter(
            kind=TagDictionaryEntry.KIND_PART_NAME,
            enabled=True,
        )
        .order_by("priority", "canonical_value")
        .values("canonical_value", "aliases_json", "priority", "note")
    )

    payload = {
        "schemaVersion": "drawing_entity_name_audit.v2",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(drawings),
        ),
        "counts": dict(sorted(counts.items())),
        "partNameDictionary": {
            "activeMapping": part_name_mapping,
            "enabledDbEntries": part_name_db_entries,
        },
        "rows": rows,
    }
    output_dir = ROOT / "output" / "drawing_entity_name_audit_2026-07-29"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "drawing_entity_name_audit.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload["scope"], ensure_ascii=False))
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print(f"output={output_path}")
    print("missing samples:")
    for row in [item for item in rows if item["entityNameMissing"]][:20]:
        print(
            json.dumps(
                {
                    "filename": row["filename"],
                    "targetKey": row["targetKey"],
                    "drawingName2d": row["drawingName2d"],
                    "partNameCandidates2d": row["partNameCandidates2d"],
                    "topPartName3d": row["topPartName3d"],
                    "nameLabelEvidence2d": row["nameLabelEvidence2d"][:3],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
