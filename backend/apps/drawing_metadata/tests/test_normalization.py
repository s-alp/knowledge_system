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
            ],
            "dimensions": [{"value_1": "100", "value_2": None, "mark_2": "M5", "mark_3": None, "front_word": None, "back_word": None}],
            "weld_notes": [{"text": "WELD A"}],
            "balloons": [{"text": "B1"}],
            "tolerances": [{"text": "±0.1"}],
        },
    }

    canonical = normalize_raw_extract(payload)
    assert canonical["source_full_path"] == r"J:\澁谷工業\sample.icd"
    assert canonical["customer_name"] == "澁谷工業"
    assert canonical["equipment_category"] == "ロボット"
    assert "SES" in canonical["spec_tokens"]
