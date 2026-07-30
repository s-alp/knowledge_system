"""raw抽出からcanonical属性と根拠付きタグまでを1回で生成する公開パイプライン。

C# RunnerまたはSTEP/DXF抽出器のJSONを受け取り、正規化とタグ生成を同じ設定・辞書で実行する。
DB保存や本番API登録は行わず、創屋側が任意の保存先へ接続できる決定的な結果だけを返す。
"""
from __future__ import annotations

from icad_tag_extraction.configuration import DEFAULT_CONFIG, ExtractionConfig
from icad_tag_extraction.dictionary_provider import (
    DictionaryProvider,
    SeedDictionaryProvider,
)
from icad_tag_extraction.normalization import normalize_raw_extract
from icad_tag_extraction.tag_builder import build_derived_tags


def process_extraction(
    raw_payload: dict,
    *,
    config: ExtractionConfig = DEFAULT_CONFIG,
    dictionary_provider: DictionaryProvider | None = None,
) -> dict:
    """C#またはgeneric raw JSONを正規化し、配布契約の処理結果を返す。

    `source_format`、`source_kind`、`raw_extract`が無い入力はC#・Python境界を満たさないため
    明示的に拒否する。処理中にファイル、DB、外部APIを変更する副作用はない。
    """

    if not isinstance(raw_payload, dict):
        raise TypeError("raw_payloadはobject形式で指定してください。")
    source_format = raw_payload.get("source_format")
    source_kind = raw_payload.get("source_kind")
    raw_extract = raw_payload.get("raw_extract")
    if not isinstance(source_format, str) or not source_format.strip():
        raise ValueError("raw_payload.source_formatは空でない文字列が必要です。")
    if source_kind not in {"2d", "3d"}:
        raise ValueError("raw_payload.source_kindは2dまたは3dが必要です。")
    if not isinstance(raw_extract, dict):
        raise ValueError("raw_payload.raw_extractはobject形式が必要です。")

    provider = dictionary_provider or SeedDictionaryProvider()
    canonical_attributes = normalize_raw_extract(
        raw_payload,
        config=config,
        dictionary_provider=provider,
    )
    derived_tags = build_derived_tags(
        canonical_attributes,
        config=config,
    )
    return {
        "schema_version": config.schema_version,
        "normalizer_version": config.normalizer_version,
        "tag_rule_version": config.tag_rule_version,
        "source_file": raw_payload.get("source_file") or {},
        "source_format": source_format,
        "source_kind": source_kind,
        "raw_extract": raw_extract,
        "canonical_attributes": canonical_attributes,
        "derived_tags": derived_tags,
        "warnings": list(raw_payload.get("warnings") or []),
    }
