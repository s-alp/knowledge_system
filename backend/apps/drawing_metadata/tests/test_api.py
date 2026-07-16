import tempfile
import json
from pathlib import Path
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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
def test_registration_upload_icad_file(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    client = APIClient()

    response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile("sample.icd", b"icad-data")},
        format="multipart",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "sample.icd"
    assert payload["sourceFormat"] == "icad"
    stored_path = Path(payload["sourcePath"])
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"icad-data"


@pytest.mark.django_db
def test_registration_upload_rejects_non_icad(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    client = APIClient()

    response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile("sample.txt", b"not-icad")},
        format="multipart",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "icad_file_extension"


@pytest.mark.django_db
def test_tag_automation_settings_api_uses_runtime_settings_without_exposing_api_key(settings):
    settings.DRAWING_METADATA_LLM_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "secret-value-must-not-be-returned"
    settings.GEMINI_MODEL = "gemini-test-model"
    settings.GEMINI_TEMPERATURE = 0.0

    response = APIClient().get("/api/v1/drawing-metadata/settings/tag-automation")

    assert response.status_code == 200
    payload = response.json()
    runtime_by_label = {row["label"]: row["value"] for row in payload["runtimeRows"]}
    assert runtime_by_label["LLM provider"] == "gemini"
    assert runtime_by_label["Gemini APIキー"] == "設定済み"
    assert runtime_by_label["主モデル"] == "gemini-test-model"
    assert runtime_by_label["温度"] == "0.0"
    assert payload["managementLinks"] == [
        {
            "key": "icad-extraction-management",
            "label": "ICAD抽出管理",
            "description": "登録済みICAD、抽出snapshot、2D/3Dジョブ、保存元パスをシステム設定内で確認します。",
            "action": "open_icad_extraction_review",
        },
        {
            "key": "integration-data-review",
            "label": "API仕様・引継ぎ資料",
            "description": "移植用API、対象別payload、viewer/RAG連携の集計を確認します。",
            "action": "show_handoff_note",
        },
    ]
    assert "secret-value-must-not-be-returned" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_handoff_summary_api_returns_dashboard_payload(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="handoff-api.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"material_keywords": ["SUS304"]},
        derived_tags_json=[],
    )
    DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        worker_name="test-worker",
        error_message="sxnet.SxException: 指定したファイルは図面ファイルではありません。",
    )

    response = APIClient().get("/api/v1/drawing-metadata/handoff-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summaryCards"][0]["label"] == "登録図面"
    assert payload["summaryCards"][0]["value"] == 1
    assert payload["apiRows"][0]["path"] == "/api/v1/drawings/{drawing_id}/bootstrap"
    assert any(row["path"] == "/api/v1/drawing-metadata/handoff-summary" for row in payload["apiRows"])
    assert payload["rows"][0]["filename"] == "handoff-api.icd"
    assert payload["rows"][0]["snapshotStateLabel"] == "3Dのみ抽出済み"
    assert payload["workerStatus"]["status"] in {"missing", "running", "stale", "unreadable"}
    assert payload["jobStatusCounts"]["failed"] == 1
    assert payload["recentFailedJobs"][0]["filename"] == "handoff-api.icd"
    assert "図面ファイルとして開けていません" in payload["recentFailedJobs"][0]["reextractCondition"]


@pytest.mark.django_db
def test_handoff_and_registration_list_follow_manifest_scope(settings, tmp_path, sample_registration_payload):
    included = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="included.icd",
        source_path=r"J:\sample\included.icd",
        source_format=sample_registration_payload["sourceFormat"],
    )
    excluded = RegisteredDrawing.objects.create(
        host_drawing_id="probe",
        filename="browser_icad_probe.icd",
        source_path=r"C:\Users\s-iwata\Desktop\knowledge_system\backend\var\drawing_metadata\uploads\probe.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(drawing=included, extraction_mode="2d")
    DrawingMetadataSnapshot.objects.create(drawing=included, extraction_mode="3d")
    DrawingMetadataSnapshot.objects.create(drawing=excluded, extraction_mode="3d")
    manifest_path = tmp_path / "shared_manifest.json"
    manifest_path.write_text(
        json.dumps({"entries": [{"sourcePath": included.source_path}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    settings.DRAWING_METADATA_HANDOFF_MANIFEST = str(manifest_path)

    list_payload = APIClient().get("/api/v1/drawing-metadata/registrations").json()
    assert [item["filename"] for item in list_payload] == ["included.icd"]

    summary_payload = APIClient().get("/api/v1/drawing-metadata/handoff-summary").json()
    assert summary_payload["summaryCards"][0]["value"] == 1
    assert summary_payload["rows"][0]["filename"] == "included.icd"
    assert summary_payload["scope"]["mode"] == "manifest"
    assert summary_payload["scope"]["manifestSourceCount"] == 1
    assert summary_payload["scope"]["totalRegistrationCount"] == 2
    assert summary_payload["scope"]["scopedRegistrationCount"] == 1
    assert summary_payload["scope"]["excludedRegistrationCount"] == 1


@pytest.mark.django_db
def test_icad_entity_api_registers_one_assembly_for_one_icd(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="assembly-sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "top_part": {"name": "MACHINE"},
            "parts": [
                {
                    "node_id": "node-000000",
                    "parent_node_id": None,
                    "depth": 0,
                    "child_count": 2,
                    "entity_kind": "assembly",
                    "tree_path": ["MACHINE"],
                    "name": "MACHINE",
                    "ex_info_fields": {"PRFX": "CAA5012"},
                },
                {
                    "node_id": "node-000001",
                    "parent_node_id": "node-000000",
                    "depth": 1,
                    "child_count": 1,
                    "entity_kind": "subassembly",
                    "tree_path": ["MACHINE", "FEEDER"],
                    "name": "FEEDER",
                    "ex_info_fields": {"ユニット番号": "34000"},
                },
                {
                    "node_id": "node-000002",
                    "parent_node_id": "node-000001",
                    "depth": 2,
                    "child_count": 0,
                    "entity_kind": "part",
                    "tree_path": ["MACHINE", "FEEDER", "BRACKET-A"],
                    "name": "BRACKET-A",
                    "ex_info_fields": {"部品番号": "CAA5012-02434006P1R1", "表面処理": "黒染め"},
                    "materials": [{"mat_id": "SS400", "name": "一般構造用圧延鋼材"}],
                },
                {
                    "node_id": "node-000003",
                    "parent_node_id": "node-000000",
                    "depth": 1,
                    "child_count": 0,
                    "entity_kind": "part",
                    "tree_path": ["MACHINE", "COVER-B"],
                    "name": "COVER-B",
                    "ex_info_fields": {},
                    "materials": [{"mat_id": "SUS304"}],
                },
            ],
        },
        canonical_attributes_json={
            "customer_name": "ライズ",
            "drawing_number": "CAA5012-02434006P1R1",
            "mass_value": 12.3456,
            "weight_value": 121.068,
            "part_names": ["MACHINE", "FEEDER", "BRACKET-A", "COVER-B"],
        },
        derived_tags_json=[],
    )

    client = APIClient()
    product_response = client.get(f"/api/v1/knowledge-entities?target=product&drawingId={drawing.id}")
    part_response = client.get(f"/api/v1/knowledge-entities?target=part&drawingId={drawing.id}")

    assert product_response.status_code == 200
    assert part_response.status_code == 200
    products = product_response.json()["items"]
    parts = part_response.json()["items"]
    assert len(products) == 1
    assert products[0]["entityKind"] == "assembly"
    assert products[0]["drawingId"] == str(drawing.id)
    assert products[0]["treePath"] == ["MACHINE"]
    assert products[0]["parentEntityId"] is None
    assert parts == []
    assert any(attribute["key"] == "materials" for attribute in products[0]["attributes"])

    detail_response = client.get(f"/api/v1/knowledge-entities/{products[0]['entityId']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["treePath"] == ["MACHINE"]
    assert detail_response.json()["classificationEvidence"] == "filename"
    assert detail_response.json()["businessFields"]["status"] == ""
    assert detail_response.json()["extractionReview"]["label"] == "未確認"
    assert next(item for item in detail_response.json()["attributes"] if item["key"] == "mass_value")["value"] == "12.35 kg"
    assert next(item for item in detail_response.json()["attributes"] if item["key"] == "weight_value")["value"] == "12.35 kg"
    assert all(item["reason"] for item in detail_response.json()["attributes"])
    assert all(item["reason"] for item in detail_response.json()["tags"])
    assert all(item["reason"] and item["confidence"] for item in detail_response.json()["provenance"])


@pytest.mark.django_db
def test_icad_entity_api_does_not_expand_legacy_tree_paths(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="legacy-sample.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [
                {"tree_path": ["ROOT"], "name": "ROOT"},
                {"tree_path": ["ROOT", "SUB"], "name": "SUB"},
                {"tree_path": ["ROOT", "SUB", "PART"], "name": "PART"},
            ]
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?drawingId={drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["entityKind"] == "part"
    assert payload["items"][0]["treePath"] == ["legacy-sample"]
    assert payload["items"][0]["drawingId"] == str(drawing.id)


@pytest.mark.django_db
def test_icad_entity_api_classifies_external_reference_as_assembly(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="external-reference-drawing",
        filename="external-reference.icd",
        source_path=r"C:\temp\external-reference.icd",
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [
                {"tree_path": ["ROOT"], "name": "ROOT", "depth": 0, "child_count": 1},
                {
                    "tree_path": ["ROOT", "SUB"],
                    "name": "SUB",
                    "depth": 1,
                    "child_count": 0,
                    "is_external": True,
                },
            ]
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?target=product&drawingId={drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["entityKind"] == "assembly"
    assert payload["items"][0]["classificationEvidence"] == "sxnet_external_parts"


@pytest.mark.django_db
def test_icad_entity_api_treats_ref_model_name_as_external_reference(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="ref-model-name-drawing",
        filename="ref-model-name.icd",
        source_path=r"C:\temp\ref-model-name.icd",
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [
                {"tree_path": ["ROOT"], "name": "ROOT", "depth": 0, "child_count": 1},
                {
                    "tree_path": ["ROOT", "SUB"],
                    "name": "SUB",
                    "depth": 1,
                    "child_count": 1,
                    "is_external": False,
                    "ref_model_name": "SUB-REF",
                },
                {"tree_path": ["ROOT", "SUB", "LEAF"], "name": "LEAF", "depth": 2, "child_count": 0},
            ]
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?target=product&drawingId={drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["classificationEvidence"] == "sxnet_external_parts"
    assert payload["items"][0]["childAssemblyCount"] == 1


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
def test_entity_business_edit_and_drawing_link_are_persisted(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="",
        filename="entity-part.icd",
        source_path=r"J:\parts\entity-part.icd",
        source_format="icad",
    )
    linked = RegisteredDrawing.objects.create(
        host_drawing_id="",
        filename="related-drawing.icd",
        source_path=r"J:\drawings\related-drawing.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={"top_part": {"name": "PART-A"}, "parts": []},
        canonical_attributes_json={"drawing_number": "P-001"},
    )
    client = APIClient()
    catalog = client.get(f"/api/v1/knowledge-entities?target=part&drawingId={drawing.id}").json()
    entity_id = catalog["items"][0]["entityId"]

    response = client.patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/overrides",
        {
            "extractionMode": "3d",
            "businessFields": {
                "name": "編集後部品名",
                "partNumber": "P-001-R1",
                "category": "ブラケット",
                "status": "完了",
                "owner": "設計担当者",
                "remarks": "確認済み",
            },
            "relatedDrawingIds": [str(linked.id)],
            "knowledgeEntityTarget": "part",
            "knowledgeEntityKind": "part",
            "reason": "登録情報と関連図面を更新",
        },
        format="json",
    )
    assert response.status_code == 200

    detail = client.get(f"/api/v1/knowledge-entities/{entity_id}?drawingId={drawing.id}").json()
    assert detail["name"] == "編集後部品名"
    assert detail["partNumber"] == "P-001-R1"
    assert detail["businessFields"]["status"] == "完了"
    assert detail["businessFieldSources"]["status"]["source"] == "manual_override"
    assert [item["relationship"] for item in detail["relatedDrawings"]] == ["source", "linked"]
    assert detail["relatedDrawings"][1]["drawingId"] == str(linked.id)
    assert any(item["action"] == "override" for item in detail["history"])

    options = client.get("/api/v1/drawing-options?q=related-drawing").json()
    assert options["totalCount"] == 1
    assert options["items"][0]["drawingId"] == str(linked.id)


@pytest.mark.django_db
def test_entity_business_edit_rejects_unknown_fields(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="",
        filename="invalid-business-field.icd",
        source_path=r"J:\parts\invalid-business-field.icd",
        source_format="icad",
    )
    DrawingMetadataSnapshot.objects.create(drawing=drawing, extraction_mode="3d")

    response = APIClient().patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/overrides",
        {
            "extractionMode": "3d",
            "businessFields": {"unknown": "value"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert "unknownFields" in response.json()["businessFields"]


@pytest.mark.django_db
def test_review_patch_persists_confirmation_and_override_resets_it(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    snapshot = DrawingMetadataSnapshot.objects.create(drawing=drawing, extraction_mode="3d")
    client = APIClient()

    response = client.patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/review",
        {"extractionMode": "3d", "decision": "confirmed", "reason": "候補確認済み"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["reviewStatus"] == "confirmed"
    snapshot.refresh_from_db()
    assert snapshot.review_status == DrawingMetadataSnapshot.REVIEW_CONFIRMED
    assert snapshot.reviewed_at is not None

    override_response = client.patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/overrides",
        {
            "extractionMode": "3d",
            "canonicalAttributes": {"material": {"value": "SUS304"}},
            "reason": "材質を手直し",
        },
        format="json",
    )
    assert override_response.status_code == 200
    snapshot.refresh_from_db()
    assert snapshot.review_status == DrawingMetadataSnapshot.REVIEW_PENDING
    assert snapshot.reviewed_at is None


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
def test_detail_returns_latest_jobs_by_mode_even_without_snapshots(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="failed-before-snapshot.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    two_d_job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        extraction_profile="2d_all_views_layers_print_frame",
        error_message="sxnet.SxException: 指定したファイルは図面ファイルではありません。",
    )
    three_d_job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_QUEUED,
        extraction_profile="3d_model_part_attributes",
    )

    response = APIClient().get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshotsByMode"] == {}
    assert payload["latestJobsByMode"]["2d"]["jobId"] == str(two_d_job.id)
    assert payload["latestJobsByMode"]["2d"]["status"] == "failed"
    assert payload["latestJobsByMode"]["2d"]["errorMessage"] == "sxnet.SxException: 指定したファイルは図面ファイルではありません。"
    assert payload["latestJobsByMode"]["3d"]["jobId"] == str(three_d_job.id)
    assert payload["latestJobsByMode"]["3d"]["status"] == "queued"


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
def test_viewer_open_prefers_actual_preview_assets_when_snapshot_provides_urls(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="viewer-actual-assets.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={
            "viewer_assets": {
                "2d": {
                    "sourceUrl": "https://pdm.example.local/previews/viewer-actual-assets.pdf",
                    "mimeType": "application/pdf",
                    "pageCount": 2,
                }
            }
        },
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={
            "viewer_assets": {
                "3d": {
                    "modelUrl": "https://pdm.example.local/previews/viewer-actual-assets.stl",
                    "modelFormat": "stl",
                }
            }
        },
    )

    client = APIClient()
    response_2d = client.post(f"/api/v1/drawings/{drawing.id}/viewer2d/open", {}, format="json")
    response_3d = client.post(f"/api/v1/drawings/{drawing.id}/viewer3d/open", {}, format="json")

    assert response_2d.status_code == 200
    payload_2d = response_2d.json()
    assert payload_2d["extension"] == "pdf"
    assert payload_2d["sourceUrl"] == "https://pdm.example.local/previews/viewer-actual-assets.pdf"
    assert payload_2d["pageCount"] == 2
    assert payload_2d["diagnostics"]["previewKind"] == "actual_pdf"

    assert response_3d.status_code == 200
    payload_3d = response_3d.json()
    assert payload_3d["modelFormat"] == "stl"
    assert payload_3d["modelUrl"] == "https://pdm.example.local/previews/viewer-actual-assets.stl"
    assert payload_3d["diagnostics"]["previewKind"] == "actual_stl"


@pytest.mark.django_db
def test_viewer_open_accepts_generated_relative_preview_asset_urls(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="viewer-generated-assets.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    job_id = uuid4()
    model_url = f"/api/v1/drawing-metadata-preview-assets/{job_id}/{job_id}.stl"
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "viewer_assets": {
                "3d": [
                    {
                        "url": model_url,
                        "filename": f"{job_id}.stl",
                        "extension": "stl",
                        "model_format": "stl",
                        "status": "ready",
                    }
                ]
            }
        },
    )

    client = APIClient()
    response = client.post(f"/api/v1/drawings/{drawing.id}/viewer3d/open", {}, format="json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["modelFormat"] == "stl"
    assert payload["modelUrl"] == model_url
    assert payload["diagnostics"]["previewKind"] == "actual_stl"


@pytest.mark.django_db
def test_preview_asset_endpoint_serves_generated_file(settings):
    job_id = uuid4()
    with tempfile.TemporaryDirectory() as temp_dir:
        settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT = Path(temp_dir) / "preview_assets"
        asset_dir = settings.DRAWING_METADATA_PREVIEW_ASSET_ROOT / str(job_id)
        asset_dir.mkdir(parents=True)
        asset_path = asset_dir / "model.stl"
        asset_path.write_text("solid generated\nendsolid generated\n", encoding="utf-8")

        client = APIClient()
        response = client.get(f"/api/v1/drawing-metadata-preview-assets/{job_id}/model.stl")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("model/stl")
        assert b"solid generated" in b"".join(response.streaming_content)


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
