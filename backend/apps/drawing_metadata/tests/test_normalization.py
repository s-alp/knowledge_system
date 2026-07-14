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
    assert canonical["material_ids"] == ["SUS304", "A5052"]
    assert canonical["material_names"] == ["SUS304", "AL"]
    assert canonical["material_specific_gravities"] == [7.93, 2.68]
    assert canonical["part_material_candidate_count"] == 3
    assert canonical["part_material_candidates"][0]["part_path"] == "Top.UnitA"
    assert canonical["part_material_candidates"][0]["material_id"] == "SUS304"
    assert canonical["part_material_candidates"][0]["source"] == "3d_part_material"
    assert canonical["part_material_candidates"][0]["confidence"] == "high"
    assert canonical["part_material_candidates"][1]["material_id"] == "ZZZ"
    assert canonical["part_material_candidates"][1]["confidence"] == "high"
    assert canonical["part_material_candidates"][2]["material_id"] == "SUS"
    assert canonical["part_material_candidates"][2]["confidence"] == "medium"
    assert "ZZZ" not in canonical["material_keywords"]
    assert canonical["unresolved_material_keywords"] == ["ZZZ"]
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
    assert canonical["title_block_fields"]["coating_instruction"] == "マンセル 5Y7/1"
    assert canonical["title_block_fields"]["prfx"] == "RAA4844"
    assert canonical["title_block_fields"]["unit_number"] == "U01"
    assert "designer" not in canonical["title_block_fields"]
    assert all(candidate.get("value") != "SS400" for candidate in canonical["title_block_candidates"])
    assert all("\ufffd" not in str(candidate.get("evidence_text")) for candidate in canonical["title_block_candidates"])
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)
    assert canonical["revision_note_count"] == 1
    assert canonical["revision_note_candidates"][0]["value"] == "A 寸法変更"
    assert canonical["revision_note_candidates"][0]["confidence"] == "medium"
    assert any(tag["tag"] == "改訂情報あり" for tag in tags)
    assert any(tag["tag"] == "塗装:マンセル 5Y7/1" for tag in tags)
    assert any(tag["tag"] == "PRFX:RAA4844" for tag in tags)
    assert any(tag["tag"] == "ユニット:U01" for tag in tags)
    feature_tags = {candidate["tag"] for candidate in canonical["geometry_feature_candidates"]}
    assert "加工指示:表面粗さ" in feature_tags
    assert "図面特徴:切断線" in feature_tags
    assert "形状候補:長穴" in feature_tags
    assert "形状候補:穴" in feature_tags
    assert any(tag["tag"] == "加工指示:表面粗さ" for tag in tags)
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
