from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "db.sqlite3"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    print("jobs")
    for mode, status, count in connection.execute(
        """
        SELECT extraction_mode, status, COUNT(*)
        FROM drawing_metadata_drawingmetadataextractionjob
        GROUP BY extraction_mode, status
        ORDER BY extraction_mode, status
        """
    ):
        print(f"{mode}\t{status}\t{count}")

    print("latest_2d_snapshots")
    rows = connection.execute(
        """
        SELECT s.raw_extract_json
        FROM drawing_metadata_drawingmetadatasnapshot s
        WHERE s.extraction_mode = '2d'
        """
    ).fetchall()
    distribution: dict[tuple[int, int, int], int] = {}
    for (raw_json,) in rows:
        try:
            payload = json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            continue
        raw_extract = payload.get("raw_extract") or payload
        key = (
            len(raw_extract.get("view_sheets") or []),
            len(raw_extract.get("texts") or []),
            len(raw_extract.get("geometry_primitives") or []),
        )
        distribution[key] = distribution.get(key, 0) + 1
    for (view_count, text_count, primitive_count), count in sorted(distribution.items()):
        print(f"views={view_count}\ttexts={text_count}\tprimitives={primitive_count}\tcount={count}")

    print("recent_failed")
    for filename, mode, error_message in connection.execute(
        """
        SELECT d.filename, j.extraction_mode, j.error_message
        FROM drawing_metadata_drawingmetadataextractionjob j
        JOIN drawing_metadata_registereddrawing d ON d.id = j.drawing_id
        WHERE j.status = 'failed'
        ORDER BY j.updated_at DESC
        LIMIT 5
        """
    ):
        compact = " ".join((error_message or "").split())
        print(f"{mode}\t{filename}\t{compact[:240]}")


if __name__ == "__main__":
    main()
