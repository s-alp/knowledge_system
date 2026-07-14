from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings

from apps.drawing_metadata.services.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    MAKER_KEYWORDS,
    SPEC_KEYWORDS,
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


def _match_dictionary(tokens: Iterable[str], mapping: dict[str, list[str]]) -> str | None:
    lowered = " ".join(token.lower() for token in tokens)
    for canonical, candidates in mapping.items():
        if any(candidate.lower() in lowered for candidate in candidates):
            return canonical
    return None


def normalize_raw_extract(raw_payload: dict) -> dict:
    source_kind = raw_payload.get("source_kind")
    raw_extract = raw_payload.get("raw_extract", {})
    source_file = raw_payload.get("source_file", {}) or raw_extract.get("_source_file", {}) or {}
    source_path_tokens = _flatten_strings(
        [
            source_file.get("full_path"),
            source_file.get("directory_path"),
            source_file.get("file_name"),
            source_file.get("file_name_without_extension"),
        ]
    )

    canonical = {
        "drawing_number": None,
        "drawing_name": None,
        "revision": None,
        "source_format": raw_payload.get("source_format", "icad"),
        "source_kind": source_kind,
        "document_kind": None,
        "customer_name": None,
        "project_name": None,
        "equipment_name": None,
        "equipment_category": None,
        "module_name": None,
        "status": None,
        "owner": None,
        "design_purpose": None,
        "paper_size": None,
        "extraction_status": "success",
        "ocr_used": False,
        "confidence_summary": "medium",
        "source_full_path": source_file.get("full_path"),
        "source_directory_path": source_file.get("directory_path"),
        "source_file_name": source_file.get("file_name"),
        "source_file_stem": source_file.get("file_name_without_extension"),
        "source_extension": source_file.get("extension"),
        "source_path_tokens": source_path_tokens,
        "top_part_name": None,
        "top_part_comment": None,
        "top_part_ex_info": None,
        "part_names": [],
        "part_comments": [],
        "part_tree_paths": [],
        "part_ex_info_fields": {},
        "part_ex_info_tokens": [],
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
        "part_keywords": [],
        "material_keywords": [],
        "maker_keywords": [],
        "process_keywords": [],
        "heat_treatment_keywords": [],
        "inspection_keywords": [],
        "change_keywords": [],
        "issue_keywords": [],
        "normalizer_version": settings.DRAWING_METADATA_NORMALIZER_VERSION,
    }

    if source_kind == "3d":
        top_part = raw_extract.get("top_part", {})
        parts = raw_extract.get("parts", [])
        canonical["top_part_name"] = top_part.get("name")
        canonical["top_part_comment"] = top_part.get("comment")
        canonical["top_part_ex_info"] = top_part.get("ex_info")
        canonical["part_names"] = _flatten_strings(part.get("name") for part in parts)
        canonical["part_comments"] = _flatten_strings(part.get("comment") for part in parts)
        canonical["part_tree_paths"] = [" > ".join(part.get("tree_path", [])) for part in parts if part.get("tree_path")]
        canonical["part_ex_info_fields"] = {
            ".".join(part.get("tree_path", []) or [part.get("name") or f"part_{index}"]): part.get("ex_info_fields", {})
            for index, part in enumerate(parts)
            if part.get("ex_info_fields")
        }
        canonical["part_ex_info_tokens"] = _flatten_strings(
            value
            for part in parts
            for value in [part.get("ex_info"), *(part.get("ex_info_fields", {}) or {}).values()]
        )
        canonical["ref_model_names"] = _flatten_strings(part.get("ref_model_name") for part in parts)
        canonical["ref_model_paths"] = _flatten_strings(part.get("ref_model_path") for part in parts)
        canonical["external_part_exists"] = any(part.get("is_external") for part in parts)
        canonical["mirror_part_exists"] = any(part.get("is_mirror") for part in parts)
        canonical["unresolved_part_exists"] = any(part.get("is_unloaded") for part in parts)

        search_tokens = _flatten_strings(
            [
                *source_path_tokens,
                top_part.get("name"),
                top_part.get("comment"),
                top_part.get("ex_info"),
                *canonical["part_names"],
                *canonical["part_comments"],
                *canonical["part_ex_info_tokens"],
                *canonical["ref_model_names"],
            ]
        )
        canonical["part_keywords"] = search_tokens
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
        canonical["spec_tokens"] = _flatten_strings(canonical["text_tokens"] + canonical["tolerance_texts"])

        search_tokens = (
            source_path_tokens
            + canonical["text_tokens"]
            + canonical["dimension_symbols"]
            + canonical["weld_note_texts"]
            + canonical["balloon_keys"]
            + canonical["tolerance_texts"]
        )
        canonical["part_keywords"] = search_tokens

    customer_name = _match_dictionary(canonical["part_keywords"], CUSTOMER_KEYWORDS)
    equipment_category = _match_dictionary(canonical["part_keywords"], EQUIPMENT_CATEGORY_KEYWORDS)

    if customer_name:
        canonical["customer_name"] = customer_name
    if equipment_category:
        canonical["equipment_category"] = equipment_category

    for maker, candidates in MAKER_KEYWORDS.items():
        if any(candidate in " ".join(token.lower() for token in canonical["part_keywords"]) for candidate in candidates):
            canonical["maker_keywords"].append(maker)

    for spec, candidates in SPEC_KEYWORDS.items():
        if any(candidate in " ".join(token.lower() for token in canonical["part_keywords"]) for candidate in candidates):
            canonical["spec_tokens"].append(spec)

    if source_kind == "3d":
        canonical["confidence_summary"] = "high"

    return canonical
