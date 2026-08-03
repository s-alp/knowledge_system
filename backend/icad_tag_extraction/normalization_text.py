"""文字列、辞書、図番、図枠値の正規化に使う共通ヘルパーを定義する。

2D/3Dのどちらからも利用する判定だけを置き、形式固有の構造化処理と分離する。
入力値だけを処理し、ファイル、DB、外部APIを変更しない。
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import PureWindowsPath
import re
import unicodedata

from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_material import _classify_material_value
from icad_tag_extraction.normalization_rules import *  # noqa: F403


def _flatten_strings(values: Iterable[str | None]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not value:
            continue
        stripped = value.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _normalize_layer_names(values: Iterable[object]) -> list[str]:
    names: list[str] = []
    for value in values:
        if isinstance(value, str):
            candidate = value
        elif isinstance(value, dict):
            candidate = value.get("name")
        else:
            raise TypeError(
                f"layers[]は文字列または辞書である必要があります: {type(value).__name__}"
            )
        if isinstance(candidate, str) and candidate.strip():
            names.append(candidate.strip())
    return _merge_unique(names)


def _match_dictionary(tokens: Iterable[str], mapping: dict[str, list[str]]) -> str | None:
    lowered = " ".join(unicodedata.normalize("NFKC", token).casefold() for token in tokens)
    for canonical, candidates in mapping.items():
        if any(unicodedata.normalize("NFKC", candidate).casefold() in lowered for candidate in candidates):
            return canonical
    return None


def _match_dictionary_values(tokens: Iterable[str], mapping: dict[str, list[str]]) -> list[str]:
    lowered = " ".join(unicodedata.normalize("NFKC", token).casefold() for token in tokens)
    matches: list[str] = []
    for canonical, candidates in mapping.items():
        if any(unicodedata.normalize("NFKC", candidate).casefold() in lowered for candidate in candidates):
            matches.append(canonical)
    return matches


def _normalize_for_match(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


# 尺度表記(例: 1:6, 1/6, S=1:6, 尺度 1:6)。トークン全体が尺度表記であるものだけを拾い、
# 寸法・テーパ注記(テーパ1:10 等の接頭語付き)への誤反応を抑える。
_SCALE_RATIO_TOKEN_RE = re.compile(
    r"(?:SCALE|尺度|縮尺)?\s*S?\s*[=＝:：]?\s*([0-9]{1,3})\s*[:：/]\s*([0-9]{1,4})",
    re.IGNORECASE,
)
_SCALE_LABEL_HINT_RE = re.compile(r"scale|尺度|縮尺|^s\s*[=＝:：]", re.IGNORECASE)

# NTC図面で塗装仕様として使われるKS番号を、一般の英数字や図番から分離して拾う。
# 図枠の「PAINT OR」「PORTION」のような分割見出しは対象にせず、仕様値そのものだけを採用する。
_PAINT_KS_CODE_RE = re.compile(r"(?<![A-Z0-9])KS\s*[-－]?\s*([0-9]{1,3})(?![A-Z0-9])", re.IGNORECASE)
_PAINT_INSTRUCTION_PHRASES = ("マシン塗装色", "MC塗装色", "マシン塗装", "MC塗装")
_PAINT_LABEL_FRAGMENT_VALUES = {"OR", "PORTION", "マシン", "MC"}

# 硬度指定(例: HRC58, HRC58-62, Hv500, HB230)
_HARDNESS_SPEC_RE = re.compile(
    r"(?<![A-Z0-9])(?:HRC|HRB|HRA|HV|HBW|HB|HS)\s*[0-9]{1,4}"
    r"(?:\s*[~〜\-±]\s*[0-9]{1,4})?(?![A-Z0-9])",
    re.IGNORECASE,
)
_DIMENSION_TOLERANCE_TEXT_RE = re.compile(
    r"(?:±|\+/-|%%p|[+＋]\s*\d+(?:\.\d+)?\s*[-－]\s*\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_ICAD_DIMENSION_TOLERANCE_RATIO_RE = re.compile(
    r"(?:^|;)\s*dimtol_ratio=([+-]?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_WELD_INSTRUCTION_RE = re.compile(
    r"(?:溶接|すみ肉|隅肉|開先|現場溶接|全周溶接|\bWELD(?:ING)?\b|\bFILLET\b)",
    re.IGNORECASE,
)
_WELD_FILLET_RE = re.compile(r"(?:すみ肉|隅肉|\bFILLET\b)", re.IGNORECASE)
_WELD_ALL_AROUND_RE = re.compile(r"(?:全周(?:溶接)?|\bALL[\s_-]*AROUND\b)", re.IGNORECASE)


def _has_nonzero_tolerance_value(value: object) -> bool:
    if value is None:
        return False
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return False
    try:
        return float(text) != 0.0
    except ValueError:
        return True


def _dimension_has_tolerance(dimension: dict) -> bool:
    if dimension.get("has_tolerance") is True:
        return True
    if any(
        _has_nonzero_tolerance_value(dimension.get(key))
        for key in ("upper_tol", "lower_tol", "dimtp", "dimtm")
    ):
        return True
    text = " ".join(
        _flatten_strings(
            str(dimension.get(key)) if dimension.get(key) is not None else None
            for key in (
                "value_1",
                "value1",
                "value_2",
                "value2",
                "front_word",
                "back_word",
                "summary",
                "text_override",
            )
        )
    )
    if _DIMENSION_TOLERANCE_TEXT_RE.search(text):
        return True
    ratio_match = _ICAD_DIMENSION_TOLERANCE_RATIO_RE.search(
        str(dimension.get("summary") or "")
    )
    return bool(ratio_match and float(ratio_match.group(1)) != 0.0)


def _classify_weld_types(values: Iterable[str | None]) -> list[str]:
    text = " ".join(
        unicodedata.normalize("NFKC", value)
        for value in _flatten_strings(values)
    )
    weld_types: list[str] = []
    if _WELD_FILLET_RE.search(text):
        weld_types.append("すみ肉")
    if _WELD_ALL_AROUND_RE.search(text):
        weld_types.append("全周")
    return weld_types


def _weld_instruction_texts(values: Iterable[str | None]) -> list[str]:
    return _merge_unique(
        value
        for value in _flatten_strings(values)
        if _WELD_INSTRUCTION_RE.search(unicodedata.normalize("NFKC", value))
    )


def _extract_scale_candidates(tokens: Iterable[str]) -> list[dict]:
    candidates: dict[str, dict] = {}
    for token in _flatten_strings(tokens):
        text = unicodedata.normalize("NFKC", token).strip()
        matched = _SCALE_RATIO_TOKEN_RE.fullmatch(text)
        if not matched:
            continue
        left, right = int(matched.group(1)), int(matched.group(2))
        if left == 0 or right == 0:
            continue
        # 図面尺度はほぼ必ず片側が1(1:6, 1:10, 2:1 等)。インチ分数(7/16)や比率表記の誤検出を抑える。
        if left != 1 and right != 1:
            continue
        value = f"{left}:{right}"
        confidence = "medium" if _SCALE_LABEL_HINT_RE.search(text) else "low"
        existing = candidates.get(value)
        if existing and (existing["confidence"] == "medium" or confidence == "low"):
            continue
        candidates[value] = {
            "value": value,
            "evidence_text": token,
            "confidence": confidence,
            "source": "2d_text_scale_pattern",
        }
    return list(candidates.values())


def _extract_paint_instruction_tokens(tokens: Iterable[str]) -> list[str]:
    """図面内に単独で記載された、誤認しにくい塗装仕様だけを抽出する。

    ICADでは英語の図枠見出しが複数文字要素へ分割されることがあるため、
    座標だけで見出しと値を結合しない。KS番号や「マシン塗装色」のように、
    文字列自体が塗装仕様だと判別できる値は、図枠欄とは別の根拠として保持する。
    """

    values: list[str] = []
    for token in _flatten_strings(tokens):
        normalized = unicodedata.normalize("NFKC", token).strip()
        for matched in _PAINT_KS_CODE_RE.finditer(normalized):
            values.append(f"KS{matched.group(1)}")
        normalized_for_match = _normalize_for_match(normalized)
        for phrase in _PAINT_INSTRUCTION_PHRASES:
            if _normalize_for_match(phrase) in normalized_for_match:
                values.append(phrase)
                break
    return _merge_unique(values)


def _heat_treatment_rules(mapping: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    rules: list[tuple[str, str, str]] = []
    for canonical_name, aliases in mapping.items():
        for alias in aliases:
            rules.append((canonical_name, alias, unicodedata.normalize("NFKC", alias).casefold()))
    # 長い別名を優先照合し、「高周波焼入れ」が「焼入れ」にも同時ヒットする二重取りを防ぐ。
    rules.sort(key=lambda item: len(item[2]), reverse=True)
    return rules


def _match_heat_treatment_keywords(
    tokens: Iterable[str],
    mapping: dict[str, list[str]],
) -> tuple[list[str], list[dict]]:
    matched: list[str] = []
    evidence: list[dict] = []
    rules = _heat_treatment_rules(mapping)
    for token in _flatten_strings(tokens):
        token_norm = unicodedata.normalize("NFKC", token).casefold()
        for canonical_name, alias, alias_norm in rules:
            if alias_norm.isascii():
                if not re.search(rf"(?<![0-9a-z]){re.escape(alias_norm)}", token_norm):
                    continue
            elif alias_norm not in token_norm:
                continue
            if canonical_name not in matched:
                matched.append(canonical_name)
            if len(evidence) < 20:
                evidence.append({"value": canonical_name, "alias": alias, "token": token})
            break  # 1トークンにつき最長一致の1件だけ採用する
    return matched, evidence


def _extract_hardness_spec_candidates(tokens: Iterable[str]) -> list[dict]:
    candidates: dict[str, dict] = {}
    for token in _flatten_strings(tokens):
        text = unicodedata.normalize("NFKC", token)
        for matched in _HARDNESS_SPEC_RE.finditer(text):
            value = re.sub(r"\s+", "", matched.group(0)).upper()
            if value not in candidates:
                candidates[value] = {
                    "value": value,
                    "evidence_text": token,
                    "confidence": "medium",
                    "source": "hardness_spec_pattern",
                }
    return list(candidates.values())


def _strip_label_value(text: str, keyword: str) -> str | None:
    """全角・半角とラベル内空白をそろえ、同じ文字要素内のラベル部分だけを除く。"""

    normalized_text = unicodedata.normalize("NFKC", text)
    normalized_keyword = unicodedata.normalize("NFKC", keyword)
    keyword_tokens = re.findall(r"[A-Z0-9]+|[^\s]", normalized_keyword, re.IGNORECASE)
    if not keyword_tokens:
        return None
    keyword_pattern = r"\s*".join(re.escape(token) for token in keyword_tokens)
    match = re.search(keyword_pattern, normalized_text, re.IGNORECASE)
    if not match:
        return None

    value = normalized_text[: match.start()] + normalized_text[match.end() :]
    value = value.strip(" 　:：=＝-－_/／[]【】()（）")
    return value or None


def _text_lines_from_payload(text: dict) -> list[str]:
    lines = _flatten_strings(text.get("text_lines", []) or [])
    text_value = text.get("text")
    if text_value and text_value not in lines:
        lines.append(text_value)
    value = text.get("value")
    if value and value not in lines:
        lines.append(value)
    joined_text = text.get("joined_text")
    if joined_text and joined_text not in lines:
        lines.append(joined_text)
    return lines


def _normalize_text_items(items: Iterable) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if isinstance(item, str):
            normalized.append({"text_lines": [item], "joined_text": item, "source_type": "text"})
            continue
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        lines = _text_lines_from_payload(copied)
        if lines:
            copied["text_lines"] = lines
            if "joined_text" not in copied and ("text" in copied or "value" in copied):
                copied["joined_text"] = " / ".join(lines)
        normalized.append(copied)
    return normalized


def _normalize_material_items(items: Iterable) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if isinstance(item, str):
            normalized.append({"matid": item, "name": item})
            continue
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        if "material_id" in copied and "matid" not in copied:
            copied["matid"] = copied["material_id"]
        if "material_name" in copied and "name" not in copied:
            copied["name"] = copied["material_name"]
        normalized.append(copied)
    return normalized


def _is_external_part_payload(part: dict) -> bool:
    """外部参照パーツを本体パーツから分離するための共通判定。"""

    return bool(
        part.get("is_external")
        or part.get("ref_model_name")
        or part.get("ref_model_path")
    )


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


def _is_drawing_number_value_usable(value: str | None) -> bool:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not normalized:
        return False
    compact = _normalize_for_match(normalized)
    if normalized in DRAWING_NUMBER_NOISE_VALUES:
        return False
    if compact in DRAWING_NUMBER_NOISE_COMPACT_VALUES:
        return False
    if any(keyword in normalized for keyword in DRAWING_NUMBER_REFERENCE_KEYWORDS):
        return False
    if FILE_EXTENSION_FRAGMENT_PATTERN.fullmatch(normalized):
        return False
    return bool(re.search(r"\d", normalized))


def _clean_drawing_number_value(value: str | None) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip(" 　:：=＝-－_/／[]【】")
    wrapper_match = re.fullmatch(r"[\[(（【](.+?)[\])）】]", normalized)
    if wrapper_match:
        normalized = wrapper_match.group(1).strip()
    if not _is_drawing_number_value_usable(normalized):
        return None

    size_match = DRAWING_SIZE_SUFFIX_PATTERN.fullmatch(normalized)
    if size_match:
        normalized = size_match.group("body").strip()

    segments = [segment.strip() for segment in normalized.split("_") if segment.strip()]
    if len(segments) > 1:
        filtered_segments = [
            segment
            for segment in segments
            if not re.fullmatch(r"[0-9]{1,3}", segment)
            and not re.fullmatch(r"A[0-4]", segment, re.IGNORECASE)
        ]
        for segment in filtered_segments:
            if DRAWING_NUMBER_CODE_SEGMENT_PATTERN.fullmatch(segment):
                return segment
        return None

    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", normalized):
        match = DRAWING_NUMBER_CODE_SEGMENT_PATTERN.search(normalized)
        return match.group(0) if match else None
    return normalized if _is_drawing_number_value_usable(normalized) else None


def _drawing_number_match_key(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).upper()
    return re.sub(r"[^A-Z0-9]", "", normalized)


def _source_file_stem(source_file: dict) -> str:
    explicit_stem = str(source_file.get("file_name_without_extension") or "").strip()
    if explicit_stem:
        return explicit_stem
    file_name = str(source_file.get("file_name") or "").strip()
    if file_name:
        return PureWindowsPath(file_name).stem
    full_path = str(source_file.get("full_path") or "").strip()
    return PureWindowsPath(full_path).stem if full_path else ""


def _clean_filename_drawing_number(value: str | None) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not normalized:
        return None
    for match in DRAWING_NUMBER_FILENAME_WORD_PATTERN.finditer(normalized):
        word = match.group("word").upper()
        if word in DRAWING_NUMBER_FILENAME_WORD_EXCLUSIONS:
            normalized = normalized[: match.start()]
            break
    normalized = re.sub(r"(?:[-_\s]+(?:A[0-4]|[23]D|REV[A-Z0-9]*|R\d+))+$", "", normalized, flags=re.IGNORECASE)
    return _clean_drawing_number_value(normalized)


def _drawing_number_candidates_from_texts(texts: Iterable[str | None]) -> list[str]:
    """図面文字から英数字を含む図面番号らしい連続トークンだけを列挙する。"""

    values: list[str] = []
    for text in _flatten_strings(texts):
        normalized = unicodedata.normalize("NFKC", text).upper()
        for match in DRAWING_NUMBER_TOKEN_PATTERN.finditer(normalized):
            value = _clean_drawing_number_value(match.group(0))
            if value and value not in values:
                values.append(value)
    return values


def _derive_drawing_number(
    *,
    source_file: dict,
    title_number: str | None,
    text_tokens: Iterable[str | None],
) -> tuple[str | None, list[dict]]:
    """図枠値を優先し、次に図面文字とファイル名が一致する候補、最後にファイル名を使う。

    印刷枠外・枠判定不明の文字を無条件に復活させると参照図番まで混ざるため、
    raw文字の救済はファイル名と英数字列が一致する候補だけに限定する。
    """

    candidates: list[dict] = []
    title_value = _clean_drawing_number_value(title_number)
    if title_value:
        candidates.append(
            {
                "value": title_value,
                "source": "2d_title_block",
                "confidence": "high",
                "evidence": "title_block_fields.drawing_number",
            }
        )

    filename_stem = _source_file_stem(source_file)
    filename_key = _drawing_number_match_key(filename_stem)
    for value in _drawing_number_candidates_from_texts(text_tokens):
        value_key = _drawing_number_match_key(value)
        if not value_key or not filename_key:
            continue
        if value_key not in filename_key and filename_key not in value_key:
            continue
        if any(item["value"] == value for item in candidates):
            continue
        candidates.append(
            {
                "value": value,
                "source": "2d_text_filename_match",
                "confidence": "high",
                "evidence": f"raw_extract.texts ↔ source_file:{filename_stem}",
            }
        )

    filename_value = _clean_filename_drawing_number(filename_stem)
    if filename_value and not any(item["value"] == filename_value for item in candidates):
        candidates.append(
            {
                "value": filename_value,
                "source": "filename",
                "confidence": "medium",
                "evidence": f"source_file:{filename_stem}",
            }
        )

    matched_text_values = [
        item["value"]
        for item in candidates
        if item["source"] == "2d_text_filename_match"
    ]
    filename_value_key = _drawing_number_match_key(filename_value)

    def matches_filename_number(value: str) -> bool:
        value_key = _drawing_number_match_key(value)
        if not value_key or not filename_value_key:
            return False
        if value_key == filename_value_key:
            return True
        # ファイル名末尾の「-00」は管理用付番として図面内番号から省略される実例がある。
        # 「-01」等は実体の枝番にもなるため短さだけでは削らず、全ゼロの場合だけ一致扱いにする。
        # 逆向き（図面内値だけが長い）は子部品番号の可能性があるため一致扱いにしない。
        suffix = filename_value_key[len(value_key) :] if filename_value_key.startswith(value_key) else ""
        return bool(suffix and len(suffix) <= 3 and set(suffix) == {"0"})

    matched_filename_value = next(
        (
            value
            for value in matched_text_values
            if filename_value_key
            and matches_filename_number(value)
        ),
        None,
    )
    if title_value:
        if not filename_value_key or matches_filename_number(title_value):
            return title_value, candidates
        # ファイル名にも有効な図面番号があるのに図枠値が一致しない場合は、
        # 子部品番号や参照図番を拾った可能性が高いためファイル名側を採用する。
        return matched_filename_value or filename_value, candidates
    return matched_filename_value or filename_value or (matched_text_values[0] if matched_text_values else None), candidates


def _is_field_value_usable(field: str, value: str | None, evidence_text: str) -> bool:
    if not _is_title_block_value_usable(
        value,
        max_length=int(TITLE_BLOCK_FIELD_RULES.get(field, {}).get("max_value_length", 80)),
    ):
        return False
    normalized_value = unicodedata.normalize("NFKC", str(value)).strip()
    normalized_evidence = unicodedata.normalize("NFKC", evidence_text).strip()

    if field == "drawing_number":
        if any(token in normalized_evidence for token in DRAWING_NUMBER_REFERENCE_KEYWORDS):
            return False
        if not _clean_drawing_number_value(normalized_value):
            return False
    if field == "material":
        classification = _classify_material_value(normalized_value, allow_unknown=False)
        if classification["status"] != "formal":
            return False
        if re.search(r"(?:丸棒|角棒|パイプ|板厚|φ\s*\d)", normalized_value, re.IGNORECASE) and not MATERIAL_VALUE_PATTERN.search(normalized_value.upper()):
            return False
    if field == "unit_number" and not re.search(r"\d", normalized_value):
        return False
    if field == "weight":
        if not re.search(r"[-+]?\d+(?:\.\d+)?\s*(?:kg|g|t|ｋｇ|ｇ)\b", normalized_value, re.IGNORECASE):
            return False
        if any(token in normalized_evidence for token in ("吸引力", "倍", "÷")):
            return False
    if field in {"date", "created_date", "checked_date", "approved_date", "revision_date"}:
        if not DATE_VALUE_PATTERN.search(normalized_value):
            return False
    if field == "coating_instruction":
        if "仕上げ面不可" in normalized_value:
            return False
        # 「PAINT OR」「PORTION」が別文字に分割された図枠では、ORは塗装値ではなく見出しの断片。
        # 「マシン塗装色」からラベルだけを除いた「マシン」「MC」も仕様値として確定しない。
        if normalized_value.upper() in _PAINT_LABEL_FRAGMENT_VALUES:
            return False
    return True

__all__ = (
    "_flatten_strings",
    "_normalize_layer_names",
    "_match_dictionary",
    "_match_dictionary_values",
    "_normalize_for_match",
    "_has_nonzero_tolerance_value",
    "_dimension_has_tolerance",
    "_classify_weld_types",
    "_weld_instruction_texts",
    "_extract_scale_candidates",
    "_extract_paint_instruction_tokens",
    "_heat_treatment_rules",
    "_match_heat_treatment_keywords",
    "_extract_hardness_spec_candidates",
    "_strip_label_value",
    "_text_lines_from_payload",
    "_normalize_text_items",
    "_normalize_material_items",
    "_is_external_part_payload",
    "_extract_labeled_field_candidates",
    "_extract_identity_candidates_from_part_ex_info",
    "_looks_like_title_block_label",
    "_contains_replacement_character",
    "_looks_like_title_block_label_fragment",
    "_is_title_block_value_usable",
    "_is_drawing_number_value_usable",
    "_clean_drawing_number_value",
    "_drawing_number_match_key",
    "_source_file_stem",
    "_clean_filename_drawing_number",
    "_drawing_number_candidates_from_texts",
    "_derive_drawing_number",
    "_is_field_value_usable",
)
