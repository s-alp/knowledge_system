from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django

django.setup()

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.persistence import enqueue_extraction_job


MODE_SETTINGS = {
    "2d": (
        "2d_all_views_layers_print_frame",
        {"scanAllViews": True, "scanAllLayers": True, "capturePrintFrames": True},
    ),
    "3d": ("3d_model_part_attributes", {}),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue drawing metadata extraction jobs through the normal service.")
    parser.add_argument("drawing_id")
    parser.add_argument("--mode", choices=["2d", "3d", "all"], default="all")
    parser.add_argument("--reason", default="Manual re-extraction requested from Codex diagnostics.")
    parser.add_argument("--executed-by", default="codex")
    args = parser.parse_args()

    drawing = RegisteredDrawing.objects.get(pk=args.drawing_id)
    modes = ["2d", "3d"] if args.mode == "all" else [args.mode]
    for mode in modes:
        profile, options = MODE_SETTINGS[mode]
        job = enqueue_extraction_job(
            drawing=drawing,
            extraction_mode=mode,
            reason=args.reason,
            executed_by=args.executed_by,
            extraction_profile=profile,
            extraction_options=options,
            diagnostics={"trigger": "requeue_drawing_metadata_extractions"},
        )
        print(f"{job.id}\t{job.extraction_mode}\t{job.status}\t{job.extraction_profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
