"""創屋向け最小パッケージが単独で処理・契約検証できることを確認する。

実行前提:
- パッケージ直下で `python -m pip install -e python` を実行する。
- `python -m pip install -r python/requirements-dev.txt` でテスト依存を入れる。

失敗時は、Pythonソース、初期辞書、Schema、2D/3D例のどこに差分があるかを確認する。
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from icad_tag_extraction.dictionary_provider import load_json_dictionary_provider
from icad_tag_extraction.pipeline import process_extraction


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = PACKAGE_ROOT / "schemas"
RAW_EXAMPLE_ROOT = PACKAGE_ROOT / "examples" / "raw"
RESULT_EXAMPLE_ROOT = PACKAGE_ROOT / "examples" / "results"
DICTIONARY_PATH = PACKAGE_ROOT / "dictionaries" / "initial-dictionaries.json"


def _load_schemas() -> dict[str, dict]:
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json"))
    }


def _schema_registry(schemas: dict[str, dict]) -> Registry:
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
    )


def test_python_core_imports_without_django() -> None:
    """Djangoをインストールしていない環境でもコアを読み込めることを別プロセスで確認する。"""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "python")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import icad_tag_extraction.pipeline; "
                "assert 'django' not in sys.modules"
            ),
        ],
        cwd=PACKAGE_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_2d_and_3d_examples_match_schemas_and_expected_results() -> None:
    """C#入力例からの結果が同梱済みの期待値と完全一致することを確認する。"""

    schemas = _load_schemas()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    raw_validator = Draft202012Validator(
        schemas["icad-csharp-raw-extraction.v1.schema.json"]
    )
    result_validator = Draft202012Validator(
        schemas["icad-tag-extraction-result.v1.schema.json"],
        registry=_schema_registry(schemas),
    )
    dictionary_provider = load_json_dictionary_provider(DICTIONARY_PATH)
    raw_paths = sorted(RAW_EXAMPLE_ROOT.glob("csharp_raw_*.v1.json"))

    assert {path.name for path in raw_paths} == {
        "csharp_raw_2d.v1.json",
        "csharp_raw_3d.v1.json",
    }
    for raw_path in raw_paths:
        raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_validator.validate(raw_payload)
        actual = process_extraction(
            raw_payload,
            dictionary_provider=dictionary_provider,
        )
        expected_path = RESULT_EXAMPLE_ROOT / raw_path.name.replace(
            "csharp_raw",
            "tagged_result",
        )
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        assert actual == expected
        result_validator.validate(actual)


def test_equipment_category_uses_top_level_business_name_before_child_parts() -> None:
    """最上位の業務名称が、子部品名や「組立図」という図面種別より優先されることを確認する。"""

    dictionary_provider = load_json_dictionary_provider(DICTIONARY_PATH)
    result = process_extraction(
        {
            "source_format": "icad",
            "source_kind": "3d",
            "raw_extract": {
                "parts": [
                    {
                        "tree_path": ["SAMPLE-TOP"],
                        "name": "SAMPLE-TOP",
                        "depth": 0,
                        "ex_info_fields": {
                            "User_WBHNA": "シュート中間部(SAMPLE内) 組立図",
                        },
                    },
                    {
                        "tree_path": ["SAMPLE-TOP", "SAMPLE-CHILD"],
                        "name": "SAMPLE-CHILD",
                        "depth": 1,
                        "ex_info_fields": {
                            "User_WBHNA": "アーム",
                        },
                    },
                ]
            },
        },
        dictionary_provider=dictionary_provider,
    )

    assert result["canonical_attributes"]["equipment_category"] == "シュート"
    assert any(tag["tag"] == "装置:シュート" for tag in result["derived_tags"])


def test_paint_instruction_ignores_split_labels_and_keeps_explicit_code() -> None:
    """分割見出しを塗装値にせず、文字列だけで確定できる架空のKS番号を採用する。"""

    dictionary_provider = load_json_dictionary_provider(DICTIONARY_PATH)
    result = process_extraction(
        {
            "source_format": "icad",
            "source_kind": "2d",
            "raw_extract": {
                "texts": [
                    {"text_lines": ["PAINT OR"], "inside_print_area": True},
                    {"text_lines": ["PORTION"], "inside_print_area": True},
                    {"text_lines": ["KS42"], "inside_print_area": True},
                ]
            },
        },
        dictionary_provider=dictionary_provider,
    )

    canonical = result["canonical_attributes"]
    assert canonical["paint_instruction_tokens"] == ["KS42"]
    assert canonical["paint"] == "KS42"
    assert any(tag["tag"] == "塗装:KS42" for tag in result["derived_tags"])
    assert all(tag["tag"] != "塗装:OR" for tag in result["derived_tags"])
