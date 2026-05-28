from __future__ import annotations


NOISY_COMPOSED_KEYS = (
    "text_tokens",
    "spec_tokens",
    "part_keywords",
)

COMPOSED_SUMMARY_FIELDS = (
    ("customer_name", "客先"),
    ("project_name", "案件"),
    ("equipment_category", "装置カテゴリ"),
    ("equipment_name", "装置名"),
    ("document_kind", "文書種別"),
    ("drawing_number", "図番"),
    ("drawing_name", "図面名"),
    ("revision", "リビジョン"),
    ("module_name", "モジュール"),
    ("source_format", "形式"),
    ("extraction_status", "抽出状態"),
    ("confidence_summary", "信頼度"),
    ("top_part_name", "最上位パーツ名"),
    ("external_part_exists", "外部参照パーツあり"),
    ("mirror_part_exists", "ミラーパーツあり"),
    ("unresolved_part_exists", "未解決パーツあり"),
)


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _display_value(value) -> str:
    if value is None:
        return "未抽出"
    if isinstance(value, bool):
        return "あり" if value else "なし"
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or "未抽出"
    if isinstance(value, (list, tuple, set)):
        return str(len(value))
    if isinstance(value, dict):
        return str(len(value))
    return str(value)


def _make_row(key: str, label: str, value) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "displayValue": _display_value(value),
        "hasValue": _has_value(value),
    }


def _string_values(values) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _raw_part_tree_paths(raw_extract: dict) -> list[str]:
    paths: list[str] = []
    for part in raw_extract.get("parts", []) or []:
        tree_path = part.get("tree_path", [])
        if tree_path:
            paths.append(" > ".join(item for item in tree_path if item))
    return _string_values(paths)


def _preview_items(values, limit: int = 5) -> list[str]:
    return _string_values(values)[:limit]


def build_composed_display_payload(composed_metadata: dict) -> dict:
    canonical_attributes = composed_metadata.get("canonicalAttributes", {}) or {}
    part_names = canonical_attributes.get("part_names", []) or []
    derived_tags = [
        item.get("tag")
        for item in composed_metadata.get("derivedTags", []) or []
        if item.get("tag")
    ]

    summary_rows = [_make_row(key, label, canonical_attributes.get(key)) for key, label in COMPOSED_SUMMARY_FIELDS]
    summary_rows.append(_make_row("part_count", "3Dパーツ数", len(part_names)))

    return {
        "title": "統合結果（viewer/RAG 用の統合属性）",
        "summaryRows": summary_rows,
        "tags": derived_tags,
        "conflicts": composed_metadata.get("conflicts", []) or [],
        "hiddenKeys": [key for key in NOISY_COMPOSED_KEYS if key in canonical_attributes],
    }


def build_3d_snapshot_display(*, raw_extract: dict | None, canonical_attributes: dict | None) -> dict:
    raw_extract = raw_extract or {}
    canonical_attributes = canonical_attributes or {}

    part_tree_paths = _string_values(canonical_attributes.get("part_tree_paths")) or _raw_part_tree_paths(raw_extract)
    ref_model_names = _string_values(canonical_attributes.get("ref_model_names"))
    raw_parts = raw_extract.get("parts", []) or []
    part_count = len(raw_parts) if raw_parts else len(_string_values(canonical_attributes.get("part_names")))

    summary_rows = [
        _make_row("top_part_name", "最上位パーツ名", canonical_attributes.get("top_part_name")),
        _make_row("part_count", "抽出パーツ数", part_count),
        _make_row("external_part_exists", "外部参照パーツあり", canonical_attributes.get("external_part_exists", False)),
        _make_row("mirror_part_exists", "ミラーパーツあり", canonical_attributes.get("mirror_part_exists", False)),
        _make_row("unresolved_part_exists", "未解決パーツあり", canonical_attributes.get("unresolved_part_exists", False)),
    ]

    return {
        "topPartName": canonical_attributes.get("top_part_name"),
        "partCount": part_count,
        "partTreePaths": _preview_items(part_tree_paths),
        "partTreePathTotal": len(part_tree_paths),
        "partTreePathsTruncated": len(part_tree_paths) > 5,
        "refModelNames": _preview_items(ref_model_names),
        "refModelNameTotal": len(ref_model_names),
        "refModelNamesTruncated": len(ref_model_names) > 5,
        "externalPartExists": bool(canonical_attributes.get("external_part_exists", False)),
        "mirrorPartExists": bool(canonical_attributes.get("mirror_part_exists", False)),
        "unresolvedPartExists": bool(canonical_attributes.get("unresolved_part_exists", False)),
        "summaryRows": summary_rows,
    }
