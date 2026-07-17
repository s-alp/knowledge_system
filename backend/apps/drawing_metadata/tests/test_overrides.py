import pytest

from apps.drawing_metadata.models import (
    DrawingComposedMetadata,
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.overrides import merge_manual_overrides
from apps.drawing_metadata.services.persistence import apply_manual_overrides, save_extraction_snapshot


RAW_3D = {
    "top_part": {"name": "KO小山ガントリー", "comment": None, "ex_info": "コマツ小山"},
    "parts": [],
}


def _make_drawing(**kwargs) -> RegisteredDrawing:
    defaults = {
        "host_drawing_id": "sample-overrides",
        "filename": "overrides.icd",
        "source_path": r"C:\temp\overrides.icd",
        "source_format": "icad",
    }
    defaults.update(kwargs)
    return RegisteredDrawing.objects.create(**defaults)


def _run_extraction(drawing: RegisteredDrawing) -> DrawingMetadataSnapshot:
    job = DrawingMetadataExtractionJob.objects.create(drawing=drawing, extraction_mode="3d", status="processing")
    canonical = normalize_raw_extract({"source_format": "icad", "source_kind": "3d", "raw_extract": RAW_3D})
    return save_extraction_snapshot(
        drawing=drawing,
        extraction_mode="3d",
        job=job,
        raw_extract=RAW_3D,
        canonical_attributes=canonical,
        executed_by="test",
    )


def test_merge_manual_overrides_is_per_key():
    first = merge_manual_overrides({}, {"canonicalAttributes": {"customer_name": {"value": "コマツ小山"}}})
    second = merge_manual_overrides(first, {"canonicalAttributes": {"equipment_category": {"value": "ガントリー"}}})

    # 2回目の補正で1回目の補正記録が消えない(旧実装ではマップ全体が置換されていた)
    assert second["canonicalAttributes"]["customer_name"] == {"value": "コマツ小山"}
    assert second["canonicalAttributes"]["equipment_category"] == {"value": "ガントリー"}

    # null 指定で補正解除できる
    third = merge_manual_overrides(second, {"canonicalAttributes": {"customer_name": None}})
    assert "customer_name" not in third["canonicalAttributes"]


def test_merge_manual_overrides_tag_add_remove_cancels_out():
    state = merge_manual_overrides({}, {"derivedTags": {"added": ["手動:A"], "removed": ["装置:ロボット"]}})
    state = merge_manual_overrides(state, {"derivedTags": {"removed": ["手動:A"]}})
    state = merge_manual_overrides(state, {"derivedTags": {"added": ["装置:ロボット"]}})

    assert state["derivedTags"]["added"] == ["装置:ロボット"]
    assert state["derivedTags"]["removed"] == ["手動:A"]


@pytest.mark.django_db
def test_manual_tags_and_removals_survive_re_extraction():
    drawing = _make_drawing()
    _run_extraction(drawing)

    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"derivedTags": {"added": ["手動:優先"], "removed": ["客先:コマツ小山"]}},
        reason="test",
        executed_by="test",
    )

    # 再抽出(2回目の save_extraction_snapshot)後も手動タグと削除が維持される
    snapshot = _run_extraction(drawing)
    displays = [tag["tag"] for tag in snapshot.derived_tags_json]
    assert "手動:優先" in displays
    assert "客先:コマツ小山" not in displays

    manual_tag = next(tag for tag in snapshot.derived_tags_json if tag["tag"] == "手動:優先")
    assert manual_tag["manual_flag"] is True


@pytest.mark.django_db
def test_attribute_override_survives_re_extraction_and_can_be_reverted():
    drawing = _make_drawing()
    _run_extraction(drawing)

    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"canonicalAttributes": {"customer_name": {"value": "広島アルミ"}}},
        reason="test",
        executed_by="test",
    )
    snapshot = _run_extraction(drawing)
    assert snapshot.canonical_attributes_json["customer_name"] == "広島アルミ"

    # 補正解除(null)で自動抽出値へ戻る
    snapshot = apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"canonicalAttributes": {"customer_name": None}},
        reason="revert",
        executed_by="test",
    )
    assert snapshot.canonical_attributes_json["customer_name"] == "コマツ小山"


@pytest.mark.django_db
def test_persistence_refreshes_composed_metadata():
    drawing = _make_drawing()
    _run_extraction(drawing)

    composed = DrawingComposedMetadata.objects.get(drawing=drawing)
    assert composed.canonical_attributes_json["customer_name"] == "コマツ小山"
    assert any(tag["tag"] == "客先:コマツ小山" for tag in composed.derived_tags_json)

    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"derivedTags": {"removed": ["客先:コマツ小山"]}},
        reason="test",
        executed_by="test",
    )
    composed.refresh_from_db()
    assert all(tag["tag"] != "客先:コマツ小山" for tag in composed.derived_tags_json)
