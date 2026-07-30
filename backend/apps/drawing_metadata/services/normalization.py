"""独立正規化コアへDjangoの設定と辞書providerを渡す互換adapter。"""
from __future__ import annotations

from apps.drawing_metadata.services.core_adapter import get_normalization_dependencies
from icad_tag_extraction.configuration import ExtractionConfig
from icad_tag_extraction.dictionary_provider import DictionaryProvider
from icad_tag_extraction.normalization import (
    normalize_identity_name_value,
    normalize_raw_extract as _normalize_raw_extract,
)


def normalize_raw_extract(
    raw_payload: dict,
    *,
    config: ExtractionConfig | None = None,
    dictionary_provider: DictionaryProvider | None = None,
) -> dict:
    """既存Django契約を維持し、正規化本体は独立コアだけで実行する。"""

    default_config, default_provider = get_normalization_dependencies()
    return _normalize_raw_extract(
        raw_payload,
        config=config or default_config,
        dictionary_provider=dictionary_provider or default_provider,
    )


__all__ = ["normalize_identity_name_value", "normalize_raw_extract"]
