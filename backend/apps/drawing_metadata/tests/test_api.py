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
    assert list_response.json()[0]["drawingId"] == drawing_id


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


@pytest.mark.django_db
def test_detail_returns_viewer_bootstrap_contract(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={
            "drawing_number": "DWG-001",
            "drawing_name": "供給台",
            "paper_size": "A3",
            "revision": "R1",
            "designer": "設計者A",
            "equipment_category": "ロボット",
        },
        derived_tags_json=[
            {"tag": "材質:SUS304", "manual_flag": True},
            {"tag": "材質:SUS304", "manual_flag": True},
        ],
    )

    client = APIClient()
    response = client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")

    assert response.status_code == 200
    bootstrap = response.json()["viewerBootstrap"]
    assert bootstrap["drawingId"] == str(drawing.id)
    assert bootstrap["title"] == "供給台"
    assert bootstrap["version"] == "R1"
    assert bootstrap["defaultMode"] == "2d"
    assert bootstrap["availability"] == {"has2d": True, "has3d": False}
    assert bootstrap["metadata"]["drawingNumber"] == "DWG-001"
    assert bootstrap["metadata"]["drawingName"] == "供給台"
    assert bootstrap["metadata"]["drawingType"] == "ロボット"
    assert bootstrap["metadata"]["paperSize"] == "A3"
    assert bootstrap["metadata"]["owner"] == "設計者A"
    assert bootstrap["metadata"]["tags"] == ["材質:SUS304", "装置:ロボット"]
