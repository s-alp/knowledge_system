from __future__ import annotations

from dataclasses import dataclass

from apps.drawing_metadata.models import EXTRACTION_MODE_2D, EXTRACTION_MODE_3D, RegisteredDrawing
from apps.drawing_metadata.services.persistence import enqueue_extraction_job


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


def build_missing_or_partial_reextract_plan(*, drawing: RegisteredDrawing) -> list[ReextractPlanItem]:
    snapshot_modes = {snapshot.extraction_mode for snapshot in drawing.snapshots.all()}
    items: list[ReextractPlanItem] = []

    for extraction_mode in (EXTRACTION_MODE_2D, EXTRACTION_MODE_3D):
        if extraction_mode in snapshot_modes:
            continue

        profile_config = REEXTRACT_PROFILES[extraction_mode]
        items.append(
            ReextractPlanItem(
                drawing=drawing,
                extraction_mode=extraction_mode,
                profile=profile_config["profile"],
                options=profile_config["options"],
                diagnostics={
                    "schemaVersion": "reextract_diagnostics.v1",
                    "reason": "missing_snapshot",
                    "missingMode": extraction_mode,
                    "latestJobStatus": _latest_job_status(drawing, extraction_mode),
                    "requiredConditionChecks": profile_config["checks"],
                    "note": "未抽出は存在しない判定ではなく、ビュー差・レイヤー差・印刷枠差・パーツ付加情報差を条件別に再試行する。",
                },
            )
        )

    return items


def enqueue_missing_or_partial_reextract_jobs(
    *,
    drawing: RegisteredDrawing,
    executed_by: str,
    reason: str = "missing or partial extraction condition retry",
) -> list:
    jobs = []
    for item in build_missing_or_partial_reextract_plan(drawing=drawing):
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
