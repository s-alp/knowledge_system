"""Compare drawing metadata handoff fixture tags between a git revision and a file.

The script is intentionally narrow: it compares the fixture shape exported by
export_drawing_metadata_fixtures and reports per drawing/mode tag and keyword
differences. It does not modify the database or fixture files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def _load_json_from_git(revision_path: str, cwd: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "show", revision_path],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def _load_json_from_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tag_value(tag: Any) -> str:
    if isinstance(tag, dict):
        return str(tag.get("tag") or tag.get("label") or tag)
    return str(tag)


def _snapshot_key(item: dict[str, Any], mode: str) -> str:
    payload = item.get("detailApiPayload") or {}
    filename = payload.get("filename") or item.get("filename") or ""
    source_path = payload.get("sourcePath") or ""
    return f"{filename}|{source_path}|{mode}"


def _index_fixture(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in fixture.get("items") or []:
        snapshots = ((item.get("detailApiPayload") or {}).get("snapshotsByMode") or {})
        for mode, snapshot in snapshots.items():
            if not isinstance(snapshot, dict):
                continue
            canonical = snapshot.get("canonicalAttributes") or {}
            tags = [_tag_value(tag) for tag in snapshot.get("derivedTags") or []]
            key = _snapshot_key(item, str(mode))
            indexed[key] = {
                "filename": (item.get("detailApiPayload") or {}).get("filename") or item.get("filename"),
                "mode": str(mode),
                "tags": sorted(tags),
                "part_keywords": sorted(str(value) for value in canonical.get("part_keywords") or []),
                "spec_tokens": sorted(str(value) for value in canonical.get("spec_tokens") or []),
                "title_block_candidate_count": len(canonical.get("title_block_candidates") or []),
                "revision_note_count": canonical.get("revision_note_count") or 0,
                "geometry_feature_count": len(canonical.get("geometry_feature_candidates") or []),
                "hatch_or_section_count": canonical.get("hatch_or_section_count") or 0,
                "hole_candidate_count": canonical.get("hole_candidate_count") or 0,
            }
    return indexed


def _diff_counter(before: list[str], after: list[str]) -> tuple[list[str], list[str]]:
    before_counter = Counter(before)
    after_counter = Counter(after)
    removed = sorted((before_counter - after_counter).elements())
    added = sorted((after_counter - before_counter).elements())
    return removed, added


def compare(old_fixture: dict[str, Any], new_fixture: dict[str, Any]) -> dict[str, Any]:
    old_index = _index_fixture(old_fixture)
    new_index = _index_fixture(new_fixture)
    keys = sorted(set(old_index) | set(new_index))
    changed: list[dict[str, Any]] = []
    totals = {
        "snapshot_count_old": len(old_index),
        "snapshot_count_new": len(new_index),
        "removed_tags": 0,
        "added_tags": 0,
        "removed_part_keywords": 0,
        "added_part_keywords": 0,
        "removed_spec_tokens": 0,
        "added_spec_tokens": 0,
        "title_block_candidates_delta": 0,
        "revision_note_count_delta": 0,
        "geometry_feature_count_delta": 0,
        "hatch_or_section_count_delta": 0,
        "hole_candidate_count_delta": 0,
    }

    for key in keys:
        before = old_index.get(key, {})
        after = new_index.get(key, {})
        removed_tags, added_tags = _diff_counter(before.get("tags", []), after.get("tags", []))
        removed_keywords, added_keywords = _diff_counter(before.get("part_keywords", []), after.get("part_keywords", []))
        removed_specs, added_specs = _diff_counter(before.get("spec_tokens", []), after.get("spec_tokens", []))
        metric_delta = {
            "title_block_candidate_count": (after.get("title_block_candidate_count") or 0) - (before.get("title_block_candidate_count") or 0),
            "revision_note_count": (after.get("revision_note_count") or 0) - (before.get("revision_note_count") or 0),
            "geometry_feature_count": (after.get("geometry_feature_count") or 0) - (before.get("geometry_feature_count") or 0),
            "hatch_or_section_count": (after.get("hatch_or_section_count") or 0) - (before.get("hatch_or_section_count") or 0),
            "hole_candidate_count": (after.get("hole_candidate_count") or 0) - (before.get("hole_candidate_count") or 0),
        }
        if not any([removed_tags, added_tags, removed_keywords, added_keywords, removed_specs, added_specs, *metric_delta.values()]):
            continue

        totals["removed_tags"] += len(removed_tags)
        totals["added_tags"] += len(added_tags)
        totals["removed_part_keywords"] += len(removed_keywords)
        totals["added_part_keywords"] += len(added_keywords)
        totals["removed_spec_tokens"] += len(removed_specs)
        totals["added_spec_tokens"] += len(added_specs)
        totals["title_block_candidates_delta"] += metric_delta["title_block_candidate_count"]
        totals["revision_note_count_delta"] += metric_delta["revision_note_count"]
        totals["geometry_feature_count_delta"] += metric_delta["geometry_feature_count"]
        totals["hatch_or_section_count_delta"] += metric_delta["hatch_or_section_count"]
        totals["hole_candidate_count_delta"] += metric_delta["hole_candidate_count"]
        changed.append(
            {
                "key": key,
                "filename": after.get("filename") or before.get("filename"),
                "mode": after.get("mode") or before.get("mode"),
                "removed_tags": removed_tags,
                "added_tags": added_tags,
                "removed_part_keywords_count": len(removed_keywords),
                "added_part_keywords_count": len(added_keywords),
                "removed_spec_tokens": removed_specs,
                "added_spec_tokens": added_specs,
                "metric_delta": metric_delta,
            }
        )

    return {
        "totals": totals,
        "changed_snapshot_count": len(changed),
        "changed_snapshots": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-git", required=True, help="git revision path, e.g. HEAD:path/to/file.json")
    parser.add_argument("--new-file", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    old_fixture = _load_json_from_git(args.old_git, args.repo)
    new_fixture = _load_json_from_file(args.new_file)
    report = compare(old_fixture, new_fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False, indent=2))
    print(f"changed_snapshot_count={report['changed_snapshot_count']}")


if __name__ == "__main__":
    main()
