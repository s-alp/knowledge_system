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
from apps.drawing_metadata.services.path_constraints import normalize_icad_display_filename, sxnet_staging_reasons


@pytest.mark.django_db
def test_registration_create_and_list(sample_registration_payload, tmp_path):
    client = APIClient()
    source_file = tmp_path / "sample_3d.icd"
    source_file.write_bytes(b"icad-data")
    sample_registration_payload["sourcePath"] = str(source_file)

    create_response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")
    assert create_response.status_code == 201
    drawing_id = create_response.json()["drawingId"]

    list_response = client.get("/api/v1/drawing-metadata/registrations")
    assert list_response.status_code == 200
    assert list_response.json()[0]["drawingId"] == drawing_id


@pytest.mark.django_db
def test_registration_create_returns_existing_for_same_source_path(sample_registration_payload, tmp_path):
    client = APIClient()
    source_file = tmp_path / "same_source.icd"
    source_file.write_bytes(b"icad-data")
    sample_registration_payload["sourcePath"] = str(source_file)
    sample_registration_payload["filename"] = "same_source.icd"

    first_response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")
    second_response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.json()["drawingId"] == first_response.json()["drawingId"]
    assert RegisteredDrawing.objects.count() == 1


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
    assert stored_path.name == "input.icd"
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"icad-data"
    assert RegisteredDrawing.objects.get().source_content_sha256


@pytest.mark.django_db
def test_registration_upload_returns_existing_for_same_content(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    client = APIClient()

    first_response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile("sample.icd", b"same-icad-data")},
        format="multipart",
    )
    second_response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile("renamed_sample.icd", b"same-icad-data")},
        format="multipart",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.json()["drawingId"] == first_response.json()["drawingId"]
    assert RegisteredDrawing.objects.count() == 1
    assert len(list((tmp_path / "uploads").glob("*/*.icd"))) == 1


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
def test_registration_upload_accepts_django_normalized_long_filename(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    client = APIClient()
    too_long_name = f"{'A' * 256}.icd"

    response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile(too_long_name, b"icad-data")},
        format="multipart",
    )

    assert response.status_code == 201
    drawing = RegisteredDrawing.objects.get()
    assert len(drawing.filename) == 255
    assert Path(drawing.source_path).name == "input.icd"


def test_icad_display_filename_normalization_keeps_storage_length_and_extension():
    normalized = normalize_icad_display_filename(f"{'A' * 256}.icd")

    assert len(normalized) == 255
    assert normalized.endswith(".icd")


def test_sxnet_staging_reasons_explain_path_and_filename_limits():
    long_path = "C:\\" + "\\".join(["segment"] * 40) + "\\sample.icd"
    long_filename = f"{'A' * 256}.icd"

    assert sxnet_staging_reasons(long_path, filename="sample.icd") == ["path_length"]
    assert sxnet_staging_reasons(r"C:\temp\sample.icd", filename=long_filename) == ["filename_length"]
    assert sxnet_staging_reasons(long_path, filename=long_filename) == ["path_length", "filename_length"]


@pytest.mark.django_db
def test_registration_upload_stores_short_internal_filename(settings, tmp_path):
    settings.DRAWING_METADATA_STORAGE_ROOT = tmp_path
    client = APIClient()

    response = client.post(
        "/api/v1/drawing-metadata/registrations/upload",
        {"file": SimpleUploadedFile("customer_original_name.icd", b"icad-data")},
        format="multipart",
    )

    assert response.status_code == 201
    drawing = RegisteredDrawing.objects.get()
    assert drawing.filename == "customer_original_name.icd"
    assert Path(drawing.source_path).name == "input.icd"


@pytest.mark.django_db
def test_registration_create_rejects_missing_original_path(sample_registration_payload):
    client = APIClient()
    sample_registration_payload["sourcePath"] = r"C:\missing\sample_3d.icd"

    response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")

    assert response.status_code == 400
    assert "指定されたICADファイルが見つかりません" in str(response.json())


@pytest.mark.django_db
def test_registration_create_accepts_too_long_original_path_for_staged_sxnet(
    monkeypatch, sample_registration_payload
):
    client = APIClient()
    segment_path = "\\".join(["segment"] * 35)
    sample_registration_payload["sourcePath"] = rf"C:\{segment_path}\sample_3d.icd"
    monkeypatch.setattr(
        "apps.drawing_metadata.api.serializers.icad_source_path_exists",
        lambda _path: True,
    )

    response = client.post("/api/v1/drawing-metadata/registrations", sample_registration_payload, format="json")

    assert response.status_code == 201
    assert RegisteredDrawing.objects.get().source_path == sample_registration_payload["sourcePath"]


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
            "description": "登録済みICAD、抽出snapshot、2D/3Dジョブ、抽出で使うICADファイルをシステム設定内で確認します。",
            "action": "open_icad_extraction_review",
        },
        {
            "key": "tag-dictionaries",
            "label": "タグ辞書管理",
            "description": "客先・案件・装置カテゴリ・メーカー・規格・熱処理の辞書語彙を登録・編集します。編集後は再正規化で既存図面へ反映します。",
            "action": "open_tag_dictionaries",
        },
        {
            "key": "integration-data-review",
            "label": "API仕様・連携仕様",
            "description": "移植用API、対象別payload、viewer/RAG連携の仕様と集計を確認します。",
            "action": "show_handoff_note",
        },
    ]
    assert "secret-value-must-not-be-returned" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_handoff_summary_api_returns_dashboard_payload(sample_registration_payload, tmp_path):
    source_file = tmp_path / "handoff-api.icd"
    source_file.write_bytes(b"icad-data")
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="handoff-api.icd",
        source_path=str(source_file),
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
    assert payload["recentFailedJobs"][0]["errorClass"] == "sxnet_rejected_as_not_drawing_file"
    assert payload["recentFailedJobs"][0]["sourcePreflight"]["sourceExistsFromCurrentMachine"] is True
    assert "SXNETが図面モデルとして開けていません" in payload["recentFailedJobs"][0]["reextractCondition"]


@pytest.mark.django_db
def test_handoff_summary_api_explains_path_length_failure(sample_registration_payload):
    long_source_path = "C:\\" + "\\".join(["segment"] * 40) + "\\too-long-path.icd"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="too-long-path.icd",
        source_path=long_source_path,
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        error_message="ICADファイルのパスが長すぎます。SXNETへ渡すパスは259文字以下にしてください。",
    )

    response = APIClient().get("/api/v1/drawing-metadata/handoff-summary")

    assert response.status_code == 200
    failed_job = response.json()["recentFailedJobs"][0]
    assert failed_job["errorClass"] == "path_length_limit"
    assert failed_job["sourcePreflight"]["sourcePathWithinSxnetLegacyLimit"] is False
    assert failed_job["sourcePreflight"]["requiresSxnetStagedInput"] is True
    assert failed_job["sourcePreflight"]["sxnetStagingReasons"] == ["path_length"]
    assert "一時パス" in failed_job["reextractCondition"]


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
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={
            "material_keywords": ["SS400"],
            "drawing_number": "CAA5012-02434006P1R1",
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
    assert any(item["attribute"] == "drawing_number" and item["status"] == "matched" for item in detail_response.json()["reconciledAttributes"])
    assert any(item["attribute"] == "material_keywords" and item["status"] == "only_2d" for item in detail_response.json()["reconciledAttributes"])
    assert detail_response.json()["diagnosticConflicts"] == []
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
    assert payload["items"][0]["treePath"] == ["名称未抽出"]
    assert payload["items"][0]["drawingId"] == str(drawing.id)


@pytest.mark.django_db
def test_icad_part_entity_uses_part_name_separately_from_part_number(sample_registration_payload):
    drawing_number = "CAA5012-02434006P1R1"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="part-name-drawing",
        filename=f"{drawing_number}.icd",
        source_path=rf"C:\temp\部品\{drawing_number}.icd",
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        raw_extract_json={
            "texts": [
                {"text_lines": ["品名 PLATE"], "inside_print_area": True},
                {"text_lines": [f"図番 {drawing_number}"], "inside_print_area": True},
            ],
        },
        canonical_attributes_json={
            "drawing_number": drawing_number,
            "drawing_name": "BRACKET",
            "part_name_candidates": ["BRACKET"],
        },
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "top_part": {"name": "MODEL_NODE"},
            "parts": [{"tree_path": ["MODEL_NODE"], "name": "MODEL_NODE", "depth": 0, "child_count": 0}],
        },
        canonical_attributes_json={
            "drawing_number": drawing_number,
            "drawing_name": None,
            "part_name_candidates": [],
            "part_names": ["MODEL_NODE"],
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?target=part&drawingId={drawing.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["partNumber"] == drawing_number
    assert item["name"] == "BRACKET"
    assert item["treePath"] == ["BRACKET"]
    assert item["businessFields"]["partNumber"] == drawing_number
    assert item["businessFields"]["name"] == "BRACKET"


@pytest.mark.django_db
def test_icad_part_entity_rejects_obvious_part_number_noise(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="part-number-noise-drawing",
        filename=".ni",
        source_path=r"C:\temp\部品\.ni",
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [{"tree_path": ["PLATE"], "name": "PLATE", "depth": 0, "child_count": 0}],
        },
        canonical_attributes_json={
            "drawing_number": "組",
            "drawing_name": "PLATE",
            "part_name_candidates": ["PLATE"],
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?target=part&drawingId={drawing.id}")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["partNumber"] == ""
    assert item["businessFields"]["partNumber"] == ""
    assert item["name"] == "PLATE"


@pytest.mark.django_db
def test_icad_part_entity_cleans_filename_style_part_number(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="filename-style-part-number-drawing",
        filename="03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd",
        source_path=r"C:\temp\部品\03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd",
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [{"tree_path": ["シュートベース"], "name": "シュートベース", "depth": 0, "child_count": 0}],
        },
        canonical_attributes_json={
            "drawing_number": "U8718-S71-002_A3",
            "drawing_name": "シュートベース",
            "part_name_candidates": ["シュートベース"],
        },
    )

    response = APIClient().get(f"/api/v1/knowledge-entities?target=part&drawingId={drawing.id}")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["partNumber"] == "U8718-S71-002"
    assert item["businessFields"]["partNumber"] == "U8718-S71-002"
    assert item["name"] == "シュートベース"


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
    # 部品数は外部参照パーツのみ。子構造なしの外部参照は部品として数える。
    assert payload["items"][0]["childAssemblyCount"] == 0
    assert payload["items"][0]["childPartCount"] == 1
    assert payload["items"][0]["descendantPartCount"] == 1


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
    # 子構造を持つ外部参照はサブアセンブリ候補として数え、内部末端パーツは部品数に入れない。
    assert payload["items"][0]["childAssemblyCount"] == 1
    assert payload["items"][0]["childPartCount"] == 0
    assert payload["items"][0]["descendantPartCount"] == 1


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
def test_registration_extract_does_not_duplicate_active_job(sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    existing_job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        status=DrawingMetadataExtractionJob.STATUS_QUEUED,
        extraction_profile="3d_model_part_attributes",
    )
    client = APIClient()

    response = client.post(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/extract",
        {"extractionMode": "3d"},
        format="json",
    )

    assert response.status_code == 202
    assert response.json()["jobId"] == str(existing_job.id)
    assert DrawingMetadataExtractionJob.objects.filter(drawing=drawing, extraction_mode="3d").count() == 1


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
def test_registration_extract_queues_too_long_registered_path(sample_registration_payload):
    long_source_path = "C:\\" + "\\".join(["segment"] * 40) + "\\sample.icd"
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="sample.icd",
        source_path=long_source_path,
        source_format=sample_registration_payload["sourceFormat"],
    )
    client = APIClient()

    response = client.post(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/extract",
        {"extractionMode": "3d"},
        format="json",
    )

    assert response.status_code == 202
    assert response.json()["status"] == DrawingMetadataExtractionJob.STATUS_QUEUED
    assert DrawingMetadataExtractionJob.objects.count() == 1


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
def test_detail_limits_long_job_error_message_for_api(sample_registration_payload):
    long_error = "\n".join(
        [
            "error[0].type=System.Reflection.TargetInvocationException",
            "error[1].message=指定したファイルは図面ファイルではありません。",
            "A" * 1400,
            "TAIL_SHOULD_NOT_LEAK",
        ]
    )
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename="long-error.icd",
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_FAILED,
        extraction_profile="2d_all_views_layers_print_frame",
        error_message=long_error,
    )

    response = APIClient().get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")

    assert response.status_code == 200
    job_payload = response.json()["latestJobsByMode"]["2d"]
    assert job_payload["errorMessageSummary"] == "ICD拡張子ですが、ICAD/SXNETが図面モデルとして開けていません。"
    assert job_payload["errorMessageLength"] == len(long_error)
    assert job_payload["errorMessageTruncated"] is True
    assert len(job_payload["errorMessage"]) < len(long_error)
    assert "TAIL_SHOULD_NOT_LEAK" not in job_payload["errorMessage"]
    assert "全文はworkerログまたは診断スクリプトで確認してください" in job_payload["errorMessage"]


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
            "material": "SUS304",
            "revision_note_candidates": [
                {
                    "value": "A 寸法変更",
                    "confidence": "medium",
                    "inside_print_area": True,
                }
            ],
        },
        derived_tags_json=[
            {
                "tag": "材質:SUS304",
                "manual_flag": True,
                "source": "manual_override",
                "evidence": "test",
                "confidence": "high",
                "reason": "テスト",
            },
            {
                "tag": "材質:SUS304",
                "manual_flag": True,
                "source": "manual_override",
                "evidence": "test",
                "confidence": "high",
                "reason": "テスト",
            },
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
    assert bootstrap["metadata"]["owner"] is None
    assert bootstrap["metadata"]["tags"] == ["材質:SUS304", "装置:ロボット"]
    assert bootstrap["metadata"]["tagAttributes"]["schemaVersion"] == "viewer_tag_attributes.v1"
    assert bootstrap["metadata"]["tagAttributes"]["reviewRequired"] is True
    assert bootstrap["metadata"]["extractionDiagnostics"]["status"] == "partial"
    assert bootstrap["metadata"]["extractionDiagnostics"]["missingModes"] == ["3d"]
    knowledge_detail = bootstrap["metadata"]["knowledgeDetail"]
    assert knowledge_detail["schemaVersion"] == "viewer_knowledge_detail.v1"
    assert {"label": "材質", "value": "SUS304"} in knowledge_detail["attributes"]
    assert knowledge_detail["revisionHistory"][0]["summary"] == "A 寸法変更"
    assert knowledge_detail["revisionHistory"][0]["status"] == "印刷枠内 / 信頼度:medium"
    assert knowledge_detail["relatedTabs"]
    assert knowledge_detail["changeHistory"][0]["summary"] == "2D snapshotを更新"
    assert knowledge_detail["tagAttributeTargets"]
    assert knowledge_detail["tagAttributeReviewRequired"] is True
    target_by_key = {
        target["targetKey"]: target
        for target in bootstrap["metadata"]["tagAttributes"]["targets"]
    }
    assert target_by_key["drawing"]["tags"] == ["材質:SUS304", "装置:ロボット"]
    assert target_by_key["drawing"]["tagEvidence"][0] == {
        "tag": "材質:SUS304",
        "source": "manual_override",
        "evidence": "test",
        "confidence": "high",
        "reason": "テスト",
        "manualFlag": True,
        "tagRuleVersion": None,
    }
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
    assert "材質要確認:ZZZ" not in payload["rankingSignals"]["tags"]
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
