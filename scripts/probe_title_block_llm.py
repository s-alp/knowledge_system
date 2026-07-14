from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def _setup_django() -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")
    import django

    django.setup()


def _iter_json_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _is_2d_payload(path: Path, payload: dict) -> bool:
    source_kind = str(payload.get("source_kind") or "").lower()
    return source_kind == "2d" or path.name.lower().endswith("_2d.json")


def _candidate_summary(path: Path, payload: dict) -> dict:
    from apps.drawing_metadata.services.normalization import normalize_raw_extract

    canonical = normalize_raw_extract(payload)
    candidates = canonical.get("title_block_candidates") or []
    return {
        "path": str(path),
        "file": path.name,
        "candidate_count": len(candidates),
        "selected_fields": canonical.get("title_block_fields") or {},
        "candidates": candidates,
    }


def _sample_key(path: Path) -> str:
    stem = path.stem
    for suffix in (
        "_allviews_2d",
        "_layered_2d",
        "_layers_2d",
        "_positioned_2d",
        "_primitives_2d",
        "_v2meta_2d",
        "_2d",
    ):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _classify(summary: dict, limit_candidates: int) -> dict:
    from apps.drawing_metadata.services.llm_title_block_classifier import (
        apply_title_block_classifications,
        classify_title_block_candidates,
    )

    candidates = summary["candidates"][:limit_candidates]
    classifications = classify_title_block_candidates(candidates)
    canonical = {
        "title_block_fields": dict(summary["selected_fields"]),
        "title_block_candidates": [dict(candidate) for candidate in candidates],
    }
    apply_title_block_classifications(canonical, classifications)
    accepted = [
        item
        for item in canonical.get("title_block_llm_classifications", [])
        if item.get("accepted_as_field")
    ]
    return {
        "classifications": classifications,
        "accepted_count": len(accepted),
        "accepted": accepted,
        "fields_after_llm": canonical.get("title_block_fields") or {},
        "candidates_after_llm": canonical.get("title_block_candidates") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe ICAD 2D title-block candidates and optional Gemini labels.")
    parser.add_argument(
        "--root",
        default=str(PROJECT_ROOT / "output" / "live_extracts" / "shared_icad_probe_2026-07-14"),
        help="Directory that contains extracted JSON files.",
    )
    parser.add_argument("--top-files", type=int, default=8, help="Number of candidate-rich files to report.")
    parser.add_argument("--limit-candidates", type=int, default=12, help="Candidate count sent to Gemini per file.")
    parser.add_argument("--classify", action="store_true", help="Call Gemini API for selected files.")
    parser.add_argument("--output", help="Optional JSON report path.")
    args = parser.parse_args()

    _setup_django()

    root = Path(args.root)
    summaries = []
    for path in _iter_json_files(root):
        payload = _load_json(path)
        if not isinstance(payload, dict) or not _is_2d_payload(path, payload):
            continue
        summary = _candidate_summary(path, payload)
        if summary["candidate_count"]:
            summaries.append(summary)

    summaries.sort(key=lambda item: (-item["candidate_count"], item["file"]))
    deduped = []
    seen_samples: set[str] = set()
    for summary in summaries:
        sample_key = _sample_key(Path(summary["path"]))
        if sample_key in seen_samples:
            continue
        seen_samples.add(sample_key)
        deduped.append(summary)
    selected = deduped[: args.top_files]

    report = {
        "root": str(root),
        "json_file_count": len(_iter_json_files(root)),
        "candidate_file_count": len(summaries),
        "candidate_sample_count": len(deduped),
        "selected_file_count": len(selected),
        "classified": bool(args.classify),
        "files": [],
    }

    for summary in selected:
        item = {
            "file": summary["file"],
            "path": summary["path"],
            "candidate_count": summary["candidate_count"],
            "selected_fields": summary["selected_fields"],
            "candidate_preview": [
                {
                    "field": candidate.get("field"),
                    "value": candidate.get("value"),
                    "confidence": candidate.get("confidence"),
                    "evidence_text": candidate.get("evidence_text"),
                    "view_name": candidate.get("view_name"),
                    "layer_no": candidate.get("layer_no"),
                    "inside_print_area": candidate.get("inside_print_area"),
                }
                for candidate in summary["candidates"][: args.limit_candidates]
            ],
        }
        if args.classify:
            try:
                item["gemini"] = _classify(summary, args.limit_candidates)
            except (RuntimeError, OSError, ValueError) as exc:
                item["gemini_error"] = str(exc)
        report["files"].append(item)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
