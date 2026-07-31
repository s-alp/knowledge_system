"""C#・STEP・DXFのraw抽出をDjango非依存の共通canonical形式へ正規化する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import PureWindowsPath
import re
import unicodedata

from icad_tag_extraction.configuration import DEFAULT_CONFIG, ExtractionConfig
from icad_tag_extraction.dictionary_provider import (
    DICTIONARY_KINDS,
    KIND_CUSTOMER,
    KIND_EQUIPMENT_CATEGORY,
    KIND_HEAT_TREATMENT,
    KIND_MAKER,
    KIND_PART_NAME,
    KIND_PROJECT,
    KIND_SPEC,
    DictionaryProvider,
    SeedDictionaryProvider,
)
from icad_tag_extraction.seed_dictionaries import MATERIAL_CLASSIFICATION_RULES


TITLE_BLOCK_FIELD_RULES: dict[str, dict[str, object]] = {
    "drawing_number": {"label": "図番", "keywords": ["図番", "図面番号", "品番", "部品番号", "drawing no", "dwg no", "part no"], "max_value_length": 80},
    "drawing_name": {"label": "図面名", "keywords": ["図名", "図面名", "名称", "drawing name", "drawing title", "title"], "max_value_length": 80},
    "part_name": {"label": "部品名", "keywords": ["部品名", "部品名称", "品名", "part name", "parts name"], "max_value_length": 80},
    "product_name": {"label": "製品名", "keywords": ["製品名", "製品名称", "product name"], "max_value_length": 80},
    "equipment_name": {"label": "装置名", "keywords": ["装置名", "装置名称", "設備名", "機械名", "equipment name", "machine name"], "max_value_length": 80},
    "unit_name": {"label": "ユニット名", "keywords": ["ユニット名", "ユニット名称", "unit name", "unit title"], "max_value_length": 80},
    "material": {"label": "材質", "keywords": ["材質", "材料", "material", "matl"], "max_value_length": 40},
    "weight": {"label": "重量", "keywords": ["重量", "質量", "weight", "mass", "wt"], "max_value_length": 40},
    "surface_treatment": {"label": "表面処理", "keywords": ["表面処理", "表処", "処理", "surface treatment", "finish"], "max_value_length": 40},
    "coating_instruction": {"label": "塗装指示", "keywords": ["塗装", "塗装色", "paint", "coating"], "max_value_length": 40},
    "scale": {"label": "尺度", "keywords": ["尺度", "縮尺", "scale"], "max_value_length": 24},
    "checker": {"label": "検図者", "keywords": ["検図", "照査", "check", "checked"], "max_value_length": 40},
    "approver": {"label": "承認者", "keywords": ["承認", "認可", "approved"], "max_value_length": 40},
    "created_date": {"label": "作成日", "keywords": ["作成日", "製図日", "作図日", "drawn date", "designed date"], "max_value_length": 40},
    "checked_date": {"label": "検図日", "keywords": ["検図日", "照査日", "checked date"], "max_value_length": 40},
    "approved_date": {"label": "承認日", "keywords": ["承認日", "認可日", "approved date"], "max_value_length": 40},
    "revision_date": {"label": "改訂日", "keywords": ["改訂日", "訂正日", "revision date", "rev date"], "max_value_length": 40},
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
DATE_VALUE_PATTERN = re.compile(
    r"(?:"
    r"(?:19|20)?[0-9]{2}[./年月日\-\s]+[01]?[0-9][./月日\-\s]+[0-3]?[0-9]日?"
    r"|(?:19|20)[0-9]{2}[01][0-9][0-3][0-9]"
    r")"
)
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
DRAWING_NUMBER_NOISE_VALUES = {"組", "クミ", "くみ"}
DRAWING_NUMBER_NOISE_COMPACT_VALUES = {"cad"}
DRAWING_NUMBER_REFERENCE_KEYWORDS = ("参考", "元図", "参照", "参照組立号")
ICAD_BUSINESS_NAME_FIELD_KEYS = {"user_wbhna"}
FILE_EXTENSION_FRAGMENT_PATTERN = re.compile(r"\.[a-z0-9]{1,5}", re.IGNORECASE)
DRAWING_SIZE_SUFFIX_PATTERN = re.compile(r"(?P<body>.+?)(?:[_\s-]+A[0-4])$", re.IGNORECASE)
DRAWING_NUMBER_CODE_SEGMENT_PATTERN = re.compile(r"(?=.*\d)[A-Z0-9][A-Z0-9.-]{2,}[A-Z0-9]", re.IGNORECASE)
DRAWING_NUMBER_TOKEN_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?=[A-Z0-9._-]{4,}(?![A-Z0-9]))(?=[A-Z0-9._-]*\d)"
    r"[A-Z0-9][A-Z0-9._-]*[A-Z0-9](?![A-Z0-9])",
    re.IGNORECASE,
)
DRAWING_NUMBER_FILENAME_WORD_PATTERN = re.compile(r"-(?P<word>[A-Z]{3,})(?:-|$)", re.IGNORECASE)
DRAWING_NUMBER_FILENAME_WORD_EXCLUSIONS = {
    "ASSY",
    "ASSEMBLY",
    "BRACKET",
    "COVER",
    "DRAWING",
    "MACHINE",
    "MODEL",
    "PART",
    "PLATE",
    "PRODUCT",
    "UNIT",
}
IDENTITY_NAME_FIELDS = {"drawing_name", "part_name", "product_name", "equipment_name", "unit_name"}
IDENTITY_NAME_PREFIX_MARKERS_RE = re.compile(r"^[\s　★☆※*●○◎■□◆◇▲△▼▽]+")
IDENTITY_SPEC_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])(?:SFF|[LWHT])\s*[-=＝]\s*\d+(?:\.\d+)?(?:\s*mm)?(?![A-Z0-9])",
    re.IGNORECASE,
)
IDENTITY_NAME_NOISE_VALUES = {
    "ASSEMBLY",
    "ASSY",
    "CHANGED",
    "COPIED",
    "COPY",
    "DRAWING",
    "MACHINE",
    "MODEL",
    "NAME",
    "PART",
    "PRODUCT",
    "TITLE",
    "UNCHANGED",
    "UNIT",
    "コード",
    "メーカー",
    "単重量",
    "図番",
    "所要数",
    "材質",
    "名称",
    "図面名",
    "品名",
    "部品名",
    "符号",
    "型式",
    "形式",
    "品種",
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


def _should_enforce_print_area(items: Iterable[dict], *, has_print_frames: bool) -> bool:
    """枠内外を実際に判定できた要素がある場合だけ、印刷枠フィルターを有効にする。

    ICAD側が印刷枠を返しても、APIや図面状態によって全要素のinside_print_areaが
    unknownになることがある。この状態で枠の存在だけを根拠に除外すると、図面内文字を
    全件失うため、判定情報そのものが無い場合に限ってunknownを採用する。
    """

    if not has_print_frames:
        return False
    return any(
        isinstance(item, dict) and item.get("inside_print_area") is not None
        for item in items
    )


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


def _structured_2d_symbol_candidates(items: Iterable[dict], *, value_key: str, source: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(value_key)
        if not isinstance(value, str) or not value.strip() or _contains_replacement_character(value):
            continue
        key = (value.strip(), item.get("view_name"), item.get("layer_no"), item.get("position_x"), item.get("position_y"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "value": value.strip(),
                "evidence_text": value.strip(),
                "view_name": item.get("view_name"),
                "layer_no": item.get("layer_no"),
                "position_x": item.get("position_x"),
                "position_y": item.get("position_y"),
                "position_z": item.get("position_z"),
                "inside_print_area": item.get("inside_print_area"),
                "print_frame_no": item.get("print_frame_no"),
                "source": source,
                "confidence": "medium",
                "reason": "2D図面要素から値と位置情報を取得できたため、検索タグではなく図面レビュー用の属性候補として保持します。",
            }
        )
    return candidates


VIEW_REFERENCE_GEOMETRY_TYPES = {
    "SxGeomArrowView": {"kind": "arrow_view", "label": "矢視候補"},
    "SxGeomCutLine": {"kind": "cut_line", "label": "切断線候補"},
    "SxGeomSymbol": {"kind": "symbol", "label": "図面シンボル候補"},
}


def _build_view_reference_candidates(primitives: Iterable[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None, str | None]] = set()
    for primitive in primitives:
        if not isinstance(primitive, dict) or not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        definition = VIEW_REFERENCE_GEOMETRY_TYPES.get(str(geometry_type))
        if not definition:
            continue
        evidence_text = str(primitive.get("summary") or geometry_type or "").strip()
        key = (
            str(geometry_type),
            primitive.get("view_name"),
            primitive.get("layer_no"),
            primitive.get("position_x"),
            primitive.get("position_y"),
            evidence_text,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "kind": definition["kind"],
                "label": definition["label"],
                "geometry_type": geometry_type,
                "evidence_text": evidence_text,
                "view_name": primitive.get("view_name"),
                "layer_no": primitive.get("layer_no"),
                "position_x": primitive.get("position_x"),
                "position_y": primitive.get("position_y"),
                "position_z": primitive.get("position_z"),
                "end_x": primitive.get("end_x"),
                "end_y": primitive.get("end_y"),
                "end_z": primitive.get("end_z"),
                "inside_print_area": primitive.get("inside_print_area"),
                "print_frame_no": primitive.get("print_frame_no"),
                "source": "2d_view_reference_geometry",
                "confidence": "medium",
                "reason": "2D図面の矢視・切断線・シンボル要素から、別ビューや詳細図へつながる可能性があるためレビュー用候補として保持します。",
            }
        )
    return candidates


def _build_curve_section_candidates(primitives: Iterable[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None, str | None]] = set()
    for primitive in primitives:
        if not isinstance(primitive, dict) or not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        if geometry_type == "SxGeomSpline2D":
            kind = "spline_curve"
            label = "スプライン曲線候補"
            source = "2d_spline_geometry"
            reason = "2D図形のスプライン要素から曲線外形の可能性を確認できるため、検索タグではなく図面レビュー用候補として保持します。"
        elif geometry_type == "SxGeomHatch":
            kind = "hatch_section"
            label = "ハッチング/断面候補"
            source = "2d_hatch_geometry"
            reason = "2D図形のハッチング要素から断面表現または材質表現の可能性を確認できるため、検索タグではなく図面レビュー用候補として保持します。"
        else:
            continue

        evidence_text = str(primitive.get("summary") or geometry_type or "").strip()
        key = (
            str(geometry_type),
            primitive.get("view_name"),
            primitive.get("layer_no"),
            primitive.get("position_x"),
            primitive.get("position_y"),
            evidence_text,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "kind": kind,
                "label": label,
                "geometry_type": geometry_type,
                "evidence_text": evidence_text,
                "view_name": primitive.get("view_name"),
                "layer_no": primitive.get("layer_no"),
                "position_x": primitive.get("position_x"),
                "position_y": primitive.get("position_y"),
                "position_z": primitive.get("position_z"),
                "center_x": primitive.get("center_x"),
                "center_y": primitive.get("center_y"),
                "center_z": primitive.get("center_z"),
                "point_count": primitive.get("point_count"),
                "inside_print_area": primitive.get("inside_print_area"),
                "print_frame_no": primitive.get("print_frame_no"),
                "source": source,
                "confidence": "medium",
                "searchable_tag": False,
                "tag_adoption_status": "excluded",
                "tag_adoption_reason": GEOMETRY_FEATURE_TAG_EXCLUSION_REASON,
                "reason": reason,
            }
        )
    return candidates


INERTIA_MOMENT_DEFINITIONS = {
    "global_moment": {"kind": "global", "label": "全体座標系慣性モーメント"},
    "gravity_moment": {"kind": "gravity", "label": "重心座標系慣性モーメント"},
    "main_moment": {"kind": "main", "label": "主慣性モーメント"},
}


def _build_inertia_moment_candidates(mass_properties: dict) -> list[dict]:
    candidates: list[dict] = []
    for key, definition in INERTIA_MOMENT_DEFINITIONS.items():
        values = mass_properties.get(key)
        if not isinstance(values, dict):
            continue
        numeric_values = {
            str(name): value
            for name, value in values.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        if not numeric_values:
            continue
        candidates.append(
            {
                "kind": definition["kind"],
                "label": definition["label"],
                "values": numeric_values,
                "unit_name": mass_properties.get("unit_name"),
                "source": f"3d_mass_properties.{key}",
                "confidence": "medium",
                "reason": "SXNETのSxInfMassから慣性モーメント値を取得できたため、検索タグではなく3D解析属性として保持します。",
            }
        )
    return candidates


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
    enforce_text_print_area: bool,
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
            if _is_usable_print_area_item(item, has_print_frames=enforce_text_print_area)
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
        "text_print_area_policy": (
            "inside_only_when_classification_available"
            if enforce_text_print_area
            else "include_unknown_when_classification_unavailable"
        ),
        "sections": sections,
    }


def normalize_identity_name_value(value: str | None) -> str | None:
    """名称本体ではない先頭記号と寸法・型式トークンを表示名称から除く。

    `★ガイドレール`の★や`SFF-424 L=1572`は図面上の注記・仕様情報であり、
    原文はraw証跡に残しつつ、製品名・部品名へそのまま登録しない。
    """

    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    normalized = IDENTITY_NAME_PREFIX_MARKERS_RE.sub("", normalized)
    normalized = IDENTITY_SPEC_TOKEN_RE.sub(" ", normalized)
    # 「法兰(右)」のように名称本体の一部である括弧は残し、前後の区切り記号だけを除く。
    normalized = re.sub(r"[\s　,、，]+", " ", normalized).strip(" 　:：=＝-－_/／")
    if normalized.upper() in IDENTITY_NAME_NOISE_VALUES:
        return None
    return normalized or None


def _identity_name_value_is_usable(field: str, value: str | None) -> bool:
    normalized = normalize_identity_name_value(value)
    if (
        field not in IDENTITY_NAME_FIELDS
        or not _is_title_block_value_usable(
            normalized,
            max_length=int(TITLE_BLOCK_FIELD_RULES.get(field, {}).get("max_value_length", 80)),
        )
    ):
        return False
    normalized = str(normalized)
    if normalized.upper() in IDENTITY_NAME_NOISE_VALUES:
        return False
    if any(keyword in normalized for keyword in DRAWING_NUMBER_REFERENCE_KEYWORDS):
        return False
    if any(_normalize_for_match(keyword) in _normalize_for_match(normalized) for keyword in REVISION_NOTE_KEYWORDS):
        return False
    if not re.search(r"[A-Z\u3040-\u30ff\u3400-\u9fff]", normalized, re.IGNORECASE):
        return False
    if re.fullmatch(r"[A-Z0-9._/\-\s]+", normalized, re.IGNORECASE) and re.search(r"\d", normalized):
        return False
    return True


def _nearest_identity_name_value(
    *,
    label_text: dict,
    texts: list[dict],
    field: str,
    has_print_frames: bool,
) -> tuple[str | None, dict | None]:
    """名称ラベルの右または上下に整列する最短の文字要素だけを値候補にする。

    材質・日付などへ汎用化すると図枠レイアウト差で誤対応しやすいため、
    呼び出し元は製品・装置・ユニット・部品・図面の名称欄に限定する。
    """

    label_x = label_text.get("position_x")
    label_y = label_text.get("position_y")
    if not isinstance(label_x, (int, float)) or not isinstance(label_y, (int, float)):
        return None, None

    right_ranked: list[tuple[float, str, dict]] = []
    left_ranked: list[tuple[float, str, dict]] = []
    vertical_ranked: list[tuple[float, str, dict]] = []
    for candidate_text in texts:
        if candidate_text is label_text:
            continue
        if not _is_usable_print_area_item(candidate_text, has_print_frames=has_print_frames):
            continue
        if (
            label_text.get("view_name")
            and candidate_text.get("view_name")
            and label_text.get("view_name") != candidate_text.get("view_name")
        ):
            continue
        if (
            label_text.get("layer_no") is not None
            and candidate_text.get("layer_no") is not None
            and label_text.get("layer_no") != candidate_text.get("layer_no")
        ):
            continue
        candidate_x = candidate_text.get("position_x")
        candidate_y = candidate_text.get("position_y")
        if not isinstance(candidate_x, (int, float)) or not isinstance(candidate_y, (int, float)):
            continue
        lines = _text_lines_from_payload(candidate_text)
        if len(lines) != 1:
            continue
        raw_value = lines[0].strip()
        # 最短要素が無効な見出し・プレースホルダーでも順位付けには残す。
        # ここで捨てると、その奥の無関係な文字を名称として拾ってしまう。
        value = normalize_identity_name_value(raw_value) or unicodedata.normalize("NFKC", raw_value)
        delta_x = float(candidate_x) - float(label_x)
        delta_y = float(candidate_y) - float(label_y)
        right_horizontal = delta_x > 0 and abs(delta_y) <= max(0.5, abs(delta_x) * 0.15)
        # BOM欄では品名値が見出しの左側かつ行中央に置かれる実例がある。
        # 右側より少し広い行ずれを許容するが、同一ビュー・同一レイヤー・印刷枠内は必須とする。
        left_horizontal = delta_x < 0 and abs(delta_y) <= max(0.5, abs(delta_x) * 0.25)
        vertical = delta_y != 0 and abs(delta_x) <= max(0.5, abs(delta_y) * 0.15)
        if not right_horizontal and not left_horizontal and not vertical:
            continue
        distance = (delta_x**2 + delta_y**2) ** 0.5
        if right_horizontal:
            ranked_target = right_ranked
        elif left_horizontal:
            ranked_target = left_ranked
        else:
            ranked_target = vertical_ranked
        ranked_target.append((distance, unicodedata.normalize("NFKC", value), candidate_text))

    # 通常の右側配置、BOMで見られる左側配置、上下配置の順に確認する。
    # 同じ方向では最短要素だけを評価し、別欄を飛び越えて遠方文字を拾わない。
    for ranked in (right_ranked, left_ranked, vertical_ranked):
        if not ranked:
            continue
        ranked.sort(key=lambda item: item[0])
        _, value, candidate_text = ranked[0]
        if _identity_name_value_is_usable(field, value):
            return value, candidate_text
    return None, None


def _nearest_drawing_name_aligned_with_number(
    *,
    texts: list[dict],
    drawing_number: str | None,
    has_print_frames: bool,
) -> tuple[str | None, dict | None]:
    """図番と縦に揃った名称文字を、明示ラベルがない図枠の限定救済に使う。

    図番と同一ビュー・同一レイヤーで、短い距離に縦整列する4文字以上の名称だけを対象とする。
    日付、重量、尺度、材質、別図番は候補から除外し、検印欄等の誤採用を抑える。
    """

    drawing_number_key = _drawing_number_match_key(drawing_number)
    if not drawing_number_key:
        return None, None

    number_texts: list[dict] = []
    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
            continue
        for line in _text_lines_from_payload(text):
            if _drawing_number_match_key(_clean_drawing_number_value(line)) == drawing_number_key:
                number_texts.append(text)
                break

    ranked: list[tuple[float, str, dict]] = []
    for number_text in number_texts:
        number_x = number_text.get("position_x")
        number_y = number_text.get("position_y")
        if not isinstance(number_x, (int, float)) or not isinstance(number_y, (int, float)):
            continue
        for candidate_text in texts:
            if candidate_text is number_text:
                continue
            if not _is_usable_print_area_item(candidate_text, has_print_frames=has_print_frames):
                continue
            if (
                number_text.get("view_name")
                and candidate_text.get("view_name")
                and number_text.get("view_name") != candidate_text.get("view_name")
            ):
                continue
            if (
                number_text.get("layer_no") is not None
                and candidate_text.get("layer_no") is not None
                and number_text.get("layer_no") != candidate_text.get("layer_no")
            ):
                continue
            candidate_x = candidate_text.get("position_x")
            candidate_y = candidate_text.get("position_y")
            if not isinstance(candidate_x, (int, float)) or not isinstance(candidate_y, (int, float)):
                continue
            delta_x = float(candidate_x) - float(number_x)
            delta_y = float(candidate_y) - float(number_y)
            distance = abs(delta_y)
            if distance < 4.0 or distance > 40.0 or abs(delta_x) > max(1.0, distance * 0.08):
                continue
            lines = _text_lines_from_payload(candidate_text)
            if len(lines) != 1:
                continue
            value = normalize_identity_name_value(lines[0])
            if not value or len(_normalize_for_match(value)) < 4:
                continue
            if not _identity_name_value_is_usable("drawing_name", value):
                continue
            if _clean_drawing_number_value(value):
                continue
            if DATE_VALUE_PATTERN.search(value) or _SCALE_RATIO_TOKEN_RE.fullmatch(value):
                continue
            if re.search(r"[-+]?\d+(?:\.\d+)?\s*(?:kg|g|t)\b", value, re.IGNORECASE):
                continue
            if _classify_material_value(value, allow_unknown=False)["status"] == "formal":
                continue
            ranked.append((distance, value, candidate_text))

    if not ranked:
        return None, None
    ranked.sort(key=lambda item: item[0])
    _, value, candidate_text = ranked[0]
    return value, candidate_text


def _build_title_block_candidates(texts: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    # 別文字要素の座標結合は誤対応リスクが高いため、明示された名称ラベルの直近値だけに限定する。
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
                    if field in IDENTITY_NAME_FIELDS:
                        value = normalize_identity_name_value(value)
                    confidence = "medium" if _is_field_value_usable(field, value, line) else "low"
                    if confidence == "low":
                        value = None
                    if not value and line_index + 1 < len(lines):
                        next_value = lines[line_index + 1].strip()
                        if field in IDENTITY_NAME_FIELDS:
                            next_value = normalize_identity_name_value(next_value)
                        if _is_field_value_usable(field, next_value, line):
                            value = next_value
                            confidence = "medium"
                    paired_text = None
                    if not value and field in IDENTITY_NAME_FIELDS:
                        value, paired_text = _nearest_identity_name_value(
                            label_text=text,
                            texts=texts,
                            field=field,
                            has_print_frames=has_print_frames,
                        )
                        if value:
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
                            "value_position_x": paired_text.get("position_x") if paired_text else None,
                            "value_position_y": paired_text.get("position_y") if paired_text else None,
                            "source": "2d_text_near_identity_label" if paired_text else "2d_text",
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
        if DATE_VALUE_PATTERN.search(evidence_text) and any(
            _normalize_for_match(keyword) in normalized_evidence
            for keyword in ("改訂日", "訂正日", "revision date", "rev date")
        ):
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
        if field in IDENTITY_NAME_FIELDS and not _identity_name_value_is_usable(field, value):
            # 「品名 SUS304」のように欄名だけが誤っていても、値が正式な材質規格なら
            # 外部AIへ送らず材質辞書で確定する。
            material = _classify_material_value(value, allow_unknown=False)
            if material["status"] == "formal" and "material" not in selected:
                selected["material"] = material["canonical"]
            continue
        if field == "drawing_number":
            value = _clean_drawing_number_value(value)
            if not value:
                continue
        elif field in IDENTITY_NAME_FIELDS:
            value = normalize_identity_name_value(value)
            if not value:
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


def _material_name(material: dict) -> str | None:
    return material.get("name") or material.get("material_name")


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
        for material in _normalize_material_items(part.get("materials", []) or []):
            material_id = _material_id(material)
            material_name = _material_name(material)
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


def normalize_raw_extract(
    raw_payload: dict,
    *,
    config: ExtractionConfig = DEFAULT_CONFIG,
    dictionary_provider: DictionaryProvider | None = None,
) -> dict:
    """抽出方式ごとに異なるraw JSONを、タグ・検索・表示で共用するcanonical属性へ変換する。

    読み方は「共通の空枠を作る→3Dまたは2D固有値を埋める→辞書で業務語彙を確定する」の順である。
    取得できない値は推測で補わずNoneまたは空配列にし、未抽出と実値0を区別する。
    設定と辞書は引数境界から受け取り、Django settings・ORM・外部APIへアクセスしない。
    """

    provider = dictionary_provider or SeedDictionaryProvider()
    dictionary_mappings = {
        kind: provider.get_mapping(kind)
        for kind in DICTIONARY_KINDS
    }
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

    # どの抽出形式でも同じキーを返し、画面やタグ生成側に形式別の条件分岐を増やさない。
    canonical = {
        "drawing_number": None,
        "drawing_number_candidates": [],
        "drawing_name": None,
        "part_name": None,
        "product_name": None,
        "equipment_name": None,
        "unit_name": None,
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
        "created_date": None,
        "checked_date": None,
        "approved_date": None,
        "revision_date": None,
        "prfx": None,
        "unit_number": None,
        "source_format": raw_payload.get("source_format", "icad"),
        "source_kind": source_kind,
        "document_kind": None,
        "customer_name": None,
        "project_name": None,
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
        "global_moment": {},
        "gravity_moment": {},
        "main_moment": {},
        "inertia_moment_candidates": [],
        "inertia_moment_candidate_count": 0,
        "material_probe_status": None,
        "material_ids": [],
        "material_names": [],
        "material_specific_gravities": [],
        "part_material_candidates": [],
        "part_material_candidate_count": 0,
        "external_part_material_candidates": [],
        "external_part_material_candidate_count": 0,
        "internal_part_material_keywords": [],
        "external_part_material_keywords": [],
        "prfx_candidates": [],
        "unit_number_candidates": [],
        "part_name_candidates": [],
        "external_part_name_candidates": [],
        "part_names": [],
        "part_comments": [],
        "part_tree_paths": [],
        "internal_part_names": [],
        "internal_part_comments": [],
        "internal_part_tree_paths": [],
        "external_part_names": [],
        "external_part_comments": [],
        "external_part_tree_paths": [],
        "step_product_names": [],
        "step_products": [],
        "step_assembly_relationships": [],
        "step_assembly_relationship_count": 0,
        "part_ex_info_fields": {},
        "part_ex_info_tokens": [],
        "internal_part_ex_info_fields": {},
        "internal_part_ex_info_tokens": [],
        "external_part_ex_info_fields": {},
        "external_part_ex_info_tokens": [],
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
        "dxf_layers": [],
        "dxf_block_references": [],
        "dxf_block_attribute_count": 0,
        "dxf_block_attribute_tokens": [],
        "raw_2d_sections": None,
        "title_block_fields": {},
        "title_block_candidates": [],
        "revision_note_candidates": [],
        "revision_note_count": 0,
        "dimension_count": 0,
        "dimension_values": [],
        "dimension_symbols": [],
        "dimension_tolerance_count": 0,
        "dimension_tolerance_values": [],
        "geometric_tolerance_count": 0,
        "tolerance_texts": [],
        "tolerance_candidates": [],
        "tolerance_candidate_count": 0,
        "weld_instruction_count": 0,
        "weld_types": [],
        "weld_note_texts": [],
        "weld_note_candidates": [],
        "weld_note_candidate_count": 0,
        "balloon_keys": [],
        "balloon_candidates": [],
        "balloon_candidate_count": 0,
        "surface_treatment_tokens": [],
        "paint_instruction_tokens": [],
        "geometry_feature_candidates": [],
        "view_reference_candidates": [],
        "view_reference_candidate_count": 0,
        "curve_section_candidates": [],
        "curve_section_candidate_count": 0,
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
        "heat_treatment_evidence": [],
        "hardness_spec_candidates": [],
        "hardness_spec_values": [],
        "scale_candidates": [],
        "inspection_keywords": [],
        "change_keywords": [],
        "issue_keywords": [],
        "normalizer_version": config.normalizer_version,
    }
    equipment_category_priority_tokens: list[str] = []

    if source_kind == "3d":
        # 3Dではパーツツリーを中心に、材質・質量・外部参照・付加情報を対象別候補へ展開する。
        top_part = raw_extract.get("top_part", {})
        parts = [part for part in (raw_extract.get("parts", []) or []) if isinstance(part, dict)]
        # アセンブリ本体と外部参照パーツは別の情報源である。
        # 外部パーツは検索・構成証跡として保持するが、本体名称・本体材質へ混ぜない。
        internal_parts = [part for part in parts if not _is_external_part_payload(part)]
        external_parts = [part for part in parts if _is_external_part_payload(part)]
        mass_properties = raw_extract.get("mass_properties", {}) or {}
        materials = _normalize_material_items(raw_extract.get("materials", []) or [])
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
        canonical["global_moment"] = mass_properties.get("global_moment") or {}
        canonical["gravity_moment"] = mass_properties.get("gravity_moment") or {}
        canonical["main_moment"] = mass_properties.get("main_moment") or {}
        canonical["inertia_moment_candidates"] = _build_inertia_moment_candidates(mass_properties)
        canonical["inertia_moment_candidate_count"] = len(canonical["inertia_moment_candidates"])
        if all(mass_properties.get(key) is not None for key in ("center_of_gravity_x", "center_of_gravity_y", "center_of_gravity_z")):
            canonical["center_of_gravity"] = (
                f"{mass_properties.get('center_of_gravity_x')}, "
                f"{mass_properties.get('center_of_gravity_y')}, "
                f"{mass_properties.get('center_of_gravity_z')}"
            )
        canonical["material_probe_status"] = raw_extract.get("material_probe_status")
        canonical["material_ids"] = _flatten_strings(_material_id(material) for material in materials)
        canonical["material_names"] = _flatten_strings(_material_name(material) for material in materials)
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
        canonical["internal_part_names"] = _flatten_strings(part.get("name") for part in internal_parts)
        canonical["internal_part_comments"] = _flatten_strings(part.get("comment") for part in internal_parts)
        canonical["internal_part_tree_paths"] = [
            " > ".join(part.get("tree_path", []))
            for part in internal_parts
            if part.get("tree_path")
        ]
        canonical["external_part_names"] = _flatten_strings(part.get("name") for part in external_parts)
        canonical["external_part_comments"] = _flatten_strings(part.get("comment") for part in external_parts)
        canonical["external_part_tree_paths"] = [
            " > ".join(part.get("tree_path", []))
            for part in external_parts
            if part.get("tree_path")
        ]
        step_products = raw_extract.get("step_products", []) or []
        step_assembly_relationships = raw_extract.get("step_assembly_relationships", []) or []
        canonical["step_products"] = step_products
        canonical["step_product_names"] = _flatten_strings(product.get("name") for product in step_products if isinstance(product, dict))
        canonical["step_assembly_relationships"] = step_assembly_relationships
        canonical["step_assembly_relationship_count"] = len(step_assembly_relationships)
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
        for scope_name, scoped_parts in (
            ("internal", internal_parts),
            ("external", external_parts),
        ):
            canonical[f"{scope_name}_part_ex_info_fields"] = {
                ".".join(part.get("tree_path", []) or [part.get("name") or f"part_{index}"]): part.get("ex_info_fields", {})
                for index, part in enumerate(scoped_parts)
                if part.get("ex_info_fields")
            }
            canonical[f"{scope_name}_part_ex_info_tokens"] = _flatten_strings(
                value
                for part in scoped_parts
                for value in [part.get("ex_info"), *(part.get("ex_info_fields", {}) or {}).values()]
            )
        canonical["ref_model_names"] = _flatten_strings(part.get("ref_model_name") for part in parts)
        canonical["ref_model_paths"] = _flatten_strings(part.get("ref_model_path") for part in parts)
        internal_identity_tokens = _flatten_strings(
            [
                top_part.get("name"),
                top_part.get("comment"),
                top_part.get("ex_info"),
                *canonical["internal_part_names"],
                *canonical["internal_part_ex_info_tokens"],
            ]
        )
        external_identity_tokens = _flatten_strings(
            [
                *canonical["external_part_names"],
                *canonical["external_part_comments"],
                *canonical["external_part_ex_info_tokens"],
                *canonical["ref_model_names"],
            ]
        )
        top_level_parts = [
            part
            for part in internal_parts
            if (
                part.get("depth") == 0
                or (
                    isinstance(part.get("tree_path"), list)
                    and len(part.get("tree_path") or []) <= 1
                )
            )
        ]
        if not top_level_parts and internal_parts:
            top_level_parts = [internal_parts[0]]
        # ICADのUser_WBHNAは部品ツリー名ではなく、設計者が登録した業務名称。
        # 子部品の「アーム」等より最上位の業務名称を先に装置カテゴリ判定へ使う。
        equipment_category_priority_tokens = _flatten_strings(
            field_value
            for part in top_level_parts
            for field_key, field_value in (part.get("ex_info_fields") or {}).items()
            if _normalize_for_match(str(field_key)) in ICAD_BUSINESS_NAME_FIELD_KEYS
        )
        top_level_identity_tokens = _flatten_strings(
            [
                top_part.get("comment"),
                top_part.get("ex_info"),
                *[
                    value
                    for part in top_level_parts
                    for value in [
                        part.get("comment"),
                        part.get("ex_info"),
                        *(part.get("ex_info_fields") or {}).values(),
                    ]
                ],
            ]
        )
        # 3D最上位パーツ名はモデル内部識別子であり業務名称とは限らない。
        # 名称・図番として採用するのは、最上位コメントや最上位付加情報に明示ラベルがある値だけにする。
        # 子部品の「製品名」「部品番号」をICD全体へ誤って昇格させない。
        for field in ("drawing_number", "drawing_name", "part_name", "product_name", "equipment_name", "unit_name"):
            candidates = _merge_unique(
                _extract_identity_candidates_from_part_ex_info(top_level_parts, field)
                + _extract_labeled_field_candidates(field, top_level_identity_tokens)
            )
            if field in IDENTITY_NAME_FIELDS:
                candidates = [
                    candidate
                    for candidate in candidates
                    if _identity_name_value_is_usable(field, candidate)
                ]
            if candidates:
                canonical[field] = (
                    _clean_drawing_number_value(candidates[0])
                    if field == "drawing_number"
                    else normalize_identity_name_value(candidates[0])
                )
        if canonical.get("drawing_number"):
            canonical["drawing_number_candidates"] = [
                {
                    "value": canonical["drawing_number"],
                    "source": "3d_part_extended_info",
                    "confidence": "high",
                    "evidence": "top_part/parts.ex_info_fields",
                }
            ]
        canonical["part_name_candidates"] = _merge_unique(
            _flatten_strings([canonical.get("part_name")])
            + _match_dictionary_values(
                internal_identity_tokens,
                dictionary_mappings[KIND_PART_NAME],
            )
        )
        canonical["external_part_name_candidates"] = _match_dictionary_values(
            external_identity_tokens,
            dictionary_mappings[KIND_PART_NAME],
        )
        canonical["prfx_candidates"] = _merge_unique(
            _extract_identity_candidates_from_part_ex_info(internal_parts, "prfx")
            + _extract_labeled_field_candidates("prfx", internal_identity_tokens)
        )
        canonical["unit_number_candidates"] = _merge_unique(
            _extract_identity_candidates_from_part_ex_info(internal_parts, "unit_number")
            + _extract_labeled_field_candidates("unit_number", internal_identity_tokens)
        )
        heat_treatment_tokens = _flatten_strings(
            [
                top_part.get("comment"),
                top_part.get("ex_info"),
                *canonical["part_comments"],
                *canonical["part_ex_info_tokens"],
            ]
        )
        canonical["heat_treatment_keywords"], canonical["heat_treatment_evidence"] = _match_heat_treatment_keywords(
            heat_treatment_tokens,
            dictionary_mappings[KIND_HEAT_TREATMENT],
        )
        canonical["hardness_spec_candidates"] = _extract_hardness_spec_candidates(heat_treatment_tokens)
        canonical["hardness_spec_values"] = [item["value"] for item in canonical["hardness_spec_candidates"]]
        canonical["part_material_candidates"] = _build_part_material_candidates(internal_parts, materials)
        canonical["part_material_candidate_count"] = len(canonical["part_material_candidates"])
        canonical["external_part_material_candidates"] = _build_part_material_candidates(external_parts, [])
        canonical["external_part_material_candidate_count"] = len(canonical["external_part_material_candidates"])
        part_material_keywords, part_unresolved_material_keywords = _split_material_keywords(
            _flatten_strings(candidate.get("canonical_material") for candidate in canonical["part_material_candidates"])
            + _flatten_strings(candidate.get("material_id") for candidate in canonical["part_material_candidates"])
            + _flatten_strings(candidate.get("material_name") for candidate in canonical["part_material_candidates"])
        )
        canonical["internal_part_material_keywords"] = part_material_keywords
        canonical["material_keywords"] = _merge_unique(canonical["material_keywords"] + part_material_keywords)
        canonical["unresolved_material_keywords"] = _merge_unique(
            canonical["unresolved_material_keywords"] + part_unresolved_material_keywords
        )
        external_material_keywords, _ = _split_material_keywords(
            _flatten_strings(
                candidate.get("canonical_material")
                for candidate in canonical["external_part_material_candidates"]
            )
            + _flatten_strings(
                candidate.get("material_id")
                for candidate in canonical["external_part_material_candidates"]
            )
            + _flatten_strings(
                candidate.get("material_name")
                for candidate in canonical["external_part_material_candidates"]
            )
        )
        canonical["external_part_material_keywords"] = external_material_keywords
        canonical["external_part_exists"] = bool(external_parts)
        canonical["mirror_part_exists"] = any(part.get("is_mirror") for part in parts)
        canonical["unresolved_part_exists"] = any(part.get("is_unloaded") for part in parts)

        # 検索用語はraw値を捨てずにまとめ、後段の辞書照合で客先・案件・装置名へ昇格させる。
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
                *canonical["step_product_names"],
                *_flatten_strings(
                    value
                    for relationship in step_assembly_relationships
                    if isinstance(relationship, dict)
                    for value in [
                        relationship.get("parent_name"),
                        relationship.get("child_name"),
                        relationship.get("name"),
                        relationship.get("description"),
                    ]
                ),
                *canonical["part_comments"],
                *canonical["part_ex_info_tokens"],
                *canonical["ref_model_names"],
            ]
        )
        canonical["part_keywords"] = search_tokens
    else:
        # 2Dでは印刷枠内を自動採用対象とし、枠外・判定不明の要素はraw証跡にだけ残す。
        texts = _normalize_text_items(raw_extract.get("texts", []))
        dimensions = raw_extract.get("dimensions", [])
        primitives = raw_extract.get("geometry_primitives", [])
        weld_notes = raw_extract.get("weld_notes", [])
        balloons = raw_extract.get("balloons", [])
        tolerances = raw_extract.get("tolerances", [])
        block_references = raw_extract.get("block_references", []) or []
        referenced_parts = raw_extract.get("referenced_parts", [])
        has_print_frames = _has_print_frames(raw_extract)
        # 印刷枠があっても全文字の枠内外がunknownなら、フィルターの判定材料がない。
        # その場合だけ文字を残し、名称・図面番号を「未抽出」にしてしまう過剰除外を避ける。
        enforce_text_print_area = _should_enforce_print_area(texts, has_print_frames=has_print_frames)
        trusted_texts = _trusted_print_area_items(texts, has_print_frames=enforce_text_print_area)
        trusted_dimensions = _trusted_print_area_items(dimensions, has_print_frames=has_print_frames)
        trusted_weld_notes = _trusted_print_area_items(weld_notes, has_print_frames=has_print_frames)
        trusted_balloons = _trusted_print_area_items(balloons, has_print_frames=has_print_frames)
        trusted_tolerances = _trusted_print_area_items(tolerances, has_print_frames=has_print_frames)
        trusted_referenced_parts = _trusted_print_area_items(referenced_parts, has_print_frames=has_print_frames)
        trusted_text_tokens = _flatten_strings(
            text_line
            for text in trusted_texts
            for text_line in _text_lines_from_payload(text)
        )
        trusted_dimension_symbols = _flatten_strings(
            value
            for dimension in trusted_dimensions
            for value in [
                dimension.get("mark_2") or dimension.get("mark2"),
                dimension.get("mark_3") or dimension.get("mark3"),
                dimension.get("front_word"),
                dimension.get("back_word"),
            ]
        )
        trusted_native_weld_note_texts = _flatten_strings(
            note.get("text")
            for note in trusted_weld_notes
        )
        trusted_weld_note_texts = _merge_unique(
            [
                *trusted_native_weld_note_texts,
                *_weld_instruction_texts(trusted_text_tokens),
            ]
        )
        trusted_balloon_keys = _flatten_strings(balloon.get("text") for balloon in trusted_balloons)
        trusted_tolerance_texts = _flatten_strings(tolerance.get("text") for tolerance in trusted_tolerances)

        canonical["text_tokens"] = _flatten_strings(
            text_line
            for text in texts
            for text_line in _text_lines_from_payload(text)
        )
        canonical["label_texts"] = _flatten_strings(text.get("joined_text") for text in texts if text.get("source_type") == "label")
        canonical["dxf_layers"] = _normalize_layer_names(raw_extract.get("layers", []) or [])
        canonical["dxf_block_references"] = [
            reference
            for reference in block_references
            if isinstance(reference, dict)
        ]
        canonical["dxf_block_attribute_count"] = sum(
            len(reference.get("attributes") or [])
            for reference in canonical["dxf_block_references"]
        )
        canonical["dxf_block_attribute_tokens"] = _flatten_strings(
            value
            for reference in canonical["dxf_block_references"]
            for attribute in (reference.get("attributes") or [])
            if isinstance(attribute, dict)
            for value in [reference.get("block_name"), attribute.get("tag"), attribute.get("value")]
        )
        trusted_dimension_tolerances = [
            dimension
            for dimension in trusted_dimensions
            if _dimension_has_tolerance(dimension)
        ]
        canonical["dimension_count"] = len(trusted_dimensions)
        canonical["dimension_values"] = _flatten_strings(
            value
            for dimension in dimensions
            for value in [
                dimension.get("value_1") or dimension.get("value1"),
                dimension.get("value_2") or dimension.get("value2"),
            ]
        )
        canonical["dimension_symbols"] = _flatten_strings(
            value
            for dimension in dimensions
            for value in [
                dimension.get("mark_2") or dimension.get("mark2"),
                dimension.get("mark_3") or dimension.get("mark3"),
                dimension.get("front_word"),
                dimension.get("back_word"),
            ]
        )
        canonical["dimension_tolerance_count"] = len(trusted_dimension_tolerances)
        canonical["dimension_tolerance_values"] = _flatten_strings(
            str(value) if value is not None else None
            for dimension in trusted_dimension_tolerances
            for value in [
                dimension.get("upper_tol"),
                dimension.get("lower_tol"),
                dimension.get("dimtp"),
                dimension.get("dimtm"),
            ]
        )
        if str(canonical["source_format"]).lower() == "icad":
            canonical["geometric_tolerance_count"] = len(trusted_tolerances)
        else:
            canonical["geometric_tolerance_count"] = sum(
                1
                for tolerance in trusted_tolerances
                if tolerance.get("source_type") == "geometric_tolerance"
                or tolerance.get("dxf_entity_type") == "TOLERANCE"
            )
        canonical["weld_instruction_count"] = max(
            len(trusted_weld_notes),
            len(trusted_weld_note_texts),
        )
        canonical["weld_types"] = _classify_weld_types(trusted_weld_note_texts)
        canonical["weld_note_texts"] = _merge_unique(
            [
                *_flatten_strings(note.get("text") for note in weld_notes),
                *_weld_instruction_texts(canonical["text_tokens"]),
            ]
        )
        canonical["balloon_keys"] = _flatten_strings(balloon.get("text") for balloon in balloons)
        canonical["tolerance_texts"] = _flatten_strings(tolerance.get("text") for tolerance in tolerances)
        canonical["weld_note_candidates"] = _structured_2d_symbol_candidates(
            trusted_weld_notes,
            value_key="text",
            source="2d_weld_note",
        )
        canonical["weld_note_candidate_count"] = len(canonical["weld_note_candidates"])
        canonical["balloon_candidates"] = _structured_2d_symbol_candidates(
            trusted_balloons,
            value_key="text",
            source="2d_balloon",
        )
        canonical["balloon_candidate_count"] = len(canonical["balloon_candidates"])
        canonical["tolerance_candidates"] = _structured_2d_symbol_candidates(
            trusted_tolerances,
            value_key="text",
            source="2d_tolerance",
        )
        canonical["tolerance_candidate_count"] = len(canonical["tolerance_candidates"])
        canonical["referenced_2d_part_count"] = len(referenced_parts)
        canonical["referenced_2d_trusted_part_count"] = len(trusted_referenced_parts)
        canonical["referenced_2d_part_names"] = _flatten_strings(part.get("name") for part in trusted_referenced_parts)
        canonical["referenced_2d_part3d_names"] = _flatten_strings(part.get("part3d_name") for part in trusted_referenced_parts)
        canonical["referenced_2d_ref_model_names"] = _flatten_strings(part.get("ref_model_name") for part in trusted_referenced_parts)
        canonical["referenced_2d_ref_vs_names"] = _flatten_strings(part.get("ref_vs_name") for part in trusted_referenced_parts)
        # 生の図面文字列はtext_tokens等へ監査証跡として残す。
        # spec_tokensは後段の辞書照合で正規名だけを追加し、任意の注記を規格タグへ誤採用しない。
        canonical["spec_tokens"] = []
        # 図枠は候補一覧と採用値を分け、どの文字要素から値を選んだか後でレビューできるようにする。
        canonical["title_block_candidates"] = _build_title_block_candidates(
            texts,
            has_print_frames=enforce_text_print_area,
        )
        canonical["title_block_fields"] = _select_title_block_fields(canonical["title_block_candidates"])
        title_fields = canonical["title_block_fields"]
        # 図面番号は図枠の明示値を正とする。図枠で取れないときだけ、
        # raw文字とファイル名を照合して参照図番の混入を抑えながら救済する。
        canonical["drawing_number"], canonical["drawing_number_candidates"] = _derive_drawing_number(
            source_file=source_file,
            title_number=title_fields.get("drawing_number"),
            text_tokens=canonical["text_tokens"],
        )
        if not any(title_fields.get(field) for field in IDENTITY_NAME_FIELDS):
            aligned_name, aligned_text = _nearest_drawing_name_aligned_with_number(
                texts=texts,
                drawing_number=canonical["drawing_number"],
                has_print_frames=enforce_text_print_area,
            )
            if aligned_name and aligned_text:
                title_fields["drawing_name"] = aligned_name
                canonical["title_block_candidates"].append(
                    {
                        "field": "drawing_name",
                        "label": "図面名",
                        "value": aligned_name,
                        "evidence_text": aligned_name,
                        "confidence": "medium",
                        "view_name": aligned_text.get("view_name"),
                        "layer_no": aligned_text.get("layer_no"),
                        "position_x": aligned_text.get("position_x"),
                        "position_y": aligned_text.get("position_y"),
                        "value_position_x": aligned_text.get("position_x"),
                        "value_position_y": aligned_text.get("position_y"),
                        "source": "2d_text_aligned_with_drawing_number",
                    }
                )
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
            "drawing_name": "drawing_name",
            "part_name": "part_name",
            "product_name": "product_name",
            "equipment_name": "equipment_name",
            "unit_name": "unit_name",
            "material": "material",
            "weight": "weight_value",
            "surface_treatment": "surface_treatment",
            "coating_instruction": "paint",
            "scale": "scale",
            "checker": "checker",
            "approver": "approver",
            "date": "drawing_date",
            "created_date": "created_date",
            "checked_date": "checked_date",
            "approved_date": "approved_date",
            "revision_date": "revision_date",
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
        # 図枠見出しと値が別文字要素でも、KS番号など文字列単体で意味が確定する塗装仕様は採用する。
        # 候補が複数ある場合は代表値を推測せず、一覧候補だけを保持してpaintは確定しない。
        canonical["paint_instruction_tokens"] = _extract_paint_instruction_tokens(trusted_text_tokens)
        if not canonical.get("paint") and len(canonical["paint_instruction_tokens"]) == 1:
            canonical["paint"] = canonical["paint_instruction_tokens"][0]
        part_name_tokens = _flatten_strings(
            [
                *trusted_text_tokens,
                *[str(value) for value in title_fields.values() if value],
            ]
        )
        canonical["part_name_candidates"] = _match_dictionary_values(
            part_name_tokens,
            dictionary_mappings[KIND_PART_NAME],
        )
        canonical["part_name_candidates"] = _merge_unique(
            _flatten_strings([canonical.get("part_name")])
            + canonical["part_name_candidates"]
        )
        # 尺度: ラベル付き図枠欄が無い場合でも「1:6」「S=1:6」形のトークンから拾う。
        # 候補が1種類に定まる場合だけ scale を確定する(テーパ表記 1:10 との衝突対策)。
        canonical["scale_candidates"] = _extract_scale_candidates(trusted_text_tokens)
        if not canonical.get("scale"):
            distinct_scale_values = _merge_unique([item["value"] for item in canonical["scale_candidates"]])
            if len(distinct_scale_values) == 1:
                canonical["scale"] = distinct_scale_values[0]
        # 熱処理・硬度: 図面注記と図枠欄の値から抽出する。
        heat_treatment_tokens = _flatten_strings(
            [
                *trusted_text_tokens,
                *[str(value) for value in title_fields.values() if value],
            ]
        )
        canonical["heat_treatment_keywords"], canonical["heat_treatment_evidence"] = _match_heat_treatment_keywords(
            heat_treatment_tokens,
            dictionary_mappings[KIND_HEAT_TREATMENT],
        )
        canonical["hardness_spec_candidates"] = _extract_hardness_spec_candidates(heat_treatment_tokens)
        canonical["hardness_spec_values"] = [item["value"] for item in canonical["hardness_spec_candidates"]]
        canonical["revision_note_candidates"] = _build_revision_note_candidates(
            texts,
            has_print_frames=enforce_text_print_area,
        )
        canonical["revision_note_count"] = len(canonical["revision_note_candidates"])
        canonical["geometry_feature_candidates"] = _build_geometry_feature_candidates(primitives, has_print_frames=has_print_frames)
        canonical.update(_build_geometry_attribute_summary(primitives, has_print_frames=has_print_frames))
        canonical["view_reference_candidates"] = _build_view_reference_candidates(primitives, has_print_frames=has_print_frames)
        canonical["view_reference_candidate_count"] = len(canonical["view_reference_candidates"])
        canonical["curve_section_candidates"] = _build_curve_section_candidates(primitives, has_print_frames=has_print_frames)
        canonical["curve_section_candidate_count"] = len(canonical["curve_section_candidates"])
        # 画面レビュー用に図枠・中央図面・寸法・注記・バルーン・製造記号の区分を保持する。
        canonical["raw_2d_sections"] = _build_2d_sections(
            raw_extract={**raw_extract, "texts": texts},
            canonical=canonical,
            has_print_frames=has_print_frames,
            trusted_texts=trusted_texts,
            trusted_dimensions=trusted_dimensions,
            trusted_weld_notes=trusted_weld_notes,
            trusted_balloons=trusted_balloons,
            trusted_tolerances=trusted_tolerances,
            enforce_text_print_area=enforce_text_print_area,
        )

        search_tokens = (
            source_path_tokens
            + model_info_tokens
            + trusted_text_tokens
            + canonical["dxf_block_attribute_tokens"]
            + canonical["dxf_layers"]
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

    # 最後に2D/3D共通の検索語へ辞書を適用し、業務上の客先・案件・装置カテゴリを確定する。
    # 辞書はDB(GUI編集)を正とし、未登録種別は seed へフォールバックする。
    customer_name = _match_dictionary(canonical["part_keywords"], dictionary_mappings[KIND_CUSTOMER])
    equipment_identity_tokens = _flatten_strings(
        [
            canonical.get("equipment_name"),
            canonical.get("unit_name"),
            canonical.get("product_name"),
            canonical.get("drawing_name"),
            canonical.get("part_name"),
            *equipment_category_priority_tokens,
        ]
    )
    # 装置カテゴリは名称欄・最上位業務名称を先に判定する。図面全体には子部品名も含まれるため、
    # 全検索語を先に使うと「シュート」内の1部品である「アーム」へ誤分類される。
    equipment_category = _match_dictionary(
        equipment_identity_tokens,
        dictionary_mappings[KIND_EQUIPMENT_CATEGORY],
    ) or _match_dictionary(
        canonical["part_keywords"],
        dictionary_mappings[KIND_EQUIPMENT_CATEGORY],
    )
    project_name = _match_dictionary(canonical["part_keywords"], dictionary_mappings[KIND_PROJECT])

    if customer_name:
        canonical["customer_name"] = customer_name
    if equipment_category:
        canonical["equipment_category"] = equipment_category
    if project_name and not canonical.get("project_name"):
        # 案件辞書(パス・部品名のフォルダ語彙)から案件名を確定する。図枠由来があればそちらを優先。
        canonical["project_name"] = project_name

    for maker, candidates in dictionary_mappings[KIND_MAKER].items():
        if any(candidate.lower() in " ".join(token.lower() for token in canonical["part_keywords"]) for candidate in candidates):
            canonical["maker_keywords"].append(maker)

    for spec, candidates in dictionary_mappings[KIND_SPEC].items():
        if any(candidate.lower() in " ".join(token.lower() for token in canonical["part_keywords"]) for candidate in candidates):
            canonical["spec_tokens"].append(spec)

    if source_kind == "3d":
        canonical["confidence_summary"] = "high"

    return canonical
