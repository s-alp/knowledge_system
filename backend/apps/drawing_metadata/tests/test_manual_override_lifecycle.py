import pytest

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview
from apps.drawing_metadata.services.overrides import merge_manual_overrides
from apps.drawing_metadata.services.persistence import apply_manual_overrides, save_extraction_snapshot


def _make_drawing(**kwargs) -> RegisteredDrawing:
    defaults = {
        "host_drawing_id": "lifecycle-sample",
        "filename": "lifecycle.icd",
        "source_path": r"C:\temp\lifecycle.icd",
        "source_format": "icad",
    }
    defaults.update(kwargs)
    return RegisteredDrawing.objects.create(**defaults)


AUTO_CANONICAL = {
    "customer_name": "コマツ小山",
    "equipment_category": "ガントリー",
}
AUTO_TAGS = [
    {"tag": "客先:コマツ小山", "source": "customer_name", "evidence": "e", "confidence": "high", "reason": "r", "manual_flag": False},
    {"tag": "装置:ガントリー", "source": "equipment_category", "evidence": "e", "confidence": "high", "reason": "r", "manual_flag": False},
]


def _run_extraction(drawing: RegisteredDrawing, mode: str = "3d") -> DrawingMetadataSnapshot:
    job = DrawingMetadataExtractionJob.objects.create(drawing=drawing, extraction_mode=mode, status="processing")
    return save_extraction_snapshot(
        drawing=drawing,
        extraction_mode=mode,
        job=job,
        raw_extract={"top_part": {"name": "sample"}},
        canonical_attributes=dict(AUTO_CANONICAL),
        derived_tags=[dict(tag) for tag in AUTO_TAGS],
        executed_by="test",
    )


def test_merge_manual_overrides_is_per_key():
    first = merge_manual_overrides({}, {"canonicalAttributes": {"customer_name": {"value": "広島アルミ"}}})
    second = merge_manual_overrides(first, {"canonicalAttributes": {"equipment_category": {"value": "治具"}}})

    # 2回目の補正で1回目の補正記録が消えない(旧実装はマップ全体を置換していた)
    assert second["canonicalAttributes"]["customer_name"] == {"value": "広島アルミ"}
    assert second["canonicalAttributes"]["equipment_category"] == {"value": "治具"}

    # null 指定でそのキーだけ補正解除できる
    third = merge_manual_overrides(second, {"canonicalAttributes": {"customer_name": None}})
    assert "customer_name" not in third["canonicalAttributes"]
    assert "equipment_category" in third["canonicalAttributes"]


def test_merge_manual_overrides_accumulates_tag_add_remove():
    state = merge_manual_overrides({}, {"derivedTags": {"added": ["手動:A"], "removed": ["装置:ガントリー"]}})
    state = merge_manual_overrides(state, {"derivedTags": {"removed": ["手動:A"]}})
    state = merge_manual_overrides(state, {"derivedTags": {"added": ["装置:ガントリー"]}})

    assert state["derivedTags"]["added"] == ["装置:ガントリー"]
    assert state["derivedTags"]["removed"] == ["手動:A"]


@pytest.mark.django_db
def test_manual_tags_and_removals_survive_re_extraction():
    drawing = _make_drawing()
    _run_extraction(drawing)

    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"derivedTags": {"added": ["工程:熱処理"], "removed": ["客先:コマツ小山"]}},
        reason="test",
        executed_by="test",
    )

    # 再抽出(2回目の save_extraction_snapshot)後も手動タグと削除が維持される
    snapshot = _run_extraction(drawing)
    displays = [tag["tag"] for tag in snapshot.derived_tags_json]
    assert "工程:熱処理" in displays
    assert "客先:コマツ小山" not in displays
    manual_tag = next(tag for tag in snapshot.derived_tags_json if tag["tag"] == "工程:熱処理")
    assert manual_tag["manual_flag"] is True


@pytest.mark.django_db
def test_attribute_override_survives_re_extraction():
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

    # 補正解除(null)を記録してから再抽出すると自動抽出値へ戻る
    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"canonicalAttributes": {"customer_name": None}},
        reason="revert",
        executed_by="test",
    )
    snapshot = _run_extraction(drawing)
    assert snapshot.canonical_attributes_json["customer_name"] == "コマツ小山"


@pytest.mark.django_db
def test_sequential_overrides_both_apply_after_re_extraction():
    drawing = _make_drawing()
    _run_extraction(drawing)

    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"canonicalAttributes": {"customer_name": {"value": "広島アルミ"}}},
        reason="first",
        executed_by="test",
    )
    apply_manual_overrides(
        drawing=drawing,
        extraction_mode="3d",
        payload={"canonicalAttributes": {"equipment_category": {"value": "治具"}}},
        reason="second",
        executed_by="test",
    )

    snapshot = _run_extraction(drawing)
    # 旧実装では2回目の補正保存で1回目の補正が manual_overrides から消え、再抽出で失われていた
    assert snapshot.canonical_attributes_json["customer_name"] == "広島アルミ"
    assert snapshot.canonical_attributes_json["equipment_category"] == "治具"


@pytest.mark.django_db
def test_composition_respects_removed_tags():
    drawing = _make_drawing()
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        canonical_attributes_json={"customer_name": "コマツ小山", "equipment_category": "ガントリー"},
        derived_tags_json=[],
        manual_overrides_json={"derivedTags": {"added": [], "removed": ["装置:ガントリー"]}},
    )

    payload = compose_drawing_metadata(drawing)
    displays = [tag["tag"] for tag in payload["derivedTags"]]
    # 削除済みタグは統合属性からの再生成でも復活しない
    assert "装置:ガントリー" not in displays
    assert "客先:コマツ小山" in displays


@pytest.mark.django_db
def test_payload_preview_formats_mass_and_weight_as_kg():
    drawing = _make_drawing()
    composed = {
        "canonicalAttributes": {
            "mass_value": 11.66123,
            "weight_value": 114.3577,  # 重量(質量×9.80665)は kg 換算して表示する
        },
        "derivedTags": [],
    }
    preview = build_knowledge_system_payload_preview(drawing=drawing, composed_metadata=composed)
    drawing_target = next(t for t in preview["targets"] if t["targetKey"] == "drawing")
    values = {item["attributeName"]: item for item in drawing_target["attributes"]}
    assert values["質量"]["attributeValue"] == "11.66 kg"
    assert values["重量"]["attributeValue"] == "11.66 kg"
    # 根拠には抽出生値を残す
    assert "11.66123" in values["質量"]["evidence"]
