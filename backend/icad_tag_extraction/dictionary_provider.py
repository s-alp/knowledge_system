"""タグ・属性正規化で使う辞書の入出力境界を定義する。

コア処理はDjango ORMや特定DBを知らず、本モジュールのproviderから
「辞書種別 -> 正規名と別名一覧」を受け取る。DB、JSON、固定seedの違いは呼び出し側で吸収する。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol
import json

from icad_tag_extraction.seed_dictionaries import (
    CUSTOMER_KEYWORDS,
    EQUIPMENT_CATEGORY_KEYWORDS,
    HEAT_TREATMENT_KEYWORDS,
    MAKER_KEYWORDS,
    PART_NAME_KEYWORDS,
    SPEC_KEYWORDS,
)


KIND_CUSTOMER = "customer"
KIND_EQUIPMENT_CATEGORY = "equipment_category"
KIND_PROJECT = "project"
KIND_MAKER = "maker"
KIND_SPEC = "spec"
KIND_HEAT_TREATMENT = "heat_treatment"
KIND_PART_NAME = "part_name"

DICTIONARY_KINDS = (
    KIND_CUSTOMER,
    KIND_EQUIPMENT_CATEGORY,
    KIND_PROJECT,
    KIND_MAKER,
    KIND_SPEC,
    KIND_HEAT_TREATMENT,
    KIND_PART_NAME,
)

SEED_DICTIONARIES: dict[str, dict[str, list[str]]] = {
    KIND_CUSTOMER: CUSTOMER_KEYWORDS,
    KIND_EQUIPMENT_CATEGORY: EQUIPMENT_CATEGORY_KEYWORDS,
    KIND_PROJECT: {},
    KIND_MAKER: MAKER_KEYWORDS,
    KIND_SPEC: SPEC_KEYWORDS,
    KIND_HEAT_TREATMENT: HEAT_TREATMENT_KEYWORDS,
    KIND_PART_NAME: PART_NAME_KEYWORDS,
}


class DictionaryConfigurationError(ValueError):
    """辞書の種別、正規名、別名一覧が契約を満たさない場合に送出する。"""


class DictionaryProvider(Protocol):
    """正規化コアへ辞書を渡す最小インターフェース。"""

    def get_mapping(self, kind: str) -> dict[str, list[str]]:
        """指定種別の辞書を、正規名をキーとする新しいdictとして返す。"""


def normalize_dictionary_mapping(
    kind: str,
    mapping: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    """外部辞書を検証・正規化し、照合に使用できる独立コピーを返す。

    空の辞書は案件辞書などで正当な状態なので許可する。一方、不明種別、空の正規名、
    文字列でない別名は曖昧な照合を生むため、既定値へ置き換えず明示的に失敗する。
    """

    if kind not in DICTIONARY_KINDS:
        raise DictionaryConfigurationError(f"未対応の辞書種別です: {kind}")
    if not isinstance(mapping, Mapping):
        raise DictionaryConfigurationError(f"{kind}辞書はobject形式で指定してください。")

    normalized: dict[str, list[str]] = {}
    for canonical_value, aliases in mapping.items():
        canonical_text = str(canonical_value).strip()
        if not canonical_text:
            raise DictionaryConfigurationError(f"{kind}辞書に空の正規名があります。")
        if isinstance(aliases, (str, bytes)) or not isinstance(aliases, Sequence):
            raise DictionaryConfigurationError(
                f"{kind}.{canonical_text}の別名は文字列配列で指定してください。"
            )

        candidates: list[str] = []
        for candidate in (canonical_text, *aliases):
            if not isinstance(candidate, str):
                raise DictionaryConfigurationError(
                    f"{kind}.{canonical_text}の別名に文字列以外が含まれています。"
                )
            candidate_text = candidate.strip()
            if candidate_text and candidate_text not in candidates:
                candidates.append(candidate_text)
        if not candidates:
            raise DictionaryConfigurationError(f"{kind}.{canonical_text}に照合語がありません。")
        normalized[canonical_text] = candidates
    return normalized


class SeedDictionaryProvider:
    """同梱seed辞書だけを使う、DB非依存のprovider。"""

    def get_mapping(self, kind: str) -> dict[str, list[str]]:
        if kind not in SEED_DICTIONARIES:
            raise DictionaryConfigurationError(f"未対応の辞書種別です: {kind}")
        return normalize_dictionary_mapping(kind, SEED_DICTIONARIES[kind])


class MappingDictionaryProvider:
    """メモリ上の辞書を使うprovider。

    JSON読込や呼び出し側DBの変換後データを受け取る用途を想定し、
    生成時に全種別を検証してから保持する。
    """

    def __init__(self, mappings: Mapping[str, Mapping[str, Sequence[str]]]) -> None:
        unknown_kinds = sorted(set(mappings) - set(DICTIONARY_KINDS))
        if unknown_kinds:
            raise DictionaryConfigurationError(
                f"未対応の辞書種別が含まれています: {', '.join(unknown_kinds)}"
            )
        self._mappings = {
            kind: normalize_dictionary_mapping(kind, mappings.get(kind, {}))
            for kind in DICTIONARY_KINDS
        }

    def get_mapping(self, kind: str) -> dict[str, list[str]]:
        if kind not in self._mappings:
            raise DictionaryConfigurationError(f"未対応の辞書種別です: {kind}")
        return {
            canonical_value: list(candidates)
            for canonical_value, candidates in self._mappings[kind].items()
        }


def load_json_dictionary_provider(path: str | Path) -> MappingDictionaryProvider:
    """UTF-8 JSON辞書を読み込み、検証済みproviderを返す。

    ファイル不存在、文字コード不正、JSON不正、辞書契約違反は呼び出し元へ伝える。
    読み込み失敗時にseedへ切り替えると運用辞書の欠落を見逃すため、自動フォールバックしない。
    """

    dictionary_path = Path(path)
    with dictionary_path.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, Mapping):
        raise DictionaryConfigurationError("辞書JSONの最上位はobject形式で指定してください。")
    return MappingDictionaryProvider(payload)
