"""正規化コアの後方互換な公開入口を提供する。

既存の呼び出し側がimport先を変更せずに済むよう、公開関数だけを再公開する。
実装は責務別モジュールへ分割し、変更時の影響範囲を追いやすくしている。
"""
from __future__ import annotations

from icad_tag_extraction.normalization_2d import normalize_identity_name_value
from icad_tag_extraction.normalization_pipeline import normalize_raw_extract

__all__ = ["normalize_identity_name_value", "normalize_raw_extract"]
