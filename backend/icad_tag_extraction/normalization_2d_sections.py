"""2D要素の印刷範囲判定と、用途別セクションへの整理を担当する。

図枠候補の値決定は行わず、入力要素を監査しやすいまとまりへ分類する。
入力dictだけを読み、ファイル、DB、外部APIを変更しない。
"""
from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_rules import *  # noqa: F403
from icad_tag_extraction.normalization_text import *  # noqa: F403

def _has_print_frames(raw_extract: dict) -> bool:
    print_frames = raw_extract.get("print_frames") or []
    return isinstance(print_frames, list) and bool(print_frames)


def _is_usable_print_area_item(item: dict, *, has_print_frames: bool) -> bool:
    inside_print_area = item.get("inside_print_area")
    if inside_print_area is False:
        return False
    if has_print_frames and inside_print_area is not True:
        return False
    return True


def _trusted_print_area_items(items: Iterable[dict], *, has_print_frames: bool) -> list[dict]:
    return [
        item
        for item in items
        if isinstance(item, dict) and _is_usable_print_area_item(item, has_print_frames=has_print_frames)
    ]


def _should_enforce_print_area(items: Iterable[dict], *, has_print_frames: bool) -> bool:
    """枠内外を実際に判定できた要素がある場合だけ、印刷枠フィルターを有効にする。

    ICAD側が印刷枠を返しても、APIや図面状態によって全要素のinside_print_areaが
    unknownになることがある。この状態で枠の存在だけを根拠に除外すると、図面内文字を
    全件失うため、判定情報そのものが無い場合に限ってunknownを採用する。
    """

    if not has_print_frames:
        return False
    return any(
        isinstance(item, dict) and item.get("inside_print_area") is not None
        for item in items
    )


def _print_area_count_summary(items: Iterable[dict]) -> dict[str, int]:
    counts = {"inside": 0, "outside": 0, "unknown": 0}
    for item in items:
        if not isinstance(item, dict):
            continue
        inside_print_area = item.get("inside_print_area")
        if inside_print_area is True:
            counts["inside"] += 1
        elif inside_print_area is False:
            counts["outside"] += 1
        else:
            counts["unknown"] += 1
    return counts


def _structured_2d_symbol_candidates(items: Iterable[dict], *, value_key: str, source: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(value_key)
        if not isinstance(value, str) or not value.strip() or _contains_replacement_character(value):
            continue
        key = (value.strip(), item.get("view_name"), item.get("layer_no"), item.get("position_x"), item.get("position_y"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "value": value.strip(),
                "evidence_text": value.strip(),
                "view_name": item.get("view_name"),
                "layer_no": item.get("layer_no"),
                "position_x": item.get("position_x"),
                "position_y": item.get("position_y"),
                "position_z": item.get("position_z"),
                "inside_print_area": item.get("inside_print_area"),
                "print_frame_no": item.get("print_frame_no"),
                "source": source,
                "confidence": "medium",
                "reason": "2D図面要素から値と位置情報を取得できたため、検索タグではなく図面レビュー用の属性候補として保持します。",
            }
        )
    return candidates


VIEW_REFERENCE_GEOMETRY_TYPES = {
    "SxGeomArrowView": {"kind": "arrow_view", "label": "矢視候補"},
    "SxGeomCutLine": {"kind": "cut_line", "label": "切断線候補"},
    "SxGeomSymbol": {"kind": "symbol", "label": "図面シンボル候補"},
}


def _build_view_reference_candidates(primitives: Iterable[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None, str | None]] = set()
    for primitive in primitives:
        if not isinstance(primitive, dict) or not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        definition = VIEW_REFERENCE_GEOMETRY_TYPES.get(str(geometry_type))
        if not definition:
            continue
        evidence_text = str(primitive.get("summary") or geometry_type or "").strip()
        key = (
            str(geometry_type),
            primitive.get("view_name"),
            primitive.get("layer_no"),
            primitive.get("position_x"),
            primitive.get("position_y"),
            evidence_text,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "kind": definition["kind"],
                "label": definition["label"],
                "geometry_type": geometry_type,
                "evidence_text": evidence_text,
                "view_name": primitive.get("view_name"),
                "layer_no": primitive.get("layer_no"),
                "position_x": primitive.get("position_x"),
                "position_y": primitive.get("position_y"),
                "position_z": primitive.get("position_z"),
                "end_x": primitive.get("end_x"),
                "end_y": primitive.get("end_y"),
                "end_z": primitive.get("end_z"),
                "inside_print_area": primitive.get("inside_print_area"),
                "print_frame_no": primitive.get("print_frame_no"),
                "source": "2d_view_reference_geometry",
                "confidence": "medium",
                "reason": "2D図面の矢視・切断線・シンボル要素から、別ビューや詳細図へつながる可能性があるためレビュー用候補として保持します。",
            }
        )
    return candidates


def _build_curve_section_candidates(primitives: Iterable[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, int | None, float | None, float | None, str | None]] = set()
    for primitive in primitives:
        if not isinstance(primitive, dict) or not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        if geometry_type == "SxGeomSpline2D":
            kind = "spline_curve"
            label = "スプライン曲線候補"
            source = "2d_spline_geometry"
            reason = "2D図形のスプライン要素から曲線外形の可能性を確認できるため、検索タグではなく図面レビュー用候補として保持します。"
        elif geometry_type == "SxGeomHatch":
            kind = "hatch_section"
            label = "ハッチング/断面候補"
            source = "2d_hatch_geometry"
            reason = "2D図形のハッチング要素から断面表現または材質表現の可能性を確認できるため、検索タグではなく図面レビュー用候補として保持します。"
        else:
            continue

        evidence_text = str(primitive.get("summary") or geometry_type or "").strip()
        key = (
            str(geometry_type),
            primitive.get("view_name"),
            primitive.get("layer_no"),
            primitive.get("position_x"),
            primitive.get("position_y"),
            evidence_text,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "kind": kind,
                "label": label,
                "geometry_type": geometry_type,
                "evidence_text": evidence_text,
                "view_name": primitive.get("view_name"),
                "layer_no": primitive.get("layer_no"),
                "position_x": primitive.get("position_x"),
                "position_y": primitive.get("position_y"),
                "position_z": primitive.get("position_z"),
                "center_x": primitive.get("center_x"),
                "center_y": primitive.get("center_y"),
                "center_z": primitive.get("center_z"),
                "point_count": primitive.get("point_count"),
                "inside_print_area": primitive.get("inside_print_area"),
                "print_frame_no": primitive.get("print_frame_no"),
                "source": source,
                "confidence": "medium",
                "searchable_tag": False,
                "tag_adoption_status": "excluded",
                "tag_adoption_reason": GEOMETRY_FEATURE_TAG_EXCLUSION_REASON,
                "reason": reason,
            }
        )
    return candidates


INERTIA_MOMENT_DEFINITIONS = {
    "global_moment": {"kind": "global", "label": "全体座標系慣性モーメント"},
    "gravity_moment": {"kind": "gravity", "label": "重心座標系慣性モーメント"},
    "main_moment": {"kind": "main", "label": "主慣性モーメント"},
}


def _build_inertia_moment_candidates(mass_properties: dict) -> list[dict]:
    candidates: list[dict] = []
    for key, definition in INERTIA_MOMENT_DEFINITIONS.items():
        values = mass_properties.get(key)
        if not isinstance(values, dict):
            continue
        numeric_values = {
            str(name): value
            for name, value in values.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        if not numeric_values:
            continue
        candidates.append(
            {
                "kind": definition["kind"],
                "label": definition["label"],
                "values": numeric_values,
                "unit_name": mass_properties.get("unit_name"),
                "source": f"3d_mass_properties.{key}",
                "confidence": "medium",
                "reason": "SXNETのSxInfMassから慣性モーメント値を取得できたため、検索タグではなく3D解析属性として保持します。",
            }
        )
    return candidates


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _item_position(item: dict) -> str | None:
    x = _first_present(item.get("position_x"), item.get("center_x"), item.get("x1"))
    y = _first_present(item.get("position_y"), item.get("center_y"), item.get("y1"))
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _sample_text(value: object, *, max_length: int = 120) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def _item_display_text(item: dict) -> str | None:
    if item.get("evidence_text"):
        return _sample_text(item["evidence_text"])
    if item.get("joined_text"):
        return _sample_text(item["joined_text"])
    text_lines = item.get("text_lines")
    if isinstance(text_lines, list) and text_lines:
        return _sample_text(" / ".join(str(line) for line in text_lines if line))
    dimension_values = _flatten_strings(
        str(value)
        for value in [
            item.get("value_1"),
            item.get("value_2"),
            item.get("value1"),
            item.get("value2"),
            item.get("mark_2"),
            item.get("mark_3"),
            item.get("mark2"),
            item.get("mark3"),
            item.get("front_word"),
            item.get("back_word"),
        ]
        if value is not None
    )
    if dimension_values:
        return _sample_text(" ".join(dimension_values))
    if isinstance(item.get("summary"), str) and "line_color=" in item["summary"]:
        return "寸法候補"
    return _sample_text(item.get("text") or item.get("geometry_type") or item.get("summary"))


def _section_samples(items: Iterable[dict], *, limit: int = 5) -> list[dict]:
    samples: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sample = {
            "text": _item_display_text(item),
            "source_type": item.get("source_type") or item.get("geometry_type") or item.get("field"),
            "view_name": item.get("view_name"),
            "layer_no": item.get("layer_no"),
            "position": _item_position(item),
            "inside_print_area": item.get("inside_print_area"),
        }
        samples.append({key: value for key, value in sample.items() if value is not None})
        if len(samples) >= limit:
            break
    return samples


def _make_2d_section(
    *,
    key: str,
    all_items: list[dict],
    trusted_items: list[dict],
    source_names: list[str],
) -> dict:
    definition_by_key = {definition_key: (label, description) for definition_key, label, description in TWO_D_SECTION_DEFINITIONS}
    label, description = definition_by_key[key]
    print_area_counts = _print_area_count_summary(all_items)
    return {
        "key": key,
        "label": label,
        "description": description,
        "source_names": source_names,
        "total_count": len(all_items),
        "trusted_count": len(trusted_items),
        "inside_print_area_count": print_area_counts["inside"],
        "outside_print_area_count": print_area_counts["outside"],
        "unknown_print_area_count": print_area_counts["unknown"],
        "samples": _section_samples(trusted_items),
    }


def _build_2d_sections(
    *,
    raw_extract: dict,
    canonical: dict,
    has_print_frames: bool,
    trusted_texts: list[dict],
    trusted_dimensions: list[dict],
    trusted_weld_notes: list[dict],
    trusted_balloons: list[dict],
    trusted_tolerances: list[dict],
    enforce_text_print_area: bool,
) -> dict:
    texts = raw_extract.get("texts", []) or []
    dimensions = raw_extract.get("dimensions", []) or []
    primitives = raw_extract.get("geometry_primitives", []) or []
    weld_notes = raw_extract.get("weld_notes", []) or []
    balloons = raw_extract.get("balloons", []) or []
    tolerances = raw_extract.get("tolerances", []) or []
    trusted_primitives = _trusted_print_area_items(primitives, has_print_frames=has_print_frames)

    title_block_candidates = canonical.get("title_block_candidates", []) or []
    title_block_evidence = {candidate.get("evidence_text") for candidate in title_block_candidates if candidate.get("evidence_text")}
    revision_note_candidates = canonical.get("revision_note_candidates", []) or []

    manufacturing_primitives = [
        primitive
        for primitive in primitives
        if primitive.get("geometry_type") in MANUFACTURING_GEOMETRY_TYPES
    ]
    trusted_manufacturing_primitives = [
        primitive
        for primitive in trusted_primitives
        if primitive.get("geometry_type") in MANUFACTURING_GEOMETRY_TYPES
    ]
    drawing_body_primitives = [
        primitive
        for primitive in primitives
        if primitive.get("geometry_type") not in MANUFACTURING_GEOMETRY_TYPES
    ]
    trusted_drawing_body_primitives = [
        primitive
        for primitive in trusted_primitives
        if primitive.get("geometry_type") not in MANUFACTURING_GEOMETRY_TYPES
    ]

    note_texts = [
        text
        for text in texts
        if (text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])) not in title_block_evidence
    ]
    trusted_note_texts = [
        text
        for text in trusted_texts
        if (text.get("joined_text") or " / ".join(text.get("text_lines", []) or [])) not in title_block_evidence
    ]
    revision_note_items = [
        {
            "evidence_text": candidate.get("evidence_text"),
            "text": candidate.get("value"),
            "view_name": candidate.get("view_name"),
            "layer_no": candidate.get("layer_no"),
            "position_x": candidate.get("position_x"),
            "position_y": candidate.get("position_y"),
            "inside_print_area": candidate.get("inside_print_area"),
            "source_type": "revision_note_candidate",
        }
        for candidate in revision_note_candidates
    ]
    note_items = [*note_texts, *revision_note_items]
    trusted_note_items = [
        *trusted_note_texts,
        *[
            item
            for item in revision_note_items
            if _is_usable_print_area_item(item, has_print_frames=enforce_text_print_area)
        ],
    ]

    sections = [
        _make_2d_section(
            key="title_block",
            all_items=title_block_candidates,
            trusted_items=title_block_candidates,
            source_names=["title_block_candidates"],
        ),
        _make_2d_section(
            key="drawing_body",
            all_items=drawing_body_primitives,
            trusted_items=trusted_drawing_body_primitives,
            source_names=["geometry_primitives"],
        ),
        _make_2d_section(
            key="dimensions",
            all_items=dimensions,
            trusted_items=trusted_dimensions,
            source_names=["dimensions"],
        ),
        _make_2d_section(
            key="notes",
            all_items=note_items,
            trusted_items=trusted_note_items,
            source_names=["texts", "revision_note_candidates"],
        ),
        _make_2d_section(
            key="balloons",
            all_items=balloons,
            trusted_items=trusted_balloons,
            source_names=["balloons"],
        ),
        _make_2d_section(
            key="manufacturing_symbols",
            all_items=[*manufacturing_primitives, *weld_notes, *tolerances],
            trusted_items=[*trusted_manufacturing_primitives, *trusted_weld_notes, *trusted_tolerances],
            source_names=["geometry_primitives", "weld_notes", "tolerances"],
        ),
    ]
    return {
        "schema_version": "raw_2d_sections.v1",
        "print_area_policy": "inside_only_when_print_frames_exist" if has_print_frames else "include_unknown_when_no_print_frames",
        "text_print_area_policy": (
            "inside_only_when_classification_available"
            if enforce_text_print_area
            else "include_unknown_when_classification_unavailable"
        ),
        "sections": sections,
    }



__all__ = (
    "_has_print_frames",
    "_is_usable_print_area_item",
    "_trusted_print_area_items",
    "_should_enforce_print_area",
    "_print_area_count_summary",
    "_structured_2d_symbol_candidates",
    "_build_view_reference_candidates",
    "_build_curve_section_candidates",
    "_build_inertia_moment_candidates",
    "_first_present",
    "_item_position",
    "_sample_text",
    "_item_display_text",
    "_section_samples",
    "_make_2d_section",
    "_build_2d_sections",
)
