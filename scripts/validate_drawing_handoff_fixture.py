"""Validate drawing metadata handoff fixture contracts.

This script checks the JSON package that is handed to Souya/importing systems.
It intentionally validates shape and read-only handoff guarantees, not business
truth. The goal is to catch accidental contract drift before sharing a fixture.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_TARGET_KEYS = {"drawing", "product", "part", "project"}
EXPECTED_ATTRIBUTE_PAYLOAD_KEYS = {"attribute", "attribute_option", "attribute_value"}
EXPECTED_WRITE_POLICY = "preview_only_no_production_write"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _add_issue(issues: list[dict[str, Any]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def _validate_snapshot(snapshot: dict[str, Any], *, path: str, expected_mode: str, issues: list[dict[str, Any]]) -> None:
    if snapshot.get("extractionMode") != expected_mode:
        _add_issue(issues, f"{path}.extractionMode", f"expected {expected_mode!r}")
    if not isinstance(snapshot.get("rawExtract"), dict):
        _add_issue(issues, f"{path}.rawExtract", "must be an object")
    if not isinstance(snapshot.get("canonicalAttributes"), dict):
        _add_issue(issues, f"{path}.canonicalAttributes", "must be an object")
    if not isinstance(snapshot.get("derivedTags"), list):
        _add_issue(issues, f"{path}.derivedTags", "must be a list")
    latest_job = snapshot.get("latestJob")
    if not isinstance(latest_job, dict):
        _add_issue(issues, f"{path}.latestJob", "must be an object")
    elif latest_job.get("status") != "succeeded":
        _add_issue(issues, f"{path}.latestJob.status", "must be succeeded in a handoff fixture")


def _validate_attribute(attribute: dict[str, Any], *, path: str, issues: list[dict[str, Any]]) -> None:
    if not _is_non_empty_string(attribute.get("attributeName")):
        _add_issue(issues, f"{path}.attributeName", "must be a non-empty string")
    if not _is_non_empty_string(attribute.get("attributeValue")):
        _add_issue(issues, f"{path}.attributeValue", "must be a non-empty string")
    if not _is_non_empty_string(attribute.get("bindingStatus")):
        _add_issue(issues, f"{path}.bindingStatus", "must be a non-empty string")
    payload_shape = attribute.get("payloadShape")
    if not isinstance(payload_shape, dict):
        _add_issue(issues, f"{path}.payloadShape", "must be an object")
    elif set(payload_shape.keys()) != EXPECTED_ATTRIBUTE_PAYLOAD_KEYS:
        _add_issue(issues, f"{path}.payloadShape", "must use attribute/attribute_option/attribute_value keys")


def _validate_target(target: dict[str, Any], *, path: str, issues: list[dict[str, Any]]) -> None:
    if target.get("writePolicy") != EXPECTED_WRITE_POLICY:
        _add_issue(issues, f"{path}.writePolicy", f"must be {EXPECTED_WRITE_POLICY}")
    if target.get("targetKey") not in EXPECTED_TARGET_KEYS:
        _add_issue(issues, f"{path}.targetKey", "unknown target key")
    if not _is_non_empty_string(target.get("existingReception")):
        _add_issue(issues, f"{path}.existingReception", "must describe current production reception")
    if not isinstance(target.get("reviewRequired"), bool):
        _add_issue(issues, f"{path}.reviewRequired", "must be boolean")

    attributes = target.get("attributes")
    if not isinstance(attributes, list):
        _add_issue(issues, f"{path}.attributes", "must be a list")
        attributes = []
    for index, attribute in enumerate(attributes):
        if not isinstance(attribute, dict):
            _add_issue(issues, f"{path}.attributes[{index}]", "must be an object")
            continue
        _validate_attribute(attribute, path=f"{path}.attributes[{index}]", issues=issues)

    payload_preview = target.get("payloadPreview")
    if not isinstance(payload_preview, dict):
        _add_issue(issues, f"{path}.payloadPreview", "must be an object")
    else:
        preview_attributes = payload_preview.get("attributes", [])
        if preview_attributes and not isinstance(preview_attributes, list):
            _add_issue(issues, f"{path}.payloadPreview.attributes", "must be a list when present")
        preview_tags = payload_preview.get("tags", [])
        if preview_tags and not isinstance(preview_tags, list):
            _add_issue(issues, f"{path}.payloadPreview.tags", "must be a list when present")


def validate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    target_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    attribute_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()

    if fixture.get("schemaVersion") != "drawing_metadata_handoff_fixture.v1":
        _add_issue(issues, "schemaVersion", "must be drawing_metadata_handoff_fixture.v1")

    items = fixture.get("items")
    if not isinstance(items, list):
        _add_issue(issues, "items", "must be a list")
        items = []
    if fixture.get("itemCount") != len(items):
        _add_issue(issues, "itemCount", "must match len(items)")

    for index, item in enumerate(items):
        item_path = f"items[{index}]"
        if not isinstance(item, dict):
            _add_issue(issues, item_path, "must be an object")
            continue
        for key in ("drawingId", "filename", "detailApiPayload", "viewerBootstrap", "ragPayload", "knowledgeSystemPayloadPreview"):
            if key not in item:
                _add_issue(issues, f"{item_path}.{key}", "is required")

        detail = item.get("detailApiPayload")
        if not isinstance(detail, dict):
            _add_issue(issues, f"{item_path}.detailApiPayload", "must be an object")
            continue
        if detail.get("drawingId") != item.get("drawingId"):
            _add_issue(issues, f"{item_path}.detailApiPayload.drawingId", "must match item drawingId")
        if detail.get("filename") != item.get("filename"):
            _add_issue(issues, f"{item_path}.detailApiPayload.filename", "must match item filename")
        if not _is_non_empty_string(detail.get("sourcePath")):
            _add_issue(issues, f"{item_path}.detailApiPayload.sourcePath", "must be a non-empty string")

        snapshots = detail.get("snapshotsByMode")
        if not isinstance(snapshots, dict) or not snapshots:
            _add_issue(issues, f"{item_path}.detailApiPayload.snapshotsByMode", "must be a non-empty object")
        else:
            for mode, snapshot in snapshots.items():
                mode_counts[str(mode)] += 1
                if not isinstance(snapshot, dict):
                    _add_issue(issues, f"{item_path}.detailApiPayload.snapshotsByMode.{mode}", "must be an object")
                    continue
                _validate_snapshot(
                    snapshot,
                    path=f"{item_path}.detailApiPayload.snapshotsByMode.{mode}",
                    expected_mode=str(mode),
                    issues=issues,
                )

        viewer = item.get("viewerBootstrap")
        if not isinstance(viewer, dict):
            _add_issue(issues, f"{item_path}.viewerBootstrap", "must be an object")
        else:
            availability = viewer.get("availability")
            if not isinstance(availability, dict):
                _add_issue(issues, f"{item_path}.viewerBootstrap.availability", "must be an object")
            else:
                for key in ("has2d", "has3d"):
                    if not isinstance(availability.get(key), bool):
                        _add_issue(issues, f"{item_path}.viewerBootstrap.availability.{key}", "must be boolean")
            metadata = viewer.get("metadata")
            if not isinstance(metadata, dict):
                _add_issue(issues, f"{item_path}.viewerBootstrap.metadata", "must be an object")
            elif not isinstance(metadata.get("tags"), list):
                _add_issue(issues, f"{item_path}.viewerBootstrap.metadata.tags", "must be a list")

        rag = item.get("ragPayload")
        if not isinstance(rag, dict):
            _add_issue(issues, f"{item_path}.ragPayload", "must be an object")
        else:
            for key in ("schemaVersion", "drawing", "preFilters", "rankingSignals", "searchTextChunks", "reconciliation"):
                if key not in rag:
                    _add_issue(issues, f"{item_path}.ragPayload.{key}", "is required")

        preview = item.get("knowledgeSystemPayloadPreview")
        if not isinstance(preview, dict):
            _add_issue(issues, f"{item_path}.knowledgeSystemPayloadPreview", "must be an object")
        else:
            if preview.get("schemaVersion") != "knowledge_system_payload_preview.v1":
                _add_issue(issues, f"{item_path}.knowledgeSystemPayloadPreview.schemaVersion", "must be knowledge_system_payload_preview.v1")
            targets = preview.get("targets")
            if not isinstance(targets, list):
                _add_issue(issues, f"{item_path}.knowledgeSystemPayloadPreview.targets", "must be a list")
                targets = []
            target_keys = {target.get("targetKey") for target in targets if isinstance(target, dict)}
            if target_keys != EXPECTED_TARGET_KEYS:
                _add_issue(issues, f"{item_path}.knowledgeSystemPayloadPreview.targets", "must include drawing/product/part/project exactly")
            for target_index, target in enumerate(targets):
                if not isinstance(target, dict):
                    _add_issue(issues, f"{item_path}.knowledgeSystemPayloadPreview.targets[{target_index}]", "must be an object")
                    continue
                target_key = str(target.get("targetKey"))
                target_counts[target_key] += 1
                attribute_counts[target_key] += len(target.get("attributes") or [])
                tag_counts[target_key] += len(target.get("tags") or [])
                _validate_target(
                    target,
                    path=f"{item_path}.knowledgeSystemPayloadPreview.targets[{target_index}]",
                    issues=issues,
                )

    return {
        "valid": not issues,
        "itemCount": len(items),
        "issueCount": len(issues),
        "issues": issues,
        "summary": {
            "modes": dict(sorted(mode_counts.items())),
            "targets": dict(sorted(target_counts.items())),
            "attributeCounts": dict(sorted(attribute_counts.items())),
            "tagCounts": dict(sorted(tag_counts.items())),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate drawing metadata handoff fixture contract.")
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate_fixture(_load_json(args.fixture))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
