from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.tag_builder import build_derived_tags


def _payload_2d(text_lines: list[str]) -> dict:
    return {
        "source_format": "icad",
        "source_kind": "2d",
        "raw_extract": {
            "texts": [{"text_lines": text_lines, "source_type": "text"}],
            "dimensions": [],
            "weld_notes": [],
            "balloons": [],
            "tolerances": [],
        },
    }


def test_scale_detected_from_bare_ratio_token():
    canonical = normalize_raw_extract(_payload_2d(["1:6", "SUS304"]))
    assert canonical["scale"] == "1:6"
    assert canonical["scale_candidates"][0]["confidence"] == "low"


def test_scale_detected_from_labeled_token_with_medium_confidence():
    canonical = normalize_raw_extract(_payload_2d(["S=1:6"]))
    assert canonical["scale"] == "1:6"
    assert canonical["scale_candidates"][0]["confidence"] == "medium"


def test_scale_not_confirmed_when_multiple_candidates():
    # 尺度候補が複数(テーパ 1:10 との併存など)は確定しない。候補として残す。
    canonical = normalize_raw_extract(_payload_2d(["1:6", "1:10"]))
    assert canonical["scale"] is None
    assert {item["value"] for item in canonical["scale_candidates"]} == {"1:6", "1:10"}


def test_scale_ignores_prefixed_and_non_scale_ratios():
    # 接頭語付き(テーパ1:10)やインチ分数(7/16)は拾わない
    canonical = normalize_raw_extract(_payload_2d(["テーパ1:10", "7/16"]))
    assert canonical["scale"] is None
    assert canonical["scale_candidates"] == []


def test_heat_treatment_and_hardness_extracted_from_2d_notes():
    canonical = normalize_raw_extract(
        _payload_2d(["高周波焼入れのこと", "浸炭処理", "硬度HRC58-62", "全周焼なまし"])
    )
    assert canonical["heat_treatment_keywords"] == ["高周波焼入れ", "浸炭", "焼なまし"]
    # 「高周波焼入れ」の行が単独の「焼入れ」として二重計上されない
    assert "焼入れ" not in canonical["heat_treatment_keywords"]
    assert canonical["hardness_spec_values"] == ["HRC58-62"]
    evidence = canonical["heat_treatment_evidence"]
    assert any(item["value"] == "高周波焼入れ" and item["token"] == "高周波焼入れのこと" for item in evidence)

    tags = build_derived_tags(canonical)
    assert any(tag["tag"] == "熱処理:高周波焼入れ" for tag in tags)
    assert any(tag["tag"] == "熱処理:浸炭" for tag in tags)


def test_heat_treatment_extracted_from_3d_ex_info():
    payload = {
        "source_format": "icad",
        "source_kind": "3d",
        "raw_extract": {
            "top_part": {"name": "SHAFT", "comment": "焼入焼戻し HRC50", "ex_info": None},
            "parts": [
                {
                    "tree_path": ["Top", "SHAFT"],
                    "name": "SHAFT",
                    "comment": None,
                    "ex_info_fields": {"User_NOTE": "窒化処理"},
                }
            ],
        },
    }
    canonical = normalize_raw_extract(payload)
    assert "窒化" in canonical["heat_treatment_keywords"]
    assert "焼入れ" in canonical["heat_treatment_keywords"] or "焼戻し" in canonical["heat_treatment_keywords"]
    assert canonical["hardness_spec_values"] == ["HRC50"]
