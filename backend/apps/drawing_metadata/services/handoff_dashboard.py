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


def _api_rows() -> list[dict]:
    return [
        {
            "area": "図面管理 viewer",
            "method": "GET",
            "path": "/api/v1/drawings/{drawing_id}/bootstrap",
            "purpose": "2D/3D viewer が図面名、タグ、属性、関連情報を読み込む。",
        },
        {
            "area": "ICAD抽出登録",
            "method": "GET",
            "path": "/api/v1/drawing-metadata/registrations",
            "purpose": "登録済みICD単位の抽出状態、snapshot有無、最新ジョブ状態を確認する。",
        },
        {
            "area": "ICAD抽出登録",
            "method": "GET",
            "path": "/api/v1/drawing-metadata/registrations/{drawing_id}",
            "purpose": "1件の2D/3D snapshot、属性、タグ、手直し値、viewer bootstrap候補を確認する。",
        },
        {
            "area": "タグ候補レビュー",
            "method": "POST",
            "path": "/api/v1/drawing-metadata/registrations/{drawing_id}/review",
            "purpose": "レビュー状態、確認者、確認日時をローカル検証DBへ記録する。",
        },
        {
            "area": "手直し",
            "method": "POST",
            "path": "/api/v1/drawing-metadata/registrations/{drawing_id}/overrides",
            "purpose": "抽出値を直接JSON編集させず、画面項目単位の補正値として保存する。",
        },
        {
            "area": "RAG/創屋連携",
            "method": "GET",
            "path": "/api/v1/drawing-metadata/registrations/{drawing_id}/rag-payload",
            "purpose": "RAG投入候補、タグ、属性、根拠、競合を読み取り用payloadとして出力する。",
        },
        {
            "area": "製品・装置・ユニット/部品",
            "method": "GET",
            "path": "/api/v1/knowledge-entities?target=product|part",
            "purpose": "ICD単位で製品・装置・ユニット候補または部品候補を一覧表示する。",
        },
        {
            "area": "紐づけ",
            "method": "GET",
            "path": "/api/v1/drawing-options",
            "purpose": "製品・装置・ユニット/部品詳細から紐づけ可能な図面候補を取得する。",
        },
        {
            "area": "システム設定",
            "method": "GET",
            "path": "/api/v1/drawing-metadata/settings/tag-automation",
            "purpose": "タグ自動取得の実行時設定、運用項目、採用ルールを確認する。",
        },
        {
            "area": "システム設定",
            "method": "GET",
            "path": "/api/v1/drawing-metadata/handoff-summary",
            "purpose": "抽出管理、API仕様、対象別payload集計をシステム設定内に表示する。",
        },
    ]


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
                "detailUrl": f"/internal/drawing-metadata/{drawing.id}/",
                "tagReviewUrl": f"/internal/drawing-metadata/{drawing.id}/tags/",
                "bootstrapApiUrl": f"/api/v1/drawings/{drawing.id}/bootstrap",
                "ragPayloadApiUrl": f"/api/v1/drawing-metadata/registrations/{drawing.id}/rag-payload",
            }
        )

    return {
        "apiRows": _api_rows(),
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
