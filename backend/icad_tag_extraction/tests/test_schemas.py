"""C#・Python境界とPython処理結果がDraft 2020-12 Schemaを満たすことを検証する。

Schema自己検証、C# DTOからの再生成一致、代表処理結果のinstance検証を行う。
失敗時は`Models.cs`と生成Schema、または正規化キーのどちらが変わったかを確認する。
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import json

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from icad_tag_extraction.pipeline import process_extraction


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "schemas" / "tag_extraction"
GENERATOR_PATH = ROOT / "scripts" / "generate_tag_extraction_schemas.py"
EXAMPLE_ROOT = ROOT / "examples" / "tag_extraction_contract"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_tag_extraction_schemas", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Schema生成スクリプトを読み込めません: {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_generated_schemas_match_current_csharp_and_python_contracts() -> None:
    generator = _load_generator_module()
    expected = generator.build_schemas()
    actual = _load_schemas()

    assert actual == expected
    for schema in actual.values():
        Draft202012Validator.check_schema(schema)


def test_csharp_contract_examples_validate_for_2d_and_3d() -> None:
    schemas = _load_schemas()
    validator = Draft202012Validator(
        schemas["icad-csharp-raw-extraction.v1.schema.json"]
    )
    example_paths = sorted(EXAMPLE_ROOT.glob("csharp_raw_*.v1.json"))

    assert {path.name for path in example_paths} == {
        "csharp_raw_2d.v1.json",
        "csharp_raw_3d.v1.json",
    }
    for path in example_paths:
        validator.validate(json.loads(path.read_text(encoding="utf-8")))


def test_python_result_validates_against_canonical_tag_and_result_schemas() -> None:
    schemas = _load_schemas()
    registry = _schema_registry(schemas)
    canonical_schema = schemas["icad-canonical-attributes.v1.schema.json"]
    tags_schema = schemas["icad-derived-tags.v1.schema.json"]
    result_schema = schemas["icad-tag-extraction-result.v1.schema.json"]
    for path in sorted(EXAMPLE_ROOT.glob("csharp_raw_*.v1.json")):
        result = process_extraction(json.loads(path.read_text(encoding="utf-8")))

        Draft202012Validator(canonical_schema).validate(result["canonical_attributes"])
        Draft202012Validator(tags_schema).validate(result["derived_tags"])
        Draft202012Validator(result_schema, registry=registry).validate(result)
