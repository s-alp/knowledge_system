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
    derived_tags: list[dict],
    executed_by: str,
) -> DrawingMetadataSnapshot:
    snapshot, _ = DrawingMetadataSnapshot.objects.get_or_create(
        drawing=drawing,
        extraction_mode=extraction_mode,
    )
    before_payload = {
        "raw_extract": deepcopy(snapshot.raw_extract_json),
        "canonical_attributes": deepcopy(snapshot.canonical_attributes_json),
        "derived_tags": deepcopy(snapshot.derived_tags_json),
        "manual_overrides": deepcopy(snapshot.manual_overrides_json),
    }
    snapshot.latest_job = job
    snapshot.raw_extract_json = raw_extract
    snapshot.canonical_attributes_json = canonical_attributes
    snapshot.derived_tags_json = derived_tags
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
            "raw_extract": raw_extract,
            "canonical_attributes": canonical_attributes,
            "derived_tags": derived_tags,
            "manual_overrides": snapshot.manual_overrides_json,
        },
        executed_by=executed_by,
    )
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
        before_payload = {
            "canonical_attributes": deepcopy(snapshot.canonical_attributes_json),
            "derived_tags": deepcopy(snapshot.derived_tags_json),
            "manual_overrides": deepcopy(snapshot.manual_overrides_json),
        }

        manual_overrides = deepcopy(snapshot.manual_overrides_json or {})
        manual_overrides.update(
            {
                "canonicalAttributes": payload.get("canonicalAttributes", manual_overrides.get("canonicalAttributes", {})),
                "derivedTags": payload.get("derivedTags", manual_overrides.get("derivedTags", {})),
            }
        )
        snapshot.manual_overrides_json = manual_overrides

        canonical_attributes = deepcopy(snapshot.canonical_attributes_json or {})
        for key, item in payload.get("canonicalAttributes", {}).items():
            canonical_attributes[key] = item.get("value") if isinstance(item, dict) else item

        derived_tags = list(snapshot.derived_tags_json or [])
        added = payload.get("derivedTags", {}).get("added", [])
        removed = set(payload.get("derivedTags", {}).get("removed", []))
        derived_tags = [tag for tag in derived_tags if tag.get("tag") not in removed]
        for tag_value in added:
            if any(item.get("tag") == tag_value for item in derived_tags):
                continue
            derived_tags.append(
                {
                    "tag": tag_value,
                    "source": "manual_override",
                    "confidence": "high",
                    "manual_flag": True,
                    "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
                }
            )

        snapshot.canonical_attributes_json = canonical_attributes
        snapshot.derived_tags_json = derived_tags
        snapshot.updated_by = executed_by
        snapshot.save()

        DrawingMetadataAuditLog.objects.create(
            drawing=drawing,
            extraction_mode=extraction_mode,
            action_type=DrawingMetadataAuditLog.ACTION_OVERRIDE,
            reason=reason,
            before_json=before_payload,
            after_json={
                "canonical_attributes": canonical_attributes,
                "derived_tags": derived_tags,
                "manual_overrides": manual_overrides,
            },
            executed_by=executed_by,
        )
        return snapshot
