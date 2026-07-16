"""Validate the human-readable drawing handoff review summary.

The full handoff fixture is for machines and can be large. This validator keeps
the review summary small enough to open in editors and checks that heavy API
payloads did not leak into it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA_VERSION = "drawing_metadata_handoff_review_summary.v1"
FORBIDDEN_ITEM_KEYS = {"detailApiPayload", "viewerBootstrap", "ragPayload"}


def _add_issue(issues: list[dict[str, Any]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def validate_summary(path: Path, *, max_bytes: int) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    size_bytes = path.stat().st_size
    if size_bytes > max_bytes:
        _add_issue(issues, "$", f"file is too large for review: {size_bytes} bytes > {max_bytes} bytes")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        _add_issue(issues, "$.schemaVersion", f"must be {EXPECTED_SCHEMA_VERSION}")
    export_policy = payload.get("exportPolicy")
    if not isinstance(export_policy, dict):
        _add_issue(issues, "$.exportPolicy", "must be an object")
    else:
        if export_policy.get("profile") != "review-summary":
            _add_issue(issues, "$.exportPolicy.profile", "must be review-summary")
        if export_policy.get("fileSizePolicy") != "human_review_compact_no_raw_extract":
            _add_issue(issues, "$.exportPolicy.fileSizePolicy", "must be human_review_compact_no_raw_extract")

    items = payload.get("items")
    if not isinstance(items, list):
        _add_issue(issues, "$.items", "must be a list")
        items = []
    if payload.get("itemCount") != len(items):
        _add_issue(issues, "$.itemCount", "must match items length")

    for index, item in enumerate(items):
        item_path = f"$.items[{index}]"
        if not isinstance(item, dict):
            _add_issue(issues, item_path, "must be an object")
            continue
        leaked_keys = sorted(FORBIDDEN_ITEM_KEYS.intersection(item.keys()))
        if leaked_keys:
            _add_issue(issues, item_path, f"heavy payload keys are not allowed: {', '.join(leaked_keys)}")
        for key in ("drawingId", "filename", "sourcePath", "snapshotSummary", "selectedAttributes"):
            if key not in item:
                _add_issue(issues, f"{item_path}.{key}", "is required")

    return {
        "valid": not issues,
        "schemaVersion": payload.get("schemaVersion"),
        "file": str(path),
        "sizeBytes": size_bytes,
        "maxBytes": max_bytes,
        "itemCount": len(items),
        "issueCount": len(issues),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--max-bytes", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = validate_summary(args.summary_json, max_bytes=args.max_bytes)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
