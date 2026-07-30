"""Django設定・DB辞書を独立タグ抽出コアへ接続するadapter。

このファイルだけがDjango settingsと辞書DBを認識し、正規化・タグ生成コアへ
明示的な設定オブジェクトとproviderを渡す。コア側へDjango依存を逆流させない。
"""
from __future__ import annotations

from django.conf import settings

from apps.drawing_metadata.services.dictionaries import get_dictionary_provider
from icad_tag_extraction.configuration import ExtractionConfig
from icad_tag_extraction.dictionary_provider import DictionaryProvider


def get_extraction_config() -> ExtractionConfig:
    """Djangoの現行バージョン設定を独立コアの設定型へ変換する。"""

    return ExtractionConfig(
        schema_version=settings.DRAWING_METADATA_SCHEMA_VERSION,
        normalizer_version=settings.DRAWING_METADATA_NORMALIZER_VERSION,
        tag_rule_version=settings.DRAWING_METADATA_TAG_RULE_VERSION,
    )


def get_normalization_dependencies() -> tuple[ExtractionConfig, DictionaryProvider]:
    """正規化1回分の設定と辞書providerを同じ時点で確定して返す。"""

    return get_extraction_config(), get_dictionary_provider()
