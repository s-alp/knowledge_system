import pytest
from rest_framework.test import APIClient

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
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
def test_registration_extract_enqueue_accepts_condition_profile(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    client = APIClient()

    response = client.post(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/extract",
        {
            "extractionMode": "2d",
            "extractionProfile": "2d_all_views_layers_print_frame",
            "extractionOptions": {
                "scanAllViews": True,
                "scanAllLayers": True,
                "classifyPrintFrame": True,
            },
        },
        format="json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["extractionProfile"] == "2d_all_views_layers_print_frame"
    assert payload["extractionOptions"]["scanAllViews"] is True
    job = DrawingMetadataExtractionJob.objects.get(pk=payload["jobId"])
    assert job.extraction_profile == "2d_all_views_layers_print_frame"
    assert job.extraction_options_json["scanAllLayers"] is True


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
    assert bootstrap["metadata"]["tagAttributes"]["schemaVersion"] == "viewer_tag_attributes.v1"
    assert bootstrap["metadata"]["tagAttributes"]["reviewRequired"] is True
    assert bootstrap["metadata"]["extractionDiagnostics"]["status"] == "partial"
    assert bootstrap["metadata"]["extractionDiagnostics"]["missingModes"] == ["3d"]
    target_by_key = {
        target["targetKey"]: target
        for target in bootstrap["metadata"]["tagAttributes"]["targets"]
    }
    assert target_by_key["drawing"]["tags"] == ["材質:SUS304", "装置:ロボット"]
    assert any(attribute["name"] == "図面名" for attribute in target_by_key["drawing"]["attributes"])


@pytest.mark.django_db
def test_viewer_bootstrap_endpoint_matches_existing_viewer_contract(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="viewer-sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={
            "drawing_number": "DWG-002",
            "drawing_name": "ロードカップ",
            "drawing_size": "A2",
            "revision": "R3",
            "owner": "承認者B",
            "design_purpose": "既存2D/3Dビューワー連携確認",
        },
        derived_tags_json=[{"tag": "装置:搬送部", "manual_flag": True}],
    )

    client = APIClient()
    detail_response = client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")
    bootstrap_response = client.get(f"/api/v1/drawings/{drawing.id}/bootstrap")
    bootstrap_slash_response = client.get(f"/api/v1/drawings/{drawing.id}/bootstrap/")

    assert detail_response.status_code == 200
    assert bootstrap_response.status_code == 200
    assert bootstrap_slash_response.status_code == 200
    detail_bootstrap = detail_response.json()["viewerBootstrap"]
    assert bootstrap_response.json() == detail_bootstrap
    assert bootstrap_slash_response.json() == detail_bootstrap
    payload = bootstrap_response.json()
    assert payload["drawingId"] == str(drawing.id)
    assert payload["title"] == "ロードカップ"
    assert payload["version"] == "R3"
    assert payload["defaultMode"] == "3d"
    assert payload["availability"] == {"has2d": False, "has3d": True}
    assert payload["metadata"]["drawingNumber"] == "DWG-002"
    assert payload["metadata"]["drawingName"] == "ロードカップ"
    assert payload["metadata"]["drawingType"] is None
    assert payload["metadata"]["paperSize"] == "A2"
    assert payload["metadata"]["status"] is None
    assert payload["metadata"]["owner"] == "承認者B"
    assert payload["metadata"]["designPurpose"] == "既存2D/3Dビューワー連携確認"
    assert payload["metadata"]["tags"] == ["装置:搬送部"]
    assert payload["metadata"]["tagAttributes"]["schemaVersion"] == "viewer_tag_attributes.v1"
    assert payload["metadata"]["tagAttributes"]["targetCount"] == 4
    assert payload["metadata"]["extractionDiagnostics"]["schemaVersion"] == "viewer_extraction_diagnostics.v1"
    assert payload["metadata"]["extractionDiagnostics"]["status"] == "partial"
    assert payload["metadata"]["extractionDiagnostics"]["missingModes"] == ["2d"]


@pytest.mark.django_db
def test_viewer_open_endpoints_return_snapshot_preview_sources(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="viewer-open-sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        raw_extract_json={
            "texts": [{"text_lines": ["材質 SUS304"], "x": 10, "y": 20, "inside_print_area": True}],
            "dimensions": [{"value_1": "100", "x": 30, "y": 40, "inside_print_area": True}],
            "print_frames": [{"size": "A3"}],
        },
        canonical_attributes_json={
            "drawing_name": "ブラケット",
            "drawing_number": "DWG-001",
            "title_block_fields": {"material": "SUS304"},
        },
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={"parts": [{"name": "TOP"}, {"name": "CHILD"}]},
        canonical_attributes_json={"top_part_name": "TOP", "part_names": ["TOP", "CHILD"]},
    )

    client = APIClient()
    response_2d = client.post(f"/api/v1/drawings/{drawing.id}/viewer2d/open", {}, format="json")
    response_3d = client.post(f"/api/v1/drawings/{drawing.id}/viewer3d/open/", {}, format="json")

    assert response_2d.status_code == 200
    assert response_2d["Content-Type"] == "application/json"
    payload_2d = response_2d.json()
    assert payload_2d["extension"] == "svg"
    assert payload_2d["mimeType"] == "image/svg+xml"
    assert payload_2d["sourceUrl"] == f"/api/v1/drawings/{drawing.id}/viewer2d/preview.svg"
    assert payload_2d["diagnostics"]["previewKind"] == "metadata_svg"

    preview_2d = client.get(payload_2d["sourceUrl"])
    assert preview_2d.status_code == 200
    assert preview_2d["Content-Type"].startswith("image/svg+xml")
    assert "ブラケット" in preview_2d.content.decode("utf-8")
    assert "材質 SUS304" in preview_2d.content.decode("utf-8")

    assert response_3d.status_code == 200
    assert response_3d["Content-Type"] == "application/json"
    payload_3d = response_3d.json()
    assert payload_3d["status"] == "ready"
    assert payload_3d["modelFormat"] == "stl"
    assert payload_3d["modelUrl"] == f"/api/v1/drawings/{drawing.id}/viewer3d/preview.stl"
    assert payload_3d["diagnostics"]["previewKind"] == "metadata_stl"

    preview_3d = client.get(payload_3d["modelUrl"])
    assert preview_3d.status_code == 200
    assert preview_3d["Content-Type"].startswith("model/stl")
    assert preview_3d.content.decode("utf-8").startswith("solid icad_metadata_preview")


@pytest.mark.django_db
def test_viewer_open_endpoint_reports_missing_snapshot_as_json(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="viewer-open-missing.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )

    client = APIClient()
    response = client.post(f"/api/v1/drawings/{drawing.id}/viewer2d/open", {}, format="json")

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"
    assert response.json()["error"]["code"] == "viewer_2d_snapshot_missing"


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
    assert client.get(f"/api/v1/drawings/{drawing.id}/bootstrap/").status_code == 200
    assert client.post(f"/api/v1/drawings/{drawing.id}/viewer3d/open/").status_code == 200
    assert client.get(f"/api/v1/drawings/{drawing.id}/viewer3d/preview.stl").status_code == 200
    assert client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload/").status_code == 200
