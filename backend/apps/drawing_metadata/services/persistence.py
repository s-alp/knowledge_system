from __future__ import annotations

from copy import deepcopy

from django.conf import settings
from django.db import transaction

from apps.drawing_metadata.models import (
    DrawingMetadataAuditLog,
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.composition import refresh_composed_metadata
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.overrides import compute_effective_state, merge_manual_overrides


def _snapshot_state(snapshot: DrawingMetadataSnapshot) -> dict:
    # 監査ログには意味付け済みデータだけを残す。raw_extract 全文はジョブ参照で辿れるため二重保存しない。
    return {
        "canonical_attributes": deepcopy(snapshot.canonical_attributes_json),
        "derived_tags": deepcopy(snapshot.derived_tags_json),
        "manual_overrides": deepcopy(snapshot.manual_overrides_json),
    }


def compute_auto_canonical(snapshot: DrawingMetadataSnapshot) -> dict:
    """保存済み raw_extract から自動抽出分の canonical を再計算する。raw が無ければ空。"""
    raw_extract = snapshot.raw_extract_json or {}
    if not raw_extract:
        return {}
    warnings = snapshot.latest_job.warnings_json if snapshot.latest_job else []
    payload = {
        "source_kind": snapshot.extraction_mode,
        "source_format": snapshot.drawing.source_format,
        "raw_extract": raw_extract,
        "warnings": warnings,
    }
    return normalize_raw_extract(payload)


def enqueue_extraction_job(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    reason: str,
    executed_by: str,
) -> DrawingMetadataExtractionJob:
    job = DrawingMetadataExtractionJob.objects.create(
        drawing=drawing,
        extraction_mode=extraction_mode,
        status=DrawingMetadataExtractionJob.STATUS_QUEUED,
        schema_version=settings.DRAWING_METADATA_SCHEMA_VERSION,
    )
    DrawingMetadataAuditLog.objects.create(
        drawing=drawing,
        extraction_mode=extraction_mode,
        action_type=DrawingMetadataAuditLog.ACTION_REQUEUE,
        reason=reason,
        before_json={},
        after_json={"job_id": str(job.id), "status": job.status, "extraction_mode": extraction_mode},
        executed_by=executed_by,
    )
    return job


def save_extraction_snapshot(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    job: DrawingMetadataExtractionJob,
    raw_extract: dict,
    canonical_attributes: dict,
    executed_by: str,
) -> DrawingMetadataSnapshot:
    """抽出結果を保存する。既存の手動補正(属性・タグ追加・タグ削除)は必ず再適用する。"""
    snapshot, _ = DrawingMetadataSnapshot.objects.get_or_create(
        drawing=drawing,
        extraction_mode=extraction_mode,
    )
    before_payload = _snapshot_state(snapshot)

    manual_overrides = snapshot.manual_overrides_json or {}
    effective_canonical, effective_tags = compute_effective_state(canonical_attributes, manual_overrides)

    snapshot.latest_job = job
    snapshot.raw_extract_json = raw_extract
    snapshot.canonical_attributes_json = effective_canonical
    snapshot.derived_tags_json = effective_tags
    snapshot.normalizer_version = settings.DRAWING_METADATA_NORMALIZER_VERSION
    snapshot.tag_rule_version = settings.DRAWING_METADATA_TAG_RULE_VERSION
    snapshot.updated_by = executed_by
    snapshot.save()

    DrawingMetadataAuditLog.objects.create(
        drawing=drawing,
        extraction_mode=extraction_mode,
        action_type=DrawingMetadataAuditLog.ACTION_EXTRACTION,
        reason="extractor result saved",
        before_json=before_payload,
        after_json={
            **_snapshot_state(snapshot),
            "raw_extract_ref": {"job_id": str(job.id)},
        },
        executed_by=executed_by,
    )
    refresh_composed_metadata(drawing)
    return snapshot


def apply_manual_overrides(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    payload: dict,
    reason: str,
    executed_by: str,
) -> DrawingMetadataSnapshot:
    with transaction.atomic():
        snapshot, _ = DrawingMetadataSnapshot.objects.select_for_update().get_or_create(
            drawing=drawing,
            extraction_mode=extraction_mode,
        )
        before_payload = _snapshot_state(snapshot)

        merged_overrides = merge_manual_overrides(snapshot.manual_overrides_json, payload)
        snapshot.manual_overrides_json = merged_overrides

        # 属性・タグは常に「自動抽出値 + 補正」の合成として再計算する。
        # 補正解除(null 指定)時に自動値へ戻せるよう、自動値は raw_extract から起こす。
        auto_canonical = compute_auto_canonical(snapshot)
        effective_canonical, effective_tags = compute_effective_state(auto_canonical, merged_overrides)

        snapshot.canonical_attributes_json = effective_canonical
        snapshot.derived_tags_json = effective_tags
        snapshot.updated_by = executed_by
        snapshot.save()

        DrawingMetadataAuditLog.objects.create(
            drawing=drawing,
            extraction_mode=extraction_mode,
            action_type=DrawingMetadataAuditLog.ACTION_OVERRIDE,
            reason=reason,
            before_json=before_payload,
            after_json=_snapshot_state(snapshot),
            executed_by=executed_by,
        )
        refresh_composed_metadata(drawing)
        return snapshot


def re_normalize_snapshot(
    *,
    snapshot: DrawingMetadataSnapshot,
    executed_by: str,
    reason: str = "re-normalize from stored raw_extract",
) -> DrawingMetadataSnapshot:
    """ICAD 再抽出なしで、保存済み raw_extract から正規化・タグ生成をやり直す。

    辞書やタグ生成ルールを改訂した後、既存図面へ反映するための経路。
    """
    before_payload = _snapshot_state(snapshot)

    auto_canonical = compute_auto_canonical(snapshot)
    effective_canonical, effective_tags = compute_effective_state(
        auto_canonical, snapshot.manual_overrides_json or {}
    )

    snapshot.canonical_attributes_json = effective_canonical
    snapshot.derived_tags_json = effective_tags
    snapshot.normalizer_version = settings.DRAWING_METADATA_NORMALIZER_VERSION
    snapshot.tag_rule_version = settings.DRAWING_METADATA_TAG_RULE_VERSION
    snapshot.updated_by = executed_by
    snapshot.save()

    DrawingMetadataAuditLog.objects.create(
        drawing=snapshot.drawing,
        extraction_mode=snapshot.extraction_mode,
        action_type=DrawingMetadataAuditLog.ACTION_RENORMALIZE,
        reason=reason,
        before_json=before_payload,
        after_json=_snapshot_state(snapshot),
        executed_by=executed_by,
    )
    return snapshot
