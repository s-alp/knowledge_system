"""C#契約と独立Pythonコアから創屋引き渡し用JSON Schemaを生成・検査する。

実行目的:
- `Models.cs`の公開DTOをsnake_case JSON Schemaへ変換し、C#からPythonへの境界を固定する。
- Pythonのcanonical全キーとderived tagの型を機械可読Schemaとして固定する。

前提:
- Python 3.12
- `backend`配下の`icad_tag_extraction`をimportできること

失敗時:
- C#型の解析不能、Schema自己検証失敗、`--check`時の生成差分を明示して終了する。
- 既存Schemaを推測で補修せず、生成規則またはC#契約を確認する。
"""
from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Mapping
from pathlib import Path
import json
import re
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
SCHEMA_ROOT = ROOT / "schemas" / "tag_extraction"
EXAMPLE_ROOT = ROOT / "examples" / "tag_extraction_contract"
CSHARP_MODELS_PATH = ROOT / "src" / "IcadExtraction.Contracts" / "Models.cs"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from icad_tag_extraction.normalization import normalize_raw_extract  # noqa: E402


_CLASS_RE = re.compile(r"^\s*public sealed class (?P<name>[A-Za-z0-9_]+)\s*$")
_PROPERTY_RE = re.compile(
    r"^\s*public (?P<type>.+?) (?P<name>[A-Za-z0-9_]+) \{ get; set; \}"
)
_PASCAL_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _snake_case(value: str) -> str:
    return _PASCAL_BOUNDARY_RE.sub("_", value).lower()


def _parse_csharp_classes(source: str) -> dict[str, list[tuple[str, str]]]:
    """公開DTOとプロパティ型を行単位で収集する。

    `Models.cs`は公開プロパティを1行で宣言する規約なので、C#コンパイラを起動せず
    契約監査できる。クラスを検出できない場合はSchemaを生成せず失敗する。
    """

    classes: dict[str, list[tuple[str, str]]] = {}
    current_class: str | None = None
    for line in source.splitlines():
        class_match = _CLASS_RE.match(line)
        if class_match:
            current_class = class_match.group("name")
            classes[current_class] = []
            continue
        property_match = _PROPERTY_RE.match(line)
        if current_class and property_match:
            classes[current_class].append(
                (property_match.group("name"), property_match.group("type").strip())
            )
    if "ExtractionEnvelope" not in classes:
        raise ValueError("Models.csからExtractionEnvelopeを検出できません。")
    return classes


def _split_generic_arguments(value: str) -> list[str]:
    arguments: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "<":
            depth += 1
        elif character == ">":
            depth -= 1
        elif character == "," and depth == 0:
            arguments.append(value[start:index].strip())
            start = index + 1
    arguments.append(value[start:].strip())
    return arguments


def _csharp_type_schema(type_name: str, known_classes: set[str]) -> dict:
    nullable = type_name.endswith("?")
    normalized = type_name[:-1] if nullable else type_name

    if normalized.startswith("List<") and normalized.endswith(">"):
        item_type = normalized[5:-1].strip()
        schema: dict = {
            "type": "array",
            "items": _csharp_type_schema(item_type, known_classes),
        }
    elif normalized.startswith("Dictionary<") and normalized.endswith(">"):
        key_type, value_type = _split_generic_arguments(normalized[11:-1])
        if key_type != "string":
            raise ValueError(f"未対応のDictionaryキー型です: {type_name}")
        schema = {
            "type": "object",
            "additionalProperties": _csharp_type_schema(value_type, known_classes),
        }
    elif normalized == "string":
        schema = {"type": "string"}
    elif normalized in {"int", "long"}:
        schema = {"type": "integer"}
    elif normalized == "double":
        schema = {"type": "number"}
    elif normalized == "bool":
        schema = {"type": "boolean"}
    elif normalized == "object":
        schema = {}
    elif normalized in known_classes:
        schema = {"$ref": f"#/$defs/{normalized}"}
    else:
        raise ValueError(f"JSON Schemaへ変換できないC#型です: {type_name}")

    if not nullable:
        return schema
    if "$ref" in schema:
        return {"anyOf": [schema, {"type": "null"}]}
    if "type" in schema:
        nullable_type = schema["type"]
        return {**schema, "type": [nullable_type, "null"]}
    return {"anyOf": [schema, {"type": "null"}]}


def _csharp_schema() -> dict:
    classes = _parse_csharp_classes(CSHARP_MODELS_PATH.read_text(encoding="utf-8-sig"))
    known_classes = set(classes)
    definitions: dict[str, dict] = {}
    for class_name, properties in classes.items():
        property_schemas = {
            _snake_case(property_name): _csharp_type_schema(type_name, known_classes)
            for property_name, type_name in properties
        }
        definitions[class_name] = {
            "type": "object",
            "properties": property_schemas,
            "required": list(property_schemas),
            "additionalProperties": False,
        }

    source_file = definitions["SourceFilePayload"]["properties"]
    source_file["sx_net_input_strategy"]["enum"] = [
        "original",
        "windows_short_path",
        "temporary_copy",
        "temporary_copy_forced",
    ]

    envelope = definitions["ExtractionEnvelope"]["properties"]
    envelope["source_format"] = {"const": "icad"}
    envelope["source_kind"] = {"enum": ["2d", "3d"]}
    envelope["raw_extract"] = {
        "oneOf": [
            {"$ref": "#/$defs/RawExtract2DPayload"},
            {"$ref": "#/$defs/RawExtract3DPayload"},
        ]
    }
    definitions["ExtractionEnvelope"]["allOf"] = [
        {
            "if": {"properties": {"source_kind": {"const": "2d"}}},
            "then": {
                "properties": {
                    "raw_extract": {"$ref": "#/$defs/RawExtract2DPayload"}
                }
            },
        },
        {
            "if": {"properties": {"source_kind": {"const": "3d"}}},
            "then": {
                "properties": {
                    "raw_extract": {"$ref": "#/$defs/RawExtract3DPayload"}
                }
            },
        },
    ]

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://alpine.example/schemas/icad-csharp-raw-extraction.v1.schema.json",
        "title": "ICAD C# raw extraction envelope",
        "description": (
            "IcadExtraction.Contracts.Models.csを正本として生成した、"
            "C# RunnerからPython正規化コアへの入力契約。"
        ),
        "$ref": "#/$defs/ExtractionEnvelope",
        "$defs": definitions,
    }


def _observed_json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError(f"canonical型をSchemaへ変換できません: {type(value).__name__}")


def _schema_for_observed_values(values: list[object]) -> dict:
    """2D/3Dで異なる既定値を統合し、現行canonicalの型を固定する。"""

    observed_types = {_observed_json_type(value) for value in values}
    if observed_types == {"null"}:
        # 値がない空入力だけでは実型を特定できないため、現行の任意型契約を維持する。
        return {
            "type": ["array", "boolean", "integer", "number", "object", "string", "null"]
        }
    if "number" in observed_types:
        # JSON Schemaのnumberはintegerも含むため、重複するinteger指定は除く。
        observed_types.discard("integer")
    ordered_types = [
        schema_type
        for schema_type in ("array", "boolean", "integer", "number", "object", "string", "null")
        if schema_type in observed_types
    ]
    return {"type": ordered_types[0] if len(ordered_types) == 1 else ordered_types}


def _canonical_schema() -> dict:
    canonical_samples = [
        normalize_raw_extract(
            {
                "source_format": "icad",
                "source_kind": source_kind,
                "raw_extract": {},
            }
        )
        for source_kind in ("2d", "3d")
    ]
    canonical = canonical_samples[0]
    if any(set(sample) != set(canonical) for sample in canonical_samples[1:]):
        raise ValueError("2D/3Dでcanonical属性のキー集合が一致しません。")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://alpine.example/schemas/icad-canonical-attributes.v1.schema.json",
        "title": "ICAD canonical attributes",
        "description": (
            "独立Python正規化コアが常に返すキー集合を固定する。"
            "未抽出値はnullまたは空配列として保持する。"
        ),
        "type": "object",
        "properties": {
            key: _schema_for_observed_values(
                [sample[key] for sample in canonical_samples]
            )
            for key in canonical
        },
        "required": list(canonical),
        "additionalProperties": False,
    }


def _derived_tags_schema() -> dict:
    tag_item = {
        "type": "object",
        "properties": {
            "tag": {"type": "string", "minLength": 1},
            "source": {"type": "string", "minLength": 1},
            "evidence": {"type": "string", "minLength": 1},
            "confidence": {"enum": ["high", "medium", "low"]},
            "reason": {"type": "string", "minLength": 1},
            "manual_flag": {"type": "boolean"},
            "tag_rule_version": {"type": "string", "minLength": 1},
        },
        "required": [
            "tag",
            "source",
            "evidence",
            "confidence",
            "reason",
            "manual_flag",
            "tag_rule_version",
        ],
        "additionalProperties": False,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://alpine.example/schemas/icad-derived-tags.v1.schema.json",
        "title": "ICAD derived tags",
        "type": "array",
        "items": tag_item,
    }


def _result_schema(canonical_schema: Mapping, derived_tags_schema: Mapping) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://alpine.example/schemas/icad-tag-extraction-result.v1.schema.json",
        "title": "ICAD tag extraction result",
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "minLength": 1},
            "normalizer_version": {"type": "string", "minLength": 1},
            "tag_rule_version": {"type": "string", "minLength": 1},
            "source_file": {"type": "object"},
            "source_format": {"enum": ["icad", "step", "dxf"]},
            "source_kind": {"enum": ["2d", "3d"]},
            "raw_extract": {"type": "object"},
            "canonical_attributes": {
                "$ref": canonical_schema["$id"],
            },
            "derived_tags": {
                "$ref": derived_tags_schema["$id"],
            },
            "warnings": {"type": "array", "items": {"type": "object"}},
        },
        "required": [
            "schema_version",
            "normalizer_version",
            "tag_rule_version",
            "source_file",
            "source_format",
            "source_kind",
            "raw_extract",
            "canonical_attributes",
            "derived_tags",
            "warnings",
        ],
        "additionalProperties": False,
    }


def build_schemas() -> dict[str, dict]:
    canonical = _canonical_schema()
    derived_tags = _derived_tags_schema()
    return {
        "icad-csharp-raw-extraction.v1.schema.json": _csharp_schema(),
        "icad-canonical-attributes.v1.schema.json": canonical,
        "icad-derived-tags.v1.schema.json": derived_tags,
        "icad-tag-extraction-result.v1.schema.json": _result_schema(
            canonical,
            derived_tags,
        ),
    }


def _minimal_instance(schema: Mapping, root_schema: Mapping) -> object:
    """Schemaの必須項目を全て持つ最小instanceを再帰生成する。"""

    if "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/$defs/"
        if not ref.startswith(prefix):
            raise ValueError(f"最小instance生成で未対応のrefです: {ref}")
        return _minimal_instance(root_schema["$defs"][ref[len(prefix):]], root_schema)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "oneOf" in schema:
        return _minimal_instance(schema["oneOf"][0], root_schema)
    if "anyOf" in schema:
        non_null = [
            item
            for item in schema["anyOf"]
            if item.get("type") != "null"
        ]
        return _minimal_instance(non_null[0] if non_null else schema["anyOf"][0], root_schema)

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next(item for item in schema_type if item != "null")
    if schema_type == "object":
        properties = schema.get("properties", {})
        return {
            key: _minimal_instance(properties[key], root_schema)
            for key in schema.get("required", [])
        }
    if schema_type == "array":
        return []
    if schema_type == "string":
        return "sample"
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0.0
    if schema_type == "boolean":
        return False
    if not schema:
        return {}
    raise ValueError(f"最小instanceを生成できないSchemaです: {schema}")


def _csharp_contract_example(csharp_schema: Mapping, source_kind: str) -> dict:
    """C# DTOの全必須fieldを持つ匿名化済み2D/3D例を生成する。"""

    envelope_schema = csharp_schema["$defs"]["ExtractionEnvelope"]
    example = _minimal_instance(envelope_schema, csharp_schema)
    if not isinstance(example, dict):
        raise TypeError("ExtractionEnvelopeの最小instanceがobjectではありません。")

    filename = f"sample_{source_kind}.icd"
    example.update(
        {
            "input_path": rf"C:\fixtures\{filename}",
            "source_format": "icad",
            "source_kind": source_kind,
            "extraction_profile": "default",
            "extractor_name": "icad-csharp-extractor",
            "extractor_version": "1.0.0",
            "elapsed_ms": 1,
            "warnings": [],
        }
    )
    example["source_file"].update(
        {
            "full_path": rf"C:\fixtures\{filename}",
            "directory_path": r"C:\fixtures",
            "file_name": filename,
            "file_name_without_extension": f"sample_{source_kind}",
            "extension": ".icd",
            "sx_net_input_path": rf"C:\fixtures\{filename}",
            "sx_net_input_strategy": "original",
            "used_sx_net_alternate_path": False,
            "original_path_length": len(rf"C:\fixtures\{filename}"),
            "sx_net_input_path_length": len(rf"C:\fixtures\{filename}"),
        }
    )

    raw_definition = csharp_schema["$defs"][
        "RawExtract2DPayload" if source_kind == "2d" else "RawExtract3DPayload"
    ]
    raw_extract = _minimal_instance(raw_definition, csharp_schema)
    if not isinstance(raw_extract, dict):
        raise TypeError("raw_extractの最小instanceがobjectではありません。")
    if source_kind == "2d":
        text = _minimal_instance(csharp_schema["$defs"]["TextPayload"], csharp_schema)
        text.update(
            {
                "text_lines": ["材質 SUS304", "ガントリー"],
                "line_count": 2,
                "source_type": "text",
                "inside_print_area": True,
                "joined_text": "材質 SUS304 ガントリー",
            }
        )
        raw_extract["texts"] = [text]
    else:
        raw_extract["top_part"].update(
            {
                "name": "SAMPLE-3D",
                "comment": "ガントリー",
                "ex_info": "材質 SUS304",
                "ex_info_fields": {"material": "SUS304"},
            }
        )
    example["raw_extract"] = raw_extract
    return example


def build_contract_examples(schemas: Mapping[str, Mapping]) -> dict[str, dict]:
    csharp_schema = schemas["icad-csharp-raw-extraction.v1.schema.json"]
    return {
        "csharp_raw_2d.v1.json": _csharp_contract_example(csharp_schema, "2d"),
        "csharp_raw_3d.v1.json": _csharp_contract_example(csharp_schema, "3d"),
    }


def _serialized(schema: Mapping) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def write_or_check(*, check: bool) -> None:
    schemas = build_schemas()
    for filename, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        target = SCHEMA_ROOT / filename
        rendered = _serialized(schema)
        if check:
            if not target.is_file():
                raise FileNotFoundError(f"生成済みSchemaがありません: {target}")
            if target.read_text(encoding="utf-8") != rendered:
                raise ValueError(
                    f"Schemaが現行コードと一致しません。生成し直してください: {target}"
                )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")

    examples = build_contract_examples(schemas)
    csharp_schema = schemas["icad-csharp-raw-extraction.v1.schema.json"]
    validator = Draft202012Validator(csharp_schema)
    for filename, example in examples.items():
        validator.validate(example)
        target = EXAMPLE_ROOT / filename
        rendered = _serialized(example)
        if check:
            if not target.is_file():
                raise FileNotFoundError(f"生成済み契約例がありません: {target}")
            if target.read_text(encoding="utf-8") != rendered:
                raise ValueError(
                    f"契約例が現行C# Schemaと一致しません。生成し直してください: {target}"
                )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="ファイルを書き換えず、現行コードからの生成結果と一致するか確認する",
    )
    args = parser.parse_args()
    write_or_check(check=args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
