from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "db.sqlite3"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute(
        """
        SELECT d.source_path, d.filename, s.extraction_mode, s.raw_extract_json
        FROM drawing_metadata_drawingmetadatasnapshot s
        JOIN drawing_metadata_registereddrawing d ON d.id = s.drawing_id
        """
    ).fetchall()

    distribution: dict[str, int] = {}
    samples: list[tuple[int, int, int, str, str, str]] = []
    for source_path, filename, extraction_mode, raw_json in rows:
        try:
            payload = json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            continue
        raw_extract = payload.get("raw_extract") or payload
        texts = raw_extract.get("texts") or []
        view_sheets = raw_extract.get("view_sheets") or []
        geometry_primitives = raw_extract.get("geometry_primitives") or []
        text_count = len(texts)
        view_count = len(view_sheets)
        primitive_count = len(geometry_primitives)
        key = f"{extraction_mode}:{text_count}"
        distribution[key] = distribution.get(key, 0) + 1
        if extraction_mode == "2d":
            samples.append((text_count, primitive_count, view_count, extraction_mode, filename, source_path))

    print("distribution")
    for key, count in sorted(distribution.items())[:50]:
        print(f"{key}\t{count}")
    print("samples")
    for text_count, primitive_count, view_count, extraction_mode, filename, source_path in sorted(samples)[:50]:
        print(f"texts={text_count}\tprimitives={primitive_count}\tviews={view_count}\t{extraction_mode}\t{filename}\t{source_path}")


if __name__ == "__main__":
    main()
