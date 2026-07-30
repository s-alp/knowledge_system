"""Djangoなしで正規化・辞書・タグ生成・CLIが完結することを検証する。

失敗時は、独立コアへDjango依存が逆流したか、辞書注入または入出力契約が崩れた可能性を確認する。
"""
from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import json
import subprocess
import sys

import pytest

from icad_tag_extraction.cli import run
from icad_tag_extraction.configuration import ExtractionConfig
from icad_tag_extraction.dictionary_provider import (
    DictionaryConfigurationError,
    MappingDictionaryProvider,
)
from icad_tag_extraction.pipeline import process_extraction


def _raw_payload() -> dict:
    return {
        "source_file": {
            "full_path": r"C:\fixtures\sample.icd",
            "file_name": "sample.icd",
        },
        "source_format": "icad",
        "source_kind": "2d",
        "warnings": [],
        "raw_extract": {
            "texts": [
                {
                    "text_lines": ["ABC工業", "専用搬送装置", "材質 SUS304"],
                    "inside_print_area": True,
                }
            ]
        },
    }


def _dictionary_payload() -> dict:
    return {
        "customer": {"ABC工業": ["ABC"]},
        "equipment_category": {"搬送装置": ["専用搬送装置"]},
        "project": {},
        "maker": {},
        "spec": {},
        "heat_treatment": {},
        "part_name": {},
    }


def test_process_extraction_uses_explicit_config_and_dictionary() -> None:
    config = ExtractionConfig(
        schema_version="test-schema",
        normalizer_version="test-normalizer",
        tag_rule_version="test-tags",
    )
    result = process_extraction(
        _raw_payload(),
        config=config,
        dictionary_provider=MappingDictionaryProvider(_dictionary_payload()),
    )

    assert result["canonical_attributes"]["customer_name"] == "ABC工業"
    assert result["canonical_attributes"]["equipment_category"] == "搬送装置"
    assert result["canonical_attributes"]["normalizer_version"] == "test-normalizer"
    assert {item["tag"] for item in result["derived_tags"]} >= {
        "客先:ABC工業",
        "装置:搬送装置",
        "材質:SUS304",
    }
    assert {item["tag_rule_version"] for item in result["derived_tags"]} == {"test-tags"}


def test_invalid_dictionary_does_not_fall_back_to_seed() -> None:
    with pytest.raises(DictionaryConfigurationError, match="文字列配列"):
        MappingDictionaryProvider(
            {
                **_dictionary_payload(),
                "customer": {"ABC工業": "ABC"},
            }
        )


def test_cli_writes_tagged_result_without_django(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.json"
    dictionary_path = tmp_path / "dictionaries.json"
    output_path = tmp_path / "result.json"
    input_path.write_text(json.dumps(_raw_payload(), ensure_ascii=False), encoding="utf-8")
    dictionary_path.write_text(
        json.dumps(_dictionary_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = run(
        Namespace(
            input=input_path,
            output=output_path,
            dictionary=dictionary_path,
            source_kind=None,
            schema_version="1.0.0",
            normalizer_version="1.1.0",
            tag_rule_version="1.1.0",
        )
    )

    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8")) == result


def test_package_import_does_not_load_django() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "from icad_tag_extraction import process_extraction; "
            "assert 'django' not in sys.modules; "
            "print(process_extraction.__module__)"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=backend_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "icad_tag_extraction.pipeline"
