from __future__ import annotations


NOISY_COMPOSED_KEYS = (
    "text_tokens",
    "spec_tokens",
    "part_keywords",
    "source_path_tokens",
)

COMPOSED_SUMMARY_FIELDS = (
    ("source_file_name", "ファイル名"),
    ("source_directory_path", "保存フォルダ"),
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

SOURCE_FILE_FIELDS = (
    ("source_file_name", "ファイル名"),
    ("source_file_stem", "拡張子なしファイル名"),
    ("source_extension", "拡張子"),
    ("source_directory_path", "保存フォルダ"),
    ("source_full_path", "フルパス"),
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


def _tag_target_candidates(tag: str, source: str) -> list[str]:
    if tag.startswith("客先:"):
        return ["プロジェクト", "製品・装置・ユニット", "図面"]
    if tag.startswith("装置:"):
        return ["製品・装置・ユニット", "プロジェクト", "図面"]
    if tag.startswith("メーカー:"):
        return ["部品", "図面", "製品・装置・ユニット"]
    if tag.startswith("規格:"):
        return ["図面", "部品", "製品・装置・ユニット"]
    if source in {"material_keywords", "part_ex_info_fields", "part_ex_info_tokens"}:
        return ["部品", "図面"]
    return ["図面"]


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


def _tag_items(tags: list[dict]) -> list[dict]:
    items: list[dict] = []
    for tag in tags or []:
        tag_value = tag.get("tag", "")
        source = tag.get("source", "")
        items.append(
            {
                "tag": tag_value,
                "source": _display_value(source),
                "confidence": _display_value(tag.get("confidence")),
                "manualFlag": _display_value(tag.get("manual_flag")),
                "ruleVersion": _display_value(tag.get("tag_rule_version")),
                "targetCandidates": _tag_target_candidates(tag_value, source),
            }
        )
    return items


def _source_file_rows(canonical_attributes: dict | None) -> list[dict]:
    canonical_attributes = canonical_attributes or {}
    return [_make_row(key, label, canonical_attributes.get(key)) for key, label in SOURCE_FILE_FIELDS]


def _text_preview_items(texts: list[dict], limit: int = 8) -> list[dict]:
    previews: list[dict] = []
    for text in texts[:limit]:
        previews.append(
            {
                "viewName": _display_value(text.get("view_name")),
                "layerNo": _display_value(text.get("layer_no")),
                "text": _display_value(text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])),
            }
        )
    return previews


def _dimension_preview_items(dimensions: list[dict], limit: int = 8) -> list[dict]:
    previews: list[dict] = []
    for dimension in dimensions[:limit]:
        values = _string_values(
            [
                dimension.get("front_word"),
                dimension.get("value_1"),
                dimension.get("value_2"),
                dimension.get("back_word"),
                dimension.get("upper_tol"),
                dimension.get("lower_tol"),
                dimension.get("mark_2"),
                dimension.get("mark_3"),
            ]
        )
        previews.append(
            {
                "viewName": _display_value(dimension.get("view_name")),
                "layerNo": _display_value(dimension.get("layer_no")),
                "value": _display_value(" ".join(values) if values else None),
            }
        )
    return previews


def _view_sheet_preview_items(view_sheets: list[dict], limit: int = 10) -> list[dict]:
    return [
        {
            "name": _display_value(view_sheet.get("name")),
            "geometryCount": _display_value(view_sheet.get("geometry_count")),
            "scale": _display_value(view_sheet.get("scale")),
            "comment": _display_value(view_sheet.get("comment")),
        }
        for view_sheet in view_sheets[:limit]
    ]


def _print_frame_preview_items(print_frames: list[dict], limit: int = 5) -> list[dict]:
    return [
        {
            "no": _display_value(print_frame.get("no")),
            "size": _display_value(print_frame.get("size")),
            "scale": _display_value(print_frame.get("drawing_scale")),
            "range": _display_value(
                f"{print_frame.get('range_min_x')}, {print_frame.get('range_min_y')} - "
                f"{print_frame.get('range_max_x')}, {print_frame.get('range_max_y')}"
                if print_frame.get("range_min_x") is not None
                else None
            ),
        }
        for print_frame in print_frames[:limit]
    ]


def _layer_preview_items(layers: list[dict], limit: int = 10) -> list[dict]:
    named_layers = [layer for layer in layers if layer.get("name")]
    preview_source = named_layers or layers
    return [
        {
            "no": _display_value(layer.get("no")),
            "name": _display_value(layer.get("name")),
            "displayed": _display_value(layer.get("is_displayed")),
            "searchable": _display_value(layer.get("is_searchable")),
        }
        for layer in preview_source[:limit]
    ]


def _part_ex_info_preview_items(raw_parts: list[dict], limit: int = 8) -> list[dict]:
    previews: list[dict] = []
    for part in raw_parts:
        fields = part.get("ex_info_fields", {}) or {}
        if not fields:
            continue
        previews.append(
            {
                "path": _display_value(" > ".join(part.get("tree_path", []) or []) or part.get("name")),
                "fields": [
                    {"key": key, "value": value}
                    for key, value in list(fields.items())[:6]
                ],
                "fieldTotal": len(fields),
            }
        )
        if len(previews) >= limit:
            break
    return previews


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


def build_tag_review_display_payload(*, composed_metadata: dict, snapshots_by_mode: dict) -> dict:
    canonical_attributes = composed_metadata.get("canonicalAttributes", {}) or {}
    groups = [
        {
            "key": "composed",
            "label": "統合タグ",
            "description": "2D と 3D を照合したあと、viewer / RAG / 本番ナレッジシステム連携で使う候補です。",
            "tags": _tag_items(composed_metadata.get("derivedTags", []) or []),
        }
    ]
    for mode, label in (("2d", "2Dタグ"), ("3d", "3Dタグ")):
        snapshot = snapshots_by_mode.get(mode)
        groups.append(
            {
                "key": mode,
                "label": label,
                "description": f"{label}だけを根拠に作った候補です。統合時に競合があれば統合タグ側で採否を確認します。",
                "tags": _tag_items(snapshot.derived_tags_json if snapshot else []),
            }
        )

    return {
        "title": "タグ候補レビュー",
        "targetRows": [
            _make_row("drawing", "図面", "図面詳細レスポンスに tags / attributes があり、drawing_attributes API も既存受け口候補"),
            _make_row("project", "プロジェクト", "一覧画面にタグ列は未表示。project_attributes は未確認のため、詳細または補助タブ追加候補"),
            _make_row("product", "製品・装置・ユニット", "product_attributes API が既存受け口候補。装置カテゴリタグの適用候補"),
            _make_row("part", "部品", "part_attributes API が既存受け口候補。パーツ付加情報タグの適用候補"),
        ],
        "evidenceRows": [
            _make_row("source_file_name", "ファイル名", canonical_attributes.get("source_file_name")),
            _make_row("source_directory_path", "保存フォルダ", canonical_attributes.get("source_directory_path")),
            _make_row("customer_name", "客先", canonical_attributes.get("customer_name")),
            _make_row("equipment_category", "装置カテゴリ", canonical_attributes.get("equipment_category")),
            _make_row("top_part_name", "最上位パーツ名", canonical_attributes.get("top_part_name")),
            _make_row("part_ex_info_count", "パーツ付加情報あり", len(canonical_attributes.get("part_ex_info_fields", {}) or {})),
        ],
        "groups": groups,
        "conflicts": composed_metadata.get("conflicts", []) or [],
    }


def build_2d_snapshot_display(*, raw_extract: dict | None, canonical_attributes: dict | None) -> dict:
    raw_extract = raw_extract or {}
    canonical_attributes = canonical_attributes or {}

    texts = raw_extract.get("texts", []) or []
    dimensions = raw_extract.get("dimensions", []) or []
    primitives = raw_extract.get("geometry_primitives", []) or []
    weld_notes = raw_extract.get("weld_notes", []) or []
    balloons = raw_extract.get("balloons", []) or []
    tolerances = raw_extract.get("tolerances", []) or []
    view_sheets = raw_extract.get("view_sheets", []) or []
    print_frames = raw_extract.get("print_frames", []) or []
    layers = raw_extract.get("layers", []) or []
    inspectable_items = texts + dimensions + primitives + weld_notes + balloons + tolerances
    layer_tagged_count = len([item for item in inspectable_items if item.get("layer_no") is not None])
    displayed_layer_count = len([layer for layer in layers if layer.get("is_displayed")])

    summary_rows = [
        _make_row("view_sheet_count", "ビュー/用紙数", len(view_sheets)),
        _make_row("print_frame_count", "印刷枠数", len(print_frames)),
        _make_row("layer_count", "レイヤー数", len(layers)),
        _make_row("displayed_layer_count", "表示レイヤー数", displayed_layer_count),
        _make_row("text_count", "文字数", len(texts)),
        _make_row("dimension_count", "寸法数", len(dimensions)),
        _make_row("geometry_primitive_count", "線・円などの図形数", len(primitives)),
        _make_row("layer_tagged_count", "所属レイヤー取得済み要素数", layer_tagged_count),
    ]

    return {
        "summaryRows": summary_rows,
        "sourceFileRows": _source_file_rows(canonical_attributes),
        "viewSheets": _view_sheet_preview_items(view_sheets),
        "viewSheetTotal": len(view_sheets),
        "viewSheetsTruncated": len(view_sheets) > 10,
        "printFrames": _print_frame_preview_items(print_frames),
        "printFrameTotal": len(print_frames),
        "layers": _layer_preview_items(layers),
        "layerTotal": len(layers),
        "layersTruncated": len(layers) > 10,
        "textSamples": _text_preview_items(texts),
        "textTotal": len(texts),
        "dimensionSamples": _dimension_preview_items(dimensions),
        "dimensionTotal": len(dimensions),
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
        "sourceFileRows": _source_file_rows(canonical_attributes),
        "partCount": part_count,
        "partTreePaths": _preview_items(part_tree_paths),
        "partTreePathTotal": len(part_tree_paths),
        "partTreePathsTruncated": len(part_tree_paths) > 5,
        "refModelNames": _preview_items(ref_model_names),
        "refModelNameTotal": len(ref_model_names),
        "refModelNamesTruncated": len(ref_model_names) > 5,
        "partExInfoSamples": _part_ex_info_preview_items(raw_parts),
        "partExInfoTotal": len([part for part in raw_parts if part.get("ex_info_fields")]),
        "externalPartExists": bool(canonical_attributes.get("external_part_exists", False)),
        "mirrorPartExists": bool(canonical_attributes.get("mirror_part_exists", False)),
        "unresolvedPartExists": bool(canonical_attributes.get("unresolved_part_exists", False)),
        "summaryRows": summary_rows,
    }
