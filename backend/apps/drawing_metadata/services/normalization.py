from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from django.conf import settings

from apps.drawing_metadata.services.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    MAKER_KEYWORDS,
    MATERIAL_CLASSIFICATION_RULES,
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
    "prfx": {"label": "PRFX", "keywords": ["prfx", "p/rfx", "prefix", "pfx"], "max_value_length": 40},
    "unit_number": {"label": "ユニット番号", "keywords": ["ユニット", "unit no", "unit_no", "unitno", "unit number"], "max_value_length": 40},
}

GEOMETRY_FEATURE_RULES: dict[str, dict[str, object]] = {
    "SxGeomHatch": {"feature": "hatch_or_section", "label": "ハッチング/断面候補", "classification_label": "ハッチング/断面候補", "confidence": "medium"},
    "SxGeomSmark": {"feature": "surface_roughness", "label": "表面粗さ", "classification_label": "表面粗さ記号あり", "confidence": "medium"},
    "SxGeomCutLine": {"feature": "cut_line", "label": "切断線", "classification_label": "切断線あり", "confidence": "medium"},
    "SxGeomTolDatum": {"feature": "datum", "label": "データム", "classification_label": "データム記号あり", "confidence": "medium"},
    "SxGeomTol": {"feature": "geometric_tolerance", "label": "幾何公差", "classification_label": "幾何公差記号あり", "confidence": "medium"},
    "SxGeomFinishMark": {"feature": "finish_mark", "label": "仕上げ記号", "classification_label": "仕上げ記号あり", "confidence": "medium"},
    "SxGeomElparc2D": {"feature": "slot_candidate", "label": "長穴/楕円弧候補", "classification_label": "長穴/楕円弧候補", "confidence": "low"},
    "SxGeomCircle2D": {"feature": "hole_candidate", "label": "穴/円候補", "classification_label": "穴/円候補", "confidence": "low"},
}
GEOMETRY_FEATURE_TAG_EXCLUSION_REASON = (
    "製造記号や形状候補の存在だけでは検索・分類タグとして粗いため、"
    "図面証拠として保持し、自動タグには採用しません。"
)

TWO_D_SECTION_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("title_block", "図枠", "図番、材質、担当者、改訂などの図枠欄候補です。"),
    ("drawing_body", "中央図面", "形状線、円、スプラインなど中央図面を構成する図形候補です。"),
    ("dimensions", "寸法", "寸法値、接頭/接尾記号、公差寸法などの寸法候補です。"),
    ("notes", "注記", "図面内の一般注記、訂正内容、文字注記の候補です。"),
    ("balloons", "バルーン", "部品番号や参照番号として使われるバルーン候補です。"),
    ("manufacturing_symbols", "製造記号", "表面粗さ、切断線、データム、幾何公差、溶接記号などの候補です。"),
)
MANUFACTURING_GEOMETRY_TYPES = set(GEOMETRY_FEATURE_RULES)

SURFACE_ROUGHNESS_PATTERN = re.compile(r"\b(Ra|Rz|Ry|Rmax)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
MATERIAL_VALUE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(SUS[0-9][0-9A-Z-]*|SUS(?!-)|SS400[A-Z-]*|SPCC|S[0-9]{2}C|A[0-9]{4}P?|AL|SKD[0-9]*|SKS[0-9]*|SCM[0-9]*|FC[0-9]*|FCD[0-9]*|PETG|PET|POM|PVC|PTFE|PPS|NBR|EPDM|FKM|PP)(?![A-Z0-9])",
    re.IGNORECASE,
)
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
    "使用",
}


def _material_lookup_key(value: str | None) -> str:
    if not value:
        return ""
    return "".join(unicodedata.normalize("NFKC", value).upper().split())


MATERIAL_CLASSIFICATION_BY_ALIAS: dict[str, dict[str, str]] = {}
for canonical_material, rule in MATERIAL_CLASSIFICATION_RULES.items():
    for alias in [canonical_material, *rule.get("aliases", [])]:
        MATERIAL_CLASSIFICATION_BY_ALIAS[_material_lookup_key(alias)] = {
            "canonical": canonical_material,
            "status": str(rule["status"]),
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


def _extract_labeled_field_candidates(field: str, texts: Iterable[str | None]) -> list[str]:
    rule = TITLE_BLOCK_FIELD_RULES[field]
    candidates: list[str] = []
    for text in _flatten_strings(texts):
        normalized_text = unicodedata.normalize("NFKC", text)
        for keyword in rule["keywords"]:
            value = _strip_label_value(normalized_text, str(keyword))
            if _is_field_value_usable(field, value, normalized_text):
                candidates.append(str(value).strip())
    return _merge_unique(candidates)


def _extract_identity_candidates_from_part_ex_info(parts: Iterable[dict], field: str) -> list[str]:
    rule = TITLE_BLOCK_FIELD_RULES[field]
    candidates: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        fields = part.get("ex_info_fields") or {}
        if not isinstance(fields, dict):
            continue
        for key, value in fields.items():
            key_text = unicodedata.normalize("NFKC", str(key))
            value_text = unicodedata.normalize("NFKC", str(value))
            evidence_text = f"{key_text} {value_text}".strip()
            key_matches_field = any(_normalize_for_match(str(keyword)) in _normalize_for_match(key_text) for keyword in rule["keywords"])
            if key_matches_field and _is_field_value_usable(field, value_text, evidence_text):
                candidates.append(value_text.strip())
                continue
            candidates.extend(_extract_labeled_field_candidates(field, [evidence_text, value_text]))
    return _merge_unique(candidates)


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
    normalized_without_number = re.sub(r"^[0-9０-９]+[.．、\-\s　]*", "", normalized)
    fragment_values = {_normalize_for_match(item) for item in TITLE_BLOCK_LABEL_FRAGMENT_VALUES}
    return normalized in fragment_values or normalized_without_number in fragment_values


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


def _is_field_value_usable(field: str, value: str | None, evidence_text: str) -> bool:
    if not _is_title_block_value_usable(
        value,
        max_length=int(TITLE_BLOCK_FIELD_RULES.get(field, {}).get("max_value_length", 80)),
    ):
        return False
    normalized_value = unicodedata.normalize("NFKC", str(value)).strip()
    normalized_evidence = unicodedata.normalize("NFKC", evidence_text).strip()

    if field == "drawing_number" and any(token in normalized_evidence for token in ("参考", "元図")):
        return False
    if field == "material":
        classification = _classify_material_value(normalized_value, allow_unknown=False)
        if classification["status"] == "unresolved":
            return False
        if re.search(r"(?:丸棒|角棒|パイプ|板厚|φ\s*\d)", normalized_value, re.IGNORECASE) and not MATERIAL_VALUE_PATTERN.search(normalized_value.upper()):
            return False
    if field == "weight":
        if not re.search(r"[-+]?\d+(?:\.\d+)?\s*(?:kg|g|t|ｋｇ|ｇ)\b", normalized_value, re.IGNORECASE):
            return False
        if any(token in normalized_evidence for token in ("吸引力", "倍", "÷")):
            return False
    if field == "coating_instruction" and "仕上げ面不可" in normalized_value:
        return False
    return True


def _has_print_frames(raw_extract: dict) -> bool:
    print_frames = raw_extract.get("print_frames") or []
    return isinstance(print_frames, list) and bool(print_frames)


def _is_usable_print_area_item(item: dict, *, has_print_frames: bool) -> bool:
    inside_print_area = item.get("inside_print_area")
    if inside_print_area is False:
        return False
    if has_print_frames and inside_print_area is not True:
        return False
    return True


def _trusted_print_area_items(items: Iterable[dict], *, has_print_frames: bool) -> list[dict]:
    return [
        item
        for item in items
        if isinstance(item, dict) and _is_usable_print_area_item(item, has_print_frames=has_print_frames)
    ]


def _print_area_count_summary(items: Iterable[dict]) -> dict[str, int]:
    counts = {"inside": 0, "outside": 0, "unknown": 0}
    for item in items:
        if not isinstance(item, dict):
            continue
        inside_print_area = item.get("inside_print_area")
        if inside_print_area is True:
            counts["inside"] += 1
        elif inside_print_area is False:
            counts["outside"] += 1
        else:
            counts["unknown"] += 1
    return counts


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _item_position(item: dict) -> str | None:
    x = _first_present(item.get("position_x"), item.get("center_x"), item.get("x1"))
    y = _first_present(item.get("position_y"), item.get("center_y"), item.get("y1"))
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _sample_text(value: object, *, max_length: int = 120) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def _item_display_text(item: dict) -> str | None:
    if item.get("evidence_text"):
        return _sample_text(item["evidence_text"])
    if item.get("joined_text"):
        return _sample_text(item["joined_text"])
    text_lines = item.get("text_lines")
    if isinstance(text_lines, list) and text_lines:
        return _sample_text(" / ".join(str(line) for line in text_lines if line))
    dimension_values = _flatten_strings(
        str(value)
        for value in [
            item.get("value_1"),
            item.get("value_2"),
            item.get("value1"),
            item.get("value2"),
            item.get("mark_2"),
            item.get("mark_3"),
            item.get("mark2"),
            item.get("mark3"),
            item.get("front_word"),
            item.get("back_word"),
        ]
        if value is not None
    )
    if dimension_values:
        return _sample_text(" ".join(dimension_values))
    if isinstance(item.get("summary"), str) and "line_color=" in item["summary"]:
        return "寸法候補"
    return _sample_text(item.get("text") or item.get("geometry_type") or item.get("summary"))


def _section_samples(items: Iterable[dict], *, limit: int = 5) -> list[dict]:
    samples: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sample = {
            "text": _item_display_text(item),
            "source_type": item.get("source_type") or item.get("geometry_type") or item.get("field"),
            "view_name": item.get("view_name"),
            "layer_no": item.get("layer_no"),
            "position": _item_position(item),
            "inside_print_area": item.get("inside_print_area"),
        }
        samples.append({key: value for key, value in sample.items() if value is not None})
        if len(samples) >= limit:
            break
    return samples


def _make_2d_section(
    *,
    key: str,
    all_items: list[dict],
    trusted_items: list[dict],
    source_names: list[str],
) -> dict:
    definition_by_key = {definition_key: (label, description) for definition_key, label, description in TWO_D_SECTION_DEFINITIONS}
    label, description = definition_by_key[key]
    print_area_counts = _print_area_count_summary(all_items)
    return {
        "key": key,
        "label": label,
        "description": description,
        "source_names": source_names,
        "total_count": len(all_items),
        "trusted_count": len(trusted_items),
        "inside_print_area_count": print_area_counts["inside"],
        "outside_print_area_count": print_area_counts["outside"],
        "unknown_print_area_count": print_area_counts["unknown"],
        "samples": _section_samples(trusted_items),
    }


def _build_2d_sections(
    *,
    raw_extract: dict,
    canonical: dict,
    has_print_frames: bool,
    trusted_texts: list[dict],
    trusted_dimensions: list[dict],
    trusted_weld_notes: list[dict],
    trusted_balloons: list[dict],
    trusted_tolerances: list[dict],
) -> dict:
    texts = raw_extract.get("texts", []) or []
    dimensions = raw_extract.get("dimensions", []) or []
    primitives = raw_extract.get("geometry_primitives", []) or []
    weld_notes = raw_extract.get("weld_notes", []) or []
    balloons = raw_extract.get("balloons", []) or []
    tolerances = raw_extract.get("tolerances", []) or []
    trusted_primitives = _trusted_print_area_items(primitives, has_print_frames=has_print_frames)

    title_block_candidates = canonical.get("title_block_candidates", []) or []
    title_block_evidence = {candidate.get("evidence_text") for candidate in title_block_candidates if candidate.get("evidence_text")}
    revision_note_candidates = canonical.get("revision_note_candidates", []) or []

    manufacturing_primitives = [
        primitive
        for primitive in primitives
        if primitive.get("geometry_type") in MANUFACTURING_GEOMETRY_TYPES
    ]
    trusted_manufacturing_primitives = [
        primitive
        for primitive in trusted_primitives
        if primitive.get("geometry_type") in MANUFACTURING_GEOMETRY_TYPES
    ]
    drawing_body_primitives = [
        primitive
        for primitive in primitives
        if primitive.get("geometry_type") not in MANUFACTURING_GEOMETRY_TYPES
    ]
    trusted_drawing_body_primitives = [
        primitive
        for primitive in trusted_primitives
        if primitive.get("geometry_type") not in MANUFACTURING_GEOMETRY_TYPES
    ]

    note_texts = [
        text
        for text in texts
        if (text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])) not in title_block_evidence
    ]
    trusted_note_texts = [
        text
        for text in trusted_texts
        if (text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])) not in title_block_evidence
    ]
    revision_note_items = [
        {
            "evidence_text": candidate.get("evidence_text"),
            "text": candidate.get("value"),
            "view_name": candidate.get("view_name"),
            "layer_no": candidate.get("layer_no"),
            "position_x": candidate.get("position_x"),
            "position_y": candidate.get("position_y"),
            "inside_print_area": candidate.get("inside_print_area"),
            "source_type": "revision_note_candidate",
        }
        for candidate in revision_note_candidates
    ]
    note_items = [*note_texts, *revision_note_items]
    trusted_note_items = [
        *trusted_note_texts,
        *[
            item
            for item in revision_note_items
            if _is_usable_print_area_item(item, has_print_frames=has_print_frames)
        ],
    ]

    sections = [
        _make_2d_section(
            key="title_block",
            all_items=title_block_candidates,
            trusted_items=title_block_candidates,
            source_names=["title_block_candidates"],
        ),
        _make_2d_section(
            key="drawing_body",
            all_items=drawing_body_primitives,
            trusted_items=trusted_drawing_body_primitives,
            source_names=["geometry_primitives"],
        ),
        _make_2d_section(
            key="dimensions",
            all_items=dimensions,
            trusted_items=trusted_dimensions,
            source_names=["dimensions"],
        ),
        _make_2d_section(
            key="notes",
            all_items=note_items,
            trusted_items=trusted_note_items,
            source_names=["texts", "revision_note_candidates"],
        ),
        _make_2d_section(
            key="balloons",
            all_items=balloons,
            trusted_items=trusted_balloons,
            source_names=["balloons"],
        ),
        _make_2d_section(
            key="manufacturing_symbols",
            all_items=[*manufacturing_primitives, *weld_notes, *tolerances],
            trusted_items=[*trusted_manufacturing_primitives, *trusted_weld_notes, *trusted_tolerances],
            source_names=["geometry_primitives", "weld_notes", "tolerances"],
        ),
    ]
    return {
        "schema_version": "raw_2d_sections.v1",
        "print_area_policy": "inside_only_when_print_frames_exist" if has_print_frames else "include_unknown_when_no_print_frames",
        "sections": sections,
    }


def _build_title_block_candidates(texts: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str, str | None, float | None, float | None]] = set()

    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
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
                for keyword in sorted(rule["keywords"], key=lambda item: len(str(item)), reverse=True):
                    normalized_keyword = _normalize_for_match(str(keyword))
                    if normalized_keyword not in normalized_line:
                        continue

                    value = _strip_label_value(line, str(keyword))
                    confidence = "medium" if _is_field_value_usable(field, value, line) else "low"
                    if confidence == "low":
                        value = None
                    if not value and line_index + 1 < len(lines):
                        next_value = lines[line_index + 1].strip()
                        if _is_field_value_usable(field, next_value, line):
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


def _build_revision_note_candidates(texts: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, float | None, float | None]] = set()

    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
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
        if not _is_field_value_usable(field, value, str(candidate.get("evidence_text") or "")):
            continue
        if field and field not in selected:
            selected[field] = value
    return selected


def _build_geometry_feature_candidates(primitives: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    grouped: dict[str, dict] = {}
    for primitive in primitives:
        if not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
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
                "classification_label": rule["classification_label"],
                "searchable_tag": False,
                "tag_adoption_status": "excluded",
                "tag_adoption_reason": GEOMETRY_FEATURE_TAG_EXCLUSION_REASON,
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


def _build_geometry_attribute_summary(primitives: list[dict], *, has_print_frames: bool = False) -> dict:
    summary = {
        "surface_roughness_count": 0,
        "surface_roughness_values": [],
        "section_feature_count": 0,
        "cut_line_count": 0,
        "hatch_or_section_count": 0,
        "finish_mark_count": 0,
        "finish_mark_types": [],
        "slot_candidate_count": 0,
        "slot_candidate_dimensions": [],
        "hole_candidate_count": 0,
        "hole_candidate_diameters": [],
    }

    roughness_values: list[str] = []
    finish_mark_types: list[int] = []
    hole_diameters: list[float] = []
    slot_dimensions: list[dict] = []

    for primitive in primitives:
        if not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
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
        if geometry_type == "SxGeomFinishMark":
            summary["finish_mark_count"] += 1
            mark_type = primitive.get("mark_type")
            if mark_type is not None:
                finish_mark_types.append(mark_type)
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
    summary["finish_mark_types"] = _merge_unique(finish_mark_types)
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


def _looks_like_weight_text(value: str | None) -> bool:
    if not value:
        return False
    normalized = _material_lookup_key(value)
    return bool(re.search(r"(KG|ＫＧ|G|Ｇ)$", normalized) and re.search(r"\d", normalized))


def _normalize_weight_to_kg_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKC", value).replace(",", "").strip()
    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(kg|g|t)\b", normalized, re.IGNORECASE)
    if not match:
        return value.strip()
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "g":
        number = number / 1000
    elif unit == "t":
        number = number * 1000
    return f"{number:.2f} kg"


def _classify_material_value(value: str | None, *, allow_unknown: bool = True) -> dict[str, str | None]:
    normalized = _material_lookup_key(value)
    if not normalized:
        return {"status": "empty", "canonical": None}
    if "\ufffd" in str(value):
        return {"status": "excluded", "canonical": None}
    if _looks_like_weight_text(value):
        return {"status": "excluded", "canonical": None}
    classified = MATERIAL_CLASSIFICATION_BY_ALIAS.get(normalized)
    if classified:
        return classified
    without_numeric_prefix = re.sub(r"^[0-9]+", "", normalized)
    if without_numeric_prefix != normalized:
        classified_without_prefix = MATERIAL_CLASSIFICATION_BY_ALIAS.get(without_numeric_prefix)
        if classified_without_prefix:
            return classified_without_prefix
    material_match = MATERIAL_VALUE_PATTERN.search(unicodedata.normalize("NFKC", str(value)).upper())
    if material_match:
        material_code = material_match.group(1)
        matched_classification = MATERIAL_CLASSIFICATION_BY_ALIAS.get(_material_lookup_key(material_code))
        if matched_classification:
            return matched_classification
        return {"status": "formal", "canonical": material_code}
    if not allow_unknown:
        return {"status": "excluded", "canonical": None}
    return {"status": "unresolved", "canonical": unicodedata.normalize("NFKC", str(value)).strip().upper()}


def _is_unresolved_material_keyword(value: str | None) -> bool:
    return _classify_material_value(value)["status"] == "unresolved"


def _split_material_keywords(values: Iterable[str | None], *, allow_unknown: bool = True) -> tuple[list[str], list[str]]:
    formal: list[str] = []
    unresolved: list[str] = []
    for value in values:
        classification = _classify_material_value(value, allow_unknown=allow_unknown)
        status = classification["status"]
        canonical = classification["canonical"]
        if not canonical or status == "excluded":
            continue
        if status == "formal":
            formal.append(canonical)
        elif status == "unresolved":
            unresolved.append(canonical)
    return _merge_unique(formal), _merge_unique(unresolved)


def _build_part_material_candidates(parts: list[dict], materials: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, str]] = set()

    for index, part in enumerate(parts):
        part_path = _part_path(part, index)
        for material in part.get("materials", []) or []:
            material_id = _material_id(material)
            material_name = material.get("name")
            material_key = material_id or material_name
            classification = _classify_material_value(material_key)
            if classification["status"] == "excluded":
                continue
            key = (part_path, material_key, "3d_part_material")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_id,
                    "material_name": material_name,
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": material.get("specific_gravity"),
                    "source": "3d_part_material",
                    "confidence": "high" if classification["status"] == "formal" else "low",
                    "reason": "ICAD部品ツリーのSxEntPartから材質一覧を取得できたため、当該部品の材質候補として採用しました。",
                }
            )

    if len(parts) == 1 and len(materials) == 1:
        part = parts[0]
        material = materials[0]
        part_path = _part_path(part, 0)
        material_id = _material_id(material)
        classification = _classify_material_value(material_id or material.get("name"))
        if classification["status"] != "excluded":
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_id,
                    "material_name": material.get("name"),
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": material.get("specific_gravity"),
                    "source": "3d_material_single_part",
                    "confidence": "high" if classification["status"] == "formal" else "low",
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
            classification = _classify_material_value(material_text)
            if classification["status"] == "excluded":
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
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": None,
                    "source": f"part_ex_info_fields.{field_key}",
                    "confidence": "medium" if classification["status"] == "formal" else "low",
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
    model_info = raw_extract.get("model_info", {}) or {}
    model_info_tokens = _flatten_strings(
        [
            model_info.get("name"),
            model_info.get("comment"),
            model_info.get("path"),
        ]
    )

    canonical = {
        "drawing_number": None,
        "drawing_name": None,
        "revision": None,
        "material": None,
        "surface_treatment": None,
        "paint": None,
        "scale": None,
        "drawing_size": None,
        "designer": None,
        "checker": None,
        "approver": None,
        "drawing_date": None,
        "prfx": None,
        "unit_number": None,
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
        "model_name": model_info.get("name"),
        "model_comment": model_info.get("comment"),
        "model_path": model_info.get("path"),
        "model_is_read_only": model_info.get("is_read_only"),
        "model_view_sheet_count": model_info.get("view_sheet_count"),
        "model_work_plane_count": model_info.get("work_plane_count"),
        "model_info_tokens": model_info_tokens,
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
        "prfx_candidates": [],
        "unit_number_candidates": [],
        "part_names": [],
        "part_comments": [],
        "part_tree_paths": [],
        "part_ex_info_fields": {},
        "part_ex_info_tokens": [],
        "ref_model_names": [],
        "ref_model_paths": [],
        "referenced_2d_part_count": 0,
        "referenced_2d_trusted_part_count": 0,
        "referenced_2d_part_names": [],
        "referenced_2d_part3d_names": [],
        "referenced_2d_ref_model_names": [],
        "referenced_2d_ref_vs_names": [],
        "external_part_exists": False,
        "mirror_part_exists": False,
        "unresolved_part_exists": False,
        "text_tokens": [],
        "label_texts": [],
        "raw_2d_sections": None,
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
        "finish_mark_count": 0,
        "finish_mark_types": [],
        "slot_candidate_count": 0,
        "slot_candidate_dimensions": [],
        "hole_candidate_count": 0,
        "hole_candidate_diameters": [],
        "spec_tokens": [],
        "part_keywords": [],
        "material_keywords": [],
        "unresolved_material_keywords": [],
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
        material_id_keywords, material_id_unresolved_keywords = _split_material_keywords(canonical["material_ids"], allow_unknown=True)
        material_name_keywords, _ = _split_material_keywords(canonical["material_names"], allow_unknown=False)
        canonical["material_keywords"] = _merge_unique(material_id_keywords + material_name_keywords)
        canonical["unresolved_material_keywords"] = material_id_unresolved_keywords
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
        identity_tokens = _flatten_strings(
            [
                top_part.get("name"),
                top_part.get("comment"),
                top_part.get("ex_info"),
                *canonical["part_names"],
                *canonical["part_ex_info_tokens"],
                *canonical["ref_model_names"],
            ]
        )
        canonical["prfx_candidates"] = _merge_unique(
            _extract_identity_candidates_from_part_ex_info(parts, "prfx")
            + _extract_labeled_field_candidates("prfx", identity_tokens)
        )
        canonical["unit_number_candidates"] = _merge_unique(
            _extract_identity_candidates_from_part_ex_info(parts, "unit_number")
            + _extract_labeled_field_candidates("unit_number", identity_tokens)
        )
        canonical["part_material_candidates"] = _build_part_material_candidates(parts, materials)
        canonical["part_material_candidate_count"] = len(canonical["part_material_candidates"])
        part_material_keywords, part_unresolved_material_keywords = _split_material_keywords(
            _flatten_strings(candidate.get("canonical_material") for candidate in canonical["part_material_candidates"])
            + _flatten_strings(candidate.get("material_id") for candidate in canonical["part_material_candidates"])
            + _flatten_strings(candidate.get("material_name") for candidate in canonical["part_material_candidates"])
        )
        canonical["material_keywords"] = _merge_unique(canonical["material_keywords"] + part_material_keywords)
        canonical["unresolved_material_keywords"] = _merge_unique(
            canonical["unresolved_material_keywords"] + part_unresolved_material_keywords
        )
        canonical["external_part_exists"] = any(part.get("is_external") for part in parts)
        canonical["mirror_part_exists"] = any(part.get("is_mirror") for part in parts)
        canonical["unresolved_part_exists"] = any(part.get("is_unloaded") for part in parts)

        search_tokens = _flatten_strings(
            [
                *source_path_tokens,
                *model_info_tokens,
                top_part.get("name"),
                top_part.get("comment"),
                top_part.get("ex_info"),
                *canonical["material_keywords"],
                *canonical["unresolved_material_keywords"],
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
        referenced_parts = raw_extract.get("referenced_parts", [])
        has_print_frames = _has_print_frames(raw_extract)
        trusted_texts = _trusted_print_area_items(texts, has_print_frames=has_print_frames)
        trusted_dimensions = _trusted_print_area_items(dimensions, has_print_frames=has_print_frames)
        trusted_weld_notes = _trusted_print_area_items(weld_notes, has_print_frames=has_print_frames)
        trusted_balloons = _trusted_print_area_items(balloons, has_print_frames=has_print_frames)
        trusted_tolerances = _trusted_print_area_items(tolerances, has_print_frames=has_print_frames)
        trusted_referenced_parts = _trusted_print_area_items(referenced_parts, has_print_frames=has_print_frames)
        trusted_text_tokens = _flatten_strings(
            text_line
            for text in trusted_texts
            for text_line in text.get("text_lines", [])
        )
        trusted_dimension_symbols = _flatten_strings(
            value
            for dimension in trusted_dimensions
            for value in [dimension.get("mark_2"), dimension.get("mark_3"), dimension.get("front_word"), dimension.get("back_word")]
        )
        trusted_weld_note_texts = _flatten_strings(note.get("text") for note in trusted_weld_notes)
        trusted_balloon_keys = _flatten_strings(balloon.get("text") for balloon in trusted_balloons)
        trusted_tolerance_texts = _flatten_strings(tolerance.get("text") for tolerance in trusted_tolerances)

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
        canonical["referenced_2d_part_count"] = len(referenced_parts)
        canonical["referenced_2d_trusted_part_count"] = len(trusted_referenced_parts)
        canonical["referenced_2d_part_names"] = _flatten_strings(part.get("name") for part in trusted_referenced_parts)
        canonical["referenced_2d_part3d_names"] = _flatten_strings(part.get("part3d_name") for part in trusted_referenced_parts)
        canonical["referenced_2d_ref_model_names"] = _flatten_strings(part.get("ref_model_name") for part in trusted_referenced_parts)
        canonical["referenced_2d_ref_vs_names"] = _flatten_strings(part.get("ref_vs_name") for part in trusted_referenced_parts)
        canonical["spec_tokens"] = _flatten_strings(trusted_text_tokens + trusted_tolerance_texts)
        canonical["title_block_candidates"] = _build_title_block_candidates(texts, has_print_frames=has_print_frames)
        canonical["title_block_fields"] = _select_title_block_fields(canonical["title_block_candidates"])
        title_fields = canonical["title_block_fields"]
        if title_fields.get("weight"):
            title_fields["weight"] = _normalize_weight_to_kg_text(title_fields["weight"])
        canonical["prfx_candidates"] = _merge_unique(
            _flatten_strings([title_fields.get("prfx")])
            + _extract_labeled_field_candidates("prfx", trusted_text_tokens)
        )
        canonical["unit_number_candidates"] = _merge_unique(
            _flatten_strings([title_fields.get("unit_number")])
            + _extract_labeled_field_candidates("unit_number", trusted_text_tokens)
        )
        for source_key, canonical_key in {
            "drawing_number": "drawing_number",
            "drawing_name": "drawing_name",
            "material": "material",
            "weight": "weight_value",
            "surface_treatment": "surface_treatment",
            "coating_instruction": "paint",
            "scale": "scale",
            "designer": "designer",
            "checker": "checker",
            "approver": "approver",
            "date": "drawing_date",
            "revision": "revision",
            "prfx": "prfx",
            "unit_number": "unit_number",
        }.items():
            if title_fields.get(source_key):
                canonical[canonical_key] = title_fields[source_key]
        if title_fields.get("material"):
            formal_materials, unresolved_materials = _split_material_keywords([title_fields["material"]])
            canonical["material_keywords"] = _merge_unique(canonical["material_keywords"] + formal_materials)
            canonical["unresolved_material_keywords"] = _merge_unique(
                canonical["unresolved_material_keywords"] + unresolved_materials
            )
        if title_fields.get("surface_treatment"):
            canonical["surface_treatment_tokens"] = [title_fields["surface_treatment"]]
        canonical["revision_note_candidates"] = _build_revision_note_candidates(texts, has_print_frames=has_print_frames)
        canonical["revision_note_count"] = len(canonical["revision_note_candidates"])
        canonical["geometry_feature_candidates"] = _build_geometry_feature_candidates(primitives, has_print_frames=has_print_frames)
        canonical.update(_build_geometry_attribute_summary(primitives, has_print_frames=has_print_frames))
        canonical["raw_2d_sections"] = _build_2d_sections(
            raw_extract=raw_extract,
            canonical=canonical,
            has_print_frames=has_print_frames,
            trusted_texts=trusted_texts,
            trusted_dimensions=trusted_dimensions,
            trusted_weld_notes=trusted_weld_notes,
            trusted_balloons=trusted_balloons,
            trusted_tolerances=trusted_tolerances,
        )

        search_tokens = (
            source_path_tokens
            + model_info_tokens
            + trusted_text_tokens
            + _flatten_strings(str(value) for value in canonical["title_block_fields"].values())
            + _flatten_strings(candidate.get("value") for candidate in canonical["revision_note_candidates"])
            + trusted_dimension_symbols
            + trusted_weld_note_texts
            + trusted_balloon_keys
            + trusted_tolerance_texts
            + canonical["referenced_2d_part_names"]
            + canonical["referenced_2d_part3d_names"]
            + canonical["referenced_2d_ref_model_names"]
            + canonical["referenced_2d_ref_vs_names"]
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
