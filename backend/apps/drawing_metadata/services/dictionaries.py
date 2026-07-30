"""Django DB辞書と社内seedを、外部共有可能な独立Pythonコアへ接続する。

DBに有効行がある場合はその値を正とし、未登録の種別だけ社内seedを使用する。
接続失敗や未対応設定は握り潰さず、呼び出し元へ明示的に送出する。
"""

from __future__ import annotations

from django.conf import settings

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.internal_seed_dictionaries import (
    INTERNAL_CUSTOMER_KEYWORDS,
    INTERNAL_SPEC_KEYWORDS,
)
from icad_tag_extraction.dictionary_provider import (
    DictionaryProvider,
    KIND_CUSTOMER,
    KIND_EQUIPMENT_CATEGORY,
    KIND_HEAT_TREATMENT,
    KIND_MAKER,
    KIND_PART_NAME,
    KIND_PROJECT,
    KIND_SPEC,
    MappingDictionaryProvider,
    SEED_DICTIONARIES,
    normalize_dictionary_mapping,
)

# 独立コアは外部共有可能な一般辞書だけを持つ。当社内の客先seedはDjango adapterで合成し、
# 管理コマンド・DB未投入時の双方で既存の社内挙動を維持する。
KIND_TO_SEED = {
    kind: (
        {canonical: list(aliases) for canonical, aliases in INTERNAL_CUSTOMER_KEYWORDS.items()}
        if kind == KIND_CUSTOMER
        else {canonical: list(aliases) for canonical, aliases in INTERNAL_SPEC_KEYWORDS.items()}
        if kind == KIND_SPEC
        else {canonical: list(aliases) for canonical, aliases in mapping.items()}
    )
    for kind, mapping in SEED_DICTIONARIES.items()
}


_MODEL_KIND_BY_CORE_KIND = {
    KIND_CUSTOMER: TagDictionaryEntry.KIND_CUSTOMER,
    KIND_EQUIPMENT_CATEGORY: TagDictionaryEntry.KIND_EQUIPMENT_CATEGORY,
    KIND_PROJECT: TagDictionaryEntry.KIND_PROJECT,
    KIND_MAKER: TagDictionaryEntry.KIND_MAKER,
    KIND_SPEC: TagDictionaryEntry.KIND_SPEC,
    KIND_HEAT_TREATMENT: TagDictionaryEntry.KIND_HEAT_TREATMENT,
    KIND_PART_NAME: TagDictionaryEntry.KIND_PART_NAME,
}


class DjangoDictionaryProvider:
    """Django DBの有効辞書を独立コアへ渡すadapter。

    有効行が0件の種別だけは仕様どおりseedを使用する。DB接続失敗やテーブル不備は
    辞書未登録とは異なる運用障害なので握り潰さず、そのまま呼び出し元へ送出する。
    """

    def __init__(self) -> None:
        self._seed_provider = MappingDictionaryProvider(KIND_TO_SEED)

    def get_mapping(self, kind: str) -> dict[str, list[str]]:
        model_kind = _MODEL_KIND_BY_CORE_KIND.get(kind)
        if model_kind is None:
            return normalize_dictionary_mapping(kind, {})

        entries = list(
            TagDictionaryEntry.objects.filter(kind=model_kind, enabled=True).order_by("priority", "id")
        )
        if not entries:
            return self._seed_provider.get_mapping(kind)

        mapping = {
            entry.canonical_value: list(entry.aliases_json or [])
            for entry in entries
        }
        return normalize_dictionary_mapping(kind, mapping)


def get_dictionary_provider() -> DictionaryProvider:
    """Django設定で明示された辞書取得方式を返す。

    通常運用は`database`、DBを使わない単体テストや限定ツールは`seed`を指定する。
    不明な設定値を暗黙に読み替えずエラーにして、辞書の適用元を監査可能にする。
    """

    source = settings.DRAWING_METADATA_DICTIONARY_SOURCE
    if source == "database":
        return DjangoDictionaryProvider()
    if source == "seed":
        return MappingDictionaryProvider(KIND_TO_SEED)
    raise ValueError(f"未対応のDRAWING_METADATA_DICTIONARY_SOURCEです: {source}")


def load_keyword_mapping(kind: str) -> dict[str, list[str]]:
    """既存Djangoコード向けに、設定済みproviderの辞書を返す。"""

    return get_dictionary_provider().get_mapping(kind)
