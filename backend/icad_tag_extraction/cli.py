"""独立タグ抽出コアをJSON、STEP、DXFから実行するコマンドライン入口。

創屋側でDjangoへ組み込む前の受入確認と、手動・バッチ処理に使用する。
入力を上書きせず、正常完了時だけ指定出力へUTF-8 JSONを書き込む。
"""
from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
import json

from icad_tag_extraction.configuration import DEFAULT_CONFIG, ExtractionConfig
from icad_tag_extraction.dictionary_provider import (
    SeedDictionaryProvider,
    load_json_dictionary_provider,
)
from icad_tag_extraction.generic_cad_extractor import extract_generic_cad_metadata
from icad_tag_extraction.pipeline import process_extraction


def build_parser() -> ArgumentParser:
    """CLI引数を定義し、実行環境に依存しないparserを返す。"""

    parser = ArgumentParser(
        prog="icad-tag-extraction",
        description="C# raw JSON、STEP、DXFを正規化し、根拠付きタグJSONを生成します。",
    )
    parser.add_argument("--input", required=True, type=Path, help="raw JSON、STEP、STP、DXFの入力パス")
    parser.add_argument("--output", required=True, type=Path, help="処理結果JSONの出力パス")
    parser.add_argument("--dictionary", type=Path, help="任意のUTF-8 JSON辞書。未指定時は同梱seedを使用")
    parser.add_argument("--source-kind", choices=("2d", "3d"), help="CAD入力時の種別。DXF=2d、STEP=3dを既定")
    parser.add_argument("--schema-version", default=DEFAULT_CONFIG.schema_version)
    parser.add_argument("--normalizer-version", default=DEFAULT_CONFIG.normalizer_version)
    parser.add_argument("--tag-rule-version", default=DEFAULT_CONFIG.tag_rule_version)
    return parser


def _load_raw_payload(args: Namespace, config: ExtractionConfig) -> dict:
    input_path = args.input.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"入力ファイルが存在しません: {input_path}")

    extension = input_path.suffix.lower()
    if extension == ".json":
        with input_path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
        if not isinstance(payload, dict):
            raise ValueError("入力JSONの最上位はobject形式が必要です。")
        return payload

    if extension in {".step", ".stp"}:
        source_format = "step"
        source_kind = args.source_kind or "3d"
    elif extension == ".dxf":
        source_format = "dxf"
        source_kind = args.source_kind or "2d"
    else:
        raise ValueError(f"未対応の入力拡張子です: {extension or '(拡張子なし)'}")

    return extract_generic_cad_metadata(
        input_path=str(input_path),
        source_format=source_format,
        source_kind=source_kind,
        config=config,
    )


def run(args: Namespace) -> dict:
    """検証済み設定・辞書で入力を処理し、出力JSONを書き込む。"""

    config = ExtractionConfig(
        schema_version=args.schema_version,
        normalizer_version=args.normalizer_version,
        tag_rule_version=args.tag_rule_version,
    )
    provider = (
        load_json_dictionary_provider(args.dictionary)
        if args.dictionary
        else SeedDictionaryProvider()
    )
    result = process_extraction(
        _load_raw_payload(args, config),
        config=config,
        dictionary_provider=provider,
    )

    output_path = args.output.resolve()
    if output_path == args.input.resolve():
        raise ValueError("入力ファイルと出力ファイルには別のパスを指定してください。")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    """コマンドライン引数を処理し、成功時に終了コード0を返す。"""

    run(build_parser().parse_args())
    return 0
