from __future__ import annotations

from django.db.utils import OperationalError, ProgrammingError

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    MAKER_KEYWORDS,
    SPEC_KEYWORDS,
)

KIND_TO_SEED: dict[str, dict[str, list[str]]] = {
    TagDictionaryEntry.KIND_CUSTOMER: CUSTOMER_KEYWORDS,
    TagDictionaryEntry.KIND_EQUIPMENT_CATEGORY: EQUIPMENT_CATEGORY_KEYWORDS,
    TagDictionaryEntry.KIND_MAKER: MAKER_KEYWORDS,
    TagDictionaryEntry.KIND_SPEC: SPEC_KEYWORDS,
}


def load_keyword_mapping(kind: str) -> dict[str, list[str]]:
    """DB 辞書を優先して {正規値: [照合候補...]} を返す。DB が空/未整備なら seed 定数へフォールバックする。"""
    try:
        entries = list(
            TagDictionaryEntry.objects.filter(kind=kind, enabled=True).order_by("priority", "id")
        )
    except (OperationalError, ProgrammingError):
        # マイグレーション未適用環境でも正規化自体は seed で動かせるようにする。
        entries = []

    mapping: dict[str, list[str]] = {}
    for entry in entries:
        candidates: list[str] = []
        for candidate in [entry.canonical_value, *(entry.aliases_json or [])]:
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        mapping[entry.canonical_value] = candidates

    if mapping:
        return mapping
    return {canonical: list(candidates) for canonical, candidates in KIND_TO_SEED.get(kind, {}).items()}
