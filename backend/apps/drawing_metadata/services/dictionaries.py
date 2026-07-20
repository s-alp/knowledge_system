from __future__ import annotations

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    HEAT_TREATMENT_KEYWORDS,
    MAKER_KEYWORDS,
    SPEC_KEYWORDS,
)

# 種別ごとの seed(初期値)。DBにエントリが1件もない種別はこの seed で動く。
KIND_TO_SEED: dict[str, dict[str, list[str]]] = {
    TagDictionaryEntry.KIND_CUSTOMER: CUSTOMER_KEYWORDS,
    TagDictionaryEntry.KIND_EQUIPMENT_CATEGORY: EQUIPMENT_CATEGORY_KEYWORDS,
    TagDictionaryEntry.KIND_PROJECT: {},  # 案件はseed無し。GUI/adminからの登録が正本。
    TagDictionaryEntry.KIND_MAKER: MAKER_KEYWORDS,
    TagDictionaryEntry.KIND_SPEC: SPEC_KEYWORDS,
    TagDictionaryEntry.KIND_HEAT_TREATMENT: HEAT_TREATMENT_KEYWORDS,
}


def _seed_mapping(kind: str) -> dict[str, list[str]]:
    return {canonical: list(candidates) for canonical, candidates in KIND_TO_SEED.get(kind, {}).items()}


def load_keyword_mapping(kind: str) -> dict[str, list[str]]:
    """{正規名: [照合候補...]} を返す。DB辞書(GUI編集)を正とし、空ならseedへフォールバックする。

    正規化はDjango外(単体テスト等)からも呼ばれるため、DBへ到達できない場合も
    seed で動作を継続する。
    """
    try:
        entries = list(
            TagDictionaryEntry.objects.filter(kind=kind, enabled=True).order_by("priority", "id")
        )
    except Exception:  # DB未整備・テスト環境などでは seed で継続する
        return _seed_mapping(kind)

    if not entries:
        return _seed_mapping(kind)

    mapping: dict[str, list[str]] = {}
    for entry in entries:
        candidates: list[str] = []
        for candidate in [entry.canonical_value, *(entry.aliases_json or [])]:
            text = str(candidate).strip()
            if text and text not in candidates:
                candidates.append(text)
        if candidates:
            mapping[entry.canonical_value] = candidates
    return mapping or _seed_mapping(kind)
