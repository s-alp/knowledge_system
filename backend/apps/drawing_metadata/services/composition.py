from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.tag_builder import build_derived_tags


MODE_PRIORITY = ("3d", "2d")
REVIEWABLE_CONFLICT_ATTRIBUTES = {
    "customer_name",
    "project_name",
    "equipment_name",
    "equipment_category",
    "module_name",
    "document_kind",
    "drawing_number",
    "drawing_name",
    "part_number",
    "paper_size",
    "drawing_size",
    "scale",
    "material",
    "material_keywords",
    "formal_material_keywords",
    "unresolved_material_keywords",
    "surface_treatment_tokens",
    "paint_instruction_tokens",
    "heat_treatment_keywords",
    "maker_keywords",
    "process_keywords",
    "weight_value",
    "mass_value",
    "volume_value",
    "area_value",
    "density_value",
    "center_of_gravity",
    "global_moment",
    "gravity_moment",
    "main_moment",
    "inertia_moment_candidates",
    "prfx_candidates",
    "unit_number_candidates",
}


def _is_scalar(value) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _merge_unique(items: Iterable) -> list:
    merged: list = []
    seen: set[str] = set()
    for item in items:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _normalize_manual_tag(tag: dict) -> dict:
    normalized = deepcopy(tag)
    normalized.setdefault("source", "manual_override")
    normalized.setdefault("evidence", "drawingMetadata.snapshot.derivedTags")
    normalized.setdefault("confidence", "high")
    normalized.setdefault("reason", "利用者が手動で追加したタグのため採用しています。")
    normalized.setdefault("manual_flag", True)
    return normalized


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if _has_value(value):
        return [value]
    return []


def _is_reviewable_conflict_attribute(key: str) -> bool:
    if key in REVIEWABLE_CONFLICT_ATTRIBUTES:
        return True
    if key.endswith("_count") or key.endswith("_exists"):
        return False
    if key.startswith(("confidence_", "source_", "raw_", "title_block_llm_")):
        return False
    return False


def _manual_override_value(snapshot: DrawingMetadataSnapshot | None, key: str):
    if not snapshot:
        return None
    override_map = snapshot.manual_overrides_json.get("canonicalAttributes", {})
    item = override_map.get(key)
    if isinstance(item, dict):
        return item.get("value")
    return item


def _snapshot_trace(snapshot: DrawingMetadataSnapshot | None) -> dict | None:
    if not snapshot:
        return None
    latest_job = snapshot.latest_job
    return {
        "snapshotId": snapshot.pk,
        "extractionMode": snapshot.extraction_mode,
        "latestJobId": str(latest_job.id) if latest_job else None,
        "latestJobStatus": latest_job.status if latest_job else None,
        "latestJobCreatedAt": latest_job.created_at.isoformat() if latest_job and latest_job.created_at else None,
        "latestJobFinishedAt": latest_job.finished_at.isoformat() if latest_job and latest_job.finished_at else None,
        "snapshotUpdatedAt": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
        "reviewStatus": snapshot.review_status,
    }


def _snapshot_by_mode(drawing: RegisteredDrawing) -> dict[str, DrawingMetadataSnapshot]:
    return {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}


def _reconciliation_record(
    *,
    key: str,
    value_2d,
    value_3d,
    manual_2d,
    manual_3d,
    chosen_value,
    chosen_mode: str,
    status: str,
    reason: str,
) -> dict:
    return {
        "attribute": key,
        "value2d": value_2d,
        "value3d": value_3d,
        "manual2d": manual_2d if _has_value(manual_2d) else None,
        "manual3d": manual_3d if _has_value(manual_3d) else None,
        "chosenValue": chosen_value,
        "chosenMode": chosen_mode,
        "status": status,
        "reason": reason,
    }


def _reconcile_attribute(key: str, value_2d, value_3d, manual_2d, manual_3d) -> tuple[object, dict]:
    candidate_2d = manual_2d if _has_value(manual_2d) else value_2d
    candidate_3d = manual_3d if _has_value(manual_3d) else value_3d

    if _has_value(manual_3d):
        return manual_3d, _reconciliation_record(
            key=key,
            value_2d=value_2d,
            value_3d=value_3d,
            manual_2d=manual_2d,
            manual_3d=manual_3d,
            chosen_value=manual_3d,
            chosen_mode="manual_3d",
            status="manual_override",
            reason="3D側の手動上書きを最優先で採用しました。",
        )

    if _has_value(manual_2d):
        return manual_2d, _reconciliation_record(
            key=key,
            value_2d=value_2d,
            value_3d=value_3d,
            manual_2d=manual_2d,
            manual_3d=manual_3d,
            chosen_value=manual_2d,
            chosen_mode="manual_2d",
            status="manual_override",
            reason="2D側の手動上書きを採用しました。",
        )

    if _is_scalar(candidate_2d) and _is_scalar(candidate_3d):
        if _has_value(candidate_2d) and _has_value(candidate_3d):
            if candidate_2d == candidate_3d:
                return candidate_3d, _reconciliation_record(
                    key=key,
                    value_2d=value_2d,
                    value_3d=value_3d,
                    manual_2d=manual_2d,
                    manual_3d=manual_3d,
                    chosen_value=candidate_3d,
                    chosen_mode="3d",
                    status="matched",
                    reason="2Dと3Dの抽出値が一致したため採用しました。",
                )
            return candidate_3d, _reconciliation_record(
                key=key,
                value_2d=value_2d,
                value_3d=value_3d,
                manual_2d=manual_2d,
                manual_3d=manual_3d,
                chosen_value=candidate_3d,
                chosen_mode="3d",
                status="conflict",
                reason="2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を採用候補として示し、確定値にはしません。",
            )
        if _has_value(candidate_3d):
            return candidate_3d, _reconciliation_record(
                key=key,
                value_2d=value_2d,
                value_3d=value_3d,
                manual_2d=manual_2d,
                manual_3d=manual_3d,
                chosen_value=candidate_3d,
                chosen_mode="3d",
                status="only_3d",
                reason="3D抽出にのみ値があるため採用しました。",
            )
        if _has_value(candidate_2d):
            return candidate_2d, _reconciliation_record(
                key=key,
                value_2d=value_2d,
                value_3d=value_3d,
                manual_2d=manual_2d,
                manual_3d=manual_3d,
                chosen_value=candidate_2d,
                chosen_mode="2d",
                status="only_2d",
                reason="2D抽出にのみ値があるため採用しました。",
            )
        return None, _reconciliation_record(
            key=key,
            value_2d=value_2d,
            value_3d=value_3d,
            manual_2d=manual_2d,
            manual_3d=manual_3d,
            chosen_value=None,
            chosen_mode="none",
            status="empty",
            reason="2D/3Dとも有効な値がありません。",
        )

    if isinstance(candidate_2d, list) or isinstance(candidate_3d, list):
        merged = _merge_unique(_as_list(candidate_2d) + _as_list(candidate_3d))
        if _has_value(candidate_2d) and _has_value(candidate_3d):
            status = "merged"
            chosen_mode = "merged"
            reason = "2Dと3Dの配列値を重複排除して統合しました。"
        elif _has_value(candidate_3d):
            status = "only_3d"
            chosen_mode = "3d"
            reason = "3D抽出にのみ配列値があるため採用しました。"
        elif _has_value(candidate_2d):
            status = "only_2d"
            chosen_mode = "2d"
            reason = "2D抽出にのみ配列値があるため採用しました。"
        else:
            status = "empty"
            chosen_mode = "none"
            reason = "2D/3Dとも有効な配列値がありません。"
        return merged, _reconciliation_record(
            key=key,
            value_2d=value_2d,
            value_3d=value_3d,
            manual_2d=manual_2d,
            manual_3d=manual_3d,
            chosen_value=merged,
            chosen_mode=chosen_mode,
            status=status,
            reason=reason,
        )

    if isinstance(candidate_2d, dict) or isinstance(candidate_3d, dict):
        merged_dict = {}
        merged_dict.update(candidate_2d or {})
        merged_dict.update(candidate_3d or {})
        if _has_value(candidate_2d) and _has_value(candidate_3d):
            status = "merged"
            chosen_mode = "merged"
            reason = "2Dと3Dの辞書値を統合しました。同一キーは3D値を優先しています。"
        elif _has_value(candidate_3d):
            status = "only_3d"
            chosen_mode = "3d"
            reason = "3D抽出にのみ辞書値があるため採用しました。"
        elif _has_value(candidate_2d):
            status = "only_2d"
            chosen_mode = "2d"
            reason = "2D抽出にのみ辞書値があるため採用しました。"
        else:
            status = "empty"
            chosen_mode = "none"
            reason = "2D/3Dとも有効な辞書値がありません。"
        return merged_dict, _reconciliation_record(
            key=key,
            value_2d=value_2d,
            value_3d=value_3d,
            manual_2d=manual_2d,
            manual_3d=manual_3d,
            chosen_value=merged_dict,
            chosen_mode=chosen_mode,
            status=status,
            reason=reason,
        )

    chosen_value = candidate_3d if _has_value(candidate_3d) else candidate_2d
    chosen_mode = "3d" if _has_value(candidate_3d) else "2d"
    status = "only_3d" if _has_value(candidate_3d) else "only_2d"
    return chosen_value, _reconciliation_record(
        key=key,
        value_2d=value_2d,
        value_3d=value_3d,
        manual_2d=manual_2d,
        manual_3d=manual_3d,
        chosen_value=chosen_value,
        chosen_mode=chosen_mode,
        status=status,
        reason="片側の抽出値を採用しました。",
    )


def compose_drawing_metadata(drawing: RegisteredDrawing) -> dict:
    snapshots = _snapshot_by_mode(drawing)
    snapshot_2d = snapshots.get("2d")
    snapshot_3d = snapshots.get("3d")
    source_by_mode = {
        "2d": _snapshot_trace(snapshot_2d),
        "3d": _snapshot_trace(snapshot_3d),
    }

    canonical_keys: set[str] = set()
    for snapshot in snapshots.values():
        canonical_keys.update((snapshot.canonical_attributes_json or {}).keys())

    conflicts: list[dict] = []
    diagnostic_conflicts: list[dict] = []
    composed_canonical: dict = {}
    conflicted_keys: set[str] = set()
    reconciled_attributes: list[dict] = []

    for key in sorted(canonical_keys):
        value_2d = deepcopy((snapshot_2d.canonical_attributes_json or {}).get(key)) if snapshot_2d else None
        value_3d = deepcopy((snapshot_3d.canonical_attributes_json or {}).get(key)) if snapshot_3d else None
        manual_2d = deepcopy(_manual_override_value(snapshot_2d, key))
        manual_3d = deepcopy(_manual_override_value(snapshot_3d, key))

        chosen_value, reconciled = _reconcile_attribute(key, value_2d, value_3d, manual_2d, manual_3d)
        reconciled["sourceByMode"] = source_by_mode
        composed_canonical[key] = chosen_value
        reconciled_attributes.append(reconciled)
        if reconciled["status"] == "conflict":
            conflict_record = {
                "attribute": key,
                "mode2dValue": reconciled["value2d"],
                "mode3dValue": reconciled["value3d"],
                "chosenMode": reconciled["chosenMode"],
                "chosenValue": reconciled["chosenValue"],
                "reason": reconciled["reason"],
                "sourceByMode": source_by_mode,
            }
            if _is_reviewable_conflict_attribute(key):
                conflicts.append(conflict_record)
                conflicted_keys.add(key)
            else:
                diagnostic_conflicts.append(
                    {
                        **conflict_record,
                        "reason": "内部品質・件数・抽出元差分のため、自動タグ/RAG投入前レビュー対象からは除外しました。",
                    }
                )

    manual_tags = []
    for snapshot in snapshots.values():
        for tag in snapshot.derived_tags_json or []:
            if tag.get("manual_flag"):
                manual_tags.append(_normalize_manual_tag(tag))
    composed_tags = _merge_unique(manual_tags + build_derived_tags(composed_canonical, excluded_sources=conflicted_keys))

    return {
        "canonicalAttributes": composed_canonical,
        "derivedTags": composed_tags,
        "conflicts": conflicts,
        "diagnosticConflicts": diagnostic_conflicts,
        "reconciledAttributes": reconciled_attributes,
        "attributeGroups": [
            {
                "group": "composed",
                "label": "統合結果",
                "attributes": composed_canonical,
            },
            {
                "group": "2d",
                "label": "2D抽出",
                "attributes": snapshot_2d.canonical_attributes_json if snapshot_2d else {},
            },
            {
                "group": "3d",
                "label": "3D抽出",
                "attributes": snapshot_3d.canonical_attributes_json if snapshot_3d else {},
            },
            {
                "group": "reconciledAttributes",
                "label": "2D/3D照合結果",
                "attributes": reconciled_attributes,
            },
            {
                "group": "conflicts",
                "label": "conflicts",
                "attributes": conflicts,
            },
            {
                "group": "diagnosticConflicts",
                "label": "diagnosticConflicts",
                "attributes": diagnostic_conflicts,
            },
        ],
    }
