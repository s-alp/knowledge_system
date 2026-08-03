"""材質コードと重量表記の正規化規則をまとめる。

2D図枠と3D部品の両方から利用されるため、形式固有処理から独立させている。
入力値だけを評価し、ファイル、DB、外部APIを変更しない。
"""
from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_rules import MATERIAL_VALUE_PATTERN
from icad_tag_extraction.seed_dictionaries import MATERIAL_CLASSIFICATION_RULES


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


def _split_material_keywords(
    values: Iterable[str | None],
    *,
    allow_unknown: bool = True,
) -> tuple[list[str], list[str]]:
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


__all__ = (
    "MATERIAL_CLASSIFICATION_BY_ALIAS",
    "_material_lookup_key",
    "_normalize_material_text",
    "_looks_like_weight_text",
    "_normalize_weight_to_kg_text",
    "_classify_material_value",
    "_is_unresolved_material_keyword",
    "_split_material_keywords",
)
