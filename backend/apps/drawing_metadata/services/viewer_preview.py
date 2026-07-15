from __future__ import annotations

from html import escape
from math import isfinite

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing


def build_2d_preview_svg(*, drawing: RegisteredDrawing, snapshot: DrawingMetadataSnapshot) -> str:
    raw_extract = snapshot.raw_extract_json or {}
    canonical = snapshot.canonical_attributes_json or {}
    texts = _list_of_dicts(raw_extract.get("texts"))
    dimensions = _list_of_dicts(raw_extract.get("dimensions"))
    primitives = _list_of_dicts(raw_extract.get("geometry_primitives"))
    print_frames = _list_of_dicts(raw_extract.get("print_frames"))
    view_sheets = _list_of_dicts(raw_extract.get("view_sheets"))

    width = 1600
    height = 1100
    title = _first_text(
        canonical.get("drawing_name"),
        canonical.get("source_file_name"),
        drawing.filename,
    )
    subtitle = _first_text(
        canonical.get("drawing_number"),
        canonical.get("paper_size"),
        canonical.get("customer_name"),
        "抽出JSONプレビュー",
    )
    title_fields = canonical.get("title_block_fields") if isinstance(canonical.get("title_block_fields"), dict) else {}
    summary_rows = [
        ("図面名", title),
        ("図番", canonical.get("drawing_number")),
        ("材質", _first_text(canonical.get("material"), title_fields.get("material"))),
        ("表面処理", title_fields.get("surface_treatment")),
        ("尺度", title_fields.get("scale")),
        ("PRFX", title_fields.get("prfx")),
        ("ユニット", title_fields.get("unit_number")),
        ("担当/承認", _first_text(title_fields.get("designer"), title_fields.get("approver"), canonical.get("designer"))),
    ]

    svg: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        ".bg{fill:#f8fafc}.paper{fill:#fff;stroke:#111827;stroke-width:2}.frame{fill:none;stroke:#2563eb;stroke-width:2;stroke-dasharray:12 8}.outside{stroke:#ef4444}.unknown{stroke:#94a3b8}.text{font-family:Meiryo,'Yu Gothic',sans-serif;fill:#111827}.muted{fill:#64748b}.small{font-size:24px}.body{font-size:30px}.title{font-size:42px;font-weight:700}.label{font-size:22px;fill:#475569}.dim{fill:#0f766e}.geom{fill:none;stroke:#334155;stroke-width:3}.note{fill:#fff7ed;stroke:#fb923c;stroke-width:2}",
        "</style>",
        '<rect class="bg" width="100%" height="100%"/>',
        '<rect class="paper" x="70" y="70" width="1460" height="960" rx="4"/>',
        f'<text class="text title" x="110" y="130">{_xml(title)}</text>',
        f'<text class="text muted body" x="110" y="176">{_xml(subtitle)}</text>',
    ]

    if print_frames:
        for index, frame in enumerate(print_frames[:4]):
            x = 105 + index * 16
            y = 215 + index * 16
            svg.append(f'<rect class="frame" x="{x}" y="{y}" width="{1020 - index * 32}" height="{650 - index * 32}"/>')
            label = _first_text(frame.get("name"), frame.get("size"), f"print frame {index + 1}")
            svg.append(f'<text class="text label" x="{x + 12}" y="{y + 34}">{_xml(label)}</text>')
    else:
        svg.append('<rect class="frame unknown" x="105" y="215" width="1020" height="650"/>')
        svg.append('<text class="text label" x="120" y="250">印刷枠未抽出: 図枠外判定は要確認</text>')

    for index, view_sheet in enumerate(view_sheets[:5]):
        x = 1170
        y = 215 + index * 66
        label = _first_text(view_sheet.get("name"), view_sheet.get("view_name"), f"view {index + 1}")
        svg.append(f'<rect x="{x}" y="{y}" width="310" height="48" fill="#eef2ff" stroke="#6366f1" rx="4"/>')
        svg.append(f'<text class="text small" x="{x + 14}" y="{y + 32}">{_xml(label)}</text>')

    for index, item in enumerate(texts[:18]):
        text_value = _item_text(item)
        x, y = _preview_point(item, fallback_x=140 + (index % 3) * 300, fallback_y=300 + (index // 3) * 70)
        css = "text body"
        if item.get("inside_print_area") is False:
            css = "text body outside"
        svg.append(f'<text class="{css}" x="{x}" y="{y}">{_xml(text_value[:36])}</text>')

    for index, dimension in enumerate(dimensions[:12]):
        value = _first_text(dimension.get("value_1"), dimension.get("value"), dimension.get("text"), "")
        x, y = _preview_point(dimension, fallback_x=165 + (index % 4) * 230, fallback_y=760 + (index // 4) * 52)
        svg.append(f'<text class="text body dim" x="{x}" y="{y}">寸法 {_xml(value[:18])}</text>')

    for index, primitive in enumerate(primitives[:24]):
        x, y = _preview_point(primitive, fallback_x=180 + (index % 8) * 100, fallback_y=520 + (index // 8) * 80)
        klass = "geom"
        if primitive.get("inside_print_area") is False:
            klass = "geom outside"
        elif primitive.get("inside_print_area") is None:
            klass = "geom unknown"
        svg.append(f'<circle class="{klass}" cx="{x}" cy="{y}" r="{12 + (index % 3) * 4}"/>')

    table_x = 1125
    table_y = 575
    svg.append(f'<rect class="note" x="{table_x}" y="{table_y}" width="360" height="350" rx="4"/>')
    svg.append(f'<text class="text body" x="{table_x + 18}" y="{table_y + 42}">タグ候補の根拠</text>')
    for index, (label, value) in enumerate(summary_rows):
        y = table_y + 84 + index * 32
        svg.append(f'<text class="text label" x="{table_x + 18}" y="{y}">{_xml(label)}</text>')
        svg.append(f'<text class="text small" x="{table_x + 135}" y="{y}">{_xml(_first_text(value, "未抽出")[:18])}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def build_3d_preview_stl(*, drawing: RegisteredDrawing, snapshot: DrawingMetadataSnapshot) -> str:
    raw_extract = snapshot.raw_extract_json or {}
    canonical = snapshot.canonical_attributes_json or {}
    parts = _list_of_dicts(raw_extract.get("parts"))
    part_names = _string_list(canonical.get("part_names"))
    if not part_names:
        part_names = [_first_text(canonical.get("top_part_name"), drawing.filename)]
    part_count = len(parts) if parts else len(part_names)
    if part_count <= 0:
        part_count = 1

    lines = ["solid icad_metadata_preview"]
    max_boxes = min(part_count, 36)
    for index in range(max_boxes):
        col = index % 6
        row = (index // 6) % 6
        layer = index // 36
        x = col * 18.0
        y = row * 18.0
        z = layer * 14.0
        size = 8.0 + (index % 4) * 1.5
        lines.extend(_box_triangles(x, y, z, size, size, 8.0 + (index % 3) * 3.0))
    lines.append("endsolid icad_metadata_preview")
    return "\n".join(lines) + "\n"


def _box_triangles(x: float, y: float, z: float, width: float, depth: float, height: float) -> list[str]:
    p = {
        "000": (x, y, z),
        "100": (x + width, y, z),
        "010": (x, y + depth, z),
        "110": (x + width, y + depth, z),
        "001": (x, y, z + height),
        "101": (x + width, y, z + height),
        "011": (x, y + depth, z + height),
        "111": (x + width, y + depth, z + height),
    }
    faces = [
        ((0, 0, -1), ("000", "110", "100"), ("000", "010", "110")),
        ((0, 0, 1), ("001", "101", "111"), ("001", "111", "011")),
        ((0, -1, 0), ("000", "100", "101"), ("000", "101", "001")),
        ((0, 1, 0), ("010", "011", "111"), ("010", "111", "110")),
        ((-1, 0, 0), ("000", "001", "011"), ("000", "011", "010")),
        ((1, 0, 0), ("100", "110", "111"), ("100", "111", "101")),
    ]
    lines: list[str] = []
    for normal, tri_a, tri_b in faces:
        lines.extend(_facet(normal, [p[key] for key in tri_a]))
        lines.extend(_facet(normal, [p[key] for key in tri_b]))
    return lines


def _facet(normal: tuple[float, float, float], vertices: list[tuple[float, float, float]]) -> list[str]:
    lines = [f"  facet normal {normal[0]} {normal[1]} {normal[2]}", "    outer loop"]
    for vertex in vertices:
        lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
    lines.extend(["    endloop", "  endfacet"])
    return lines


def _preview_point(item: dict, *, fallback_x: float, fallback_y: float) -> tuple[float, float]:
    x = _number(item.get("x") or item.get("position_x") or item.get("center_x"))
    y = _number(item.get("y") or item.get("position_y") or item.get("center_y"))
    if x is None or y is None:
        position = item.get("position")
        if isinstance(position, dict):
            x = _number(position.get("x"))
            y = _number(position.get("y"))
        elif isinstance(position, (list, tuple)) and len(position) >= 2:
            x = _number(position[0])
            y = _number(position[1])
    if x is None or y is None:
        return fallback_x, fallback_y
    return 140 + (abs(x) % 940), 280 + (abs(y) % 520)


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return number


def _item_text(item: dict) -> str:
    if item.get("joined_text"):
        return str(item["joined_text"])
    lines = item.get("text_lines")
    if isinstance(lines, list):
        return " / ".join(str(line) for line in lines if line is not None)
    return _first_text(item.get("text"), item.get("value"), "text")


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def _first_text(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _xml(value: object) -> str:
    return escape(str(value), quote=True)
