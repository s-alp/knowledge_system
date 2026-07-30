"""廃止済み外部AIメタデータを、現行の読取結果から除外する。

過去のsnapshot、ジョブwarning、監査JSONは検証証跡なので更新・削除しない。一方、
現行UI・API・RAG・照合処理へ旧AI分類項目を再露出させないため、DBから読み出した
JSONをレスポンスや合成処理へ渡す境界でコピーし、廃止済みキーだけを除外する。
"""

from __future__ import annotations

from copy import deepcopy


_RETIRED_AI_FIELD_PREFIXES = ("llm_", "title_block_llm_")
_RETIRED_AI_CAMEL_FIELDS = {
    "llmfield",
    "llmconfidence",
    "llmreason",
    "llmsource",
}
_RETIRED_AI_WARNING_PREFIX = "title_block_llm_"


def is_retired_ai_field_name(key: object) -> bool:
    """JSONキーが廃止済みAI互換項目かを判定する。"""

    if not isinstance(key, str):
        return False
    normalized = key.casefold()
    return normalized.startswith(_RETIRED_AI_FIELD_PREFIXES) or normalized in _RETIRED_AI_CAMEL_FIELDS


def contains_retired_ai_metadata(value: object) -> bool:
    """API入力に廃止済みAIキーが含まれるか、値を解釈せず再帰確認する。"""

    if isinstance(value, dict):
        return any(
            is_retired_ai_field_name(key) or contains_retired_ai_metadata(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_retired_ai_metadata(item) for item in value)
    return False


def strip_retired_ai_metadata(value):
    """DB値を変更せず、廃止済みAIキーを除いたJSON互換コピーを返す。"""

    if isinstance(value, dict):
        return {
            key: strip_retired_ai_metadata(item)
            for key, item in value.items()
            if not is_retired_ai_field_name(key)
        }
    if isinstance(value, list):
        return [strip_retired_ai_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(strip_retired_ai_metadata(item) for item in value)
    return deepcopy(value)


def filter_retired_ai_warnings(warnings: list | None) -> list:
    """旧AI warningを現行表示から除き、その他のwarningは内容を保持して返す。"""

    visible_warnings = []
    for warning in warnings or []:
        code = warning.get("code") if isinstance(warning, dict) else ""
        if isinstance(code, str) and code.casefold().startswith(_RETIRED_AI_WARNING_PREFIX):
            continue
        visible_warnings.append(strip_retired_ai_metadata(warning))
    return visible_warnings
