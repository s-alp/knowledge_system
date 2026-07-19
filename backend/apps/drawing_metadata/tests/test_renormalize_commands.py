import pytest
from django.core.management import call_command

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing


def _snapshot(**kwargs) -> DrawingMetadataSnapshot:
    drawing = RegisteredDrawing.objects.create(
        host_drawing_id="renorm-cmd",
        filename="renorm_cmd.icd",
        source_path=r"C:\temp\renorm_cmd.icd",
        source_format="icad",
    )
    defaults = {
        "drawing": drawing,
        "extraction_mode": "3d",
        "raw_extract_json": {
            "top_part": {"name": "KO小山ガントリー", "comment": None, "ex_info": "コマツ小山"},
            "parts": [],
        },
        "canonical_attributes_json": {"customer_name": "コマツ小山"},
        "derived_tags_json": [
            {"tag": "客先:コマツ小山", "source": "customer_name", "manual_flag": False},
            {"tag": "手動:優先", "source": "manual_override", "manual_flag": True},
        ],
        "manual_overrides_json": {
            "canonicalAttributes": {"equipment_category": {"value": "ガントリー"}},
            "derivedTags": {"added": ["工程:熱処理"], "removed": ["客先:コマツ小山"]},
        },
    }
    defaults.update(kwargs)
    return DrawingMetadataSnapshot.objects.create(**defaults)


@pytest.mark.django_db
def test_renormalize_command_respects_manual_overrides():
    snapshot = _snapshot()

    call_command("renormalize_drawing_metadata_snapshots")

    snapshot.refresh_from_db()
    displays = [tag["tag"] for tag in snapshot.derived_tags_json]
    # 削除済み自動タグは再正規化でも復活しない
    assert "客先:コマツ小山" not in displays
    # overrides 記録の手動タグと、旧形式の manual_flag 手動タグの両方が残る
    assert "工程:熱処理" in displays
    assert "手動:優先" in displays
    # 属性補正も再適用される
    assert snapshot.canonical_attributes_json["equipment_category"] == "ガントリー"
    # 自動抽出値は raw から再計算される
    assert snapshot.canonical_attributes_json["customer_name"] == "コマツ小山"


@pytest.mark.django_db
def test_rebuild_tags_command_respects_manual_overrides():
    snapshot = _snapshot()

    call_command("rebuild_drawing_metadata_tags")

    snapshot.refresh_from_db()
    displays = [tag["tag"] for tag in snapshot.derived_tags_json]
    assert "客先:コマツ小山" not in displays
    assert "工程:熱処理" in displays
    assert "手動:優先" in displays
