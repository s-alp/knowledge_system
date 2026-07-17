from __future__ import annotations

from copy import deepcopy

from django.conf import settings


def merge_manual_overrides(existing: dict | None, payload: dict) -> dict:
    """手動補正の正本(manual_overrides_json)へ、新しい補正リクエストをマージする。

    - canonicalAttributes はキー単位で追記・上書きする。値に null を渡した項目だけ補正解除する。
      (マップ全体を置換すると、過去の補正記録が消え、再抽出後の再適用もできなくなる)
    - derivedTags.added / removed は累積集合として保ち、追加→削除、削除→再追加は相殺する。
    - businessFields / relatedDrawingIds / knowledgeEntityTarget / knowledgeEntityKind は
      単一値のため、指定があった場合のみ置換する(現行仕様のまま)。
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

    if "businessFields" in payload:
        merged["businessFields"] = payload["businessFields"]
    if "relatedDrawingIds" in payload:
        merged["relatedDrawingIds"] = [str(item) for item in payload["relatedDrawingIds"]]
    for key in ("knowledgeEntityTarget", "knowledgeEntityKind"):
        if key in payload:
            merged[key] = payload[key]

    return merged


def override_value(item):
    return item.get("value") if isinstance(item, dict) else item


def apply_attribute_overrides(canonical_attributes: dict, manual_overrides: dict | None) -> dict:
    """自動抽出済み canonical へ、保存済みの属性補正を再適用する。"""
    result = deepcopy(canonical_attributes or {})
    for key, item in ((manual_overrides or {}).get("canonicalAttributes") or {}).items():
        if item is None:
            continue
        result[key] = deepcopy(override_value(item))
    return result


def build_manual_tag_payload(display: str, *, reason: str = "") -> dict:
    return {
        "tag": display,
        "source": "manual_override",
        "evidence": "drawingMetadata.manualOverrides.derivedTags.added",
        "confidence": "high",
        "reason": reason or "利用者が手動で追加したタグのため採用しています。",
        "manual_flag": True,
        "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
    }


def removed_tag_names(manual_overrides: dict | None) -> set[str]:
    return set((((manual_overrides or {}).get("derivedTags") or {}).get("removed")) or [])


def apply_tag_overrides(derived_tags: list[dict], manual_overrides: dict | None, *, reason: str = "") -> list[dict]:
    """自動生成タグへ、保存済みのタグ補正(削除・手動追加)を再適用する。

    最終タグ = 自動タグ - removed + added。再抽出直後もこの関数を通すことで、
    利用者のタグ削除・手動タグが自動タグの上書き保存で消えない。
    """
    removed = removed_tag_names(manual_overrides)
    added = (((manual_overrides or {}).get("derivedTags") or {}).get("added")) or []

    tags = [deepcopy(tag) for tag in (derived_tags or []) if tag.get("tag") not in removed]
    for display in added:
        if any(tag.get("tag") == display for tag in tags):
            continue
        tags.append(build_manual_tag_payload(display, reason=reason))
    return tags
