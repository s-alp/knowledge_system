from __future__ import annotations

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview


def _tag_count(derived_tags: list[dict]) -> int:
    names = {tag.get("tag") for tag in derived_tags if isinstance(tag, dict) and tag.get("tag")}
    return len(names)


def _target_summary(targets: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for target in targets:
        payload_preview = target.get("payloadPreview") or {}
        rows.append(
            {
                "targetKey": target.get("targetKey") or "",
                "targetLabel": target.get("targetLabel") or target.get("label") or target.get("targetKey") or "",
                "attributeCount": len(target.get("attributes") or []),
                "tagCount": len(target.get("tags") or []),
                "tagApiStatus": target.get("tagApiStatus") or "",
                "candidateEndpoint": target.get("candidateEndpoint") or "",
                "payloadKeys": ", ".join(sorted(payload_preview.keys())) if isinstance(payload_preview, dict) else "",
            }
        )
    return rows


def _snapshot_state_label(has_2d: bool, has_3d: bool) -> str:
    if has_2d and has_3d:
        return "2D/3D抽出済み"
    if has_2d:
        return "2Dのみ抽出済み"
    if has_3d:
        return "3Dのみ抽出済み"
    return "未抽出"


def build_handoff_dashboard_payload(drawings: list[RegisteredDrawing]) -> dict:
    rows: list[dict] = []
    target_totals: dict[str, dict] = {}
    extracted_count = 0
    both_2d_3d_count = 0
    payload_ready_count = 0
    review_conflict_count = 0
    diagnostic_conflict_count = 0

    for drawing in drawings:
        snapshots_by_mode = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}
        has_2d = "2d" in snapshots_by_mode
        has_3d = "3d" in snapshots_by_mode
        if has_2d or has_3d:
            extracted_count += 1
        if has_2d and has_3d:
            both_2d_3d_count += 1

        composed_metadata = compose_drawing_metadata(drawing)
        knowledge_payload_preview = build_knowledge_system_payload_preview(
            drawing=drawing,
            composed_metadata=composed_metadata,
        )
        targets = knowledge_payload_preview.get("targets") or []
        target_rows = _target_summary(targets)
        if target_rows:
            payload_ready_count += 1

        for target in target_rows:
            total = target_totals.setdefault(
                target["targetKey"],
                {
                    "targetKey": target["targetKey"],
                    "targetLabel": target["targetLabel"],
                    "drawingCount": 0,
                    "attributeCount": 0,
                    "tagCount": 0,
                },
            )
            total["drawingCount"] += 1
            total["attributeCount"] += target["attributeCount"]
            total["tagCount"] += target["tagCount"]

        conflicts = composed_metadata.get("conflicts") or []
        diagnostic_conflicts = composed_metadata.get("diagnosticConflicts") or []
        review_conflict_count += len(conflicts)
        diagnostic_conflict_count += len(diagnostic_conflicts)
        canonical_attributes = composed_metadata.get("canonicalAttributes") or {}
        derived_tags = composed_metadata.get("derivedTags") or []

        rows.append(
            {
                "drawingId": str(drawing.id),
                "filename": drawing.filename,
                "sourcePath": drawing.source_path,
                "has2d": has_2d,
                "has3d": has_3d,
                "has2dLabel": "あり" if has_2d else "なし",
                "has3dLabel": "あり" if has_3d else "なし",
                "snapshotStateLabel": _snapshot_state_label(has_2d, has_3d),
                "defaultMode": "2d" if has_2d else "3d" if has_3d else "",
                "canonicalAttributeCount": len(canonical_attributes),
                "tagCount": _tag_count(derived_tags),
                "reviewConflictCount": len(conflicts),
                "diagnosticConflictCount": len(diagnostic_conflicts),
                "payloadTargets": target_rows,
                "detailUrl": f"/drawing-metadata/{drawing.id}/",
                "tagReviewUrl": f"/drawing-metadata/{drawing.id}/tags/",
                "bootstrapApiUrl": f"/api/v1/drawings/{drawing.id}/bootstrap",
                "ragPayloadApiUrl": f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload",
            }
        )

    return {
        "summaryCards": [
            {"label": "登録図面", "value": len(drawings)},
            {"label": "抽出済み図面", "value": extracted_count},
            {"label": "2D/3D両snapshotあり", "value": both_2d_3d_count},
            {"label": "payload候補あり", "value": payload_ready_count},
            {"label": "レビュー競合", "value": review_conflict_count},
            {"label": "診断差分", "value": diagnostic_conflict_count},
        ],
        "targetTotals": list(target_totals.values()),
        "rows": rows,
    }
