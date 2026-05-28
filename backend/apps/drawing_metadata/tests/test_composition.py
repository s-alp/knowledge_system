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
    assert any(conflict["attribute"] == "customer_name" for conflict in payload["conflicts"])


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
