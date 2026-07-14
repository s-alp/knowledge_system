from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings

from apps.drawing_metadata.services.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    MAKER_KEYWORDS,
    SPEC_KEYWORDS,
)


TITLE_BLOCK_FIELD_RULES: dict[str, dict[str, object]] = {
    "drawing_number": {"label": "図番", "keywords": ["図番", "図面番号", "品番", "部品番号", "drawing no", "dwg no", "part no"], "max_value_length": 80},
    "drawing_name": {"label": "図面名", "keywords": ["図名", "図面名", "品名", "名称", "title", "name"], "max_value_length": 80},
    "material": {"label": "材質", "keywords": ["材質", "材料", "material", "matl"], "max_value_length": 40},
    "weight": {"label": "重量", "keywords": ["重量", "質量", "weight", "mass", "wt"], "max_value_length": 40},
    "surface_treatment": {"label": "表面処理", "keywords": ["表面処理", "表処", "処理", "surface treatment", "finish"], "max_value_length": 40},
    "coating_instruction": {"label": "塗装指示", "keywords": ["塗装", "塗装色", "paint", "coating"], "max_value_length": 40},
    "scale": {"label": "尺度", "keywords": ["尺度", "縮尺", "scale"], "max_value_length": 24},
    "designer": {"label": "設計者", "keywords": ["設計", "作成", "製図", "drawn", "designed"], "max_value_length": 40},
    "checker": {"label": "検図者", "keywords": ["検図", "照査", "check", "checked"], "max_value_length": 40},
    "approver": {"label": "承認者", "keywords": ["承認", "認可", "approved"], "max_value_length": 40},
    "date": {"label": "日付", "keywords": ["日付", "年月日", "date"], "max_value_length": 40},
    "revision": {"label": "改訂", "keywords": ["改訂", "訂正", "rev", "revision"], "max_value_length": 40},
    "prfx": {"label": "PRFX", "keywords": ["prfx", "p/rfx", "prefix"], "max_value_length": 40},
    "unit_number": {"label": "ユニット番号", "keywords": ["ユニット", "unit", "unit no"], "max_value_length": 40},
}


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


def _normalize_for_match(value: str) -> str:
    return "".join(value.lower().replace("　", " ").split())


def _strip_label_value(text: str, keyword: str) -> str | None:
    lower_text = text.lower()
    lower_keyword = keyword.lower()
    index = lower_text.find(lower_keyword)
    if index < 0:
        normalized_text = _normalize_for_match(text)
        normalized_keyword = _normalize_for_match(keyword)
        if normalized_keyword not in normalized_text:
            return None
        return None

    value = text[:index] + text[index + len(keyword) :]
    value = value.strip(" 　:：=＝-－_/／[]【】()（）")
    return value or None


def _text_lines_from_payload(text: dict) -> list[str]:
    lines = _flatten_strings(text.get("text_lines", []) or [])
    joined_text = text.get("joined_text")
    if joined_text and joined_text not in lines:
        lines.append(joined_text)
    return lines


def _looks_like_title_block_label(value: str) -> bool:
    normalized = _normalize_for_match(value)
    return any(
        normalized == _normalize_for_match(str(keyword))
        for rule in TITLE_BLOCK_FIELD_RULES.values()
        for keyword in rule["keywords"]
    )


def _is_title_block_value_usable(value: str | None, *, max_length: int = 80) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return bool(stripped) and len(stripped) <= max_length and not _looks_like_title_block_label(stripped)


def _build_title_block_candidates(texts: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str, str | None, float | None, float | None]] = set()

    for text in texts:
        if text.get("inside_print_area") is False:
            continue
        lines = _text_lines_from_payload(text)
        if not lines:
            continue

        for line_index, line in enumerate(lines):
            normalized_line = _normalize_for_match(line)
            for field, rule in TITLE_BLOCK_FIELD_RULES.items():
                max_value_length = int(rule.get("max_value_length", 80))
                for keyword in rule["keywords"]:
                    normalized_keyword = _normalize_for_match(str(keyword))
                    if normalized_keyword not in normalized_line:
                        continue

                    value = _strip_label_value(line, str(keyword))
                    confidence = "medium" if _is_title_block_value_usable(value, max_length=max_value_length) else "low"
                    if not value and line_index + 1 < len(lines):
                        next_value = lines[line_index + 1].strip()
                        if _is_title_block_value_usable(next_value, max_length=max_value_length):
                            value = next_value
                            confidence = "medium"

                    key = (field, line, value, text.get("position_x"), text.get("position_y"))
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        {
                            "field": field,
                            "label": rule["label"],
                            "value": value,
                            "evidence_text": line,
                            "confidence": confidence,
                            "view_name": text.get("view_name"),
                            "layer_no": text.get("layer_no"),
                            "position_x": text.get("position_x"),
                            "position_y": text.get("position_y"),
                            "inside_print_area": text.get("inside_print_area"),
                            "source": "2d_text",
                        }
                    )
                    break

    return candidates


def _select_title_block_fields(candidates: list[dict]) -> dict:
    selected: dict = {}
    for candidate in candidates:
        if candidate.get("confidence") != "medium":
            continue
        value = candidate.get("value")
        field = candidate.get("field")
        rule = TITLE_BLOCK_FIELD_RULES.get(field, {})
        max_value_length = int(rule.get("max_value_length", 80))
        if not _is_title_block_value_usable(value, max_length=max_value_length):
            continue
        if field and field not in selected:
            selected[field] = value
    return selected


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
        "mass_probe_status": None,
        "mass_unit_name": None,
        "mass_element_count": None,
        "mass_value": None,
        "weight_value": None,
        "volume_value": None,
        "area_value": None,
        "density_value": None,
        "center_of_gravity": None,
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
        "title_block_candidates": [],
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
        mass_properties = raw_extract.get("mass_properties", {}) or {}
        canonical["top_part_name"] = top_part.get("name")
        canonical["top_part_comment"] = top_part.get("comment")
        canonical["top_part_ex_info"] = top_part.get("ex_info")
        canonical["mass_probe_status"] = raw_extract.get("mass_probe_status")
        canonical["mass_unit_name"] = mass_properties.get("unit_name")
        canonical["mass_element_count"] = mass_properties.get("element_count")
        canonical["mass_value"] = mass_properties.get("mass")
        canonical["weight_value"] = mass_properties.get("weight")
        canonical["volume_value"] = mass_properties.get("volume")
        canonical["area_value"] = mass_properties.get("area")
        canonical["density_value"] = mass_properties.get("density")
        if all(mass_properties.get(key) is not None for key in ("center_of_gravity_x", "center_of_gravity_y", "center_of_gravity_z")):
            canonical["center_of_gravity"] = (
                f"{mass_properties.get('center_of_gravity_x')}, "
                f"{mass_properties.get('center_of_gravity_y')}, "
                f"{mass_properties.get('center_of_gravity_z')}"
            )
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
        canonical["title_block_candidates"] = _build_title_block_candidates(texts)
        canonical["title_block_fields"] = _select_title_block_fields(canonical["title_block_candidates"])

        search_tokens = (
            source_path_tokens
            + canonical["text_tokens"]
            + _flatten_strings(str(value) for value in canonical["title_block_fields"].values())
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
