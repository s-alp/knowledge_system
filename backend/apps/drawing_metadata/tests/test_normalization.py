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
                    },
                }
            ],
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)
    assert canonical["source_file_name"] == "KO小山ガントリー.icd"
    assert canonical["source_directory_path"] == r"J:\KO小山"
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
    assert canonical["material_probe_status"] == "available"
    assert canonical["material_ids"] == ["SUS304", "A5052", "75", "S45C_MISUMIFA", "03\ufffdX\ufffde"]
    assert canonical["material_names"] == ["SUS304", "AL", "75", "S45C相当", "03\ufffdX\ufffde"]
    assert canonical["material_specific_gravities"] == [7.93, 2.68, 0.0, 7.85, 0.0]
    assert canonical["part_material_candidate_count"] == 3
    assert canonical["part_material_candidates"][0]["part_path"] == "Top.UnitA"
    assert canonical["part_material_candidates"][0]["material_id"] == "SUS304"
    assert canonical["part_material_candidates"][0]["source"] == "3d_part_material"
    assert canonical["part_material_candidates"][0]["confidence"] == "high"
    assert canonical["part_material_candidates"][1]["material_id"] == "ZZZ"
    assert canonical["part_material_candidates"][1]["canonical_material"] == "ZZZ"
    assert canonical["part_material_candidates"][1]["material_status"] == "unresolved"
    assert canonical["part_material_candidates"][1]["confidence"] == "low"
    assert canonical["part_material_candidates"][2]["material_id"] == "SUS"
    assert canonical["part_material_candidates"][2]["canonical_material"] == "SUS"
    assert canonical["part_material_candidates"][2]["material_status"] == "formal"
    assert canonical["part_material_candidates"][2]["confidence"] == "medium"
    assert all(candidate["material_id"] != "RM" for candidate in canonical["part_material_candidates"])
    assert "ZZZ" not in canonical["material_keywords"]
    assert "S45C" in canonical["material_keywords"]
    assert canonical["unresolved_material_keywords"] == ["75", "ZZZ"]
    assert "SMC" in canonical["maker_keywords"]
    assert any(tag["tag"] == "客先:コマツ小山" for tag in tags)
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)
    assert not any(tag["tag"] == "材質:ZZZ" for tag in tags)
    assert any(tag["tag"] == "材質要確認:ZZZ" for tag in tags)


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
            "texts": [
                {"text_lines": ["澁谷工業", "SES"], "source_type": "text"},
                {"text_lines": ["ロボット"], "source_type": "label", "joined_text": "ロボット"},
                {"text_lines": ["材質 SUS304"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 20.0},
                {"text_lines": ["塗装", "マンセル 5Y7/1"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 30.0},
                {"text_lines": ["PRFX RAA4844"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 40.0},
                {"text_lines": ["ユニット U01"], "source_type": "text", "inside_print_area": True, "position_x": 10.0, "position_y": 50.0},
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
                {"geometry_type": "SxGeomCutLine", "summary": "cut line", "inside_print_area": True},
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
        },
    }

    canonical = normalize_raw_extract(payload)
    tags = build_derived_tags(canonical)
    assert canonical["source_full_path"] == r"J:\澁谷工業\sample.icd"
    assert canonical["customer_name"] == "澁谷工業"
    assert canonical["equipment_category"] == "ロボット"
    assert "SES" in canonical["spec_tokens"]
    assert canonical["title_block_fields"]["material"] == "SUS304"
    assert canonical["material"] == "SUS304"
    assert canonical["title_block_fields"]["coating_instruction"] == "マンセル 5Y7/1"
    assert canonical["title_block_fields"]["prfx"] == "RAA4844"
    assert canonical["title_block_fields"]["unit_number"] == "U01"
    assert "designer" not in canonical["title_block_fields"]
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
    assert "長穴/楕円弧候補" in feature_labels
    assert "穴/円候補" in feature_labels
    assert all(candidate["searchable_tag"] is False for candidate in canonical["geometry_feature_candidates"])
    assert all("tag" not in candidate for candidate in canonical["geometry_feature_candidates"])
    assert all(tag["source"] != "geometry_feature_candidates" for tag in tags)
    assert canonical["surface_roughness_count"] == 1
    assert canonical["surface_roughness_values"] == ["Ra 6.3"]
    assert canonical["section_feature_count"] == 2
    assert canonical["cut_line_count"] == 1
    assert canonical["hatch_or_section_count"] == 1
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
                {"text_lines": ["図番：P-100"], "inside_print_area": True},
                {"text_lines": ["塗装", "仕上げ面不可"], "inside_print_area": True},
            ],
            "print_frames": [{"frame_no": 1}],
        },
    }

    canonical = normalize_raw_extract(payload)

    assert canonical["title_block_fields"]["weight"] == "0.4932kg"
    assert canonical["weight_value"] == "0.4932kg"
    assert canonical["title_block_fields"]["drawing_number"] == "P-100"
    assert "material" not in canonical["title_block_fields"]
    assert "coating_instruction" not in canonical["title_block_fields"]
    assert all(candidate.get("value") != "参考：M24A88810" for candidate in canonical["title_block_candidates"])
    assert all("吸引力" not in str(candidate.get("value")) for candidate in canonical["title_block_candidates"])
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
                {"geometry_type": "SxGeomCircle2D", "summary": "unknown circle", "inside_print_area": None, "radius": 3.0},
                {"geometry_type": "SxGeomCutLine", "summary": "inside cut line", "inside_print_area": True},
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
    assert sections_by_key["notes"]["unknown_print_area_count"] >= 2
    assert sections_by_key["notes"]["trusted_count"] == 0
    assert sections_by_key["manufacturing_symbols"]["trusted_count"] == 1
