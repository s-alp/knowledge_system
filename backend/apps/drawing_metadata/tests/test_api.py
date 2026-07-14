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


@pytest.mark.django_db
def test_rag_payload_returns_filters_and_ranking_signals(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="sample.icd",
        source_path=r"C:\projects\customer\sample.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={
            "customer_name": "澁谷工業",
            "project_name": "アイソレータ",
            "equipment_category": "供給台",
            "document_kind": "部品図",
            "drawing_number": "DWG-001",
            "drawing_name": "ブラケット",
            "paper_size": "A3",
            "dimension_values": ["10", "20"],
            "weld_note_texts": ["全周溶接"],
            "unresolved_material_keywords": ["ZZZ"],
        },
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={
            "equipment_category": "供給台",
            "part_names": ["BRACKET-A", "BRACKET-A"],
            "maker_keywords": ["SMC"],
            "material_keywords": ["SUS304"],
            "part_material_candidates": [
                {
                    "part_path": "Top.BRACKET-A",
                    "part_name": "BRACKET-A",
                    "material_id": "SUS304",
                    "source": "3d_part_material",
                    "confidence": "high",
                }
            ],
        },
        derived_tags_json=[],
    )

    client = APIClient()
    response = client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "drawing_metadata_rag_payload.v1"
    assert payload["drawing"]["sourceFolder"] == r"C:\projects\customer"
    assert payload["preFilters"]["customerName"] == "澁谷工業"
    assert payload["preFilters"]["projectName"] == "アイソレータ"
    assert payload["preFilters"]["equipmentCategory"] == "供給台"
    assert payload["preFilters"]["documentKind"] == "部品図"
    assert payload["rankingSignals"]["partNames"] == ["BRACKET-A"]
    assert payload["rankingSignals"]["makerKeywords"] == ["SMC"]
    assert payload["rankingSignals"]["materialKeywords"] == ["SUS304"]
    assert payload["rankingSignals"]["unresolvedMaterialKeywords"] == ["ZZZ"]
    assert payload["partMaterialCandidates"][0]["part_path"] == "Top.BRACKET-A"
    assert "材質:SUS304" in payload["rankingSignals"]["tags"]
    assert "材質要確認:ZZZ" in payload["rankingSignals"]["tags"]
    assert payload["reconciliation"]["requiresReview"] is True
    assert payload["reconciliation"]["reviewFlags"][0]["code"] == "unresolved_material"


@pytest.mark.django_db
def test_api_accepts_trailing_slashes(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"customer_name": "澁谷工業"},
        derived_tags_json=[],
    )

    client = APIClient()

    assert client.get("/api/v1/drawing-metadata/registrations/").status_code == 200
    assert client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}/").status_code == 200
    assert client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload/").status_code == 200
