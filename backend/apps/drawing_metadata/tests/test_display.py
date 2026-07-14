import json
from pathlib import Path

import pytest

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.display import (
    build_2d_snapshot_display,
    build_3d_snapshot_display,
    build_composed_display_payload,
    build_tag_review_display_payload,
)
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
        }
    )

    row_by_key = {row["key"]: row["displayValue"] for row in payload["summaryRows"]}
    assert payload["title"] == "統合結果（viewer/RAG 用の統合属性）"
    assert payload["hiddenKeys"] == ["text_tokens", "spec_tokens", "part_keywords"]
    assert row_by_key["customer_name"] == "コマツ小山"
    assert row_by_key["part_count"] == "2"
    assert payload["tags"] == ["客先:コマツ小山"]
    assert payload["conflicts"][0]["chosenMode"] == "3d"


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
        },
    )

    assert payload["partExInfoTotal"] == 1
    assert payload["partExInfoSamples"][0]["path"] == "TR1D9K990271"
    assert payload["partExInfoSamples"][0]["fields"][0] == {"key": "User_WBZAI1", "value": "ＲＭ"}


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
            ],
            "conflicts": [],
        },
        snapshots_by_mode={},
    )

    assert payload["title"] == "タグ候補レビュー"
    assert payload["groups"][0]["tags"][0]["targetCandidates"] == ["プロジェクト", "製品・装置・ユニット", "図面"]
    assert payload["groups"][0]["tags"][2]["targetCandidates"] == ["部品", "図面", "製品・装置・ユニット"]
    assert payload["evidenceRows"][5]["displayValue"] == "1"


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
                }
            ],
        },
        canonical_attributes={
            "source_file_name": "sample.icd",
            "source_file_stem": "sample",
            "source_extension": ".icd",
            "source_directory_path": r"J:\SAMPLE",
            "source_full_path": r"J:\SAMPLE\sample.icd",
        },
    )

    row_by_key = {row["key"]: row["displayValue"] for row in payload["summaryRows"]}
    assert row_by_key["view_sheet_count"] == "1"
    assert row_by_key["print_frame_count"] == "1"
    assert row_by_key["layer_tagged_count"] == "3"
    assert payload["sourceFileRows"][0]["displayValue"] == "sample.icd"
    assert payload["viewSheets"][0]["name"] == "!XY"
    assert payload["printFrames"][0]["size"] == "A3"
    assert payload["layers"][0]["name"] == "図枠"
    assert payload["textSamples"][0]["text"] == "材質 SUS304"
    assert payload["textSamples"][0]["position"] == "12.5, 34.0"
    assert payload["textSamples"][0]["insidePrintArea"] == "inside"
    assert payload["dimensionSamples"][0]["value"] == "100"
    assert payload["dimensionSamples"][0]["insidePrintArea"] == "outside"
    assert payload["geometryPrimitiveSamples"][0]["geometryType"] == "SxGeomSpline2D"
    assert payload["geometryPrimitiveSamples"][0]["position"] == "1.0, 2.0"
    assert payload["geometryPrimitiveSamples"][0]["insidePrintArea"] == "inside"


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
    assert response.context["snapshot_2d_display"]["summaryRows"][4]["displayValue"] == "1"
    assert response.context["snapshot_3d_display"]["partCount"] == 2
    assert response.context["snapshot_3d_display"]["partExInfoTotal"] == 1
    assert "統合結果（viewer/RAG 用の統合属性）" in response.content.decode("utf-8")


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
