"""2D形状要素から、加工・表面性状・穴・中心・断面の属性を整理する。

図枠の識別処理と分離し、製造属性の判定変更が図番処理へ波及しないようにする。
印刷範囲外の要素は根拠として採用しない。
"""
from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_rules import *  # noqa: F403
from icad_tag_extraction.normalization_text import *  # noqa: F403
from icad_tag_extraction.normalization_2d_sections import *  # noqa: F403

def _build_geometry_feature_candidates(primitives: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    grouped: dict[str, dict] = {}
    for primitive in primitives:
        if not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        rule = GEOMETRY_FEATURE_RULES.get(geometry_type)
        if not rule:
            continue

        feature = rule["feature"]
        item = grouped.setdefault(
            feature,
            {
                "feature": feature,
                "label": rule["label"],
                "classification_label": rule["classification_label"],
                "searchable_tag": False,
                "tag_adoption_status": "excluded",
                "tag_adoption_reason": GEOMETRY_FEATURE_TAG_EXCLUSION_REASON,
                "confidence": rule["confidence"],
                "geometry_type": geometry_type,
                "count": 0,
                "sample_summaries": [],
                "source": "2d_geometry_primitive",
            },
        )
        item["count"] += 1
        summary = primitive.get("summary")
        if summary and len(item["sample_summaries"]) < 3:
            item["sample_summaries"].append(summary)

    return list(grouped.values())


def _double_diameter(radius) -> float | None:
    if radius is None:
        return None
    return radius * 2


def _center_label(primitive: dict) -> str | None:
    x = primitive.get("center_x")
    y = primitive.get("center_y")
    if x is None or y is None:
        return None
    return f"{x}, {y}"


def _extract_surface_roughness_values(primitive: dict) -> list[str]:
    values: list[str] = []
    for text in _flatten_strings([primitive.get("val1"), primitive.get("value"), primitive.get("summary")]):
        for match in SURFACE_ROUGHNESS_PATTERN.finditer(text):
            values.append(f"{match.group(1)} {match.group(2)}")
    return _merge_unique(values)


def _build_geometry_attribute_summary(primitives: list[dict], *, has_print_frames: bool = False) -> dict:
    summary = {
        "surface_roughness_count": 0,
        "surface_roughness_values": [],
        "section_feature_count": 0,
        "cut_line_count": 0,
        "hatch_or_section_count": 0,
        "finish_mark_count": 0,
        "finish_mark_types": [],
        "slot_candidate_count": 0,
        "slot_candidate_dimensions": [],
        "hole_candidate_count": 0,
        "hole_candidate_diameters": [],
    }

    roughness_values: list[str] = []
    finish_mark_types: list[int] = []
    hole_diameters: list[float] = []
    slot_dimensions: list[dict] = []

    for primitive in primitives:
        if not _is_usable_print_area_item(primitive, has_print_frames=has_print_frames):
            continue
        geometry_type = primitive.get("geometry_type")
        if geometry_type == "SxGeomSmark":
            summary["surface_roughness_count"] += 1
            roughness_values.extend(_extract_surface_roughness_values(primitive))
            continue
        if geometry_type == "SxGeomCutLine":
            summary["cut_line_count"] += 1
            summary["section_feature_count"] += 1
            continue
        if geometry_type == "SxGeomHatch":
            summary["hatch_or_section_count"] += 1
            summary["section_feature_count"] += 1
            continue
        if geometry_type == "SxGeomFinishMark":
            summary["finish_mark_count"] += 1
            mark_type = primitive.get("mark_type")
            if mark_type is not None:
                finish_mark_types.append(mark_type)
            continue
        if geometry_type == "SxGeomCircle2D":
            summary["hole_candidate_count"] += 1
            diameter = _double_diameter(primitive.get("radius"))
            if diameter is not None:
                hole_diameters.append(diameter)
            continue
        if geometry_type in {"SxGeomElparc2D", "SxGeomEllipse2D"}:
            summary["slot_candidate_count"] += 1
            radius1 = primitive.get("radius1")
            radius2 = primitive.get("radius2")
            slot_dimensions.append(
                {
                    "geometry_type": geometry_type,
                    "center": _center_label(primitive),
                    "major_radius": radius1,
                    "minor_radius": radius2,
                    "major_diameter": _double_diameter(radius1),
                    "minor_diameter": _double_diameter(radius2),
                    "start_angle": primitive.get("start_angle"),
                    "end_angle": primitive.get("end_angle"),
                }
            )

    summary["surface_roughness_values"] = _merge_unique(roughness_values)
    summary["finish_mark_types"] = _merge_unique(finish_mark_types)
    summary["hole_candidate_diameters"] = _merge_unique(hole_diameters)
    summary["slot_candidate_dimensions"] = slot_dimensions
    return summary


__all__ = (
    "_build_geometry_feature_candidates",
    "_double_diameter",
    "_center_label",
    "_extract_surface_roughness_values",
    "_build_geometry_attribute_summary",
)
