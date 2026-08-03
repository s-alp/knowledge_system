"""正規化で使う図枠・形状・文字列判定規則を一箇所に定義する。

値を変更すると2D/3Dの判定結果へ影響するため、処理実装から分離し、
規則差分をレビューしやすくしている。外部I/Oや状態変更は行わない。
"""
from __future__ import annotations

import re

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


__all__ = (
    "TITLE_BLOCK_FIELD_RULES",
    "GEOMETRY_FEATURE_RULES",
    "GEOMETRY_FEATURE_TAG_EXCLUSION_REASON",
    "TWO_D_SECTION_DEFINITIONS",
    "MANUFACTURING_GEOMETRY_TYPES",
    "SURFACE_ROUGHNESS_PATTERN",
    "DATE_VALUE_PATTERN",
    "MATERIAL_VALUE_PATTERN",
    "REVISION_NOTE_KEYWORDS",
    "TITLE_BLOCK_LABEL_FRAGMENT_VALUES",
    "DRAWING_NUMBER_NOISE_VALUES",
    "DRAWING_NUMBER_NOISE_COMPACT_VALUES",
    "DRAWING_NUMBER_REFERENCE_KEYWORDS",
    "ICAD_BUSINESS_NAME_FIELD_KEYS",
    "FILE_EXTENSION_FRAGMENT_PATTERN",
    "DRAWING_SIZE_SUFFIX_PATTERN",
    "DRAWING_NUMBER_CODE_SEGMENT_PATTERN",
    "DRAWING_NUMBER_TOKEN_PATTERN",
    "DRAWING_NUMBER_FILENAME_WORD_PATTERN",
    "DRAWING_NUMBER_FILENAME_WORD_EXCLUSIONS",
    "IDENTITY_NAME_FIELDS",
    "IDENTITY_NAME_PREFIX_MARKERS_RE",
    "IDENTITY_SPEC_TOKEN_RE",
    "IDENTITY_NAME_NOISE_VALUES",
)
