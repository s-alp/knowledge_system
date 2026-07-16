from __future__ import annotations

from copy import deepcopy

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.drawing_metadata.models import (
    DrawingMetadataAuditLog,
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.path_constraints import validate_icad_filename_length


def enqueue_extraction_job(
    *,
    drawing: RegisteredDrawing,
    extraction_mode: str,
    reason: str,
    executed_by: str,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
    diagnostics: dict | None = None,
) -> DrawingMetadataExtractionJob:
    validate_icad_filename_length(drawing.filename)

    with transaction.atomic():
        active_job = (
            DrawingMetadataExtractionJob.objects.select_for_update()
            .filter(
                drawing=drawing,
                extraction_mode=extraction_mode,
                status__in=[
                    DrawingMetadataExtractionJob.STATUS_QUEUED,
                    DrawingMetadataExtractionJob.STATUS_PROCESSING,
                ],
            )
            .order_by("created_at")
            .first()
        )
        if active_job is not None:
            return active_job

        job = DrawingMetadataExtractionJob.objects.create(
            drawing=drawing,
            extraction_mode=extraction_mode,
            status=DrawingMetadataExtractionJob.STATUS_QUEUED,
            extraction_profile=extraction_profile or "default",
            extraction_options_json=extraction_options or {},
            diagnostics_json=diagnostics or {},
            schema_version=settings.DRAWING_METADATA_SCHEMA_VERSION,
        )
        DrawingMetadataAuditLog.objects.create(
            drawing=drawing,
            extraction_mode=extraction_mode,
            action_type=DrawingMetadataAuditLog.ACTION_REQUEUE,
            reason=reason,
            before_json={},
            after_json={
                "job_id": str(job.id),
                "status": job.status,
                "extraction_mode": extraction_mode,
                "extraction_profile": job.extraction_profile,
                "extraction_options": job.extraction_options_json,
                "diagnostics": job.diagnostics_json,
            },
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
    snapshot.review_status = DrawingMetadataSnapshot.REVIEW_PENDING
    snapshot.reviewed_at = None
    snapshot.reviewed_by = ""
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
        manual_overrides["canonicalAttributes"] = payload.get(
            "canonicalAttributes",
            manual_overrides.get("canonicalAttributes", {}),
        )
        manual_overrides["derivedTags"] = payload.get(
            "derivedTags",
            manual_overrides.get("derivedTags", {}),
        )
        if "businessFields" in payload:
            manual_overrides["businessFields"] = payload["businessFields"]
        if "relatedDrawingIds" in payload:
            manual_overrides["relatedDrawingIds"] = [str(item) for item in payload["relatedDrawingIds"]]
        for key in ("knowledgeEntityTarget", "knowledgeEntityKind"):
            if key in payload:
                manual_overrides[key] = payload[key]
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
                    "evidence": "drawingMetadata.manualOverrides.derivedTags.added",
                    "confidence": "high",
                    "reason": reason or "利用者が手動で追加したタグのため採用しています。",
                    "manual_flag": True,
                    "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
                }
            )

        snapshot.canonical_attributes_json = canonical_attributes
        snapshot.derived_tags_json = derived_tags
        snapshot.review_status = DrawingMetadataSnapshot.REVIEW_PENDING
        snapshot.reviewed_at = None
        snapshot.reviewed_by = ""
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


def apply_review_decision(
    *,
    snapshot: DrawingMetadataSnapshot,
    decision: str,
    reason: str,
    executed_by: str,
) -> DrawingMetadataSnapshot:
    with transaction.atomic():
        locked = DrawingMetadataSnapshot.objects.select_for_update().get(pk=snapshot.pk)
        before_status = locked.review_status
        locked.review_status = decision
        locked.reviewed_at = timezone.now()
        locked.reviewed_by = executed_by
        locked.save(update_fields=["review_status", "reviewed_at", "reviewed_by", "updated_at"])

        DrawingMetadataAuditLog.objects.create(
            drawing=locked.drawing,
            extraction_mode=locked.extraction_mode,
            action_type=DrawingMetadataAuditLog.ACTION_REVIEW,
            reason=reason,
            before_json={"review_status": before_status},
            after_json={"review_status": decision},
            executed_by=executed_by,
        )
        return locked
