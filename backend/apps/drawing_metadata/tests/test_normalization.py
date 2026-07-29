"""test_normalizationの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
主な検証観点:
- 2Dと3Dのraw値が同じcanonicalキーへそろうこと。
- 印刷枠外・判定不明の要素を自動採用しないこと。
- 図枠、尺度、材質、熱処理、硬度の誤確定を防ぐこと。
- 取得できない値を推測せずNoneまたは空配列にすること。
- canonicalから生成するタグへ根拠と採用理由が付くこと。
"""
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.tag_builder import build_derived_tags


def test_normalize_3d_raw_extract():
    payload = {
        "source_format": "icad",
        "source_kind": "3d",
        "source_file": {
            "full_path": r"J:\KO小山\KO小山ガントリー.icd",
            "directory_path": r"J:\KO小山",
            "file_name": "KO小山ガントリー.icd",
            "file_name_without_extension": "KO小山ガントリー",
            "extension": ".icd",
        },
        "raw_extract": {
            "model_info": {
                "name": "KO小山ガントリーモデル",
                "comment": "モデルコメント",
                "path": r"J:\KO小山",
                "is_read_only": True,
                "view_sheet_count": 2,
                "work_plane_count": 3,
            },
            "mass_probe_status": "available",
            "mass_properties": {
                "element_count": 17,
                "unit_name": "mm-kg",
                "mass": 0.00055092,
                "weight": 0.00540269,
                "volume": 701.64779731,
                "area": 1858.76904715,
                "density": 1.0,
                "center_of_gravity_x": 10.0,
                "center_of_gravity_y": 20.0,
                "center_of_gravity_z": 30.0,
                "global_moment": {"x": 1.1, "y": 2.2, "z": 3.3},
                "gravity_moment": {"ix": 4.4, "iy": 5.5, "iz": 6.6},
                "main_moment": {"Ixx": 7.7, "Iyy": 8.8},
            },
            "material_probe_status": "available",
            "materials": [
                {"matid": "SUS304", "name": "SUS304", "specific_gravity": 7.93, "element_count": 2},
                {"matid": "A5052", "name": "AL", "specific_gravity": 2.68, "element_count": 1},
                {"matid": "75", "name": "75", "specific_gravity": 0.0, "element_count": 1},
                {"matid": "S45C_MISUMIFA", "name": "S45C相当", "specific_gravity": 7.85, "element_count": 1},
                {"matid": "03\ufffdX\ufffde", "name": "03\ufffdX\ufffde", "specific_gravity": 0.0, "element_count": 1},
            ],
            "top_part": {
                "name": "KO小山ガントリー",
                "comment": "広島アルミではない",
                "ex_info": "コマツ小山 ガントリー SMC",
            },
            "parts": [
                {
                    "tree_path": ["Top", "UnitA"],
                    "name": "SMC CYLINDER",
                    "comment": "ガントリー",
                    "ref_model_name": "sample_ref",
                    "ref_model_path": r"C:\ref\sample.icd",
                    "is_external": True,
                    "is_mirror": False,
                    "is_read_only": True,
                    "is_unloaded": False,
                    "materials": [
                        {"matid": "SUS304", "name": "SUS304", "specific_gravity": 7.93, "element_count": 2},
                        {"matid": "ZZZ", "name": "ZZZ", "specific_gravity": 0.0, "element_count": 1},
                        {"matid": "RM", "name": "RM", "specific_gravity": 0.0, "element_count": 1},
                    ],
                    "ex_info_fields": {
                        "User_WBZAI1": "ＲＭ",
                        "User_WCMNA": "ＳＵＳ",
                        "User_PRFX": "CAA5012",
                        "User_UNIT_NO": "34000",
                    },
                },
                {
                    "tree_path": ["Top", "UnitA", "Child"],
                    "name": "UnitA",
                    "comment": "ユニット名を含むが番号ラベルではない",
                    "is_external": False,
                    "is_mirror": False,
                    "is_read_only": False,
                    "is_unloaded": False,
                    "materials": [],
                }
            ],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)
    assert canonical["source_file_name"] == "KO小山ガントリー.icd"
    assert canonical["source_directory_path"] == r"J:\KO小山"
    assert canonical["model_name"] == "KO小山ガントリーモデル"
    assert canonical["model_comment"] == "モデルコメント"
    assert canonical["model_path"] == r"J:\KO小山"
    assert canonical["model_is_read_only"] is True
    assert canonical["model_view_sheet_count"] == 2
    assert canonical["model_work_plane_count"] == 3
    assert "KO小山ガントリーモデル" in canonical["part_keywords"]
    assert canonical["customer_name"] == "コマツ小山"
    assert canonical["equipment_category"] == "ガントリー"
    assert canonical["mass_probe_status"] == "available"
    assert canonical["mass_unit_name"] == "mm-kg"
    assert canonical["mass_element_count"] == 17
    assert canonical["mass_value"] == 0.00055092
    assert canonical["weight_value"] == 0.00540269
    assert canonical["volume_value"] == 701.64779731
    assert canonical["area_value"] == 1858.76904715
    assert canonical["center_of_gravity"] == "10.0, 20.0, 30.0"
    assert canonical["global_moment"] == {"x": 1.1, "y": 2.2, "z": 3.3}
    assert canonical["gravity_moment"] == {"ix": 4.4, "iy": 5.5, "iz": 6.6}
    assert canonical["main_moment"] == {"Ixx": 7.7, "Iyy": 8.8}
    assert canonical["inertia_moment_candidate_count"] == 3
    assert canonical["inertia_moment_candidates"][0]["source"] == "3d_mass_properties.global_moment"
    assert all(tag["source"] != "inertia_moment_candidates" for tag in tags)
    assert canonical["material_probe_status"] == "available"
    assert canonical["material_ids"] == ["SUS304", "A5052", "75", "S45C_MISUMIFA", "03\ufffdX\ufffde"]
    assert canonical["material_names"] == ["SUS304", "AL", "75", "S45C相当", "03\ufffdX\ufffde"]
    assert canonical["material_specific_gravities"] == [7.93, 2.68, 0.0, 7.85, 0.0]
    assert canonical["part_material_candidate_count"] == 0
    assert canonical["external_part_material_candidate_count"] == 3
    assert canonical["external_part_material_candidates"][0]["part_path"] == "Top.UnitA"
    assert canonical["external_part_material_candidates"][0]["material_id"] == "SUS304"
    assert canonical["external_part_material_candidates"][0]["source"] == "3d_part_material"
    assert canonical["external_part_material_candidates"][0]["confidence"] == "high"
    assert canonical["external_part_material_candidates"][1]["material_id"] == "ZZZ"
    assert canonical["external_part_material_candidates"][1]["canonical_material"] == "ZZZ"
    assert canonical["external_part_material_candidates"][1]["material_status"] == "unresolved"
    assert canonical["external_part_material_candidates"][1]["confidence"] == "low"
    assert canonical["external_part_material_candidates"][2]["material_id"] == "SUS"
    assert canonical["external_part_material_candidates"][2]["canonical_material"] == "SUS"
    assert canonical["external_part_material_candidates"][2]["material_status"] == "formal"
    assert canonical["external_part_material_candidates"][2]["confidence"] == "medium"
    assert all(
        candidate["material_id"] != "RM"
        for candidate in canonical["external_part_material_candidates"]
    )
    assert canonical["internal_part_names"] == ["UnitA"]
    assert canonical["external_part_names"] == ["SMC CYLINDER"]
    assert "ZZZ" not in canonical["material_keywords"]
    assert "S45C" in canonical["material_keywords"]
    assert canonical["unresolved_material_keywords"] == ["75"]
    assert "SMC" in canonical["maker_keywords"]
    assert canonical["prfx_candidates"] == []
    assert canonical["unit_number_candidates"] == []
    assert any(tag["tag"] == "客先:コマツ小山" for tag in tags)
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)
    assert not any(tag["tag"] == "PRFX:CAA5012" for tag in tags)
    assert not any(tag["tag"] == "ユニット:34000" for tag in tags)
    assert not any(tag["tag"] == "材質:ZZZ" for tag in tags)
    assert not any(tag["tag"] == "材質要確認:ZZZ" for tag in tags)


def test_normalize_2d_raw_extract():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {
            "full_path": r"J:\澁谷工業\sample.icd",
            "directory_path": r"J:\澁谷工業",
            "file_name": "sample.icd",
            "file_name_without_extension": "sample",
            "extension": ".icd",
        },
        "raw_extract": {
            "model_info": {
                "name": "澁谷2Dモデル",
                "comment": "図面側コメント",
                "path": r"J:\澁谷工業",
                "is_read_only": False,
                "view_sheet_count": 5,
                "work_plane_count": 0,
            },
            "texts": [
                {"text_lines": ["澁谷工業", "SES"], "source_type": "text"},
                {"text_lines": ["ロボット"], "source_type": "label", "joined_text": "ロボット"},
                {"text_lines": ["材質 SUS304"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 20.0},
                {"text_lines": ["塗装", "マンセル 5Y7/1"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 30.0},
                {"text_lines": ["PRFX RAA4844"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 40.0},
                {"text_lines": ["ユニット U01"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 50.0},
                {"text_lines": ["設計者", "創屋 太郎"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 60.0},
                {"text_lines": ["検図者", "山田 花子"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 70.0},
                {"text_lines": ["承認日", "2026/07/16"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 80.0},
                {"text_lines": ["改訂日", "2026-07-17"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 90.0},
                {"text_lines": ["材質 SS400"], "source_type": "text", "inside_print_area": False, "position_x": 999.0, "position_y": 999.0},
                {"text_lines": ["材質 \ufffd\ufffd"], "source_type": "text", "inside_print_area": True, "position_x": 11.0, "position_y": 20.0},
                {"text_lines": ["製図者"], "source_type": "text", "inside_print_area": True, "position_x": 12.0, "position_y": 20.0},
                {"text_lines": ["訂正内容", "A 寸法変更"], "source_type": "text", "inside_print_area": True, "position_x": 13.0, "position_y": 20.0},
                {"text_lines": ["１．使用材料"], "source_type": "text", "inside_print_area": True, "position_x": 14.0, "position_y": 20.0},
                {"text_lines": ["塗装色 手摺部:Y22-80X(黄)"], "source_type": "text", "inside_print_area": True, "position_x": 15.0, "position_y": 20.0},
            ],
            "dimensions": [{"value_1": "100", "value_2": None, "mark_2": "M5", "mark_3": None, "front_word": None, "back_word": None}],
            "geometry_primitives": [
                {"geometry_type": "SxGeomSmark", "summary": "val1=Ra 6.3", "inside_print_area": True},
                {"geometry_type": "SxGeomHatch", "summary": "hatch", "inside_print_area": True},
                {"geometry_type": "SxGeomSpline2D", "summary": "spline outer curve", "inside_print_area": True, "view_name": "SHEET1", "layer_no": 3, "position_x": 31.0, "position_y": 32.0, "point_count": 4},
                {"geometry_type": "SxGeomCutLine", "summary": "cut line", "inside_print_area": True},
                {"geometry_type": "SxGeomArrowView", "summary": "arrow view A", "inside_print_area": True, "view_name": "SHEET1", "layer_no": 2, "position_x": 21.0, "position_y": 22.0},
                {"geometry_type": "SxGeomSymbol", "summary": "detail symbol B", "inside_print_area": True, "view_name": "SHEET1", "layer_no": 2, "position_x": 23.0, "position_y": 24.0},
                {"geometry_type": "SxGeomFinishMark", "summary": "finish mark", "inside_print_area": True, "mark_type": 3},
                {
                    "geometry_type": "SxGeomElparc2D",
                    "summary": "ellipse arc",
                    "inside_print_area": True,
                    "center_x": 5.0,
                    "center_y": 10.0,
                    "radius1": 11.0,
                    "radius2": 4.0,
                    "start_angle": 10.0,
                    "end_angle": 90.0,
                },
                {"geometry_type": "SxGeomCircle2D", "summary": "inside circle", "inside_print_area": True, "radius": 3.0},
                {"geometry_type": "SxGeomCircle2D", "summary": "outside circle", "inside_print_area": False},
            ],
            "weld_notes": [{"text": "WELD A"}],
            "balloons": [{"text": "B1"}],
            "tolerances": [{"text": "±0.1"}],
            "referenced_parts": [
                {
                    "entity_type": "rpart",
                    "name": "BASE-PLATE",
                    "part3d_name": "BASE-3D",
                    "ref_model_name": "BASE_MODEL",
                    "ref_vs_name": "VS-A",
                    "inside_print_area": True,
                },
                {
                    "entity_type": "refer",
                    "ref_model_name": "OUTSIDE_MODEL",
                    "ref_vs_name": "VS-OUT",
                    "inside_print_area": False,
                },
            ],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)
    assert canonical["source_full_path"] == r"J:\澁谷工業\sample.icd"
    assert canonical["model_name"] == "澁谷2Dモデル"
    assert canonical["model_comment"] == "図面側コメント"
    assert canonical["model_path"] == r"J:\澁谷工業"
    assert canonical["model_view_sheet_count"] == 5
    assert "澁谷2Dモデル" in canonical["part_keywords"]
    assert canonical["customer_name"] == "澁谷工業"
    assert canonical["equipment_category"] == "ロボット"
    assert "SES" in canonical["spec_tokens"]
    assert canonical["title_block_fields"]["material"] == "SUS304"
    assert canonical["material"] == "SUS304"
    assert canonical["title_block_fields"]["coating_instruction"] == "マンセル 5Y7/1"
    assert canonical["title_block_fields"]["prfx"] == "RAA4844"
    assert canonical["title_block_fields"]["unit_number"] == "U01"
    assert canonical["title_block_fields"]["checker"] == "山田 花子"
    assert canonical["title_block_fields"]["approved_date"] == "2026/07/16"
    assert canonical["title_block_fields"]["revision_date"] == "2026-07-17"
    assert canonical["designer"] is None
    assert canonical["checker"] == "山田 花子"
    assert canonical["approved_date"] == "2026/07/16"
    assert canonical["revision_date"] == "2026-07-17"
    assert canonical["prfx_candidates"] == ["RAA4844"]
    assert canonical["unit_number_candidates"] == ["U01"]
    assert all(candidate.get("value") != "１．使用" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != "SS400" for candidate in canonical["title_block_candidates"])
    assert all("\ufffd" not in str(candidate.get("evidence_text")) for candidate in canonical["title_block_candidates"])
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)
    assert canonical["revision_note_count"] == 1
    assert canonical["revision_note_candidates"][0]["value"] == "A 寸法変更"
    assert canonical["revision_note_candidates"][0]["confidence"] == "medium"
    assert all(tag["tag"] != "改訂情報あり" for tag in tags)
    assert any(tag["tag"] == "塗装:マンセル 5Y7/1" for tag in tags)
    assert any(tag["tag"] == "PRFX:RAA4844" for tag in tags)
    assert any(tag["tag"] == "ユニット:U01" for tag in tags)
    feature_labels = {candidate["classification_label"] for candidate in canonical["geometry_feature_candidates"]}
    assert "表面粗さ記号あり" in feature_labels
    assert "切断線あり" in feature_labels
    assert "仕上げ記号あり" in feature_labels
    assert "長穴/楕円弧候補" in feature_labels
    assert "穴/円候補" in feature_labels
    assert all(candidate["searchable_tag"] is False for candidate in canonical["geometry_feature_candidates"])
    assert all("tag" not in candidate for candidate in canonical["geometry_feature_candidates"])
    assert all(tag["source"] != "geometry_feature_candidates" for tag in tags)
    assert canonical["surface_roughness_count"] == 1
    assert canonical["surface_roughness_values"] == ["Ra 6.3"]
    assert canonical["weld_note_candidate_count"] == 1
    assert canonical["weld_note_candidates"][0]["value"] == "WELD A"
    assert canonical["weld_note_candidates"][0]["source"] == "2d_weld_note"
    assert canonical["balloon_candidate_count"] == 1
    assert canonical["balloon_candidates"][0]["value"] == "B1"
    assert canonical["balloon_candidates"][0]["source"] == "2d_balloon"
    assert canonical["tolerance_candidate_count"] == 1
    assert canonical["tolerance_candidates"][0]["value"] == "±0.1"
    assert canonical["tolerance_candidates"][0]["source"] == "2d_tolerance"
    assert all(tag["source"] != "weld_note_candidates" for tag in tags)
    assert all(tag["source"] != "balloon_candidates" for tag in tags)
    assert all(tag["source"] != "tolerance_candidates" for tag in tags)
    assert canonical["view_reference_candidate_count"] == 3
    view_reference_kinds = {candidate["kind"] for candidate in canonical["view_reference_candidates"]}
    assert view_reference_kinds == {"arrow_view", "cut_line", "symbol"}
    assert all(candidate["source"] == "2d_view_reference_geometry" for candidate in canonical["view_reference_candidates"])
    assert all(tag["source"] != "view_reference_candidates" for tag in tags)
    assert canonical["curve_section_candidate_count"] == 2
    curve_section_kinds = {candidate["kind"] for candidate in canonical["curve_section_candidates"]}
    assert curve_section_kinds == {"hatch_section", "spline_curve"}
    assert all(candidate["searchable_tag"] is False for candidate in canonical["curve_section_candidates"])
    assert all(tag["source"] != "curve_section_candidates" for tag in tags)
    assert canonical["referenced_2d_part_count"] == 2
    assert canonical["referenced_2d_trusted_part_count"] == 1
    assert canonical["referenced_2d_part_names"] == ["BASE-PLATE"]
    assert canonical["referenced_2d_part3d_names"] == ["BASE-3D"]
    assert canonical["referenced_2d_ref_model_names"] == ["BASE_MODEL"]
    assert canonical["referenced_2d_ref_vs_names"] == ["VS-A"]
    assert "BASE_MODEL" in canonical["part_keywords"]
    assert "OUTSIDE_MODEL" not in canonical["part_keywords"]
    assert canonical["section_feature_count"] == 2
    assert canonical["cut_line_count"] == 1
    assert canonical["hatch_or_section_count"] == 1
    assert canonical["finish_mark_count"] == 1
    assert canonical["finish_mark_types"] == [3]
    assert canonical["slot_candidate_count"] == 1
    assert canonical["slot_candidate_dimensions"][0]["major_diameter"] == 22.0
    assert canonical["slot_candidate_dimensions"][0]["minor_diameter"] == 8.0
    assert canonical["hole_candidate_count"] == 1
    assert canonical["hole_candidate_diameters"] == [6.0]
    sections_by_key = {section["key"]: section for section in canonical["raw_2d_sections"]["sections"]}
    assert canonical["raw_2d_sections"]["schema_version"] == "raw_2d_sections.v1"
    assert set(sections_by_key) == {"title_block", "drawing_body", "dimensions", "notes", "balloons", "manufacturing_symbols"}
    assert sections_by_key["title_block"]["trusted_count"] >= 4
    assert sections_by_key["dimensions"]["trusted_count"] == 1
    assert sections_by_key["balloons"]["trusted_count"] == 1
    assert sections_by_key["manufacturing_symbols"]["trusted_count"] >= 4


def test_title_block_fields_reject_reference_and_calculation_false_positives():
    payload = {
        "source_kind": "2d",
        "source_file": {"full_path": r"J:\sample.icd", "file_name": "sample.icd"},
        "raw_extract": {
            "texts": [
                {"text_lines": ["重量：0.4932kg"], "inside_print_area": True},
                {"text_lines": ["ワーク重量より12.4倍の吸引力がある"], "inside_print_area": True},
                {"text_lines": ["材質：丸棒 φ90"], "inside_print_area": True},
                {"text_lines": ["図番：参考：M24A88810"], "inside_print_area": True},
                {"text_lines": ["部品番号：組"], "inside_print_area": True},
                {"text_lines": ["品番：.ni"], "inside_print_area": True},
                {"text_lines": ["部品番号：C A D"], "inside_print_area": True},
                {"text_lines": ["図番：CAD元図 図 番]"], "inside_print_area": True},
                {"text_lines": ["部品番号：参照組立号"], "inside_print_area": True},
                {"text_lines": ["図番：P-100"], "inside_print_area": True},
                {"text_lines": ["塗装", "仕上げ面不可"], "inside_print_area": True},
                {"text_lines": ["日付 未定"], "inside_print_area": True},
                {"text_lines": ["承認日 A寸法変更"], "inside_print_area": True},
            ],
            "print_frames": [{"frame_no": 1}],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["title_block_fields"]["weight"] == "0.49 kg"
    assert canonical["weight_value"] == "0.49 kg"
    assert canonical["title_block_fields"]["drawing_number"] == "P-100"
    assert "date" not in canonical["title_block_fields"]
    assert "approved_date" not in canonical["title_block_fields"]
    assert "material" not in canonical["title_block_fields"]
    assert "coating_instruction" not in canonical["title_block_fields"]
    assert all(candidate.get("value") != "参考：M24A88810" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != "組" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != ".ni" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != "C A D" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != "CAD元図 図 番]" for candidate in canonical["title_block_candidates"])
    assert all(candidate.get("value") != "参照組立号" for candidate in canonical["title_block_candidates"])
    assert all("吸引力" not in str(candidate.get("value")) for candidate in canonical["title_block_candidates"])


def test_title_block_fields_do_not_pair_separate_text_elements_by_coordinates():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {},
        "raw_extract": {
            "texts": [
                {
                    "text_lines": ["材質"],
                    "inside_print_area": True,
                    "position_x": 10.0,
                    "position_y": 20.0,
                },
                {
                    "text_lines": ["SUS304"],
                    "inside_print_area": True,
                    "position_x": 11.0,
                    "position_y": 20.0,
                },
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert "material" not in canonical["title_block_fields"]
    material_candidate = next(
        candidate
        for candidate in canonical["title_block_candidates"]
        if candidate["field"] == "material"
    )
    assert material_candidate["value"] is None
    assert material_candidate["position_x"] == 10.0
    assert material_candidate["position_y"] == 20.0


def test_identity_name_pairs_only_an_explicit_nearby_name_label():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {"file_name": "P-100.icd"},
        "raw_extract": {
            "texts": [
                {
                    "text_lines": ["品　名"],
                    "inside_print_area": True,
                    "view_name": "SHEET1",
                    "layer_no": 1,
                    "position_x": 10.0,
                    "position_y": 20.0,
                },
                {
                    "text_lines": ["PPS"],
                    "inside_print_area": True,
                    "view_name": "SHEET1",
                    "layer_no": 1,
                    "position_x": 10.0,
                    "position_y": 21.0,
                },
                {
                    "text_lines": ["開口カバー"],
                    "inside_print_area": True,
                    "view_name": "SHEET1",
                    "layer_no": 1,
                    "position_x": 20.0,
                    "position_y": 20.0,
                },
                {
                    "text_lines": ["SS400"],
                    "inside_print_area": True,
                    "view_name": "SHEET1",
                    "layer_no": 1,
                    "position_x": 12.0,
                    "position_y": 40.0,
                },
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["part_name"] == "開口カバー"
    candidate = next(
        item
        for item in canonical["title_block_candidates"]
        if item["field"] == "part_name" and item["value"] == "開口カバー"
    )
    assert candidate["source"] == "2d_text_near_identity_label"
    assert candidate["value_position_x"] == 20.0
    assert candidate["value_position_y"] == 20.0


def test_identity_name_accepts_bom_value_left_of_name_label_without_selecting_adjacent_header():
    canonical = normalize_raw_extract(
        {
            "source_format": "icad",
            "source_kind": "2d",
            "source_file": {"file_name": "23022-007.icd"},
            "raw_extract": {
                "texts": [
                    {
                        "text_lines": ["品　　　　名"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 260.0,
                        "position_y": 66.0,
                    },
                    {
                        "text_lines": ["材質"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 297.5,
                        "position_y": 66.0,
                    },
                    {
                        "text_lines": ["ブラケット"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 231.0,
                        "position_y": 72.0,
                    },
                    {
                        "text_lines": ["２３０２２－００７"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 326.0,
                        "position_y": 21.5,
                    },
                ]
            },
        }
    )

    assert canonical["drawing_number"] == "23022-007"
    assert canonical["part_name"] == "ブラケット"
    assert canonical["title_block_fields"]["part_name"] == "ブラケット"


def test_drawing_name_uses_only_short_vertical_alignment_with_drawing_number_when_label_is_absent():
    canonical = normalize_raw_extract(
        {
            "source_format": "icad",
            "source_kind": "2d",
            "source_file": {"file_name": "PSG011-P05010.icd"},
            "raw_extract": {
                "texts": [
                    {
                        "text_lines": ["ＰＳＧ０１１－Ｐ０５０１０"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 545.0,
                        "position_y": 12.0,
                    },
                    {
                        "text_lines": ["ケーブルダクト"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 545.0,
                        "position_y": 31.0,
                    },
                    {
                        "text_lines": ["４．６ｋｇ"],
                        "inside_print_area": True,
                        "view_name": "!!GLOBAL",
                        "layer_no": 1,
                        "position_x": 516.0,
                        "position_y": 15.5,
                    },
                ]
            },
        }
    )

    assert canonical["drawing_number"] == "PSG011-P05010"
    assert canonical["drawing_name"] == "ケーブルダクト"
    assert canonical["title_block_fields"]["drawing_name"] == "ケーブルダクト"
    candidate = next(
        item
        for item in canonical["title_block_candidates"]
        if item["field"] == "drawing_name"
    )
    assert candidate["source"] == "2d_text_aligned_with_drawing_number"


def test_identity_name_does_not_skip_a_nearby_placeholder_to_an_unrelated_value():
    canonical = normalize_raw_extract(
        {
            "source_format": "icad",
            "source_kind": "2d",
            "source_file": {"file_name": "P-100.icd"},
            "raw_extract": {
                "texts": [
                    {
                        "text_lines": ["PART NAME"],
                        "inside_print_area": True,
                        "position_x": 10.0,
                        "position_y": 20.0,
                    },
                    {
                        "text_lines": ["COPIED"],
                        "inside_print_area": True,
                        "position_x": 11.0,
                        "position_y": 20.0,
                    },
                    {
                        "text_lines": ["BY"],
                        "inside_print_area": True,
                        "position_x": 20.0,
                        "position_y": 20.0,
                    },
                ],
            },
        }
    )

    assert canonical["part_name"] is None


def test_title_block_drawing_number_strips_filename_noise_and_paper_size():
    payload = {
        "source_kind": "2d",
        "source_file": {"full_path": r"J:\sample.icd", "file_name": "sample.icd"},
        "raw_extract": {
            "texts": [
                {"text_lines": ["品番：03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS)"], "inside_print_area": True},
                {"text_lines": ["図番：U8718-S71-002_A3"], "inside_print_area": True},
            ],
            "print_frames": [{"frame_no": 1}],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["title_block_fields"]["drawing_number"] == "20K03379P00"


def test_identity_labels_are_separated_and_full_width_spacing_is_normalized():
    drawing_number = "9NK-5E5-1B70"
    payload = {
        "source_kind": "2d",
        "source_file": {
            "file_name": "9NK5E51B70-00-BRACKET-A0-3D-01.icd",
            "file_name_without_extension": "9NK5E51B70-00-BRACKET-A0-3D-01",
        },
        "raw_extract": {
            "texts": [
                {"text_lines": ["品　名：ＢＲＡＣＫＥＴ"], "inside_print_area": True},
                {"text_lines": [f"図　番：{drawing_number}"], "inside_print_area": True},
                {"text_lines": ["UNIT Name"], "inside_print_area": True},
                {"text_lines": ["MACHINE Name"], "inside_print_area": True},
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["part_name"] == "BRACKET"
    assert canonical["drawing_name"] is None
    assert canonical["unit_name"] is None
    assert canonical["equipment_name"] is None
    assert canonical["drawing_number"] == drawing_number
    assert canonical["title_block_fields"]["part_name"] == "BRACKET"
    assert all(
        candidate.get("value") not in {"UNIT", "MACHINE"}
        for candidate in canonical["title_block_candidates"]
    )


def test_drawing_number_recovers_only_raw_text_that_matches_filename():
    drawing_number = "9NK-5E5-1B70"
    payload = {
        "source_kind": "2d",
        "source_file": {
            "file_name": "9NK5E51B70-00-BRACKET-A0-3D-01.icd",
            "file_name_without_extension": "9NK5E51B70-00-BRACKET-A0-3D-01",
        },
        "raw_extract": {
            "texts": [
                {"text_lines": [drawing_number], "inside_print_area": None},
                {"text_lines": ["REF-99999"], "inside_print_area": None},
            ],
            "print_frames": [{"frame_no": 1}],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert "drawing_number" not in canonical["title_block_fields"]
    assert canonical["drawing_number"] == drawing_number
    assert canonical["drawing_number_candidates"][0]["source"] == "2d_text_filename_match"
    assert all(
        candidate["value"] != "REF-99999"
        for candidate in canonical["drawing_number_candidates"]
    )


def test_drawing_number_rejects_child_number_that_conflicts_with_filename():
    payload = {
        "source_kind": "2d",
        "source_file": {
            "file_name": "PSG011-PA1300_ベース.icd",
            "file_name_without_extension": "PSG011-PA1300_ベース",
        },
        "raw_extract": {
            "texts": [
                {"text_lines": ["図番 PSG011-PA13002"], "inside_print_area": True},
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["title_block_fields"]["drawing_number"] == "PSG011-PA13002"
    assert canonical["drawing_number"] == "PSG011-PA1300"


def test_filename_drawing_number_keeps_numeric_suffix_and_parentheses():
    for drawing_number in ("4D-75", "18T5-10BF(8)", "XH3001-M08007-01"):
        canonical = normalize_raw_extract(
            {
                "source_kind": "2d",
                "source_file": {
                    "file_name": f"{drawing_number}.icd",
                    "file_name_without_extension": drawing_number,
                },
                "raw_extract": {"texts": []},
            }
        )

        assert canonical["drawing_number"] == drawing_number


def test_3d_child_identity_fields_do_not_become_drawing_identity():
    payload = {
        "source_kind": "3d",
        "source_file": {"file_name": "assembly.icd"},
        "raw_extract": {
            "top_part": {"name": "MACHINE"},
            "parts": [
                {
                    "depth": 0,
                    "tree_path": ["MACHINE"],
                    "name": "MACHINE",
                    "ex_info_fields": {},
                },
                {
                    "depth": 1,
                    "tree_path": ["MACHINE", "CHILD"],
                    "name": "CHILD",
                    "ex_info_fields": {
                        "製品名": "フローティングジョイント",
                        "部品番号": "PSG011-PA13002",
                    },
                },
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["product_name"] is None
    assert canonical["drawing_number"] is None


def test_normalize_step_extract_uses_generic_3d_materials_and_path_tokens():
    payload = {
        "source_format": "step",
        "source_kind": "3d",
        "source_file": {
            "full_path": r"J:\コマツ小山\ガントリー\HAND.step",
            "directory_path": r"J:\コマツ小山\ガントリー",
            "file_name": "HAND.step",
            "file_name_without_extension": "HAND",
            "extension": ".step",
        },
        "raw_extract": {
            "model_info": {"name": "ガントリーハンド", "comment": "SMC CYLINDER"},
            "top_part": {"name": "HAND", "comment": "浸炭焼入れ HRC58-62"},
            "parts": [
                {
                    "tree_path": ["HAND", "PLATE"],
                    "name": "PLATE",
                    "materials": ["SUS304"],
                }
            ],
            "materials": ["S45C"],
            "step_products": [
                {"entity_id": "#10", "name": "HAND", "description": "ガントリーハンド"},
                {"entity_id": "#20", "name": "PLATE", "description": "SUS304 PLATE"},
            ],
            "step_assembly_relationships": [
                {
                    "entity_id": "#30",
                    "parent_name": "HAND",
                    "child_name": "PLATE",
                    "name": "PLATE OCC",
                }
            ],
            "mass_properties": {"mass": 1.2, "unit_name": "mm-kg"},
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)

    assert canonical["source_format"] == "step"
    assert canonical["source_kind"] == "3d"
    assert canonical["customer_name"] == "コマツ小山"
    assert canonical["equipment_category"] == "ガントリー"
    assert canonical["material_keywords"] == ["S45C", "SUS304"]
    assert canonical["step_product_names"] == ["HAND", "PLATE"]
    assert canonical["step_assembly_relationship_count"] == 1
    assert canonical["step_assembly_relationships"][0]["child_name"] == "PLATE"
    assert canonical["part_material_candidates"][0]["part_name"] == "PLATE"
    assert canonical["heat_treatment_keywords"] == ["浸炭"]
    assert canonical["hardness_spec_values"] == ["HRC58-62"]
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)


def test_normalize_dxf_extract_uses_generic_2d_texts_for_title_block_tags():
    payload = {
        "source_format": "dxf",
        "source_kind": "2d",
        "source_file": {
            "full_path": r"J:\澁谷工業\ロボット\layout.dxf",
            "directory_path": r"J:\澁谷工業\ロボット",
            "file_name": "layout.dxf",
            "file_name_without_extension": "layout",
            "extension": ".dxf",
        },
        "raw_extract": {
            "texts": [
                "図番 DXF-001",
                {"text": "図名 ロボット架台"},
                {"value": "材質 SS400", "inside_print_area": True},
                {"text_lines": ["PRFX", "RAA4844"], "inside_print_area": True},
                {"joined_text": "ユニット U01", "inside_print_area": True},
                {"text": "SES", "inside_print_area": True},
            ],
            "block_references": [
                {
                    "block_name": "TITLE_BLOCK",
                    "layer_name": "TITLE",
                    "attributes": [
                        {"tag": "DWG_NO", "value": "DXF-001"},
                        {"tag": "MATERIAL", "value": "SS400"},
                    ],
                }
            ],
            "layers": ["TITLE", "NOTE"],
            "dimensions": [],
            "geometry_primitives": [],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)

    assert canonical["source_format"] == "dxf"
    assert canonical["source_kind"] == "2d"
    assert canonical["customer_name"] == "澁谷工業"
    assert canonical["equipment_category"] == "ロボット"
    assert canonical["title_block_fields"]["drawing_number"] == "DXF-001"
    assert canonical["title_block_fields"]["material"] == "SS400"
    assert canonical["material_keywords"] == ["SS400"]
    assert canonical["dxf_layers"] == ["TITLE", "NOTE"]
    assert canonical["dxf_block_attribute_count"] == 2
    assert "TITLE_BLOCK" in canonical["dxf_block_attribute_tokens"]
    assert "MATERIAL" in canonical["dxf_block_attribute_tokens"]
    assert canonical["prfx_candidates"] == ["RAA4844"]
    assert canonical["unit_number_candidates"] == ["U01"]
    assert any(tag["tag"] == "規格:SES" for tag in tags)
    assert any(tag["tag"] == "材質:SS400" for tag in tags)


def test_normalize_icad_2d_builds_dimension_tolerance_weld_and_hardness_tags():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {"full_path": r"J:\sample\manufacturing_tags.icd"},
        "raw_extract": {
            "texts": [
                {"text_lines": ["硬度 HRC58-62 HV500"], "inside_print_area": True},
                {"text_lines": ["すみ肉溶接"], "inside_print_area": True},
                {"text_lines": ["全周溶接"], "inside_print_area": True},
            ],
            "dimensions": [
                {"value_1": "100", "inside_print_area": True},
                {
                    "value_1": "50",
                    "upper_tol": "+0.1",
                    "lower_tol": "-0.1",
                    "inside_print_area": True,
                },
                {
                    "value1": "25",
                    "summary": "dimtol_ratio=0.5; suppress=False",
                    "inside_print_area": True,
                },
            ],
            "geometry_primitives": [],
            "layers": [
                {"no": 1, "name": None},
                {"no": 2, "name": "寸法"},
            ],
            "weld_notes": [
                {"text": "native weld data", "inside_print_area": True},
            ],
            "balloons": [],
            "tolerances": [
                {"text": "SxGeomTol value=0.01 datum=A", "inside_print_area": True},
            ],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = {tag["tag"] for tag in build_derived_tags(canonical)}

    assert canonical["dimension_count"] == 3
    assert canonical["dxf_layers"] == ["寸法"]
    assert canonical["dimension_tolerance_count"] == 2
    assert canonical["geometric_tolerance_count"] == 1
    assert canonical["weld_instruction_count"] == 3
    assert canonical["weld_types"] == ["すみ肉", "全周"]
    assert canonical["hardness_spec_values"] == ["HRC58-62", "HV500"]
    assert {
        "寸法あり",
        "寸法公差あり",
        "幾何公差あり",
        "溶接指示あり",
        "溶接:すみ肉",
        "溶接:全周",
        "硬度:HRC",
        "硬度:HV",
    } <= tags


def test_normalize_2d_extract_excludes_unknown_print_area_when_frames_exist():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {"full_path": r"J:\sample\unknown-print-area.icd"},
        "raw_extract": {
            "print_frames": [{"id": "frame-1"}],
            "texts": [
                {"text_lines": ["材質 SS400"], "source_type": "text", "inside_print_area": None},
                {"text_lines": ["SMC"], "source_type": "text", "inside_print_area": None},
                {"text_lines": ["材質 SUS304"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 20.0},
                {"text_lines": ["訂正内容", "旧注記"], "source_type": "text", "inside_print_area": None},
            ],
            "weld_notes": [{"text": "枠不明溶接", "inside_print_area": None}],
            "balloons": [{"text": "枠内バルーン", "inside_print_area": True}],
            "tolerances": [{"text": "SES", "inside_print_area": None}],
            "geometry_primitives": [
                {"geometry_type": "SxGeomHatch", "summary": "unknown hatch", "inside_print_area": None},
                {"geometry_type": "SxGeomSpline2D", "summary": "unknown spline", "inside_print_area": None},
                {"geometry_type": "SxGeomCircle2D", "summary": "unknown circle", "inside_print_area": None, "radius": 3.0},
                {"geometry_type": "SxGeomCutLine", "summary": "inside cut line", "inside_print_area": True},
                {"geometry_type": "SxGeomArrowView", "summary": "unknown arrow", "inside_print_area": None},
            ],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)

    assert canonical["title_block_fields"]["material"] == "SUS304"
    assert "材質 SS400" in canonical["text_tokens"]
    assert "材質 SS400" not in canonical["part_keywords"]
    assert "SMC" not in canonical["maker_keywords"]
    assert "SES" not in canonical["spec_tokens"]
    assert "枠不明溶接" in canonical["weld_note_texts"]
    assert canonical["weld_note_candidate_count"] == 0
    assert canonical["tolerance_candidate_count"] == 0
    assert canonical["balloon_candidate_count"] == 1
    assert canonical["balloon_candidates"][0]["value"] == "枠内バルーン"
    assert canonical["balloon_candidates"][0]["inside_print_area"] is True
    assert canonical["view_reference_candidate_count"] == 1
    assert canonical["view_reference_candidates"][0]["kind"] == "cut_line"
    assert canonical["curve_section_candidate_count"] == 0
    assert "枠不明溶接" not in canonical["part_keywords"]
    assert "枠内バルーン" in canonical["part_keywords"]
    assert all(candidate.get("value") != "SS400" for candidate in canonical["title_block_candidates"])
    assert canonical["revision_note_count"] == 0
    feature_labels = {candidate["classification_label"] for candidate in canonical["geometry_feature_candidates"]}
    assert "ハッチング/断面候補" not in feature_labels
    assert "穴/円候補" not in feature_labels
    assert "切断線あり" in feature_labels
    assert all("tag" not in candidate for candidate in canonical["geometry_feature_candidates"])
    assert canonical["hatch_or_section_count"] == 0
    assert canonical["hole_candidate_count"] == 0
    assert canonical["cut_line_count"] == 1
    assert not any(tag["tag"] == "材質:SS400" for tag in tags)
    sections_by_key = {section["key"]: section for section in canonical["raw_2d_sections"]["sections"]}
    assert canonical["raw_2d_sections"]["print_area_policy"] == "inside_only_when_print_frames_exist"
    assert canonical["raw_2d_sections"]["text_print_area_policy"] == "inside_only_when_classification_available"
    assert sections_by_key["notes"]["unknown_print_area_count"] >= 2
    assert sections_by_key["notes"]["trusted_count"] == 0
    assert sections_by_key["manufacturing_symbols"]["trusted_count"] == 1


def test_normalize_2d_extract_uses_unknown_texts_when_print_area_classification_is_unavailable():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "source_file": {
            "full_path": r"J:\sample\XH3001-M08007-01.icd",
            "file_name": "XH3001-M08007-01.icd",
            "file_name_without_extension": "XH3001-M08007-01",
        },
        "raw_extract": {
            "print_frames": [{"id": "frame-1"}],
            "texts": [
                {
                    "text_lines": ["名 称"],
                    "joined_text": "名 称",
                    "view_name": "!XY",
                    "position_x": 332.6,
                    "position_y": -442.4,
                    "inside_print_area": None,
                },
                {
                    "text_lines": ["法兰（右）"],
                    "joined_text": "法兰（右）",
                    "view_name": "!XY",
                    "position_x": 413.3,
                    "position_y": -449.9,
                    "inside_print_area": None,
                },
                {
                    "text_lines": ["材 料"],
                    "joined_text": "材 料",
                    "view_name": "!XY",
                    "position_x": 333.2,
                    "position_y": -424.0,
                    "inside_print_area": None,
                },
                {
                    "text_lines": ["PPS"],
                    "joined_text": "PPS",
                    "view_name": "!XY",
                    "position_x": 372.8,
                    "position_y": -427.1,
                    "inside_print_area": None,
                },
            ],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["drawing_name"] == "法兰(右)"
    assert canonical["drawing_number"] == "XH3001-M08007-01"
    assert canonical["raw_2d_sections"]["text_print_area_policy"] == "include_unknown_when_classification_unavailable"


def test_identity_name_removes_note_marker_and_rejects_spec_only_value():
    marker_canonical = normalize_raw_extract(
        {
            "source_kind": "3d",
            "source_file": {"file_name": "217008-41J-3004.icd"},
            "raw_extract": {
                "top_part": {"name": "217008-41J-3004"},
                "parts": [
                    {
                        "name": "217008-41J-3004",
                        "depth": 0,
                        "tree_path": ["217008-41J-3004"],
                        "ex_info_fields": {"部品名": "★ガイドレール"},
                    }
                ],
            },
        }
    )
    spec_canonical = normalize_raw_extract(
        {
            "source_kind": "2d",
            "source_file": {"file_name": "TR1D9K99027.icd"},
            "raw_extract": {
                "texts": [
                    {
                        "text_lines": ["名称"],
                        "view_name": "!!GLOBAL",
                        "position_x": 432.6,
                        "position_y": 353.3,
                        "inside_print_area": True,
                    },
                    {
                        "text_lines": ["型式"],
                        "view_name": "!!GLOBAL",
                        "position_x": 500.1,
                        "position_y": 353.3,
                        "inside_print_area": True,
                    },
                    {
                        "text_lines": ["SFF-424 L=1572"],
                        "view_name": "!!GLOBAL",
                        "position_x": 560.1,
                        "position_y": 353.3,
                        "inside_print_area": True,
                    },
                ],
            },
        }
    )

    assert marker_canonical["part_name"] == "ガイドレール"
    assert marker_canonical["part_name_candidates"][0] == "ガイドレール"
    assert spec_canonical["drawing_name"] is None


def test_normalize_3d_separates_internal_and_external_part_information():
    canonical = normalize_raw_extract(
        {
            "source_kind": "3d",
            "source_file": {"file_name": "assembly.icd"},
            "raw_extract": {
                "top_part": {"name": "ASSEMBLY"},
                "parts": [
                    {
                        "name": "MAIN",
                        "depth": 0,
                        "tree_path": ["MAIN"],
                        "materials": [{"matid": "SUS304", "name": "SUS304"}],
                        "ex_info_fields": {"部品名": "本体フレーム"},
                    },
                    {
                        "name": "EXTERNAL-RAIL",
                        "depth": 1,
                        "tree_path": ["MAIN", "EXTERNAL-RAIL"],
                        "is_external": True,
                        "ref_model_name": "EXTERNAL-RAIL",
                        "materials": [{"matid": "SS400", "name": "SS400"}],
                        "ex_info_fields": {"部品名": "外部ガイドレール"},
                    },
                ],
            },
        }
    )

    assert canonical["part_name"] == "本体フレーム"
    assert canonical["internal_part_names"] == ["MAIN"]
    assert canonical["external_part_names"] == ["EXTERNAL-RAIL"]
    assert canonical["internal_part_material_keywords"] == ["SUS304"]
    assert canonical["external_part_material_keywords"] == ["SS400"]
    assert all(
        candidate["part_name"] != "EXTERNAL-RAIL"
        for candidate in canonical["part_material_candidates"]
    )
    assert canonical["external_part_material_candidates"][0]["part_name"] == "EXTERNAL-RAIL"
