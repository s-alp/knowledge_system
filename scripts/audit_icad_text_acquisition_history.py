from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "output" / "live_extracts"
OUTPUT_PATH = (
    ROOT
    / "output"
    / "drawing_entity_name_audit_2026-07-29"
    / "icad_text_acquisition_history.json"
)
TARGETS = (
    "U8718-S71-002_A3",
    "U8718-S71-149_A4",
    "CAA5012-02430012P1R1",
    "CAA5012-02434006P1R1",
    "9NK5E51B70-00-BRACKET",
    "9NK5E51M00-00-COVER",
    "9NK5E56H20-00-BRACKET",
)


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _extract_raw(payload: dict) -> dict:
    raw_extract = _dict(payload.get("raw_extract"))
    if raw_extract:
        return raw_extract
    envelope = _dict(payload.get("envelope"))
    return _dict(envelope.get("raw_extract"))


def _text_value(item: dict) -> str:
    for key in ("joined_text", "text", "value"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("text_lines", "lines"):
        value = item.get(key)
        if isinstance(value, list):
            lines = [str(line).strip() for line in value if str(line).strip()]
            if lines:
                return " / ".join(lines)
    return ""


def _target_for(path: Path) -> str | None:
    name = path.name.upper()
    return next((target for target in TARGETS if target.upper() in name), None)


def main() -> None:
    rows: list[dict] = []
    parse_failures: list[dict] = []
    for path in SOURCE_ROOT.rglob("*.json"):
        target = _target_for(path)
        if target is None:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parse_failures.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        raw_extract = _extract_raw(_dict(payload))
        source_kind = str(payload.get("source_kind") or "").lower()
        if not raw_extract or source_kind == "3d":
            continue
        texts = [_dict(item) for item in _list(raw_extract.get("texts"))]
        diagnostics = _dict(payload.get("condition_diagnostics"))
        if not diagnostics:
            diagnostics = _dict(raw_extract.get("condition_diagnostics"))
        warnings = _list(payload.get("warnings"))
        rows.append(
            {
                "target": target,
                "path": str(path.relative_to(ROOT)),
                "extractionProfile": payload.get("extraction_profile"),
                "scanAllViews": diagnostics.get("scanAllViews"),
                "viewSheetCount": len(_list(raw_extract.get("view_sheets"))),
                "viewNames": [
                    _dict(item).get("name")
                    for item in _list(raw_extract.get("view_sheets"))
                ],
                "textCount": len(texts),
                "dimensionCount": len(_list(raw_extract.get("dimensions"))),
                "geometryPrimitiveCount": len(
                    _list(raw_extract.get("geometry_primitives"))
                ),
                "printFrameCount": len(_list(raw_extract.get("print_frames"))),
                "warningCodes": [
                    _dict(item).get("code")
                    for item in warnings
                    if _dict(item).get("code")
                ],
                "textSamples": [
                    value
                    for value in (_text_value(item) for item in texts[:20])
                    if value
                ],
            }
        )
    rows.sort(key=lambda row: (row["target"], row["path"]))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "sourceRoot": str(SOURCE_ROOT.relative_to(ROOT)),
                "rows": rows,
                "parseFailures": parse_failures,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"rows={len(rows)}")
    print(f"parse_failures={len(parse_failures)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
