from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata


RAG_PAYLOAD_SCHEMA_VERSION = "drawing_metadata_rag_payload.v1"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return [item for item in value if _has_value(item)]
    if _has_value(value):
        return [value]
    return []


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            text = value.get("tag") or value.get("value") or value.get("text")
        else:
            text = value
        if not _has_value(text):
            continue
        normalized = str(text).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _first_value(*values: Any) -> str | None:
    for value in values:
        if _has_value(value):
            return str(value).strip()
    return None


def _source_folder(source_path: str) -> str:
    if not source_path:
        return ""
    return str(PureWindowsPath(source_path).parent)


def _search_text_chunks(canonical: dict, tags: list[str]) -> list[str]:
    chunks = [
        canonical.get("drawing_number"),
        canonical.get("drawing_name"),
        canonical.get("customer_name"),
        canonical.get("project_name"),
        canonical.get("equipment_name"),
        canonical.get("equipment_category"),
        canonical.get("module_name"),
        canonical.get("top_part_name"),
        canonical.get("top_part_comment"),
        canonical.get("top_part_ex_info"),
    ]
    chunks.extend(_as_list(canonical.get("part_names")))
    chunks.extend(_as_list(canonical.get("part_comments")))
    chunks.extend(_as_list(canonical.get("material_keywords")))
    chunks.extend(_as_list(canonical.get("surface_treatment_tokens")))
    chunks.extend(_as_list(canonical.get("process_keywords")))
    chunks.extend(_as_list(canonical.get("weld_note_texts")))
    chunks.extend(_as_list(canonical.get("spec_tokens")))
    chunks.extend(tags)
    return _unique_strings(chunks)


def _review_flags(canonical: dict, composed: dict) -> list[dict]:
    flags: list[dict] = []
    for conflict in composed.get("conflicts", []) or []:
        flags.append(
            {
                "code": "cross_source_conflict",
                "severity": "medium",
                "attribute": conflict.get("attribute"),
                "message": "2D/3Dの抽出値が一致しないため、検索投入前に確認してください。",
            }
        )
    for material in _as_list(canonical.get("unresolved_material_keywords")):
        flags.append(
            {
                "code": "unresolved_material",
                "severity": "low",
                "attribute": "unresolved_material_keywords",
                "value": material,
                "message": "材質コードの意味が未確定です。低信頼タグとして扱います。",
            }
        )
    return flags


def build_rag_payload(drawing: RegisteredDrawing) -> dict:
    composed = compose_drawing_metadata(drawing)
    canonical = composed.get("canonicalAttributes", {}) or {}
    tags = _unique_strings(composed.get("derivedTags", []) or [])
    review_flags = _review_flags(canonical, composed)
    source_path = drawing.source_path or ""

    return {
        "schemaVersion": RAG_PAYLOAD_SCHEMA_VERSION,
        "drawing": {
            "drawingId": str(drawing.id),
            "hostDrawingId": drawing.host_drawing_id,
            "filename": drawing.filename,
            "sourcePath": source_path,
            "sourceFolder": _source_folder(source_path),
            "sourceFormat": drawing.source_format,
        },
        "preFilters": {
            "customerName": _first_value(canonical.get("customer_name")),
            "projectName": _first_value(canonical.get("project_name")),
            "equipmentCategory": _first_value(canonical.get("equipment_category")),
            "documentKind": _first_value(canonical.get("document_kind")),
            "sourceFormat": drawing.source_format,
            "drawingNumber": _first_value(canonical.get("drawing_number"), canonical.get("part_number")),
            "drawingName": _first_value(canonical.get("drawing_name")),
            "paperSize": _first_value(canonical.get("paper_size"), canonical.get("drawing_size")),
        },
        "rankingSignals": {
            "partNames": _unique_strings(_as_list(canonical.get("part_names"))),
            "makerKeywords": _unique_strings(_as_list(canonical.get("maker_keywords"))),
            "dimensionValues": _unique_strings(_as_list(canonical.get("dimension_values"))),
            "specTokens": _unique_strings(_as_list(canonical.get("spec_tokens"))),
            "processKeywords": _unique_strings(_as_list(canonical.get("process_keywords"))),
            "weldNoteTexts": _unique_strings(_as_list(canonical.get("weld_note_texts"))),
            "materialKeywords": _unique_strings(_as_list(canonical.get("material_keywords"))),
            "unresolvedMaterialKeywords": _unique_strings(_as_list(canonical.get("unresolved_material_keywords"))),
            "surfaceTreatmentTokens": _unique_strings(_as_list(canonical.get("surface_treatment_tokens"))),
            "heatTreatmentKeywords": _unique_strings(_as_list(canonical.get("heat_treatment_keywords"))),
            "inspectionKeywords": _unique_strings(_as_list(canonical.get("inspection_keywords"))),
            "changeKeywords": _unique_strings(_as_list(canonical.get("change_keywords"))),
            "issueKeywords": _unique_strings(_as_list(canonical.get("issue_keywords"))),
            "tags": tags,
        },
        "partMaterialCandidates": canonical.get("part_material_candidates", []) or [],
        "searchTextChunks": _search_text_chunks(canonical, tags),
        "reconciliation": {
            "conflicts": composed.get("conflicts", []) or [],
            "diagnosticConflicts": composed.get("diagnosticConflicts", []) or [],
            "reviewFlags": review_flags,
            "requiresReview": bool(review_flags),
        },
        "sourceAttributes": {
            "canonicalAttributes": canonical,
            "reconciledAttributes": composed.get("reconciledAttributes", []) or [],
        },
    }
