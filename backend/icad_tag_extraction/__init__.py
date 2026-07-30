"""ICAD・STEP・DXFのraw抽出を正規化し、根拠付きタグを生成する独立コア。

本パッケージはDjangoをimportせず、設定と辞書providerを引数で受け取る。
Django連携は`apps.drawing_metadata.services`側のadapterが担当する。
"""

from icad_tag_extraction.configuration import DEFAULT_CONFIG, ExtractionConfig
from icad_tag_extraction.dictionary_provider import (
    DictionaryProvider,
    MappingDictionaryProvider,
    SeedDictionaryProvider,
    load_json_dictionary_provider,
)
from icad_tag_extraction.pipeline import process_extraction

__all__ = [
    "DEFAULT_CONFIG",
    "DictionaryProvider",
    "ExtractionConfig",
    "MappingDictionaryProvider",
    "SeedDictionaryProvider",
    "load_json_dictionary_provider",
    "process_extraction",
]
