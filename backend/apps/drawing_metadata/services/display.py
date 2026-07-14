from __future__ import annotations


NOISY_COMPOSED_KEYS = (
    "text_tokens",
    "spec_tokens",
    "part_keywords",
    "source_path_tokens",
)

RECONCILIATION_STATUS_LABELS = {
    "matched": "一致",
    "conflict": "競合",
    "only_2d": "2Dのみ",
    "only_3d": "3Dのみ",
    "merged": "統合",
    "manual_override": "手動上書き",
    "empty": "未抽出",
}

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
    ("mass_probe_status", "3D重量取得状態"),
    ("mass_unit_name", "3D重量単位"),
    ("mass_value", "3D質量"),
    ("weight_value", "3D重量"),
    ("volume_value", "3D体積"),
    ("area_value", "3D面積"),
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


def _make_display_row(key: str, label: str, value, display_value: str) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "displayValue": display_value,
        "hasValue": _has_value(value),
    }


def _reconciliation_row(item: dict) -> dict:
    status = item.get("status") or "empty"
    return {
        "attribute": item.get("attribute"),
        "status": status,
        "statusLabel": RECONCILIATION_STATUS_LABELS.get(status, status),
        "value2d": item.get("value2d"),
        "value2dDisplay": _display_value(item.get("value2d")),
        "value3d": item.get("value3d"),
        "value3dDisplay": _display_value(item.get("value3d")),
        "chosenValue": item.get("chosenValue"),
        "chosenValueDisplay": _display_value(item.get("chosenValue")),
        "chosenMode": item.get("chosenMode"),
        "reason": item.get("reason"),
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
                "position": _display_value(_position_label(text)),
                "insidePrintArea": _display_value(_inside_print_area_label(text.get("inside_print_area"))),
                "text": _display_value(text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])),
            }
        )
    return previews


def _title_block_candidate_items(candidates: list[dict], limit: int = 12) -> list[dict]:
    previews: list[dict] = []
    for candidate in candidates[:limit]:
        previews.append(
            {
                "field": _display_value(candidate.get("label") or candidate.get("field")),
                "value": _display_value(candidate.get("value")),
                "confidence": _display_value(candidate.get("confidence")),
                "viewName": _display_value(candidate.get("view_name")),
                "layerNo": _display_value(candidate.get("layer_no")),
                "position": _display_value(_position_label(candidate)),
                "insidePrintArea": _display_value(_inside_print_area_label(candidate.get("inside_print_area"))),
                "evidenceText": _display_value(candidate.get("evidence_text")),
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
                "position": _display_value(_position_label(dimension)),
                "insidePrintArea": _display_value(_inside_print_area_label(dimension.get("inside_print_area"))),
                "value": _display_value(" ".join(values) if values else None),
            }
        )
    return previews


def _primitive_preview_items(primitives: list[dict], limit: int = 8) -> list[dict]:
    previews: list[dict] = []
    for primitive in primitives[:limit]:
        previews.append(
            {
                "viewName": _display_value(primitive.get("view_name")),
                "layerNo": _display_value(primitive.get("layer_no")),
                "geometryType": _display_value(primitive.get("geometry_type")),
                "position": _display_value(_position_label(primitive)),
                "center": _display_value(_center_label(primitive)),
                "insidePrintArea": _display_value(_inside_print_area_label(primitive.get("inside_print_area"))),
                "summary": _display_value(primitive.get("summary")),
            }
        )
    return previews


def _geometry_feature_candidate_items(candidates: list[dict], limit: int = 10) -> list[dict]:
    previews: list[dict] = []
    for candidate in candidates[:limit]:
        previews.append(
            {
                "label": _display_value(candidate.get("label")),
                "tag": _display_value(candidate.get("tag")),
                "confidence": _display_value(candidate.get("confidence")),
                "geometryType": _display_value(candidate.get("geometry_type")),
                "count": _display_value(candidate.get("count")),
                "sampleSummaries": _display_value(candidate.get("sample_summaries")),
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


def _mass_property_rows(raw_extract: dict, canonical_attributes: dict) -> list[dict]:
    mass_properties = raw_extract.get("mass_properties", {}) or {}
    return [
        _make_row("mass_probe_status", "取得状態", canonical_attributes.get("mass_probe_status") or raw_extract.get("mass_probe_status")),
        _make_row("mass_element_count", "計算対象要素数", canonical_attributes.get("mass_element_count") or mass_properties.get("element_count")),
        _make_row("mass_unit_name", "単位", canonical_attributes.get("mass_unit_name") or mass_properties.get("unit_name")),
        _make_row("mass_value", "質量", canonical_attributes.get("mass_value") or mass_properties.get("mass")),
        _make_row("weight_value", "重量", canonical_attributes.get("weight_value") or mass_properties.get("weight")),
        _make_row("volume_value", "体積", canonical_attributes.get("volume_value") or mass_properties.get("volume")),
        _make_row("area_value", "面積", canonical_attributes.get("area_value") or mass_properties.get("area")),
        _make_row("density_value", "密度", canonical_attributes.get("density_value") or mass_properties.get("density")),
        _make_row("center_of_gravity", "重心", canonical_attributes.get("center_of_gravity") or _mass_center_label(mass_properties)),
    ]


def _material_rows(raw_extract: dict, canonical_attributes: dict) -> list[dict]:
    materials = raw_extract.get("materials", []) or []
    rows = [
        _make_row("material_probe_status", "取得状態", canonical_attributes.get("material_probe_status") or raw_extract.get("material_probe_status")),
        _make_row("material_count", "材質数", len(materials) if materials else None),
    ]
    for index, material in enumerate(materials[:8], start=1):
        material_id = material.get("mat_id") or material.get("matid")
        label = material.get("name") or material_id or f"材質{index}"
        value_parts = _string_values(
            [
                material_id,
                material.get("name"),
                material.get("specific_gravity"),
                f"elements={material.get('element_count')}" if material.get("element_count") is not None else None,
            ]
        )
        rows.append(_make_row(f"material_{index}", label, " / ".join(value_parts)))
    return rows


def _part_material_candidate_items(candidates: list[dict], limit: int = 12) -> list[dict]:
    return [
        {
            "partPath": _display_value(candidate.get("part_path")),
            "partName": _display_value(candidate.get("part_name")),
            "material": _display_value(candidate.get("material_id") or candidate.get("material_name")),
            "materialName": _display_value(candidate.get("material_name")),
            "specificGravity": _display_value(candidate.get("specific_gravity")),
            "source": _display_value(candidate.get("source")),
            "confidence": _display_value(candidate.get("confidence")),
            "reason": _display_value(candidate.get("reason")),
        }
        for candidate in candidates[:limit]
    ]


def _position_label(item: dict) -> str | None:
    x = item.get("position_x")
    y = item.get("position_y")
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _mass_center_label(item: dict) -> str | None:
    x = item.get("center_of_gravity_x")
    y = item.get("center_of_gravity_y")
    z = item.get("center_of_gravity_z")
    if x is None or y is None or z is None:
        return None
    return f"{x}, {y}, {z}"


def _center_label(item: dict) -> str | None:
    x = item.get("center_x")
    y = item.get("center_y")
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _inside_print_area_label(value) -> str | None:
    if value is True:
        return "inside"
    if value is False:
        return "outside"
    return None


def build_composed_display_payload(composed_metadata: dict) -> dict:
    canonical_attributes = composed_metadata.get("canonicalAttributes", {}) or {}
    part_names = canonical_attributes.get("part_names", []) or []
    reconciled_rows = [_reconciliation_row(item) for item in composed_metadata.get("reconciledAttributes", []) or []]
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
        "reconciliationRows": reconciled_rows,
        "reconciliationReviewRows": [
            row
            for row in reconciled_rows
            if row["status"] in {"conflict", "manual_override", "merged", "only_2d", "only_3d"}
        ],
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
    title_block_candidates = canonical_attributes.get("title_block_candidates", []) or []
    geometry_feature_candidates = canonical_attributes.get("geometry_feature_candidates", []) or []
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
        _make_row("surface_roughness_count", "表面粗さ記号数", canonical_attributes.get("surface_roughness_count")),
        _make_row("section_feature_count", "断面/切断表現数", canonical_attributes.get("section_feature_count")),
        _make_row("slot_candidate_count", "長穴/楕円候補数", canonical_attributes.get("slot_candidate_count")),
        _make_row("hole_candidate_count", "穴/円候補数", canonical_attributes.get("hole_candidate_count")),
    ]
    geometry_attribute_rows = [
        _make_display_row(
            "surface_roughness_values",
            "表面粗さ値",
            canonical_attributes.get("surface_roughness_values", []),
            ", ".join(canonical_attributes.get("surface_roughness_values", []) or []) or "未抽出",
        ),
        _make_display_row(
            "hole_candidate_diameters",
            "穴/円候補径",
            canonical_attributes.get("hole_candidate_diameters", []),
            ", ".join(str(value) for value in canonical_attributes.get("hole_candidate_diameters", []) or []) or "未抽出",
        ),
        _make_display_row(
            "slot_candidate_dimensions",
            "長穴/楕円候補寸法",
            canonical_attributes.get("slot_candidate_dimensions", []),
            str(len(canonical_attributes.get("slot_candidate_dimensions", []) or [])),
        ),
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
        "titleBlockCandidates": _title_block_candidate_items(title_block_candidates),
        "titleBlockCandidateTotal": len(title_block_candidates),
        "dimensionSamples": _dimension_preview_items(dimensions),
        "dimensionTotal": len(dimensions),
        "geometryPrimitiveSamples": _primitive_preview_items(primitives),
        "geometryPrimitiveTotal": len(primitives),
        "geometryFeatureCandidates": _geometry_feature_candidate_items(geometry_feature_candidates),
        "geometryFeatureCandidateTotal": len(geometry_feature_candidates),
        "geometryAttributeRows": geometry_attribute_rows,
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
        _make_row("mass_probe_status", "3D重量取得状態", canonical_attributes.get("mass_probe_status") or raw_extract.get("mass_probe_status")),
        _make_row("mass_value", "3D質量", canonical_attributes.get("mass_value")),
        _make_row("weight_value", "3D重量", canonical_attributes.get("weight_value")),
        _make_row("volume_value", "3D体積", canonical_attributes.get("volume_value")),
        _make_row("material_probe_status", "3D材質取得状態", canonical_attributes.get("material_probe_status") or raw_extract.get("material_probe_status")),
        _make_row("part_material_candidate_count", "部品材質候補数", canonical_attributes.get("part_material_candidate_count")),
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
        "massPropertyRows": _mass_property_rows(raw_extract, canonical_attributes),
        "hasMassProperties": bool(raw_extract.get("mass_properties")),
        "materialRows": _material_rows(raw_extract, canonical_attributes),
        "hasMaterials": bool(raw_extract.get("materials")),
        "partMaterialCandidates": _part_material_candidate_items(canonical_attributes.get("part_material_candidates", []) or []),
        "partMaterialCandidateTotal": len(canonical_attributes.get("part_material_candidates", []) or []),
        "externalPartExists": bool(canonical_attributes.get("external_part_exists", False)),
        "mirrorPartExists": bool(canonical_attributes.get("mirror_part_exists", False)),
        "unresolvedPartExists": bool(canonical_attributes.get("unresolved_part_exists", False)),
        "summaryRows": summary_rows,
    }
