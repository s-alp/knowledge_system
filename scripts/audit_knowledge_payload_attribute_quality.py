from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import django

django.setup()

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview


VALID_CONFIDENCES = {"high", "medium", "low"}


def _attribute_issues(drawing: RegisteredDrawing, target: dict) -> list[dict]:
    issues: list[dict] = []
    for index, attribute in enumerate(target.get("attributes") or []):
        if not str(attribute.get("sourcePath") or "").strip():
            issues.append(_issue(drawing, target, index, "attribute_source_missing", attribute))
        if not str(attribute.get("evidence") or "").strip():
            issues.append(_issue(drawing, target, index, "attribute_evidence_missing", attribute))
        if str(attribute.get("confidence") or "").strip() not in VALID_CONFIDENCES:
            issues.append(_issue(drawing, target, index, "attribute_confidence_invalid", attribute))
        if not str(attribute.get("reason") or "").strip():
            issues.append(_issue(drawing, target, index, "attribute_reason_missing", attribute))
    return issues


def _tag_issues(drawing: RegisteredDrawing, target: dict) -> list[dict]:
    issues: list[dict] = []
    tags = [str(tag) for tag in target.get("tags") or [] if str(tag).strip()]
    tag_evidence = [item for item in target.get("tagEvidence") or [] if isinstance(item, dict)]
    evidence_by_tag = {str(item.get("tag") or ""): item for item in tag_evidence}
    for index, tag in enumerate(tags):
        item = evidence_by_tag.get(tag)
        if item is None:
            issues.append(_tag_issue(drawing, target, index, "tag_evidence_missing", {"tag": tag}))
            continue
        if not str(item.get("source") or "").strip():
            issues.append(_tag_issue(drawing, target, index, "tag_source_missing", item))
        if not str(item.get("evidence") or "").strip():
            issues.append(_tag_issue(drawing, target, index, "tag_evidence_text_missing", item))
        if str(item.get("confidence") or "").strip() not in VALID_CONFIDENCES:
            issues.append(_tag_issue(drawing, target, index, "tag_confidence_invalid", item))
        if not str(item.get("reason") or "").strip():
            issues.append(_tag_issue(drawing, target, index, "tag_reason_missing", item))
    extra_evidence = sorted(set(evidence_by_tag) - set(tags))
    for tag in extra_evidence:
        issues.append(_tag_issue(drawing, target, -1, "tag_evidence_without_target_tag", evidence_by_tag[tag]))
    return issues


def _issue(drawing: RegisteredDrawing, target: dict, index: int, code: str, attribute: dict) -> dict:
    return {
        "drawingId": str(drawing.id),
        "filename": drawing.filename,
        "targetKey": target.get("targetKey"),
        "attributeIndex": index,
        "code": code,
        "attributeName": attribute.get("attributeName"),
        "attributeValue": attribute.get("attributeValue"),
        "sourcePath": attribute.get("sourcePath"),
    }


def _tag_issue(drawing: RegisteredDrawing, target: dict, index: int, code: str, tag: dict) -> dict:
    return {
        "drawingId": str(drawing.id),
        "filename": drawing.filename,
        "targetKey": target.get("targetKey"),
        "tagIndex": index,
        "code": code,
        "tag": tag.get("tag"),
        "source": tag.get("source"),
    }


def main() -> int:
    base_queryset = RegisteredDrawing.objects.prefetch_related("snapshots", "jobs").order_by("filename", "id")
    total_registration_count = base_queryset.count()
    scoped_queryset, scope = apply_active_drawing_scope(base_queryset)
    drawings = list(scoped_queryset)
    issues: list[dict] = []
    attribute_count = 0
    tag_count = 0

    for drawing in drawings:
        if not any(snapshot.raw_extract_json for snapshot in drawing.snapshots.all()):
            continue
        composed = compose_drawing_metadata(drawing)
        payload = build_knowledge_system_payload_preview(drawing=drawing, composed_metadata=composed)
        for target in payload.get("targets") or []:
            attributes = target.get("attributes") or []
            attribute_count += len(attributes)
            tag_count += len(target.get("tags") or [])
            issues.extend(_attribute_issues(drawing, target))
            issues.extend(_tag_issues(drawing, target))

    result = {
        "schemaVersion": "knowledge_payload_attribute_quality_audit.v1",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(drawings),
        ),
        "drawingCount": len(drawings),
        "snapshotCount": DrawingMetadataSnapshot.objects.filter(drawing__in=drawings).count(),
        "attributeCount": attribute_count,
        "tagCount": tag_count,
        "issueCount": len(issues),
        "gatePassed": not issues,
        "issues": issues[:100],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
