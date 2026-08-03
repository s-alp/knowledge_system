"""入力形式別の候補を統合し、canonical属性を構築する正規化本体。

公開入口はnormalization.pyに残し、本モジュールは処理順序の組み立てだけを担当する。
辞書provider以外の外部I/Oは行わず、同じ入力と設定から同じ結果を返す。
"""
from __future__ import annotations

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
from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_2d import *  # noqa: F403
from icad_tag_extraction.normalization_3d import *  # noqa: F403
from icad_tag_extraction.normalization_material import *  # noqa: F403
from icad_tag_extraction.normalization_rules import *  # noqa: F403
from icad_tag_extraction.normalization_text import *  # noqa: F403

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

__all__ = ["normalize_raw_extract"]
