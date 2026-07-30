"""廃止済み外部AIメタデータが現行処理へ再露出しないことを検証する。

既存DBに残る履歴値は削除せず、API、Django内部画面、2D/3D合成、再正規化時の
手動補正適用からだけ除外する。失敗した場合は、読取境界のフィルター漏れまたは
旧AI互換キーを再び参照する実装が追加されていないかを確認する。
"""

from __future__ import annotations

import json

import pytest
from rest_framework.test import APIClient

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.display import build_2d_snapshot_display
from apps.drawing_metadata.services.overrides import apply_attribute_overrides
from apps.drawing_metadata.services.retired_ai_metadata import (
    filter_retired_ai_warnings,
    strip_retired_ai_metadata,
)


def _serialized_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_retired_ai_filter_keeps_source_history_unchanged():
    source = {
        "drawing_name": "BRACKET",
        "title_block_llm_candidate_count": 1,
        "title_block_candidates": [
            {
                "field": "material",
                "value": "SUS304",
                "confidence": "medium",
                "llm_field": "material",
                "llm_confidence": "high",
            }
        ],
    }

    filtered = strip_retired_ai_metadata(source)

    assert "title_block_llm_candidate_count" not in filtered
    assert "llm_field" not in filtered["title_block_candidates"][0]
    assert source["title_block_llm_candidate_count"] == 1
    assert source["title_block_candidates"][0]["llm_field"] == "material"


def test_retired_ai_warning_filter_hides_only_retired_warning():
    warnings = [
        {
            "code": "title_block_llm_skipped_unusable_values",
            "message": "廃止前の分類warning",
        },
        {
            "code": "geometry_layer_count_mismatch",
            "message": "現行の抽出warning",
        },
    ]

    assert filter_retired_ai_warnings(warnings) == [warnings[1]]
    assert len(warnings) == 2


def test_old_manual_ai_metadata_is_not_reapplied_to_current_canonical():
    manual_overrides = {
        "canonicalAttributes": {
            "drawing_name": {"value": "手動名称"},
            "llm_field": {"value": "material"},
        }
    }

    applied = apply_attribute_overrides({"drawing_name": "自動名称"}, manual_overrides)

    assert applied == {"drawing_name": "手動名称"}
    assert manual_overrides["canonicalAttributes"]["llm_field"]["value"] == "material"


@pytest.mark.django_db
def test_current_api_and_internal_ui_hide_retired_ai_history_without_updating_db():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="retired-ai-history",
        filename="retired-ai-history.icd",
        source_path=r"C:\temp\retired-ai-history.icd",
        source_format="icad",
    )
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        status=DrawingMetadataExtractionJob.STATUS_SUCCEEDED,
        warnings_json=[
            {
                "code": "title_block_llm_skipped_unusable_values",
                "message": "廃止前の分類warning",
            },
            {
                "code": "geometry_layer_count_mismatch",
                "message": "現行の抽出warning",
            },
        ],
        diagnostics_json={"llm_field": "material", "currentStatus": "ok"},
    )
    snapshot = DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        latest_job=job,
        raw_extract_json={
            "title_block_candidates": [
                {"value": "SUS304", "llm_field": "material"}
            ]
        },
        canonical_attributes_json={
            "drawing_name": "BRACKET",
            "title_block_llm_candidate_count": 1,
            "title_block_candidates": [
                {
                    "field": "material",
                    "label": "材質",
                    "value": "SUS304",
                    "confidence": "medium",
                    "llm_field": "material",
                    "llm_confidence": "high",
                    "llm_reason": "廃止前の分類結果",
                }
            ],
        },
        manual_overrides_json={
            "canonicalAttributes": {"llm_field": {"value": "material"}}
        },
        derived_tags_json=[
            {"tag": "材質:SUS304", "source": "title_block", "llm_source": "gemini"}
        ],
    )

    composed = compose_drawing_metadata(drawing)
    client = APIClient()
    detail_response = client.get(f"/api/v1/drawing-metadata/registrations/{drawing.id}")
    job_response = client.get(f"/api/v1/drawing-metadata/jobs/{job.id}")
    internal_response = client.get(f"/internal/drawing-metadata/{drawing.id}/")
    job_page_response = client.get(f"/internal/drawing-metadata/jobs/{job.id}/")

    assert detail_response.status_code == 200
    assert job_response.status_code == 200
    assert internal_response.status_code == 200
    assert job_page_response.status_code == 200
    assert "llm_" not in _serialized_text(composed)
    assert "title_block_llm_" not in _serialized_text(detail_response.json())
    assert "llm_" not in _serialized_text(detail_response.json())
    assert job_response.json()["warnings"] == [
        {
            "code": "geometry_layer_count_mismatch",
            "message": "現行の抽出warning",
        }
    ]
    assert "AI分類" not in internal_response.content.decode("utf-8")
    assert "廃止前の分類warning" not in job_page_response.content.decode("utf-8")
    assert "現行の抽出warning" in job_page_response.content.decode("utf-8")

    snapshot.refresh_from_db()
    job.refresh_from_db()
    assert snapshot.canonical_attributes_json["title_block_llm_candidate_count"] == 1
    assert snapshot.canonical_attributes_json["title_block_candidates"][0]["llm_field"] == "material"
    assert snapshot.manual_overrides_json["canonicalAttributes"]["llm_field"]["value"] == "material"
    assert job.warnings_json[0]["code"] == "title_block_llm_skipped_unusable_values"


@pytest.mark.django_db
def test_manual_override_api_rejects_retired_ai_fields():
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="retired-ai-input",
        filename="retired-ai-input.icd",
        source_path=r"C:\temp\retired-ai-input.icd",
        source_format="icad",
    )
    snapshot = DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="2d",
        canonical_attributes_json={"drawing_name": "BRACKET"},
    )

    response = APIClient().patch(
        f"/api/v1/drawing-metadata/registrations/{drawing.id}/overrides",
        {
            "extractionMode": "2d",
            "canonicalAttributes": {"llm_field": {"value": "material"}},
        },
        format="json",
    )

    assert response.status_code == 400
    snapshot.refresh_from_db()
    assert snapshot.manual_overrides_json == {}


def test_2d_display_does_not_create_retired_ai_columns():
    display = build_2d_snapshot_display(
        raw_extract={},
        canonical_attributes={
            "title_block_candidates": [
                {
                    "field": "material",
                    "value": "SUS304",
                    "confidence": "medium",
                    "llm_field": "material",
                    "llm_confidence": "high",
                    "llm_reason": "廃止前の分類結果",
                }
            ]
        },
    )

    candidate = display["titleBlockCandidates"][0]
    assert candidate["field"] == "material"
    assert candidate["value"] == "SUS304"
    assert candidate["confidence"] == "medium"
    assert not any(key.casefold().startswith("llm") for key in candidate)
