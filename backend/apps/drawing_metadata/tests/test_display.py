import json
from pathlib import Path

import pytest

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.display import build_3d_snapshot_display, build_composed_display_payload
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
                {"tree_path": ["TOP"]},
                {"tree_path": ["TOP", "CHILD-A"]},
            ]
        },
        canonical_attributes_json={
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
    assert response.context["snapshot_3d_display"]["partCount"] == 2
    assert "統合結果（viewer/RAG 用の統合属性）" in response.content.decode("utf-8")
