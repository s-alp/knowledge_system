import pytest

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata


@pytest.mark.django_db
def test_compose_drawing_metadata_prefers_3d_scalar_and_unions_lists():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-compose",
        filename="compose.icd",
        source_path=r"C:\temp\compose.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={
            "customer_name": "澁谷工業",
            "equipment_category": "ロボット",
            "dimension_values": ["100"],
        },
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={
            "customer_name": "コマツ小山",
            "equipment_category": "ガントリー",
            "part_names": ["PART-A"],
            "dimension_values": ["200"],
        },
        derived_tags_json=[],
    )

    payload = compose_drawing_metadata(drawing)
    assert payload["canonicalAttributes"]["customer_name"] == "コマツ小山"
    assert payload["canonicalAttributes"]["equipment_category"] == "ガントリー"
    assert payload["canonicalAttributes"]["dimension_values"] == ["100", "200"]

    conflict = next(item for item in payload["conflicts"] if item["attribute"] == "customer_name")
    # chosenMode は実際に採用した値の出所を指す
    assert conflict["chosenMode"] == "3d"

    # 競合した属性のタグは除外せず confidence=low で残す
    customer_tag = next(tag for tag in payload["derivedTags"] if tag["source"] == "customer_name")
    assert customer_tag["tag"] == "客先:コマツ小山"
    assert customer_tag["confidence"] == "low"


@pytest.mark.django_db
def test_compose_drawing_metadata_keeps_manual_tags():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-manual",
        filename="manual.icd",
        source_path=r"C:\temp\manual.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"equipment_category": "ガントリー"},
        derived_tags_json=[{"tag": "手動:優先", "manual_flag": True, "source": "manual_override"}],
    )

    payload = compose_drawing_metadata(drawing)
    assert any(tag["tag"] == "手動:優先" for tag in payload["derivedTags"])


@pytest.mark.django_db
def test_compose_drawing_metadata_respects_removed_tags():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-removed",
        filename="removed.icd",
        source_path=r"C:\temp\removed.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"equipment_category": "ガントリー", "customer_name": "コマツ小山"},
        derived_tags_json=[],
        manual_overrides_json={"derivedTags": {"added": [], "removed": ["装置:ガントリー"]}},
    )

    payload = compose_drawing_metadata(drawing)
    displays = [tag["tag"] for tag in payload["derivedTags"]]
    # 削除済みタグは統合属性から再生成されても復活しない
    assert "装置:ガントリー" not in displays
    assert "客先:コマツ小山" in displays


@pytest.mark.django_db
def test_compose_drawing_metadata_records_manual_choice_in_conflict():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-manual-conflict",
        filename="manual_conflict.icd",
        source_path=r"C:\temp\manual_conflict.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={"customer_name": "澁谷工業"},
        manual_overrides_json={"canonicalAttributes": {"customer_name": {"value": "広島アルミ"}}},
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"customer_name": "コマツ小山"},
        derived_tags_json=[],
    )

    payload = compose_drawing_metadata(drawing)
    # 優先順は manual_3d > manual_2d > 3d自動 > 2d自動。ここでは manual_2d が採用され、
    # conflict 記録もその事実(manual_2d)を指す(旧実装は常に "3d" と誤記していた)。
    assert payload["canonicalAttributes"]["customer_name"] == "広島アルミ"
    conflict = next(item for item in payload["conflicts"] if item["attribute"] == "customer_name")
    assert conflict["chosenMode"] == "manual_2d"
