import pytest
from django.core.management import call_command

from apps.drawing_metadata.models import (
    DrawingComposedMetadata,
    DrawingMetadataAuditLog,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
    TagDictionaryEntry,
)


@pytest.mark.django_db
def test_re_normalize_snapshots_applies_new_dictionary_without_re_extraction(settings):
    drawing = RegisteredDrawing.objects.create(
        filename="renorm.icd", source_path=r"C:\temp\renorm.icd", source_format="icad"
    )
    # 旧バージョンで正規化された体のスナップショット(客先未検出)
    DrawingMetadataSnapshot.objects.create(
        drawing=drawing,
        extraction_mode="3d",
        raw_extract_json={
            "top_part": {"name": "NEWCUST 装置", "comment": None, "ex_info": None},
            "parts": [],
        },
        canonical_attributes_json={"customer_name": None},
        derived_tags_json=[],
        normalizer_version="1.0.0",
        tag_rule_version="1.0.0",
    )

    # 辞書を後から追加(ICAD 再抽出なしで反映できることを確認する)
    TagDictionaryEntry.objects.create(
        kind=TagDictionaryEntry.KIND_CUSTOMER,
        canonical_value="新規客先",
        aliases_json=["NEWCUST"],
    )

    call_command("re_normalize_snapshots", "--stale-only")

    snapshot = DrawingMetadataSnapshot.objects.get(drawing=drawing, extraction_mode="3d")
    assert snapshot.canonical_attributes_json["customer_name"] == "新規客先"
    assert snapshot.normalizer_version == settings.DRAWING_METADATA_NORMALIZER_VERSION
    assert any(tag["tag"] == "客先:新規客先" for tag in snapshot.derived_tags_json)

    composed = DrawingComposedMetadata.objects.get(drawing=drawing)
    assert composed.canonical_attributes_json["customer_name"] == "新規客先"

    assert DrawingMetadataAuditLog.objects.filter(
        drawing=drawing, action_type=DrawingMetadataAuditLog.ACTION_RENORMALIZE
    ).exists()

    # --stale-only は現行バージョン済みスナップショットを対象外にする
    call_command("re_normalize_snapshots", "--stale-only")
    assert (
        DrawingMetadataAuditLog.objects.filter(
            drawing=drawing, action_type=DrawingMetadataAuditLog.ACTION_RENORMALIZE
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_seed_tag_dictionaries_command_is_idempotent():
    call_command("seed_tag_dictionaries")
    first_count = TagDictionaryEntry.objects.count()
    assert first_count > 0
    assert TagDictionaryEntry.objects.filter(
        kind=TagDictionaryEntry.KIND_CUSTOMER, canonical_value="コマツ小山"
    ).exists()

    call_command("seed_tag_dictionaries")
    assert TagDictionaryEntry.objects.count() == first_count
