from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

MANIFEST_PATH = (
    ROOT
    / "output"
    / "souya_handoff"
    / "icad_extract_import_manifest_all_shared_2026-07-15.json"
)
OUTPUT_PATH = (
    ROOT
    / "output"
    / "drawing_entity_name_audit_2026-07-29"
    / "icad_text_integrity.json"
)
DXF_SUMMARY_PATH = ROOT / "output" / "dxf_full_audit_2026-07-28" / "summary.json"
MOJIBAKE_MARKERS = frozenset("縺繧譁蜿逕莉髯謖陦")


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _text_values(raw_extract: dict) -> list[str]:
    values: list[str] = []
    for item_value in _list(raw_extract.get("texts")):
        item = _dict(item_value)
        joined_text = item.get("joined_text")
        if isinstance(joined_text, str):
            values.append(joined_text)
            continue
        text_lines = item.get("text_lines")
        if isinstance(text_lines, list):
            values.append(" ".join(str(line) for line in text_lines))
            continue
        values.append("")
    return values


def _integrity_issues(text: str) -> list[str]:
    issues: list[str] = []
    if "\ufffd" in text:
        issues.append("replacement_character")
    if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
        issues.append("control_character")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        issues.append("surrogate")
    if any(0xE000 <= ord(char) <= 0xF8FF for char in text):
        issues.append("private_use_character")
    if sum(char in MOJIBAKE_MARKERS for char in text) >= 2:
        issues.append("common_mojibake_marker_sequence")
    return issues


def _line_join_mismatches(raw_extract: dict) -> list[dict]:
    mismatches: list[dict] = []
    for index, item_value in enumerate(_list(raw_extract.get("texts"))):
        item = _dict(item_value)
        lines = item.get("text_lines")
        joined = item.get("joined_text")
        if not isinstance(lines, list) or not isinstance(joined, str):
            continue
        expected = " ".join(str(line).strip() for line in lines if str(line).strip())
        if expected != joined:
            mismatches.append(
                {
                    "index": index,
                    "expectedFromTextLines": expected,
                    "joinedText": joined,
                }
            )
    return mismatches


def main() -> None:
    import django

    django.setup()

    from apps.drawing_metadata.models import RegisteredDrawing
    from audit_dxf_name_fields import _text_records

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    dxf_summary = json.loads(DXF_SUMMARY_PATH.read_text(encoding="utf-8"))
    dxf_paths = {
        str(item.get("filename") or ""): Path(str(item["dxfPath"]))
        for item in dxf_summary.get("results", [])
        if isinstance(item, dict) and item.get("dxfPath")
    }
    rows: list[dict] = []
    totals = Counter()
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        selected_2d = next(
            (
                item
                for item in entry.get("selectedFiles", [])
                if isinstance(item, dict) and item.get("mode") == "2d"
            ),
            None,
        )
        if selected_2d is None:
            continue
        source_path = str(entry.get("sourcePath") or "")
        extract_path = Path(str(selected_2d.get("path") or ""))
        source_payload = json.loads(extract_path.read_text(encoding="utf-8"))
        source_raw = _dict(source_payload.get("raw_extract"))
        drawing = RegisteredDrawing.objects.filter(source_path=source_path).first()
        snapshot = (
            drawing.snapshots.filter(extraction_mode="2d").first()
            if drawing is not None
            else None
        )
        db_raw = snapshot.raw_extract_json if snapshot is not None else {}
        source_texts = _text_values(source_raw)
        db_texts = _text_values(db_raw)
        issue_counts = Counter()
        issue_samples: list[dict] = []
        dxf_path = dxf_paths.get(str(entry.get("filename") or ""))
        dxf_texts = (
            [item["text"] for item in _text_records(dxf_path)]
            if dxf_path is not None and dxf_path.is_file()
            else []
        )
        for index, text in enumerate(db_texts):
            issues = _integrity_issues(text)
            issue_counts.update(issues)
            if issues and len(issue_samples) < 10:
                issue_samples.append(
                    {
                        "index": index,
                        "text": text,
                        "issues": issues,
                        "codePoints": [f"U+{ord(char):04X}" for char in text],
                        "dxfMatchesWithoutPrivateUse": [
                            candidate
                            for candidate in dxf_texts
                            if "".join(
                                char
                                for char in text
                                if not 0xE000 <= ord(char) <= 0xF8FF
                            )
                            in candidate
                        ][:10],
                    }
                )
        text_lists_equal = source_texts == db_texts
        totals["drawings"] += 1
        totals["source_texts"] += len(source_texts)
        totals["db_texts"] += len(db_texts)
        totals["text_list_mismatch_drawings"] += int(not text_lists_equal)
        totals["line_join_mismatch_items"] += len(_line_join_mismatches(source_raw))
        totals.update(
            {
                f"issue.{key}": value
                for key, value in issue_counts.items()
            }
        )
        rows.append(
            {
                "filename": entry.get("filename"),
                "sourcePath": source_path,
                "extractPath": str(extract_path),
                "drawingId": str(drawing.id) if drawing is not None else None,
                "sourceTextCount": len(source_texts),
                "dbTextCount": len(db_texts),
                "sourceAndDbTextListsEqual": text_lists_equal,
                "sourceLineJoinMismatches": _line_join_mismatches(source_raw),
                "integrityIssueCounts": dict(issue_counts),
                "integrityIssueSamples": issue_samples,
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": "icad_text_integrity.v1",
        "manifestPath": str(MANIFEST_PATH),
        "totals": dict(sorted(totals.items())),
        "rows": rows,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["totals"], ensure_ascii=True, sort_keys=True))
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
