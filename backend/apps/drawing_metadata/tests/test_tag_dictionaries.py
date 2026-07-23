import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.dictionaries import load_keyword_mapping
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.tag_builder import build_derived_tags


def _payload_3d(ex_info: str) -> dict:
    return {
        "source_format": "icad",
        "source_kind": "3d",
        "raw_extract": {
            "top_part": {"name": "SAMPLE", "comment": None, "ex_info": ex_info},
            "parts": [],
        },
    }


def test_load_keyword_mapping_falls_back_to_seed_without_db():
    # DBに到達できない環境(非django_dbテスト)では seed 辞書で動作する
    mapping = load_keyword_mapping(TagDictionaryEntry.KIND_CUSTOMER)
    assert "コマツ小山" in mapping


@pytest.mark.django_db
def test_db_dictionary_overrides_seed_and_project_tag_from_gui_entry():
    TagDictionaryEntry.objects.create(
        kind=TagDictionaryEntry.KIND_CUSTOMER,
        canonical_value="不二越",
        aliases_json=["不二越5", "NACHI"],
        priority=1,
    )
    TagDictionaryEntry.objects.create(
        kind=TagDictionaryEntry.KIND_PROJECT,
        canonical_value="次期円筒研削盤開発",
        aliases_json=["260703_次期円筒研削盤開発"],
        priority=1,
    )

    canonical = normalize_raw_extract(_payload_3d("不二越5 260703_次期円筒研削盤開発(竹中様)"))
    assert canonical["customer_name"] == "不二越"
    assert canonical["project_name"] == "次期円筒研削盤開発"

    tags = [tag["tag"] for tag in build_derived_tags(canonical)]
    assert "客先:不二越" in tags
    assert "案件:次期円筒研削盤開発" in tags


@pytest.mark.django_db
def test_disabled_entry_is_ignored():
    TagDictionaryEntry.objects.create(
        kind=TagDictionaryEntry.KIND_CUSTOMER,
        canonical_value="不二越",
        aliases_json=["NACHI"],
        enabled=False,
    )
    # 有効なDBエントリが無い種別は seed で動く(不二越は拾わない)
    canonical = normalize_raw_extract(_payload_3d("NACHI コマツ小山"))
    assert canonical["customer_name"] == "コマツ小山"


@pytest.mark.django_db
def test_seed_command_then_gui_edit_flow():
    call_command("seed_tag_dictionaries")
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_CUSTOMER, canonical_value="コマツ小山"
    ).exists()
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_PART_NAME, canonical_value="PLATE"
    ).exists()
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_PART_NAME, canonical_value="POLE"
    ).exists()
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_PART_NAME, canonical_value="FENCE"
    ).exists()
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_PART_NAME, canonical_value="JIG"
    ).exists()
    first_count = TagDictionaryEntry.objects.count()
    call_command("seed_tag_dictionaries")
    assert TagDictionaryEntry.objects.count() == first_count


@pytest.mark.django_db
def test_part_name_dictionary_matches_drawing_text_only():
    canonical = normalize_raw_extract(
        {
            "source_format": "icad",
            "source_kind": "2d",
            "raw_extract": {
                "texts": [
                    {"text_lines": ["品名 PLATE"], "inside_print_area": True},
                    {"text_lines": ["FENCE"], "inside_print_area": True},
                    {"text_lines": ["ジグ"], "inside_print_area": True},
                    {"text_lines": ["材質 SUS304"], "inside_print_area": True},
                ],
            },
        }
    )

    assert canonical["part_name_candidates"] == ["PLATE", "FENCE", "JIG"]


@pytest.mark.django_db
def test_tag_dictionary_api_crud():
    client = APIClient()

    created = client.post(
        "/api/v1/drawing-metadata/tag-dictionaries",
        {"kind": "customer", "canonicalValue": "アイリスオーヤマ", "aliases": ["アイリス", " IRIS "]},
        format="json",
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]
    assert created.json()["aliases"] == ["アイリス", "IRIS"]

    # 重複登録は拒否
    duplicated = client.post(
        "/api/v1/drawing-metadata/tag-dictionaries",
        {"kind": "customer", "canonicalValue": "アイリスオーヤマ"},
        format="json",
    )
    assert duplicated.status_code == 400

    listed = client.get("/api/v1/drawing-metadata/tag-dictionaries")
    assert listed.status_code == 200
    payload = listed.json()
    assert any(item["canonicalValue"] == "アイリスオーヤマ" for item in payload["entries"])
    assert {kind["kind"] for kind in payload["kinds"]} >= {"customer", "project", "heat_treatment", "part_name"}

    updated = client.patch(
        f"/api/v1/drawing-metadata/tag-dictionaries/{entry_id}",
        {"enabled": False, "aliases": ["アイリス"]},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    deleted = client.delete(f"/api/v1/drawing-metadata/tag-dictionaries/{entry_id}")
    assert deleted.status_code == 204
    assert not TagDictionaryEntry.objects.filter(pk=entry_id).exists()
