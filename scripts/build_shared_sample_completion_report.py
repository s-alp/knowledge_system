from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _content_count(raw_extract: dict) -> int:
    keys = (
        "texts",
        "dimensions",
        "geometry_primitives",
        "weld_notes",
        "balloons",
        "tolerances",
    )
    return sum(len(raw_extract.get(key) or []) for key in keys)


def _extract_content(path: Path | None) -> tuple[dict, int]:
    if path is None or not path.is_file():
        return {}, 0
    payload = _load_json(path)
    raw_extract = payload.get("raw_extract") or {}
    return raw_extract, _content_count(raw_extract)


def build_report(manifest_path: Path, summary_paths: list[Path]) -> dict:
    manifest = _load_json(manifest_path)
    summary_by_source: dict[str, dict] = {}
    for summary_path in summary_paths:
        summary_rows = _load_json(summary_path)
        summary_by_source.update(
            {str(row.get("source_path")): row for row in summary_rows if row.get("source_path")}
        )

    rows: list[dict] = []
    for entry in manifest.get("entries", []):
        source_path = str(entry["sourcePath"])
        selected_by_mode = {
            str(item.get("mode")): item
            for item in entry.get("selectedFiles", [])
            if item.get("mode") and item.get("path")
        }
        source_summary = summary_by_source.get(source_path, {})
        latest_output_value = source_summary.get("output_path")
        latest_output_path = Path(str(latest_output_value)) if latest_output_value else None
        latest_raw_extract, latest_content_count = _extract_content(latest_output_path)
        latest_output_exists = bool(latest_output_path and latest_output_path.is_file())

        prior_2d = selected_by_mode.get("2d")
        prior_2d_path = Path(str(prior_2d.get("path"))) if prior_2d else None
        prior_raw_extract, prior_content_count = _extract_content(prior_2d_path)
        prior_output_exists = bool(prior_2d_path and prior_2d_path.is_file())

        if latest_output_exists:
            latest_two_d_status = (
                "extracted_with_content" if latest_content_count > 0 else "extracted_no_2d_content"
            )
            unresolved_reason = None
        elif source_summary.get("timed_out"):
            latest_two_d_status = "timeout"
            unresolved_reason = source_summary.get("error") or "timeout"
        elif source_summary.get("error"):
            latest_two_d_status = "failed"
            unresolved_reason = source_summary.get("error")
        elif source_summary.get("exit_code") not in (None, 0):
            latest_two_d_status = "failed"
            unresolved_reason = f"runner_exit_code_{source_summary['exit_code']}"
        else:
            latest_two_d_status = "not_attempted"
            unresolved_reason = "summary_or_output_missing"

        if latest_output_exists:
            usable_two_d_status = "available_from_latest_attempt"
            usable_2d_path = latest_output_path
            usable_raw_extract = latest_raw_extract
            usable_content_count = latest_content_count
        elif prior_output_exists:
            usable_two_d_status = "available_from_prior_success"
            usable_2d_path = prior_2d_path
            usable_raw_extract = prior_raw_extract
            usable_content_count = prior_content_count
        else:
            usable_two_d_status = "unavailable"
            usable_2d_path = None
            usable_raw_extract = {}
            usable_content_count = 0

        three_d = selected_by_mode.get("3d")
        three_d_path = Path(str(three_d.get("path"))) if three_d else None
        rows.append(
            {
                "sourcePath": source_path,
                "filename": entry.get("filename"),
                "customerHint": entry.get("customerHint"),
                "sourceFileExists": Path(source_path).is_file(),
                "threeDStatus": "extracted" if three_d_path and three_d_path.is_file() else "missing",
                "threeDExtractPath": str(three_d_path) if three_d_path else None,
                "latest2DAttemptStatus": latest_two_d_status,
                "latest2DExtractPath": str(latest_output_path) if latest_output_exists else None,
                "prior2DAvailable": prior_output_exists,
                "prior2DExtractPath": str(prior_2d_path) if prior_output_exists else None,
                "usable2DStatus": usable_two_d_status,
                "usable2DExtractPath": str(usable_2d_path) if usable_2d_path else None,
                "twoDContentCount": usable_content_count,
                "viewSheetCount": len(usable_raw_extract.get("view_sheets") or []),
                "printFrameCount": len(usable_raw_extract.get("print_frames") or []),
                "layerCount": len(usable_raw_extract.get("layers") or []),
                "unresolvedReason": unresolved_reason,
            }
        )

    latest_status_counts: dict[str, int] = {}
    usable_status_counts: dict[str, int] = {}
    unresolved_reason_counts: dict[str, int] = {}
    for row in rows:
        latest_status = row["latest2DAttemptStatus"]
        usable_status = row["usable2DStatus"]
        latest_status_counts[latest_status] = latest_status_counts.get(latest_status, 0) + 1
        usable_status_counts[usable_status] = usable_status_counts.get(usable_status, 0) + 1
        if row["unresolvedReason"]:
            reason = row["unresolvedReason"]
            unresolved_reason_counts[reason] = unresolved_reason_counts.get(reason, 0) + 1
    return {
        "schemaVersion": "icad_shared_sample_completion.v2",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifestPath": str(manifest_path),
        "summaryPaths": [str(summary_path) for summary_path in summary_paths],
        "sampleCount": len(rows),
        "threeDExtractedCount": sum(row["threeDStatus"] == "extracted" for row in rows),
        "sourceFileMissingCount": sum(not row["sourceFileExists"] for row in rows),
        "latest2DAttemptStatusCounts": latest_status_counts,
        "usable2DStatusCounts": usable_status_counts,
        "unresolvedReasonCounts": unresolved_reason_counts,
        "unresolvedCount": sum(bool(row["unresolvedReason"]) for row in rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="共有ICADサンプルの2D/3D抽出完了状況を理由付きで集計します。")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--summary", required=True, action="append", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.manifest.resolve(), [path.resolve() for path in args.summary])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} samples={report['sampleCount']} "
        f"3d={report['threeDExtractedCount']} "
        f"latest2d={report['latest2DAttemptStatusCounts']} "
        f"usable2d={report['usable2DStatusCounts']} "
        f"unresolved={report['unresolvedCount']}"
    )


if __name__ == "__main__":
    main()
