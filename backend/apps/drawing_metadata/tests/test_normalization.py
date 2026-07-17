import pytest

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.tag_builder import build_derived_tags


@pytest.mark.django_db
def test_normalize_3d_raw_extract():
    payload = {
        "source_format": "icad",
        "source_kind": "3d",
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
    assert canonical["customer_name"] == "コマツ小山"
    assert canonical["equipment_category"] == "ガントリー"
    assert "SMC" in canonical["maker_keywords"]
    assert any(tag["tag"] == "客先:コマツ小山" for tag in tags)

    # 複数客先語(コマツ小山 / 広島アルミ)が混在するため候補として両方残り、要約信頼度が下がる
    assert set(canonical["customer_name_candidates"]) == {"コマツ小山", "広島アルミ"}
    assert canonical["confidence_summary"] == "medium"

    # 部品単位の対応関係が構造のまま保持される
    assert canonical["parts"][0]["name"] == "SMC CYLINDER"
    assert canonical["parts"][0]["tree_path"] == ["Top", "UnitA"]
    assert canonical["parts"][0]["is_external"] is True

    # 根拠: どのフィールドのどのトークンがどの別名に一致したか
    customer_evidence = canonical["match_evidence"]["customer_name"]
    assert any(item["value"] == "コマツ小山" and item["field"] == "top_part_ex_info" for item in customer_evidence)

    # タグにも namespace / value / evidence が入る
    customer_tag = next(tag for tag in tags if tag["source"] == "customer_name")
    assert customer_tag["namespace"] == "客先"
    assert customer_tag["value"] == "コマツ小山"
    assert customer_tag["evidence"]
    assert customer_tag["confidence"] == "medium"  # 複数候補のため


@pytest.mark.django_db
def test_normalize_2d_raw_extract():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
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
    assert canonical["customer_name"] == "澁谷工業"
    assert canonical["equipment_category"] == "ロボット"
    # spec_tokens は生トークン、spec_names は辞書一致した正規規格名として分離される
    assert "SES" in canonical["spec_tokens"]
    assert canonical["spec_names"] == ["SES"]

    tags = build_derived_tags(canonical)
    assert any(tag["tag"] == "規格:SES" for tag in tags)


@pytest.mark.django_db
def test_normalize_absorbs_fullwidth_and_rejects_substring_false_positive():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "raw_extract": {
            "texts": [
                # 全角の「ＳＥＳ」は NFKC 正規化で一致する
                {"text_lines": ["ＳＥＳ規格による"], "source_type": "text"},
                # "hoses" の部分文字列 "ses" には誤ヒットしない
                {"text_lines": ["air hoses"], "source_type": "text"},
                {"text_lines": ["processes list"], "source_type": "text"},
            ],
            "dimensions": [],
            "weld_notes": [],
            "balloons": [],
            "tolerances": [],
        },
    }

    canonical = normalize_raw_extract(payload)
    assert canonical["spec_names"] == ["SES"]
    evidence = canonical["match_evidence"]["spec_names"]
    assert all(item["token"] == "ＳＥＳ規格による" for item in evidence)


@pytest.mark.django_db
def test_normalize_uses_db_dictionary_over_seed():
    TagDictionaryEntry.objects.create(
        kind=TagDictionaryEntry.KIND_CUSTOMER,
        canonical_value="テスト重工",
        aliases_json=["TESTHI"],
        priority=1,
    )

    payload = {
        "source_format": "icad",
        "source_kind": "3d",
        "raw_extract": {
            "top_part": {"name": "TESTHI 装置", "comment": None, "ex_info": "コマツ小山"},
            "parts": [],
        },
    }

    canonical = normalize_raw_extract(payload)
    # DB 辞書が存在する場合は seed 定数ではなく DB を正とする
    assert canonical["customer_name"] == "テスト重工"
    assert canonical["customer_name_candidates"] == ["テスト重工"]


@pytest.mark.django_db
def test_normalize_marks_partial_when_warnings_present():
    payload = {
        "source_format": "icad",
        "source_kind": "2d",
        "warnings": [{"code": "unsupported_geometry", "message": "..."}],
        "raw_extract": {"texts": [], "dimensions": [], "weld_notes": [], "balloons": [], "tolerances": []},
    }
    canonical = normalize_raw_extract(payload)
    assert canonical["extraction_status"] == "partial"
