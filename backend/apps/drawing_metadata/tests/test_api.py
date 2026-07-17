import pytest
from rest_framework.test import APIClient

from apps.drawing_metadata.models import (
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)


@pytest.mark.django_db
def test_registration_create_and_list(sample_registration_payload):
    client = APIClient()

    create_response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")
    assert create_response.status_code == 201
    drawing_id = create_response.json()["drawingId"]

    list_response = client.get("/api/v1/drawing-metadata/registrations")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["drawingId"] == drawing_id


@pytest.mark.django_db
def test_registration_rejects_duplicate_source_path(sample_registration_payload):
    client = APIClient()

    first = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")
    assert first.status_code == 201
    second = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")
    assert second.status_code == 400
    assert "sourcePath" in second.json()


@pytest.mark.django_db
def test_registration_list_filters_by_composed_attributes():
    from apps.drawing_metadata.models import DrawingComposedMetadata

    drawing_a = RegisteredDrawing.objects.create(
        filename="a.icd", source_path=r"C:\temp\a.icd", source_format="icad"
    )
    drawing_b = RegisteredDrawing.objects.create(
        filename="b.icd", source_path=r"C:\temp\b.icd", source_format="icad"
    )
    DrawingComposedMetadata.objects.create(
        drawing=drawing_a,
        canonical_attributes_json={"customer_name": "コマツ小山", "equipment_category": "ガントリー"},
        derived_tags_json=[{"tag": "客先:コマツ小山"}],
    )
    DrawingComposedMetadata.objects.create(
        drawing=drawing_b,
        canonical_attributes_json={"customer_name": "澁谷工業", "equipment_category": "ロボット"},
        derived_tags_json=[{"tag": "客先:澁谷工業"}],
    )

    client = APIClient()

    response = client.get("/api/v1/drawing-metadata/registrations", {"customer": "コマツ小山"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["filename"] == "a.icd"

    response = client.get("/api/v1/drawing-metadata/registrations", {"tag": "客先:澁谷工業"})
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["filename"] == "b.icd"

    response = client.get("/api/v1/drawing-metadata/registrations", {"pageSize": "1", "page": "2"})
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1


@pytest.mark.django_db
def test_registration_extract_enqueue(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    client = APIClient()

    response = client.post(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/extract",
        {"extractionMode": "3d"},
        format="json",
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["extractionMode"] == "3d"


@pytest.mark.django_db
def test_override_patch(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(drawing=drawing, extraction_mode="3d")
    client = APIClient()

    response = client.patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/overrides",
        {
            "extractionMode": "3d",
            "canonicalAttributes": {
                "equipment_category": {"value": "ガントリー"},
            },
            "derivedTags": {
                "added": ["装置:ガントリー"],
                "removed": [],
            },
            "reason": "test",
        },
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["extractionMode"] == "3d"
    assert payload["canonicalAttributes"]["equipment_category"] == "ガントリー"
    assert payload["derivedTags"][0]["tag"] == "装置:ガントリー"


@pytest.mark.django_db
def test_detail_returns_snapshots_by_mode(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={"equipment_category": "ロボット"},
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"equipment_category": "ガントリー"},
        derived_tags_json=[],
    )

    client = APIClient()
    response = client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert "snapshotsByMode" in payload
    assert payload["snapshotsByMode"]["2d"]["extractionMode"] == "2d"
    assert payload["snapshotsByMode"]["3d"]["extractionMode"] == "3d"
    assert payload["composedMetadata"]["canonicalAttributes"]["equipment_category"] == "ガントリー"
