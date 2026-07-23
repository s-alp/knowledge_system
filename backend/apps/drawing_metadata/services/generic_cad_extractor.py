from __future__ import annotations

import json
import re
import time
from pathlib import Path, PureWindowsPath

from django.conf import settings


GENERIC_CAD_EXTRACTOR_NAME = "generic-cad-text-extractor"
GENERIC_CAD_EXTRACTOR_VERSION = "1.0.0"

_STEP_STRING_RE = re.compile(r"'((?:[^']|'')*)'")
_STEP_ENTITY_RE = re.compile(r"#\d+\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
_MATERIAL_RE = re.compile(
    r"(?<![A-Z0-9])(SUS[0-9][0-9A-Z-]*|SS400[A-Z-]*|SPCC|S[0-9]{2}C|A[0-9]{4}P?|AL|SKD[0-9]*|SKS[0-9]*|SCM[0-9]*|FC[0-9]*|FCD[0-9]*|PETG|PET|POM|PVC|PTFE|PPS|NBR|EPDM|FKM|PP)(?![A-Z0-9])",
    re.IGNORECASE,
)
_STEP_PART_ENTITY_NAMES = {
    "PRODUCT",
    "PRODUCT_DEFINITION",
    "PRODUCT_DEFINITION_FORMATION",
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
    "MANIFOLD_SOLID_BREP",
    "ADVANCED_BREP_SHAPE_REPRESENTATION",
}


def extract_generic_cad_metadata(
    *,
    input_path: str,
    source_format: str,
    source_kind: str,
    output_path: Path,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
) -> dict:
    started = time.monotonic()
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"CADファイルが存在しません: {input_path}")
    if not path.is_file():
        raise ValueError(f"CAD入力がファイルではありません: {input_path}")

    text, encoding = _read_text(path)
    normalized_format = source_format.lower()
    if normalized_format == "step":
        raw_extract = _extract_step_raw(text=text, path=path)
    elif normalized_format == "dxf":
        raw_extract = _extract_dxf_raw(text=text)
    else:
        raise ValueError(f"汎用CAD抽出器の対象外です: {source_format}")

    warnings: list[dict] = []
    if not text.strip():
        warnings.append(
            {
                "code": "generic_cad_empty_text",
                "message": "CADファイルからテキストを読み取れませんでした。",
                "source": GENERIC_CAD_EXTRACTOR_NAME,
            }
        )

    payload = {
        "input_path": input_path,
        "source_file": _source_file_payload(input_path),
        "source_format": normalized_format,
        "source_kind": source_kind,
        "extractor_name": GENERIC_CAD_EXTRACTOR_NAME,
        "extractor_version": GENERIC_CAD_EXTRACTOR_VERSION,
        "schema_version": settings.DRAWING_METADATA_SCHEMA_VERSION,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "extraction_profile": extraction_profile or "default",
        "extraction_options": extraction_options or {},
        "warnings": warnings,
        "raw_extract": {
            **raw_extract,
            "generic_cad_text_encoding": encoding,
            "generic_cad_extraction_scope": "file_text_entities",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _read_text(path: Path) -> tuple[str, str]:
    content = path.read_bytes()
    for encoding in ("utf-8-sig", "cp932", "latin-1"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace"), "utf-8-replace"


def _source_file_payload(input_path: str) -> dict:
    windows_path = PureWindowsPath(input_path)
    return {
        "full_path": input_path,
        "directory_path": str(windows_path.parent),
        "file_name": windows_path.name,
        "file_name_without_extension": windows_path.stem,
        "extension": windows_path.suffix,
    }


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(stripped)
    return unique


def _step_strings(value: str) -> list[str]:
    return [item.replace("''", "'").strip() for item in _STEP_STRING_RE.findall(value) if item.strip()]


def _extract_materials(tokens: list[str]) -> list[str]:
    materials: list[str] = []
    for token in tokens:
        for matched in _MATERIAL_RE.finditer(token.upper()):
            materials.append(matched.group(1))
    return _unique_strings(materials)


def _extract_step_raw(*, text: str, path: Path) -> dict:
    all_strings = _unique_strings(_step_strings(text))
    part_names: list[str] = []
    for entity_name, body in _STEP_ENTITY_RE.findall(text):
        if entity_name.upper() not in _STEP_PART_ENTITY_NAMES:
            continue
        part_names.extend(_step_strings(body))
    part_names = _unique_strings(part_names)
    if not part_names and path.stem:
        part_names = [path.stem]

    model_name = part_names[0] if part_names else path.stem
    comment = next((value for value in all_strings if value != model_name), None)
    materials = _extract_materials(all_strings + part_names)
    parts = [
        {
            "tree_path": [name],
            "name": name,
            "comment": None,
            "materials": [material for material in materials if material.upper() in name.upper()],
        }
        for name in part_names[:200]
    ]
    if len(parts) == 1 and materials and not parts[0]["materials"]:
        parts[0]["materials"] = materials

    return {
        "model_info": {
            "name": model_name,
            "comment": comment,
            "path": str(path.parent),
        },
        "top_part": {
            "name": model_name,
            "comment": comment,
            "ex_info": " / ".join(all_strings[:20]),
        },
        "parts": parts,
        "materials": materials,
        "step_string_literals": all_strings[:500],
    }


def _extract_dxf_raw(*, text: str) -> dict:
    pairs = _dxf_group_pairs(text)
    texts: list[dict] = []
    dimensions: list[dict] = []
    primitives: list[dict] = []
    index = 0
    while index < len(pairs):
        code, value = pairs[index]
        if code != "0":
            index += 1
            continue
        entity_type = value.upper()
        next_index = index + 1
        while next_index < len(pairs) and pairs[next_index][0] != "0":
            next_index += 1
        entity_pairs = pairs[index + 1 : next_index]
        if entity_type in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            text_item = _dxf_text_entity(entity_type, entity_pairs)
            if text_item:
                texts.append(text_item)
        elif entity_type == "DIMENSION":
            dimension = _dxf_dimension_entity(entity_pairs)
            if dimension:
                dimensions.append(dimension)
        elif entity_type in {"LINE", "CIRCLE", "ARC", "ELLIPSE", "LWPOLYLINE", "POLYLINE", "SPLINE", "HATCH"}:
            primitives.append(_dxf_geometry_entity(entity_type, entity_pairs))
        index = next_index
    return {
        "texts": texts,
        "dimensions": dimensions,
        "geometry_primitives": primitives,
        "weld_notes": [],
        "balloons": [],
        "tolerances": [],
    }


def _dxf_group_pairs(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    pairs: list[tuple[str, str]] = []
    index = 0
    while index + 1 < len(lines):
        code = lines[index].strip()
        value = lines[index + 1].rstrip("\r\n")
        pairs.append((code, value))
        index += 2
    return pairs


def _first_group(entity_pairs: list[tuple[str, str]], code: str) -> str | None:
    return next((value.strip() for group_code, value in entity_pairs if group_code == code and value.strip()), None)


def _float_group(entity_pairs: list[tuple[str, str]], code: str) -> float | None:
    value = _first_group(entity_pairs, code)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _dxf_text_entity(entity_type: str, entity_pairs: list[tuple[str, str]]) -> dict | None:
    text_values = [value.strip() for code, value in entity_pairs if code in {"1", "3"} and value.strip()]
    if not text_values:
        return None
    joined_text = " ".join(text_values).replace("\\P", " ").strip()
    if not joined_text:
        return None
    return {
        "text_lines": [joined_text],
        "joined_text": joined_text,
        "source_type": "text",
        "dxf_entity_type": entity_type,
        "layer_name": _first_group(entity_pairs, "8"),
        "position_x": _float_group(entity_pairs, "10"),
        "position_y": _float_group(entity_pairs, "20"),
        "inside_print_area": True,
    }


def _dxf_dimension_entity(entity_pairs: list[tuple[str, str]]) -> dict | None:
    value = _first_group(entity_pairs, "1") or _first_group(entity_pairs, "42")
    if value is None:
        return None
    return {
        "value_1": value,
        "layer_name": _first_group(entity_pairs, "8"),
        "position_x": _float_group(entity_pairs, "10"),
        "position_y": _float_group(entity_pairs, "20"),
        "inside_print_area": True,
    }


def _dxf_geometry_entity(entity_type: str, entity_pairs: list[tuple[str, str]]) -> dict:
    return {
        "geometry_type": f"Dxf{entity_type.title().replace('_', '')}",
        "layer_name": _first_group(entity_pairs, "8"),
        "position_x": _float_group(entity_pairs, "10"),
        "position_y": _float_group(entity_pairs, "20"),
        "radius": _float_group(entity_pairs, "40"),
        "inside_print_area": True,
        "summary": entity_type,
    }
