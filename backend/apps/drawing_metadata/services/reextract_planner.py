from __future__ import annotations

from dataclasses import dataclass

from apps.drawing_metadata.models import EXTRACTION_MODE_2D, EXTRACTION_MODE_3D, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.persistence import enqueue_extraction_job
from apps.drawing_metadata.services.source_formats import (
    default_extraction_modes_for_source_format,
    uses_generic_cad_extractor,
    uses_sxnet_extractor,
)


REEXTRACT_PROFILES: dict[str, dict] = {
    EXTRACTION_MODE_2D: {
        "profile": "2d_all_views_layers_print_frame",
        "options": {
            "scanAllViews": True,
            "scanAllLayers": True,
            "classifyPrintFrame": True,
            "recordOutsidePrintFrame": True,
            "recordUnknownPrintArea": True,
        },
        "checks": ["allViews", "allLayers", "printFrame", "outsidePrintFrame"],
    },
    EXTRACTION_MODE_3D: {
        "profile": "3d_parts_materials_ex_info",
        "options": {
            "scanPartTree": True,
            "scanPartMaterials": True,
            "scanPartExtendedInfo": True,
            "scanMassProperties": True,
        },
        "checks": ["partTree", "partMaterials", "partAttributes", "massProperties"],
    },
}

GENERIC_CAD_REEXTRACT_PROFILES: dict[str, dict[str, dict]] = {
    "step": {
        EXTRACTION_MODE_3D: {
            "profile": "step_text_entities",
            "options": {"scanStepHeader": True, "scanStepStringEntities": True},
            "checks": ["stepHeader", "stepStringEntities", "materialTextPatterns"],
        },
    },
    "dxf": {
        EXTRACTION_MODE_2D: {
            "profile": "dxf_text_layers_entities",
            "options": {"scanDxfText": True, "scanDxfLayers": True, "scanDxfGeometry": True},
            "checks": ["dxfText", "dxfLayers", "dxfGeometry"],
        },
    },
}


@dataclass(frozen=True)
class ReextractPlanItem:
    drawing: RegisteredDrawing
    extraction_mode: str
    profile: str
    options: dict
    diagnostics: dict


def _latest_job_status(drawing: RegisteredDrawing, extraction_mode: str) -> str | None:
    latest_job = drawing.jobs.filter(extraction_mode=extraction_mode).first()
    return latest_job.status if latest_job else None


def _count_raw_items(snapshot: DrawingMetadataSnapshot, key: str) -> int:
    payload = snapshot.raw_extract_json or {}
    raw_extract = payload.get("raw_extract") or payload
    value = raw_extract.get(key) or []
    return len(value) if isinstance(value, list) else 0


def _requires_partial_reextract(snapshot: DrawingMetadataSnapshot) -> bool:
    if snapshot.extraction_mode == EXTRACTION_MODE_2D:
        return (
            _count_raw_items(snapshot, "view_sheets") == 0
            and _count_raw_items(snapshot, "texts") == 0
            and _count_raw_items(snapshot, "geometry_primitives") == 0
        )
    return False


def build_missing_or_partial_reextract_plan(
    *,
    drawing: RegisteredDrawing,
    extraction_modes: tuple[str, ...] | None = None,
) -> list[ReextractPlanItem]:
    source_format = (drawing.source_format or "").lower()
    if not uses_sxnet_extractor(source_format) and not uses_generic_cad_extractor(source_format):
        return []

    snapshots_by_mode = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}
    items: list[ReextractPlanItem] = []
    default_modes = default_extraction_modes_for_source_format(source_format)
    if extraction_modes:
        target_modes = tuple(mode for mode in extraction_modes if mode in default_modes)
    else:
        target_modes = default_modes

    for extraction_mode in target_modes:
        snapshot = snapshots_by_mode.get(extraction_mode)
        reason = "missing_snapshot"
        if snapshot is not None:
            if not _requires_partial_reextract(snapshot):
                continue
            reason = "partial_snapshot"

        profile_config = (
            GENERIC_CAD_REEXTRACT_PROFILES.get(source_format, {}).get(extraction_mode)
            or REEXTRACT_PROFILES[extraction_mode]
        )
        items.append(
            ReextractPlanItem(
                drawing=drawing,
                extraction_mode=extraction_mode,
                profile=profile_config["profile"],
                options=profile_config["options"],
                diagnostics={
                    "schemaVersion": "reextract_diagnostics.v1",
                    "reason": reason,
                    "missingMode": extraction_mode,
                    "latestJobStatus": _latest_job_status(drawing, extraction_mode),
                    "requiredConditionChecks": profile_config["checks"],
                    "note": _diagnostic_note(source_format),
                },
            )
        )

    return items


def _diagnostic_note(source_format: str) -> str:
    if source_format == "step":
        return "STEPはファイル内ヘッダ・文字列リテラル・製品/形状名候補からタグ材料を抽出する。"
    if source_format == "dxf":
        return "DXFはTEXT/MTEXT/属性文字、寸法、レイヤー、基本図形からタグ材料を抽出する。"
    return "未抽出または空に近い抽出結果は、ビュー差・レイヤー差・印刷枠差・パーツ付加情報差を条件別に再試行する。"


def enqueue_missing_or_partial_reextract_jobs(
    *,
    drawing: RegisteredDrawing,
    executed_by: str,
    extraction_modes: tuple[str, ...] | None = None,
    reason: str = "missing or partial extraction condition retry",
) -> list:
    jobs = []
    for item in build_missing_or_partial_reextract_plan(drawing=drawing, extraction_modes=extraction_modes):
        jobs.append(
            enqueue_extraction_job(
                drawing=item.drawing,
                extraction_mode=item.extraction_mode,
                reason=reason,
                executed_by=executed_by,
                extraction_profile=item.profile,
                extraction_options=item.options,
                diagnostics=item.diagnostics,
            )
        )
    return jobs
