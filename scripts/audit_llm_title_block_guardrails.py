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

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload
from apps.drawing_metadata.models import RegisteredDrawing


def main() -> int:
    base_queryset = RegisteredDrawing.objects.order_by("filename", "id")
    total_registration_count = base_queryset.count()
    scoped_queryset, scope = apply_active_drawing_scope(base_queryset)
    scoped_drawing_ids = list(scoped_queryset.values_list("id", flat=True))
    snapshots = DrawingMetadataSnapshot.objects.select_related("drawing").filter(
        drawing_id__in=scoped_drawing_ids,
        extraction_mode="2d",
    )
    issues: list[dict] = []
    llm_classification_count = 0

    for snapshot in snapshots:
        canonical = snapshot.canonical_attributes_json or {}
        candidates = canonical.get("title_block_candidates") or []
        classifications = canonical.get("title_block_llm_classifications") or []
        if isinstance(classifications, list):
            llm_classification_count += len(classifications)
        if not isinstance(candidates, list) or not isinstance(classifications, list):
            continue

        for classification in classifications:
            if not isinstance(classification, dict) or not classification.get("accepted_as_field"):
                continue
            index = classification.get("index")
            if not isinstance(index, int) or index < 0 or index >= len(candidates):
                continue
            candidate = candidates[index]
            if not isinstance(candidate, dict):
                continue
            if candidate.get("inside_print_area") is False:
                issues.append(
                    {
                        "sourcePath": snapshot.drawing.source_path,
                        "filename": snapshot.drawing.filename,
                        "snapshotId": snapshot.id,
                        "code": "llm_accepted_outside_print_area",
                        "message": "Gemini分類が印刷枠外候補を属性として採用しています。",
                        "candidate": {
                            "index": index,
                            "field": candidate.get("field"),
                            "value": candidate.get("value"),
                            "evidenceText": candidate.get("evidence_text"),
                        },
                    }
                )

    payload = {
        "schemaVersion": "llm_title_block_guardrail_audit.v1",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(scoped_drawing_ids),
        ),
        "snapshotCount": snapshots.count(),
        "llmClassificationCount": llm_classification_count,
        "blockingIssueCount": len(issues),
        "gatePassed": not issues,
        "blockingIssues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
