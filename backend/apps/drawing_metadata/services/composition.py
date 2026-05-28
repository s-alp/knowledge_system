from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.tag_builder import build_derived_tags


MODE_PRIORITY = ("3d", "2d")


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


def _manual_override_value(snapshot: DrawingMetadataSnapshot | None, key: str):
    if not snapshot:
        return None
    override_map = snapshot.manual_overrides_json.get("canonicalAttributes", {})
    item = override_map.get(key)
    if isinstance(item, dict):
        return item.get("value")
    return item


def _snapshot_by_mode(drawing: RegisteredDrawing) -> dict[str, DrawingMetadataSnapshot]:
    return {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}


def compose_drawing_metadata(drawing: RegisteredDrawing) -> dict:
    snapshots = _snapshot_by_mode(drawing)
    snapshot_2d = snapshots.get("2d")
    snapshot_3d = snapshots.get("3d")

    canonical_keys: set[str] = set()
    for snapshot in snapshots.values():
        canonical_keys.update((snapshot.canonical_attributes_json or {}).keys())

    conflicts: list[dict] = []
    composed_canonical: dict = {}
    conflicted_keys: set[str] = set()

    for key in sorted(canonical_keys):
        value_2d = deepcopy((snapshot_2d.canonical_attributes_json or {}).get(key)) if snapshot_2d else None
        value_3d = deepcopy((snapshot_3d.canonical_attributes_json or {}).get(key)) if snapshot_3d else None
        manual_2d = deepcopy(_manual_override_value(snapshot_2d, key))
        manual_3d = deepcopy(_manual_override_value(snapshot_3d, key))

        candidate_2d = manual_2d if _has_value(manual_2d) else value_2d
        candidate_3d = manual_3d if _has_value(manual_3d) else value_3d

        if _is_scalar(candidate_2d) and _is_scalar(candidate_3d):
            if _has_value(candidate_2d) and _has_value(candidate_3d) and candidate_2d != candidate_3d:
                conflicts.append(
                    {
                        "attribute": key,
                        "mode2dValue": candidate_2d,
                        "mode3dValue": candidate_3d,
                        "chosenMode": "3d",
                    }
                )
                conflicted_keys.add(key)

            if _has_value(manual_3d):
                composed_canonical[key] = manual_3d
            elif _has_value(manual_2d):
                composed_canonical[key] = manual_2d
            elif _has_value(value_3d):
                composed_canonical[key] = value_3d
            else:
                composed_canonical[key] = value_2d
            continue

        if isinstance(candidate_2d, list) or isinstance(candidate_3d, list):
            merged = _merge_unique((candidate_2d or []) + (candidate_3d or []))
            composed_canonical[key] = merged
            continue

        if isinstance(candidate_2d, dict) or isinstance(candidate_3d, dict):
            merged_dict = {}
            merged_dict.update(candidate_2d or {})
            merged_dict.update(candidate_3d or {})
            composed_canonical[key] = merged_dict
            continue

        composed_canonical[key] = candidate_3d if _has_value(candidate_3d) else candidate_2d

    manual_tags = []
    for snapshot in snapshots.values():
        for tag in snapshot.derived_tags_json or []:
            if tag.get("manual_flag"):
                manual_tags.append(tag)
    composed_tags = _merge_unique(manual_tags + build_derived_tags(composed_canonical, excluded_sources=conflicted_keys))

    return {
        "canonicalAttributes": composed_canonical,
        "derivedTags": composed_tags,
        "conflicts": conflicts,
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
                "group": "conflicts",
                "label": "conflicts",
                "attributes": conflicts,
            },
        ],
    }
