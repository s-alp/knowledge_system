import json
from pathlib import Path

import pytest

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.display import (
    build_2d_snapshot_display,
    build_3d_snapshot_display,
    build_composed_display_payload,
    build_integration_handoff_display_payload,
    build_tag_review_display_payload,
)
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview
from apps.drawing_metadata.services.normalization import normalize_raw_extract


REPO_ROOT = Path(__file__).resolve().parents[4]
CASSETTE_SAMPLE_PATH = REPO_ROOT / "output" / "live_extracts" / "9NK452RS60-03-CASSETTE-A0-3D-01.json"


def test_build_composed_display_payload_hides_noisy_keys():
    payload = build_composed_display_payload(
        {
            "canonicalAttributes": {
                "customer_name": "コマツ小山",
                "equipment_category": "ガントリー",
                "source_format": "icad",
                "extraction_status": "success",
                "confidence_summary": "high",
                "top_part_name": "TOP-PART",
                "part_names": ["A", "B"],
                "external_part_exists": True,
                "mirror_part_exists": False,
                "unresolved_part_exists": False,
                "text_tokens": ["token-a"],
                "spec_tokens": ["SES"],
                "part_keywords": ["keyword-a"],
            },
            "derivedTags": [{"tag": "客先:コマツ小山"}],
            "conflicts": [
                {
                    "attribute": "customer_name",
                    "mode2dValue": "澁谷工業",
                    "mode3dValue": "コマツ小山",
                    "chosenMode": "3d",
                }
            ],
            "reconciledAttributes": [
                {
                    "attribute": "customer_name",
                    "value2d": "澁谷工業",
                    "value3d": "コマツ小山",
                    "chosenValue": "コマツ小山",
                    "chosenMode": "3d",
                    "status": "conflict",
                    "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。",
                },
                {
                    "attribute": "part_names",
                    "value2d": [],
                    "value3d": ["A", "B"],
                    "chosenValue": ["A", "B"],
                    "chosenMode": "3d",
                    "status": "only_3d",
                    "reason": "3D抽出にのみ配列値があるため採用しました。",
                },
            ],
        }
    )

    row_by_key = {row["key"]: row["displayValue"] for row in payload["summaryRows"]}
    assert payload["title"] == "統合結果（viewer/RAG 用の統合属性）"
    assert payload["hiddenKeys"] == ["text_tokens", "spec_tokens", "part_keywords"]
    assert row_by_key["customer_name"] == "コマツ小山"
    assert row_by_key["part_count"] == "2"
    assert payload["tags"] == ["客先:コマツ小山"]
    assert payload["conflicts"][0]["chosenMode"] == "3d"
    assert payload["reconciliationReviewRows"][0]["statusLabel"] == "競合"
    assert payload["reconciliationReviewRows"][0]["chosenValueDisplay"] == "コマツ小山"
    assert payload["reconciliationReviewRows"][1]["value3dDisplay"] == "2"


def test_build_3d_snapshot_display_shows_multiple_paths_for_cassette_sample():
    sample = json.loads(CASSETTE_SAMPLE_PATH.read_text(encoding="utf-8"))
    canonical = normalize_raw_extract(sample)

    payload = build_3d_snapshot_display(
        raw_extract=sample["raw_extract"],
        canonical_attributes=canonical,
    )

    assert payload["topPartName"] == "9NK452RS60-03-CASSETTE-A0-3D-01"
    assert payload["partCount"] > 5
    assert payload["partTreePathTotal"] > 5
    assert any("Fr_Bポート_アンクランプ+リフタUP" in value for value in payload["partTreePaths"])


def test_build_3d_snapshot_display_summarizes_part_ex_info_fields():
    payload = build_3d_snapshot_display(
        raw_extract={
            "mass_probe_status": "available",
            "mass_properties": {
                "element_count": 39,
                "unit_name": "mm-kg",
                "mass": 0.02220905,
                "weight": 0.2177964,
                "volume": 129916.95147963,
                "area": 1024.0,
                "density": 1.0,
                "center_of_gravity_x": 1.0,
                "center_of_gravity_y": 2.0,
                "center_of_gravity_z": 3.0,
            },
            "material_probe_status": "available",
            "materials": [
                {"matid": "SUS304", "name": "SUS304", "specific_gravity": 7.93, "element_count": 2},
            ],
            "parts": [
                {
                    "tree_path": ["TR1D9K990271"],
                    "name": "TR1D9K990271",
                    "comment": "アルミフレーム",
                    "ex_info_fields": {
                        "User_WBZAI1": "ＲＭ",
                        "User_WCMNA": "ＳＵＳ",
                    },
                }
            ]
        },
        canonical_attributes={
            "top_part_name": "TR1D9K990271",
            "part_names": ["TR1D9K990271"],
            "mass_probe_status": "available",
            "mass_unit_name": "mm-kg",
            "mass_element_count": 39,
            "mass_value": 0.02220905,
            "weight_value": 0.2177964,
            "volume_value": 129916.95147963,
            "area_value": 1024.0,
            "density_value": 1.0,
            "center_of_gravity": "1.0, 2.0, 3.0",
            "material_probe_status": "available",
            "material_ids": ["SUS304"],
            "material_names": ["SUS304"],
            "part_material_candidate_count": 2,
            "part_material_candidates": [
                {
                    "part_path": "TR1D9K990271",
                    "part_name": "TR1D9K990271",
                    "material_id": "SUS304",
                    "material_name": "SUS304",
                    "specific_gravity": 7.93,
                    "source": "3d_material_single_part",
                    "confidence": "high",
                    "reason": "単一パーツかつ3D材質一覧も単一のため、全体材質を当該パーツ候補として採用しました。",
                },
                {
                    "part_path": "TR1D9K990271",
                    "part_name": "TR1D9K990271",
                    "material_id": "SUS",
                    "material_name": "ＳＵＳ",
                    "specific_gravity": None,
                    "source": "part_ex_info_fields.User_WCMNA",
                    "confidence": "medium",
                    "reason": "パーツ付加情報の値が材質表記パターンに一致したため、部品材質候補として保持しました。",
                },
            ],
        },
    )

    assert payload["partExInfoTotal"] == 1
    assert payload["partExInfoSamples"][0]["path"] == "TR1D9K990271"
    assert payload["partExInfoSamples"][0]["fields"][0] == {"key": "User_WBZAI1", "value": "ＲＭ"}
    assert payload["hasMassProperties"] is True
    row_by_key = {row["key"]: row["displayValue"] for row in payload["massPropertyRows"]}
    assert row_by_key["mass_probe_status"] == "available"
    assert row_by_key["mass_unit_name"] == "mm-kg"
    assert row_by_key["mass_value"] == "0.02220905"
    assert row_by_key["center_of_gravity"] == "1.0, 2.0, 3.0"
    material_row_by_key = {row["key"]: row["displayValue"] for row in payload["materialRows"]}
    assert payload["hasMaterials"] is True
    assert material_row_by_key["material_probe_status"] == "available"
    assert material_row_by_key["material_1"] == "SUS304 / SUS304 / 7.93 / elements=2"
    assert payload["partMaterialCandidateTotal"] == 2
    assert payload["partMaterialCandidates"][0]["partPath"] == "TR1D9K990271"
    assert payload["partMaterialCandidates"][0]["material"] == "SUS304"
    assert payload["partMaterialCandidates"][1]["source"] == "part_ex_info_fields.User_WCMNA"


def test_build_tag_review_display_maps_tags_to_target_candidates():
    payload = build_tag_review_display_payload(
        composed_metadata={
            "canonicalAttributes": {
                "source_file_name": "sample.icd",
                "source_directory_path": r"J:\SAMPLE",
                "customer_name": "澁谷工業",
                "equipment_category": "ロボット",
                "part_ex_info_fields": {"TOP": {"User_WCMNA": "ＳＵＳ"}},
            },
            "derivedTags": [
                {"tag": "客先:澁谷工業", "source": "customer_name", "confidence": "high", "manual_flag": False, "tag_rule_version": "1.0.0"},
                {"tag": "装置:ロボット", "source": "equipment_category", "confidence": "high", "manual_flag": False, "tag_rule_version": "1.0.0"},
                {"tag": "メーカー:SMC", "source": "maker_keywords", "confidence": "medium", "manual_flag": False, "tag_rule_version": "1.0.0"},
                {"tag": "材質要確認:ZZZ", "source": "unresolved_material_keywords", "confidence": "low", "manual_flag": False, "tag_rule_version": "1.0.0"},
            ],
            "conflicts": [],
        },
        snapshots_by_mode={},
    )

    assert payload["title"] == "タグ候補レビュー"
    assert payload["groups"][0]["tags"][0]["targetCandidates"] == ["プロジェクト", "製品・装置・ユニット", "図面"]
    assert payload["groups"][0]["tags"][2]["targetCandidates"] == ["部品", "図面", "製品・装置・ユニット"]
    assert payload["groups"][0]["tags"][3]["targetCandidates"] == ["部品", "図面"]
    assert payload["evidenceRows"][5]["displayValue"] == "1"


def test_build_integration_handoff_display_payload_summarizes_viewer_and_rag_contracts():
    payload = build_integration_handoff_display_payload(
        viewer_bootstrap={
            "title": "BRACKET",
            "defaultMode": "2d",
            "availability": {"has2d": True, "has3d": True},
            "metadata": {
                "drawingNumber": "9NK-001",
                "drawingName": "BRACKET",
                "paperSize": "A3",
                "owner": "設計者A",
                "tags": ["客先:澁谷工業", "材質:SUS304"],
            },
        },
        rag_payload={
            "schemaVersion": "drawing_metadata_rag_payload.v1",
            "preFilters": {
                "customerName": "澁谷工業",
                "equipmentCategory": "ロボット",
                "sourceFormat": "icad",
                "drawingNumber": "9NK-001",
                "drawingName": "BRACKET",
                "paperSize": "A3",
            },
            "rankingSignals": {
                "partNames": ["BRACKET", "PLATE"],
                "materialKeywords": ["SUS304"],
                "tags": ["客先:澁谷工業", "材質:SUS304"],
            },
            "partMaterialCandidates": [{"part_name": "BRACKET"}],
            "searchTextChunks": ["BRACKET", "SUS304"],
            "reconciliation": {
                "requiresReview": True,
                "conflicts": [{"attribute": "material"}],
                "reviewFlags": [{"code": "cross_source_conflict", "severity": "medium", "attribute": "material"}],
            },
        },
        knowledge_payload_preview={
            "schemaVersion": "knowledge_system_payload_preview.v1",
            "targets": [
                {
                    "targetKey": "drawing",
                    "label": "図面",
                    "existingReception": "図面詳細にタグと属性情報が表示される。",
                    "tagApiStatus": "candidate_existing",
                    "tags": ["客先:澁谷工業", "材質:SUS304"],
                    "attributes": [
                        {
                            "attributeName": "材質",
                            "payloadShape": {
                                "attribute": None,
                                "attribute_option": None,
                                "attribute_value": "SUS304",
                            },
                        }
                    ],
                    "attributePayloadKeys": ["attribute", "attribute_option", "attribute_value"],
                    "candidateEndpoint": "/drawings/{drawingInternalId}/",
                    "reviewRequired": True,
                }
            ],
        },
        api_links={
            "detail_api": "http://testserver/api/v1/drawing-metadata/registrations/1/",
            "rag_payload_api": "http://testserver/api/v1/drawing-metadata/registrations/1/rag-payload/",
            "tag_review_page": "http://testserver/drawing-metadata/1/tags/",
        },
    )

    viewer_row_by_key = {row["key"]: row["displayValue"] for row in payload["viewerRows"]}
    filter_row_by_key = {row["key"]: row["displayValue"] for row in payload["ragFilterRows"]}
    review_row_by_key = {row["key"]: row["displayValue"] for row in payload["ragReviewRows"]}
    signal_row_by_key = {row["key"]: row for row in payload["ragSignalRows"]}

    assert payload["title"] == "創屋連携・viewer/RAG 受け渡し確認"
    assert payload["apiLinks"][0]["label"] == "詳細API"
    assert viewer_row_by_key["has2d"] == "あり"
    assert viewer_row_by_key["has3d"] == "あり"
    assert viewer_row_by_key["tags"] == "客先:澁谷工業, 材質:SUS304"
    assert filter_row_by_key["customerName"] == "澁谷工業"
    assert signal_row_by_key["partNames"]["count"] == 2
    assert signal_row_by_key["materialKeywords"]["displayValue"] == "SUS304"
    assert review_row_by_key["requiresReview"] == "あり"
    assert review_row_by_key["conflictCount"] == "1"
    assert payload["knowledgePayloadSchemaVersion"] == "knowledge_system_payload_preview.v1"
    assert payload["knowledgePayloadTargetRows"][0]["label"] == "図面"
    assert payload["knowledgePayloadTargetRows"][0]["attributeCount"] == 1
    assert payload["knowledgePayloadTargetRows"][0]["payloadKeys"] == "attribute, attribute_option, attribute_value"


@pytest.mark.django_db
def test_build_knowledge_system_payload_preview_maps_targets_without_production_write():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="host-001",
        filename="sample.icd",
        source_path=r"J:\SAMPLE\sample.icd",
        source_format="icad",
    )

    payload = build_knowledge_system_payload_preview(
        drawing=drawing,
        composed_metadata={
            "canonicalAttributes": {
                "customer_name": "澁谷工業",
                "equipment_category": "ロボット",
                "drawing_number": "9NK-001",
                "drawing_name": "BRACKET",
                "paper_size": "A3",
                "title_block_fields": {
                    "material": "SUS304",
                    "surface_treatment": "黒染め",
                    "coating_instruction": "マンセル 5Y7/1",
                    "scale": "1:2",
                    "prfx": "RAA4844",
                    "unit_number": "U01",
                },
                "part_names": ["BRACKET"],
                "material_keywords": ["SUS304"],
                "part_material_candidates": [
                    {
                        "part_path": "TOP > BRACKET",
                        "part_name": "BRACKET",
                        "material_id": "SUS304",
                    }
                ],
            },
            "derivedTags": [
                {"tag": "客先:澁谷工業"},
                {"tag": "装置:ロボット"},
                {"tag": "材質:SUS304"},
                {"tag": "PRFX:RAA4844"},
                {"tag": "ユニット:U01"},
            ],
        },
    )

    targets = {target["targetKey"]: target for target in payload["targets"]}
    assert payload["schemaVersion"] == "knowledge_system_payload_preview.v1"
    assert payload["contractEvidence"]["productionWritePolicy"].startswith("本番ナレッジシステムへ登録")
    assert targets["drawing"]["writePolicy"] == "preview_only_no_production_write"
    assert targets["drawing"]["payloadPreview"]["tags"] == [
        "客先:澁谷工業",
        "装置:ロボット",
        "材質:SUS304",
        "PRFX:RAA4844",
        "ユニット:U01",
    ]
    assert any(item["attributeName"] == "材質" and item["attributeValue"] == "SUS304" for item in targets["drawing"]["attributes"])
    assert targets["product"]["tagApiStatus"] == "not_found_use_attribute_fallback"
    assert any(item["attributeName"] == "自動タグ候補" and item["attributeValue"] == "PRFX:RAA4844" for item in targets["product"]["attributes"])
    assert any(item.get("entityHint") == "TOP > BRACKET" for item in targets["part"]["attributes"])
    assert targets["part"]["attributes"][-1]["bindingStatus"] == "needs_attribute_master_binding"
    assert targets["project"]["candidateEndpoint"] is None


def test_build_2d_snapshot_display_summarizes_views_frames_layers_and_samples():
    payload = build_2d_snapshot_display(
        raw_extract={
            "_source_file": {
                "file_name": "sample.icd",
                "file_name_without_extension": "sample",
                "extension": ".icd",
                "directory_path": r"J:\SAMPLE",
                "full_path": r"J:\SAMPLE\sample.icd",
            },
            "view_sheets": [{"name": "!XY", "geometry_count": 10, "scale": 1.0, "comment": ""}],
            "print_frames": [
                {
                    "no": 1,
                    "size": "A3",
                    "drawing_scale": 1.0,
                    "range_min_x": 0,
                    "range_min_y": 0,
                    "range_max_x": 420,
                    "range_max_y": 297,
                }
            ],
            "layers": [{"no": 1, "name": "図枠", "is_displayed": True, "is_searchable": True}],
            "texts": [
                {
                    "view_name": "!XY",
                    "layer_no": 1,
                    "position_x": 12.5,
                    "position_y": 34.0,
                    "inside_print_area": True,
                    "joined_text": "材質 SUS304",
                    "text_lines": ["材質 SUS304"],
                }
            ],
            "dimensions": [
                {
                    "view_name": "!XY",
                    "layer_no": 1,
                    "position_x": 450.0,
                    "position_y": 34.0,
                    "inside_print_area": False,
                    "value_1": "100",
                }
            ],
            "geometry_primitives": [
                {
                    "view_name": "!XY",
                    "layer_no": 1,
                    "geometry_type": "SxGeomSpline2D",
                    "position_x": 1.0,
                    "position_y": 2.0,
                    "inside_print_area": True,
                    "summary": "spline",
                },
                {
                    "view_name": "!DETAIL",
                    "layer_no": None,
                    "geometry_type": "SxGeomLine2D",
                    "inside_print_area": None,
                    "summary": "unknown layer",
                }
            ],
        },
        canonical_attributes={
            "source_file_name": "sample.icd",
            "source_file_stem": "sample",
            "source_extension": ".icd",
            "source_directory_path": r"J:\SAMPLE",
            "source_full_path": r"J:\SAMPLE\sample.icd",
            "title_block_candidates": [
                {
                    "field": "material",
                    "label": "材質",
                    "value": "SUS304",
                    "confidence": "medium",
                    "view_name": "!XY",
                    "layer_no": 1,
                    "position_x": 12.5,
                    "position_y": 34.0,
                    "inside_print_area": True,
                    "evidence_text": "材質 SUS304",
                }
            ],
            "revision_note_candidates": [
                {
                    "value": "A 寸法変更",
                    "evidence_text": "訂正内容 A 寸法変更",
                    "matched_keywords": ["訂正内容", "変更"],
                    "confidence": "medium",
                    "view_name": "!XY",
                    "layer_no": 1,
                    "position_x": 20.0,
                    "position_y": 40.0,
                    "inside_print_area": True,
                }
            ],
            "revision_note_count": 1,
            "geometry_feature_candidates": [
                {
                    "feature": "surface_roughness",
                    "label": "表面粗さ",
                    "tag": "加工指示:表面粗さ",
                    "confidence": "medium",
                    "geometry_type": "SxGeomSmark",
                    "count": 2,
                    "sample_summaries": ["roughness-a", "roughness-b"],
                }
            ],
            "surface_roughness_count": 2,
            "surface_roughness_values": ["Ra 6.3"],
            "section_feature_count": 1,
            "slot_candidate_count": 1,
            "hole_candidate_count": 3,
            "hole_candidate_diameters": [6.0, 8.0],
            "slot_candidate_dimensions": [{"major_diameter": 22.0, "minor_diameter": 8.0}],
        },
    )

    row_by_key = {row["key"]: row["displayValue"] for row in payload["summaryRows"]}
    assert row_by_key["view_sheet_count"] == "1"
    assert row_by_key["view_with_item_count"] == "2"
    assert row_by_key["view_without_item_count"] == "0"
    assert row_by_key["print_frame_count"] == "1"
    assert row_by_key["layer_tagged_count"] == "3"
    assert row_by_key["inside_print_area_count"] == "2"
    assert row_by_key["outside_print_area_count"] == "1"
    assert row_by_key["unknown_print_area_count"] == "1"
    assert row_by_key["revision_note_count"] == "1"
    assert payload["sourceFileRows"][0]["displayValue"] == "sample.icd"
    view_coverage_by_name = {row["viewName"]: row for row in payload["viewCoverageRows"]}
    assert view_coverage_by_name["!XY"]["textCount"] == 1
    assert view_coverage_by_name["!XY"]["dimensionCount"] == 1
    assert view_coverage_by_name["!XY"]["geometryCount"] == 1
    assert view_coverage_by_name["!XY"]["outsideCount"] == 1
    assert view_coverage_by_name["!DETAIL"]["unknownPrintAreaCount"] == 1
    layer_coverage_by_no = {row["layerNo"]: row for row in payload["layerCoverageRows"]}
    assert layer_coverage_by_no["1"]["textCount"] == 1
    assert layer_coverage_by_no["1"]["dimensionCount"] == 1
    assert layer_coverage_by_no["未抽出"]["geometryCount"] == 1
    assert payload["viewSheets"][0]["name"] == "!XY"
    assert payload["printFrames"][0]["size"] == "A3"
    assert payload["layers"][0]["name"] == "図枠"
    assert payload["textSamples"][0]["text"] == "材質 SUS304"
    assert payload["textSamples"][0]["position"] == "12.5, 34.0"
    assert payload["textSamples"][0]["insidePrintArea"] == "inside"
    assert payload["titleBlockCandidates"][0]["field"] == "材質"
    assert payload["titleBlockCandidates"][0]["value"] == "SUS304"
    assert payload["titleBlockCandidates"][0]["evidenceText"] == "材質 SUS304"
    assert payload["revisionNoteCandidates"][0]["value"] == "A 寸法変更"
    assert payload["revisionNoteCandidates"][0]["matchedKeywords"] == "訂正内容, 変更"
    assert payload["revisionNoteCandidates"][0]["insidePrintArea"] == "inside"
    assert payload["dimensionSamples"][0]["value"] == "100"
    assert payload["dimensionSamples"][0]["insidePrintArea"] == "outside"
    assert payload["geometryPrimitiveSamples"][0]["geometryType"] == "SxGeomSpline2D"
    assert payload["geometryPrimitiveSamples"][0]["position"] == "1.0, 2.0"
    assert payload["geometryPrimitiveSamples"][0]["insidePrintArea"] == "inside"
    assert payload["geometryFeatureCandidates"][0]["label"] == "表面粗さ"
    assert payload["geometryFeatureCandidates"][0]["tag"] == "加工指示:表面粗さ"
    assert payload["geometryFeatureCandidates"][0]["count"] == "2"
    assert row_by_key["surface_roughness_count"] == "2"
    assert row_by_key["section_feature_count"] == "1"
    assert row_by_key["slot_candidate_count"] == "1"
    assert row_by_key["hole_candidate_count"] == "3"
    geometry_attribute_by_key = {row["key"]: row["displayValue"] for row in payload["geometryAttributeRows"]}
    assert geometry_attribute_by_key["surface_roughness_values"] == "Ra 6.3"
    assert geometry_attribute_by_key["hole_candidate_diameters"] == "6.0, 8.0"
    assert geometry_attribute_by_key["slot_candidate_dimensions"] == "1"


@pytest.mark.django_db
def test_detail_page_context_contains_display_summaries(client, sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        raw_extract_json={"texts": [{"text_lines": ["token-a"]}]},
        canonical_attributes_json={
            "source_file_name": sample_registration_payload["filename"],
            "source_file_stem": "sample",
            "source_extension": ".icd",
            "source_directory_path": r"J:\SAMPLE",
            "source_full_path": sample_registration_payload["sourcePath"],
            "text_tokens": ["token-a"],
            "spec_tokens": ["SES"],
            "customer_name": "コマツ小山",
            "source_format": "icad",
            "extraction_status": "success",
            "confidence_summary": "medium",
        },
        derived_tags_json=[],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "parts": [
                {"tree_path": ["TOP"], "ex_info_fields": {"User_WBZAI1": "RM", "User_WCMNA": "ＳＵＳ"}},
                {"tree_path": ["TOP", "CHILD-A"]},
            ]
        },
        canonical_attributes_json={
            "source_file_name": sample_registration_payload["filename"],
            "source_file_stem": "sample",
            "source_extension": ".icd",
            "source_directory_path": r"J:\SAMPLE",
            "source_full_path": sample_registration_payload["sourcePath"],
            "customer_name": "コマツ小山",
            "equipment_category": "ガントリー",
            "source_format": "icad",
            "extraction_status": "success",
            "confidence_summary": "high",
            "top_part_name": "TOP",
            "part_names": ["TOP", "CHILD-A"],
            "part_tree_paths": ["TOP", "TOP > CHILD-A"],
            "part_keywords": ["TOP", "CHILD-A"],
            "external_part_exists": False,
            "mirror_part_exists": False,
            "unresolved_part_exists": False,
        },
        derived_tags_json=[],
    )

    response = client.get(f"/drawing-metadata/{drawing.id}/")

    assert response.status_code == 200
    assert response.context["composed_display"]["hiddenKeys"] == ["text_tokens", "spec_tokens", "part_keywords"]
    snapshot_2d_summary = {row["key"]: row["displayValue"] for row in response.context["snapshot_2d_display"]["summaryRows"]}
    assert snapshot_2d_summary["text_count"] == "1"
    assert response.context["snapshot_3d_display"]["partCount"] == 2
    assert response.context["snapshot_3d_display"]["partExInfoTotal"] == 1
    assert response.context["handoff_display"]["apiLinks"][0]["label"] == "詳細API"
    assert response.context["handoff_display"]["ragReviewRows"][0]["displayValue"] == "drawing_metadata_rag_payload.v1"
    assert "統合結果（viewer/RAG 用の統合属性）" in response.content.decode("utf-8")
    assert "創屋連携・viewer/RAG 受け渡し確認" in response.content.decode("utf-8")
    assert "RAG ランキング信号" in response.content.decode("utf-8")
    assert "本番タグ・属性 payload プレビュー" in response.content.decode("utf-8")
    assert response.context["handoff_display"]["knowledgePayloadTargetRows"][0]["label"] == "図面"
    assert response.context["handoff_display"]["knowledgePayloadTargetRows"][0]["reviewRequired"] == "あり"
    assert "2D/3D 照合結果" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_tag_review_page_renders_composed_tag_candidates(client, sample_registration_payload):
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id=sample_registration_payload["hostDrawingId"],
        filename=sample_registration_payload["filename"],
        source_path=sample_registration_payload["sourcePath"],
        source_format=sample_registration_payload["sourceFormat"],
    )
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={},
        canonical_attributes_json={
            "customer_name": "澁谷工業",
            "equipment_category": "ロボット",
            "source_file_name": sample_registration_payload["filename"],
            "source_directory_path": r"J:\SAMPLE",
            "source_format": "icad",
            "extraction_status": "success",
            "confidence_summary": "high",
            "part_names": [],
            "part_keywords": ["澁谷工業", "ロボット"],
        },
        derived_tags_json=[],
    )

    response = client.get(f"/drawing-metadata/{drawing.id}/tags/")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "タグ候補レビュー" in content
    assert "客先:澁谷工業" in content
    assert "プロジェクト, 製品・装置・ユニット, 図面" in content
