from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.dictionaries import load_keyword_mapping
from apps.drawing_metadata.services.text_matching import (
    build_token_sources,
    flatten_match_evidence,
    match_dictionary,
)


def _flatten_strings(values: Iterable[str | None]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not value:
            continue
        stripped = value.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _structured_parts(parts: list[dict]) -> list[dict]:
    """部品単位の name/comment/参照情報の対応を崩さずに保持する。"""
    structured: list[dict] = []
    for part in parts:
        structured.append(
            {
                "name": part.get("name"),
                "comment": part.get("comment"),
                "tree_path": list(part.get("tree_path") or []),
                "ref_model_name": part.get("ref_model_name"),
                "ref_model_path": part.get("ref_model_path"),
                "is_external": bool(part.get("is_external")),
                "is_mirror": bool(part.get("is_mirror")),
                "is_unloaded": bool(part.get("is_unloaded")),
            }
        )
    return structured


def normalize_raw_extract(raw_payload: dict) -> dict:
    source_kind = raw_payload.get("source_kind")
    raw_extract = raw_payload.get("raw_extract", {})
    warnings = raw_payload.get("warnings") or []

    canonical = {
        "drawing_number": None,
        "drawing_name": None,
        "revision": None,
        "source_format": raw_payload.get("source_format", "icad"),
        "source_kind": source_kind,
        "document_kind": None,
        "customer_name": None,
        "customer_name_candidates": [],
        "project_name": None,
        "equipment_name": None,
        "equipment_category": None,
        "equipment_category_candidates": [],
        "module_name": None,
        "status": None,
        "owner": None,
        "design_purpose": None,
        "paper_size": None,
        "extraction_status": "partial" if warnings else "success",
        "ocr_used": False,
        "confidence_summary": "medium",
        "top_part_name": None,
        "top_part_comment": None,
        "top_part_ex_info": None,
        "parts": [],
        "part_names": [],
        "part_comments": [],
        "part_tree_paths": [],
        "ref_model_names": [],
        "ref_model_paths": [],
        "external_part_exists": False,
        "mirror_part_exists": False,
        "unresolved_part_exists": False,
        "text_tokens": [],
        "label_texts": [],
        "title_block_fields": {},
        "dimension_values": [],
        "dimension_symbols": [],
        "tolerance_texts": [],
        "weld_note_texts": [],
        "balloon_keys": [],
        "surface_treatment_tokens": [],
        "spec_tokens": [],
        "spec_names": [],
        "part_keywords": [],
        "material_keywords": [],
        "maker_keywords": [],
        "process_keywords": [],
        "heat_treatment_keywords": [],
        "inspection_keywords": [],
        "change_keywords": [],
        "issue_keywords": [],
        "match_evidence": {},
        "normalizer_version": settings.DRAWING_METADATA_NORMALIZER_VERSION,
    }

    if source_kind == "3d":
        top_part = raw_extract.get("top_part", {})
        parts = raw_extract.get("parts", [])
        canonical["top_part_name"] = top_part.get("name")
        canonical["top_part_comment"] = top_part.get("comment")
        canonical["top_part_ex_info"] = top_part.get("ex_info")
        canonical["parts"] = _structured_parts(parts)
        canonical["part_names"] = _flatten_strings(part.get("name") for part in parts)
        canonical["part_comments"] = _flatten_strings(part.get("comment") for part in parts)
        canonical["part_tree_paths"] = [" > ".join(part.get("tree_path", [])) for part in parts if part.get("tree_path")]
        canonical["ref_model_names"] = _flatten_strings(part.get("ref_model_name") for part in parts)
        canonical["ref_model_paths"] = _flatten_strings(part.get("ref_model_path") for part in parts)
        canonical["external_part_exists"] = any(part.get("is_external") for part in parts)
        canonical["mirror_part_exists"] = any(part.get("is_mirror") for part in parts)
        canonical["unresolved_part_exists"] = any(part.get("is_unloaded") for part in parts)

        token_sources = build_token_sources(
            [
                ("top_part_name", [top_part.get("name")]),
                ("top_part_comment", [top_part.get("comment")]),
                ("top_part_ex_info", [top_part.get("ex_info")]),
                ("part_names", canonical["part_names"]),
                ("part_comments", canonical["part_comments"]),
                ("ref_model_names", canonical["ref_model_names"]),
            ]
        )
    else:
        texts = raw_extract.get("texts", [])
        dimensions = raw_extract.get("dimensions", [])
        weld_notes = raw_extract.get("weld_notes", [])
        balloons = raw_extract.get("balloons", [])
        tolerances = raw_extract.get("tolerances", [])

        canonical["text_tokens"] = _flatten_strings(
            text_line
            for text in texts
            for text_line in text.get("text_lines", [])
        )
        canonical["label_texts"] = _flatten_strings(text.get("joined_text") for text in texts if text.get("source_type") == "label")
        canonical["dimension_values"] = _flatten_strings(
            value
            for dimension in dimensions
            for value in [dimension.get("value_1"), dimension.get("value_2")]
        )
        canonical["dimension_symbols"] = _flatten_strings(
            value
            for dimension in dimensions
            for value in [dimension.get("mark_2"), dimension.get("mark_3"), dimension.get("front_word"), dimension.get("back_word")]
        )
        canonical["weld_note_texts"] = _flatten_strings(note.get("text") for note in weld_notes)
        canonical["balloon_keys"] = _flatten_strings(balloon.get("text") for balloon in balloons)
        canonical["tolerance_texts"] = _flatten_strings(tolerance.get("text") for tolerance in tolerances)
        # spec_tokens は生トークン、spec_names は辞書一致した正規規格名。混在させない。
        canonical["spec_tokens"] = _flatten_strings(canonical["text_tokens"] + canonical["tolerance_texts"])

        token_sources = build_token_sources(
            [
                ("text_tokens", canonical["text_tokens"]),
                ("dimension_symbols", canonical["dimension_symbols"]),
                ("weld_note_texts", canonical["weld_note_texts"]),
                ("balloon_keys", canonical["balloon_keys"]),
                ("tolerance_texts", canonical["tolerance_texts"]),
            ]
        )

    canonical["part_keywords"] = [source["token"] for source in token_sources]

    customer_matches = match_dictionary(token_sources, load_keyword_mapping(TagDictionaryEntry.KIND_CUSTOMER))
    equipment_matches = match_dictionary(
        token_sources, load_keyword_mapping(TagDictionaryEntry.KIND_EQUIPMENT_CATEGORY)
    )
    maker_matches = match_dictionary(token_sources, load_keyword_mapping(TagDictionaryEntry.KIND_MAKER))
    spec_matches = match_dictionary(token_sources, load_keyword_mapping(TagDictionaryEntry.KIND_SPEC))

    canonical["customer_name_candidates"] = [match["value"] for match in customer_matches]
    canonical["equipment_category_candidates"] = [match["value"] for match in equipment_matches]
    if customer_matches:
        canonical["customer_name"] = customer_matches[0]["value"]
    if equipment_matches:
        canonical["equipment_category"] = equipment_matches[0]["value"]
    canonical["maker_keywords"] = [match["value"] for match in maker_matches]
    canonical["spec_names"] = [match["value"] for match in spec_matches]

    canonical["match_evidence"] = {
        "customer_name": flatten_match_evidence(customer_matches),
        "equipment_category": flatten_match_evidence(equipment_matches),
        "maker_keywords": flatten_match_evidence(maker_matches),
        "spec_names": flatten_match_evidence(spec_matches),
    }

    base_confidence = "high" if source_kind == "3d" else "medium"
    has_ambiguity = len(customer_matches) > 1 or len(equipment_matches) > 1
    if has_ambiguity:
        base_confidence = "medium" if base_confidence == "high" else "low"
    canonical["confidence_summary"] = base_confidence

    return canonical
