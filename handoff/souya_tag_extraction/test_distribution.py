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
