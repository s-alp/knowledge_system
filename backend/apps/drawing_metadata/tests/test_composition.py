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
            "confidence_summary": "medium",
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
            "confidence_summary": "high",
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
    assert not any(conflict["attribute"] == "confidence_summary" for conflict in payload["conflicts"])
    assert any(conflict["attribute"] == "confidence_summary" for conflict in payload["diagnosticConflicts"])
    reconciled_by_attribute = {item["attribute"]: item for item in payload["reconciledAttributes"]}
    assert reconciled_by_attribute["customer_name"]["status"] == "conflict"
    assert reconciled_by_attribute["customer_name"]["value2d"] == "澁谷工業"
    assert reconciled_by_attribute["customer_name"]["value3d"] == "コマツ小山"
    assert reconciled_by_attribute["customer_name"]["chosenValue"] == "コマツ小山"
    assert reconciled_by_attribute["confidence_summary"]["status"] == "conflict"
    assert reconciled_by_attribute["equipment_category"]["status"] == "conflict"
    assert reconciled_by_attribute["dimension_values"]["status"] == "merged"
    assert reconciled_by_attribute["part_names"]["status"] == "only_3d"


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
def test_compose_drawing_metadata_records_manual_override_reconciliation():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="sample-manual-reconcile",
        filename="manual-reconcile.icd",
        source_path=r"C:\temp\manual-reconcile.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={"material": "SUS304"},
        manual_overrides_json={"canonicalAttributes": {"material": {"value": "SUS316"}}},
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"material": "SUS304"},
        derived_tags_json=[],
    )

    payload = compose_drawing_metadata(drawing)
    reconciled_by_attribute = {item["attribute"]: item for item in payload["reconciledAttributes"]}
    assert payload["canonicalAttributes"]["material"] == "SUS316"
    assert reconciled_by_attribute["material"]["status"] == "manual_override"
    assert reconciled_by_attribute["material"]["chosenMode"] == "manual_2d"
