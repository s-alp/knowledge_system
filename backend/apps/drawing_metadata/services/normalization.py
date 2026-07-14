from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

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

GEOMETRY_FEATURE_RULES: dict[str, dict[str, str]] = {
    "SxGeomHatch": {"feature": "hatch_or_section", "label": "ハッチング/断面候補", "tag": "図面特徴:ハッチング", "confidence": "medium"},
    "SxGeomSmark": {"feature": "surface_roughness", "label": "表面粗さ", "tag": "加工指示:表面粗さ", "confidence": "medium"},
    "SxGeomCutLine": {"feature": "cut_line", "label": "切断線", "tag": "図面特徴:切断線", "confidence": "medium"},
    "SxGeomTolDatum": {"feature": "datum", "label": "データム", "tag": "幾何公差:データム", "confidence": "medium"},
    "SxGeomTol": {"feature": "geometric_tolerance", "label": "幾何公差", "tag": "幾何公差", "confidence": "medium"},
    "SxGeomFinishMark": {"feature": "finish_mark", "label": "仕上げ記号", "tag": "加工指示:仕上げ記号", "confidence": "medium"},
    "SxGeomElparc2D": {"feature": "slot_candidate", "label": "長穴/楕円弧候補", "tag": "形状候補:長穴", "confidence": "low"},
    "SxGeomCircle2D": {"feature": "hole_candidate", "label": "穴/円候補", "tag": "形状候補:穴", "confidence": "low"},
}

SURFACE_ROUGHNESS_PATTERN = re.compile(r"\b(Ra|Rz|Ry|Rmax)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
MATERIAL_VALUE_PATTERN = re.compile(r"\b(SUS[0-9A-Z]*|SS[0-9A-Z]*|S[0-9]{2}C|A[0-9]{4}|AL|SKD[0-9]*|SCM[0-9]*|FC[0-9]*|FCD[0-9]*)\b", re.IGNORECASE)
REVISION_NOTE_KEYWORDS = ["訂正内容", "改訂内容", "訂正", "改訂", "変更", "修正", "rev", "revision"]
TITLE_BLOCK_LABEL_FRAGMENT_VALUES = {
    "者",
    "人",
    "名",
    "番",
    "番号",
    "号",
    "図",
    "図名",
    "年月日",
    "年",
    "月",
    "日",
    "欄",
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


def _contains_replacement_character(value: str | None) -> bool:
    return bool(value and "\ufffd" in value)


def _looks_like_title_block_label_fragment(value: str) -> bool:
    normalized = _normalize_for_match(value)
    return normalized in {_normalize_for_match(item) for item in TITLE_BLOCK_LABEL_FRAGMENT_VALUES}


def _is_title_block_value_usable(value: str | None, *, max_length: int = 80) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return (
        bool(stripped)
        and len(stripped) <= max_length
        and not _contains_replacement_character(stripped)
        and not _looks_like_title_block_label(stripped)
        and not _looks_like_title_block_label_fragment(stripped)
    )


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
            if _contains_replacement_character(line):
                continue
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


def _build_revision_note_candidates(texts: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, float | None, float | None]] = set()

    for text in texts:
        if text.get("inside_print_area") is False:
            continue
        lines = _text_lines_from_payload(text)
        if not lines:
            continue
        evidence_text = " ".join(lines).strip()
        if not evidence_text or _contains_replacement_character(evidence_text):
            continue
        normalized_evidence = _normalize_for_match(evidence_text)
        matched_keywords = [
            keyword
            for keyword in REVISION_NOTE_KEYWORDS
            if _normalize_for_match(keyword) in normalized_evidence
        ]
        if not matched_keywords:
            continue

        value = None
        for keyword in matched_keywords:
            stripped_value = _strip_label_value(evidence_text, keyword)
            if _is_title_block_value_usable(stripped_value, max_length=160):
                value = stripped_value
                break
        if value is None and _is_title_block_value_usable(evidence_text, max_length=160):
            value = evidence_text

        key = (evidence_text, text.get("position_x"), text.get("position_y"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "value": value,
                "evidence_text": evidence_text,
                "matched_keywords": matched_keywords,
                "confidence": "medium" if value else "low",
                "view_name": text.get("view_name"),
                "layer_no": text.get("layer_no"),
                "position_x": text.get("position_x"),
                "position_y": text.get("position_y"),
                "inside_print_area": text.get("inside_print_area"),
                "source": "2d_revision_text",
            }
        )

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


def _build_geometry_feature_candidates(primitives: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for primitive in primitives:
        if primitive.get("inside_print_area") is False:
            continue
        geometry_type = primitive.get("geometry_type")
        rule = GEOMETRY_FEATURE_RULES.get(geometry_type)
        if not rule:
            continue

        feature = rule["feature"]
        item = grouped.setdefault(
            feature,
            {
                "feature": feature,
                "label": rule["label"],
                "tag": rule["tag"],
                "confidence": rule["confidence"],
                "geometry_type": geometry_type,
                "count": 0,
                "sample_summaries": [],
                "source": "2d_geometry_primitive",
            },
        )
        item["count"] += 1
        summary = primitive.get("summary")
        if summary and len(item["sample_summaries"]) < 3:
            item["sample_summaries"].append(summary)

    return list(grouped.values())


def _double_diameter(radius) -> float | None:
    if radius is None:
        return None
    return radius * 2


def _center_label(primitive: dict) -> str | None:
    x = primitive.get("center_x")
    y = primitive.get("center_y")
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _extract_surface_roughness_values(primitive: dict) -> list[str]:
    values: list[str] = []
    for text in _flatten_strings([primitive.get("val1"), primitive.get("value"), primitive.get("summary")]):
        for match in SURFACE_ROUGHNESS_PATTERN.finditer(text):
            values.append(f"{match.group(1)} {match.group(2)}")
    return _merge_unique(values)


def _merge_unique(items: Iterable) -> list:
    merged: list = []
    seen: set[str] = set()
    for item in items:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _build_geometry_attribute_summary(primitives: list[dict]) -> dict:
    summary = {
        "surface_roughness_count": 0,
        "surface_roughness_values": [],
        "section_feature_count": 0,
        "cut_line_count": 0,
        "hatch_or_section_count": 0,
        "slot_candidate_count": 0,
        "slot_candidate_dimensions": [],
        "hole_candidate_count": 0,
        "hole_candidate_diameters": [],
    }

    roughness_values: list[str] = []
    hole_diameters: list[float] = []
    slot_dimensions: list[dict] = []

    for primitive in primitives:
        if primitive.get("inside_print_area") is False:
            continue
        geometry_type = primitive.get("geometry_type")
        if geometry_type == "SxGeomSmark":
            summary["surface_roughness_count"] += 1
            roughness_values.extend(_extract_surface_roughness_values(primitive))
            continue
        if geometry_type == "SxGeomCutLine":
            summary["cut_line_count"] += 1
            summary["section_feature_count"] += 1
            continue
        if geometry_type == "SxGeomHatch":
            summary["hatch_or_section_count"] += 1
            summary["section_feature_count"] += 1
            continue
        if geometry_type == "SxGeomCircle2D":
            summary["hole_candidate_count"] += 1
            diameter = _double_diameter(primitive.get("radius"))
            if diameter is not None:
                hole_diameters.append(diameter)
            continue
        if geometry_type in {"SxGeomElparc2D", "SxGeomEllipse2D"}:
            summary["slot_candidate_count"] += 1
            radius1 = primitive.get("radius1")
            radius2 = primitive.get("radius2")
            slot_dimensions.append(
                {
                    "geometry_type": geometry_type,
                    "center": _center_label(primitive),
                    "major_radius": radius1,
                    "minor_radius": radius2,
                    "major_diameter": _double_diameter(radius1),
                    "minor_diameter": _double_diameter(radius2),
                    "start_angle": primitive.get("start_angle"),
                    "end_angle": primitive.get("end_angle"),
                }
            )

    summary["surface_roughness_values"] = _merge_unique(roughness_values)
    summary["hole_candidate_diameters"] = _merge_unique(hole_diameters)
    summary["slot_candidate_dimensions"] = slot_dimensions
    return summary


def _material_id(material: dict) -> str | None:
    return material.get("mat_id") or material.get("matid")


def _part_path(part: dict, index: int) -> str:
    return ".".join(part.get("tree_path", []) or [part.get("name") or f"part_{index}"])


def _normalize_material_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    match = MATERIAL_VALUE_PATTERN.search(normalized)
    return match.group(1) if match else None


def _build_part_material_candidates(parts: list[dict], materials: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, str]] = set()

    if len(parts) == 1 and len(materials) == 1:
        part = parts[0]
        material = materials[0]
        part_path = _part_path(part, 0)
        material_id = _material_id(material)
        candidates.append(
            {
                "part_path": part_path,
                "part_name": part.get("name"),
                "material_id": material_id,
                "material_name": material.get("name"),
                "specific_gravity": material.get("specific_gravity"),
                "source": "3d_material_single_part",
                "confidence": "high",
                "reason": "単一パーツかつ3D材質一覧も単一のため、全体材質を当該パーツ候補として採用しました。",
            }
        )
        seen.add((part_path, material_id, "3d_material_single_part"))

    for index, part in enumerate(parts):
        part_path = _part_path(part, index)
        for field_key, field_value in (part.get("ex_info_fields", {}) or {}).items():
            material_text = _normalize_material_text(str(field_value))
            if not material_text:
                continue
            key = (part_path, material_text, f"part_ex_info_fields.{field_key}")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_text,
                    "material_name": str(field_value).strip(),
                    "specific_gravity": None,
                    "source": f"part_ex_info_fields.{field_key}",
                    "confidence": "medium",
                    "reason": "パーツ付加情報の値が材質表記パターンに一致したため、部品材質候補として保持しました。",
                }
            )

    return candidates


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
        "material_probe_status": None,
        "material_ids": [],
        "material_names": [],
        "material_specific_gravities": [],
        "part_material_candidates": [],
        "part_material_candidate_count": 0,
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
        "revision_note_candidates": [],
        "revision_note_count": 0,
        "dimension_values": [],
        "dimension_symbols": [],
        "tolerance_texts": [],
        "weld_note_texts": [],
        "balloon_keys": [],
        "surface_treatment_tokens": [],
        "geometry_feature_candidates": [],
        "surface_roughness_count": 0,
        "surface_roughness_values": [],
        "section_feature_count": 0,
        "cut_line_count": 0,
        "hatch_or_section_count": 0,
        "slot_candidate_count": 0,
        "slot_candidate_dimensions": [],
        "hole_candidate_count": 0,
        "hole_candidate_diameters": [],
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
        materials = raw_extract.get("materials", []) or []
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
        canonical["material_probe_status"] = raw_extract.get("material_probe_status")
        canonical["material_ids"] = _flatten_strings(_material_id(material) for material in materials)
        canonical["material_names"] = _flatten_strings(material.get("name") for material in materials)
        canonical["material_specific_gravities"] = [
            material.get("specific_gravity")
            for material in materials
            if material.get("specific_gravity") is not None
        ]
        canonical["material_keywords"] = _flatten_strings(canonical["material_ids"] + canonical["material_names"])
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
        canonical["part_material_candidates"] = _build_part_material_candidates(parts, materials)
        canonical["part_material_candidate_count"] = len(canonical["part_material_candidates"])
        canonical["material_keywords"] = _merge_unique(
            canonical["material_keywords"]
            + _flatten_strings(candidate.get("material_id") for candidate in canonical["part_material_candidates"])
            + _flatten_strings(candidate.get("material_name") for candidate in canonical["part_material_candidates"])
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
                *canonical["material_keywords"],
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
        primitives = raw_extract.get("geometry_primitives", [])
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
        canonical["revision_note_candidates"] = _build_revision_note_candidates(texts)
        canonical["revision_note_count"] = len(canonical["revision_note_candidates"])
        canonical["geometry_feature_candidates"] = _build_geometry_feature_candidates(primitives)
        canonical.update(_build_geometry_attribute_summary(primitives))

        search_tokens = (
            source_path_tokens
            + canonical["text_tokens"]
            + _flatten_strings(str(value) for value in canonical["title_block_fields"].values())
            + _flatten_strings(candidate.get("value") for candidate in canonical["revision_note_candidates"])
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
