from __future__ import annotations

import json
import re
import time
from pathlib import Path, PureWindowsPath

from django.conf import settings


GENERIC_CAD_EXTRACTOR_NAME = "generic-cad-text-extractor"
GENERIC_CAD_EXTRACTOR_VERSION = "1.1.0"

_STEP_STRING_RE = re.compile(r"'((?:[^']|'')*)'")
_STEP_ENTITY_RE = re.compile(r"#\d+\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
_STEP_ENTITY_WITH_ID_RE = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
_STEP_REFERENCE_RE = re.compile(r"#(\d+)")
_MATERIAL_RE = re.compile(
    r"(?<![A-Z0-9])(SUS[0-9][0-9A-Z-]*|SS400[A-Z-]*|SPCC|S[0-9]{2}C|A[0-9]{4}P?|AL|SKD[0-9]*|SKS[0-9]*|SCM[0-9]*|FC[0-9]*|FCD[0-9]*|PETG|PET|POM|PVC|PTFE|PPS|NBR|EPDM|FKM|PP)(?![A-Z0-9])",
    re.IGNORECASE,
)
_DXF_DIMENSION_TOLERANCE_RE = re.compile(
    r"(?:±|\+/-|%%p|[+＋]\s*\d+(?:\.\d+)?\s*[-－]\s*\d+(?:\.\d+)?)",
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


def _step_references(value: str) -> list[str]:
    return [f"#{matched}" for matched in _STEP_REFERENCE_RE.findall(value)]


def _extract_materials(tokens: list[str]) -> list[str]:
    materials: list[str] = []
    for token in tokens:
        for matched in _MATERIAL_RE.finditer(token.upper()):
            materials.append(matched.group(1))
    return _unique_strings(materials)


def _step_entity_records(text: str) -> list[dict]:
    records: list[dict] = []
    for entity_id, entity_name, body in _STEP_ENTITY_WITH_ID_RE.findall(text):
        records.append(
            {
                "id": f"#{entity_id}",
                "entity_name": entity_name.upper(),
                "strings": _step_strings(body),
                "references": _step_references(body),
            }
        )
    return records


def _step_first_product_name_for_ref(entity_ref: str, entity_by_id: dict[str, dict], seen: set[str] | None = None) -> str | None:
    seen = seen or set()
    if entity_ref in seen:
        return None
    seen.add(entity_ref)
    entity = entity_by_id.get(entity_ref)
    if not entity:
        return None
    strings = entity.get("strings", [])
    if entity.get("entity_name") == "PRODUCT" and strings:
        return strings[0]
    for child_ref in entity.get("references", []):
        product_name = _step_first_product_name_for_ref(child_ref, entity_by_id, seen)
        if product_name:
            return product_name
    return None


def _step_product_records(entity_records: list[dict]) -> list[dict]:
    products: list[dict] = []
    for entity in entity_records:
        if entity["entity_name"] != "PRODUCT":
            continue
        strings = entity["strings"]
        if not strings:
            continue
        products.append(
            {
                "entity_id": entity["id"],
                "name": strings[0],
                "description": strings[1] if len(strings) > 1 else None,
                "raw_strings": strings,
            }
        )
    return products


def _step_assembly_relationships(entity_records: list[dict], entity_by_id: dict[str, dict]) -> list[dict]:
    relationships: list[dict] = []
    for entity in entity_records:
        if entity["entity_name"] != "NEXT_ASSEMBLY_USAGE_OCCURRENCE":
            continue
        refs = entity["references"]
        parent_name = _step_first_product_name_for_ref(refs[0], entity_by_id) if len(refs) >= 1 else None
        child_name = _step_first_product_name_for_ref(refs[1], entity_by_id) if len(refs) >= 2 else None
        strings = entity["strings"]
        relationships.append(
            {
                "entity_id": entity["id"],
                "occurrence_id": strings[0] if strings else None,
                "name": strings[1] if len(strings) > 1 else None,
                "description": strings[2] if len(strings) > 2 else None,
                "parent_ref": refs[0] if len(refs) >= 1 else None,
                "child_ref": refs[1] if len(refs) >= 2 else None,
                "parent_name": parent_name,
                "child_name": child_name,
            }
        )
    return relationships


def _step_part_payloads(products: list[dict], relationships: list[dict], materials: list[str]) -> list[dict]:
    parts: list[dict] = []
    seen: set[str] = set()

    for product in products:
        name = product["name"]
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        parts.append(
            {
                "tree_path": [name],
                "name": name,
                "comment": product.get("description"),
                "materials": [material for material in materials if material.upper() in " ".join(product["raw_strings"]).upper()],
                "step_entity_id": product["entity_id"],
            }
        )

    for relationship in relationships:
        child_name = relationship.get("child_name") or relationship.get("name")
        parent_name = relationship.get("parent_name")
        if not child_name:
            continue
        path = [value for value in (parent_name, child_name) if value]
        key = " > ".join(path).casefold() if path else child_name.casefold()
        if key in seen:
            continue
        seen.add(key)
        parts.append(
            {
                "tree_path": path or [child_name],
                "name": child_name,
                "comment": relationship.get("description") or relationship.get("name"),
                "materials": [material for material in materials if material.upper() in child_name.upper()],
                "step_entity_id": relationship["entity_id"],
            }
        )

    return parts[:500]


def _extract_step_raw(*, text: str, path: Path) -> dict:
    entity_records = _step_entity_records(text)
    entity_by_id = {entity["id"]: entity for entity in entity_records}
    products = _step_product_records(entity_records)
    relationships = _step_assembly_relationships(entity_records, entity_by_id)
    all_strings = _unique_strings(_step_strings(text))
    part_names = [product["name"] for product in products]
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
    parts = _step_part_payloads(products, relationships, materials)
    if not parts:
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
        "step_products": products[:500],
        "step_assembly_relationships": relationships[:500],
        "step_string_literals": all_strings[:500],
    }


def _extract_dxf_raw(*, text: str) -> dict:
    pairs = _dxf_group_pairs(text)
    texts: list[dict] = []
    dimensions: list[dict] = []
    primitives: list[dict] = []
    block_references: list[dict] = []
    layers: list[str] = []
    dimension_styles: dict[str, dict] = {}
    geometric_tolerances: list[dict] = []
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
        if entity_type == "DIMSTYLE":
            dimension_style = _dxf_dimension_style(entity_pairs)
            if dimension_style:
                dimension_styles[dimension_style["name"]] = dimension_style
        elif entity_type in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            text_item = _dxf_text_entity(entity_type, entity_pairs)
            if text_item:
                texts.append(text_item)
                if text_item.get("layer_name"):
                    layers.append(text_item["layer_name"])
        elif entity_type == "DIMENSION":
            dimension = _dxf_dimension_entity(entity_pairs, dimension_styles)
            if dimension:
                dimensions.append(dimension)
                if dimension.get("layer_name"):
                    layers.append(dimension["layer_name"])
        elif entity_type == "TOLERANCE":
            tolerance = _dxf_tolerance_entity(entity_pairs)
            if tolerance:
                geometric_tolerances.append(tolerance)
                if tolerance.get("layer_name"):
                    layers.append(tolerance["layer_name"])
        elif entity_type == "INSERT":
            block_reference, insert_texts, next_index = _dxf_insert_entity(pairs, index, next_index)
            if block_reference:
                block_references.append(block_reference)
                if block_reference.get("layer_name"):
                    layers.append(block_reference["layer_name"])
            texts.extend(insert_texts)
            for text_item in insert_texts:
                if text_item.get("layer_name"):
                    layers.append(text_item["layer_name"])
        elif entity_type in {"LINE", "CIRCLE", "ARC", "ELLIPSE", "LWPOLYLINE", "POLYLINE", "SPLINE", "HATCH"}:
            primitive = _dxf_geometry_entity(entity_type, entity_pairs)
            primitives.append(primitive)
            if primitive.get("layer_name"):
                layers.append(primitive["layer_name"])
        index = next_index
    weld_notes = _dxf_note_candidates(texts, ("溶接", "すみ肉", "開先", "現場溶接", "WELD", "FILLET"))
    tolerances = [
        *geometric_tolerances,
        *_dxf_note_candidates(texts, ("公差", "幾何公差", "±", "+/-", "%%P", "TOL")),
    ]
    return {
        "texts": texts,
        "dimensions": dimensions,
        "geometry_primitives": primitives,
        "block_references": block_references,
        "layers": _unique_strings(layers),
        "weld_notes": weld_notes,
        "balloons": [],
        "tolerances": tolerances,
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


def _int_group(entity_pairs: list[tuple[str, str]], code: str) -> int | None:
    value = _first_group(entity_pairs, code)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _dxf_dimension_style(entity_pairs: list[tuple[str, str]]) -> dict | None:
    name = _first_group(entity_pairs, "2")
    if not name:
        return None
    return {
        "name": name,
        "dimtol": _int_group(entity_pairs, "71"),
        "dimlim": _int_group(entity_pairs, "72"),
        "dimtp": _float_group(entity_pairs, "47"),
        "dimtm": _float_group(entity_pairs, "48"),
    }


def _dxf_dimension_overrides(entity_pairs: list[tuple[str, str]]) -> dict:
    overrides: dict[str, int | float | None] = {}
    variable_names = {71: "dimtol", 72: "dimlim", 47: "dimtp", 48: "dimtm"}
    for index, (code, value) in enumerate(entity_pairs[:-1]):
        if code != "1070":
            continue
        try:
            variable_code = int(value.strip())
        except ValueError:
            continue
        variable_name = variable_names.get(variable_code)
        if not variable_name:
            continue
        next_code, next_value = entity_pairs[index + 1]
        try:
            parsed_value: int | float
            if next_code in {"1070", "1071"}:
                parsed_value = int(next_value.strip())
            elif next_code == "1040":
                parsed_value = float(next_value.strip())
            else:
                continue
        except ValueError:
            continue
        overrides[variable_name] = parsed_value
    return overrides


def _dxf_text_entity(entity_type: str, entity_pairs: list[tuple[str, str]]) -> dict | None:
    text_values = [value.strip() for code, value in entity_pairs if code in {"1", "3"} and value.strip()]
    if not text_values:
        return None
    joined_text = _clean_dxf_text(" ".join(text_values))
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


def _clean_dxf_text(value: str) -> str:
    cleaned = value.replace("\\P", " ")
    cleaned = re.sub(r"\\[A-Za-z][^;]*;", "", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _dxf_insert_entity(
    pairs: list[tuple[str, str]],
    insert_index: int,
    next_index: int,
) -> tuple[dict | None, list[dict], int]:
    insert_pairs = pairs[insert_index + 1 : next_index]
    block_name = _first_group(insert_pairs, "2")
    block_reference = {
        "block_name": block_name,
        "layer_name": _first_group(insert_pairs, "8"),
        "position_x": _float_group(insert_pairs, "10"),
        "position_y": _float_group(insert_pairs, "20"),
        "scale_x": _float_group(insert_pairs, "41"),
        "scale_y": _float_group(insert_pairs, "42"),
        "rotation": _float_group(insert_pairs, "50"),
        "attributes": [],
    }
    texts: list[dict] = []
    index = next_index
    while index < len(pairs):
        code, value = pairs[index]
        if code != "0":
            index += 1
            continue
        entity_type = value.upper()
        if entity_type == "SEQEND":
            index += 1
            break
        if entity_type != "ATTRIB":
            break
        attr_next_index = index + 1
        while attr_next_index < len(pairs) and pairs[attr_next_index][0] != "0":
            attr_next_index += 1
        attr_pairs = pairs[index + 1 : attr_next_index]
        text_item = _dxf_text_entity("ATTRIB", attr_pairs)
        tag_name = _first_group(attr_pairs, "2")
        if text_item:
            text_item["block_name"] = block_name
            text_item["attribute_tag"] = tag_name
            texts.append(text_item)
            block_reference["attributes"].append(
                {
                    "tag": tag_name,
                    "value": text_item["joined_text"],
                    "layer_name": text_item.get("layer_name"),
                    "position_x": text_item.get("position_x"),
                    "position_y": text_item.get("position_y"),
                }
            )
        index = attr_next_index
    if not block_name and not block_reference["attributes"]:
        return None, texts, index
    return block_reference, texts, index


def _dxf_note_candidates(texts: list[dict], keywords: tuple[str, ...]) -> list[dict]:
    candidates: list[dict] = []
    for text_item in texts:
        value = text_item.get("joined_text") or ""
        if not any(keyword.upper() in value.upper() for keyword in keywords):
            continue
        candidates.append(
            {
                "text": value,
                "layer_name": text_item.get("layer_name"),
                "position_x": text_item.get("position_x"),
                "position_y": text_item.get("position_y"),
                "inside_print_area": text_item.get("inside_print_area"),
                "source": "dxf_text",
            }
        )
    return candidates


def _dxf_dimension_entity(
    entity_pairs: list[tuple[str, str]],
    dimension_styles: dict[str, dict],
) -> dict | None:
    value = _first_group(entity_pairs, "1") or _first_group(entity_pairs, "42")
    if value is None:
        return None
    style_name = _first_group(entity_pairs, "3")
    style = dimension_styles.get(style_name or "", {})
    overrides = _dxf_dimension_overrides(entity_pairs)
    dimtol = overrides.get("dimtol", style.get("dimtol"))
    dimlim = overrides.get("dimlim", style.get("dimlim"))
    dimtp = overrides.get("dimtp", style.get("dimtp"))
    dimtm = overrides.get("dimtm", style.get("dimtm"))
    text_override = _first_group(entity_pairs, "1")
    tolerance_enabled = dimtol == 1 or dimlim == 1
    has_tolerance = tolerance_enabled or bool(
        text_override and _DXF_DIMENSION_TOLERANCE_RE.search(text_override)
    )
    return {
        "value_1": value,
        "text_override": text_override,
        "layer_name": _first_group(entity_pairs, "8"),
        "position_x": _float_group(entity_pairs, "10"),
        "position_y": _float_group(entity_pairs, "20"),
        "dxf_entity_type": "DIMENSION",
        "dimension_type": _int_group(entity_pairs, "70"),
        "style_name": style_name,
        "has_tolerance": has_tolerance,
        "upper_tol": str(dimtp) if tolerance_enabled and dimtp is not None else None,
        "lower_tol": str(dimtm) if tolerance_enabled and dimtm is not None else None,
        "dimtol": dimtol,
        "dimlim": dimlim,
        "inside_print_area": True,
    }


def _dxf_tolerance_entity(entity_pairs: list[tuple[str, str]]) -> dict | None:
    raw_text = " ".join(
        value.strip()
        for code, value in entity_pairs
        if code in {"1", "3"} and value.strip()
    )
    if not raw_text:
        return None
    return {
        "text": _clean_dxf_text(raw_text),
        "raw_text": raw_text,
        "source_type": "geometric_tolerance",
        "dxf_entity_type": "TOLERANCE",
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
