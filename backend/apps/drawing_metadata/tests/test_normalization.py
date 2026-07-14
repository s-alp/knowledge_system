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
    assert "SMC" in canonical["maker_keywords"]
    assert any(tag["tag"] == "客先:コマツ小山" for tag in tags)


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
            ],
            "dimensions": [{"value_1": "100", "value_2": None, "mark_2": "M5", "mark_3": None, "front_word": None, "back_word": None}],
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
    assert all(candidate.get("value") != "SS400" for candidate in canonical["title_block_candidates"])
    assert any(tag["tag"] == "材質:SUS304" for tag in tags)
    assert any(tag["tag"] == "塗装:マンセル 5Y7/1" for tag in tags)
    assert any(tag["tag"] == "PRFX:RAA4844" for tag in tags)
    assert any(tag["tag"] == "ユニット:U01" for tag in tags)
