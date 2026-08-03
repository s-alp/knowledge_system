"""2D・3D正規化の両方で使う、小さな副作用なしヘルパーを定義する。

このモジュールは値の重複除去だけを担当し、CAD形式や辞書の意味を持たない。
責務別モジュール間の循環importを避けるため、共通処理をここへ分離している。
"""
from __future__ import annotations

from collections.abc import Iterable


def _merge_unique(items: Iterable) -> list:
    """入力順を維持したまま、同じ値を2回目以降だけ除外する。"""

    result: list = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


__all__ = ["_merge_unique"]
