from __future__ import annotations

from copy import deepcopy

from django.conf import settings

from apps.drawing_metadata.services.tag_builder import build_derived_tags, split_tag_display


def merge_manual_overrides(existing: dict | None, payload: dict) -> dict:
    """手動補正の正本(manual_overrides_json)へ、新しい補正リクエストをキー単位でマージする。

    - canonicalAttributes は項目ごとに追記・上書きし、値に null を渡した項目だけ補正解除する。
      (以前の「マップ全体を置換する」挙動は、過去の補正記録と手動優先を消していた)
    - derivedTags.added / removed は累積集合として保ち、追加→削除、削除→再追加を相殺する。
    """
    merged = deepcopy(existing or {})

    attribute_overrides = dict(merged.get("canonicalAttributes") or {})
    for key, item in (payload.get("canonicalAttributes") or {}).items():
        if item is None:
            attribute_overrides.pop(key, None)
        else:
            attribute_overrides[key] = deepcopy(item)
    merged["canonicalAttributes"] = attribute_overrides

    existing_tags = merged.get("derivedTags") or {}
    added = list(existing_tags.get("added") or [])
    removed = list(existing_tags.get("removed") or [])
    payload_tags = payload.get("derivedTags") or {}
    for tag in payload_tags.get("added", []):
        if tag in removed:
            removed.remove(tag)
        if tag not in added:
            added.append(tag)
    for tag in payload_tags.get("removed", []):
        if tag in added:
            added.remove(tag)
        if tag not in removed:
            removed.append(tag)
    merged["derivedTags"] = {"added": added, "removed": removed}

    return merged


def override_value(item):
    return item.get("value") if isinstance(item, dict) else item


def apply_attribute_overrides(canonical_auto: dict, overrides: dict | None) -> dict:
    result = deepcopy(canonical_auto or {})
    for key, item in ((overrides or {}).get("canonicalAttributes") or {}).items():
        result[key] = deepcopy(override_value(item))
    return result


def build_manual_tag_payload(display: str) -> dict:
    namespace, value = split_tag_display(display)
    return {
        "tag": display,
        "namespace": namespace,
        "value": value,
        "source": "manual_override",
        "confidence": "high",
        "manual_flag": True,
        "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
        "evidence": [],
    }


def apply_tag_overrides(auto_tags: list[dict], overrides: dict | None) -> list[dict]:
    """自動タグへ手動補正を適用する。最終タグ = 自動タグ - removed + added。"""
    tag_overrides = (overrides or {}).get("derivedTags") or {}
    removed = set(tag_overrides.get("removed") or [])
    added = tag_overrides.get("added") or []

    tags = [deepcopy(tag) for tag in auto_tags if tag.get("tag") not in removed]
    for display in added:
        if any(tag.get("tag") == display for tag in tags):
            continue
        tags.append(build_manual_tag_payload(display))
    return tags


def compute_effective_state(
    canonical_auto: dict,
    overrides: dict | None,
    *,
    low_confidence_sources: set[str] | None = None,
) -> tuple[dict, list[dict]]:
    """自動抽出値と手動補正から、保存・表示に使う確定属性と確定タグを一括で計算する。

    再抽出直後もこの関数を通すことで、手動タグ・タグ削除・属性補正が消えない。
    """
    canonical = apply_attribute_overrides(canonical_auto, overrides)
    auto_tags = build_derived_tags(canonical, low_confidence_sources=low_confidence_sources)
    tags = apply_tag_overrides(auto_tags, overrides)
    return canonical, tags
