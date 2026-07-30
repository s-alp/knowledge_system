"""既存SQLiteに残る廃止前の外部AI履歴件数を読み取り専用で確認する。

目的:
    現行UI・APIから旧項目を除外しても、過去のsnapshot、manual override、job warning
    がDB上では削除されていないことを確認する。

前提:
    Django migration済みの``backend/db.sqlite3``が存在すること。

失敗時:
    DB欠落、SQL実行失敗、読取不能を例外として終了する。DB更新処理は持たず、
    SQLiteのread-only URIで接続する。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "db.sqlite3"

HISTORY_QUERIES = {
    "snapshotCanonical": """
        SELECT COUNT(*)
        FROM drawing_metadata_drawingmetadatasnapshot
        WHERE CAST(canonical_attributes_json AS TEXT) LIKE ?
    """,
    "manualOverrides": """
        SELECT COUNT(*)
        FROM drawing_metadata_drawingmetadatasnapshot
        WHERE CAST(manual_overrides_json AS TEXT) LIKE ?
    """,
    "jobWarnings": """
        SELECT COUNT(*)
        FROM drawing_metadata_drawingmetadataextractionjob
        WHERE CAST(warnings_json AS TEXT) LIKE ?
    """,
}

HISTORY_PATTERNS = {
    "snapshotCanonical": "%llm_%",
    "manualOverrides": "%llm_%",
    "jobWarnings": "%title_block_llm_%",
}


def main() -> int:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"監査対象DBがありません: {DB_PATH}")

    connection = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        counts = {
            key: connection.execute(query, (HISTORY_PATTERNS[key],)).fetchone()[0]
            for key, query in HISTORY_QUERIES.items()
        }
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "database": str(DB_PATH),
                "readOnly": True,
                "retiredAiHistoryCounts": counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
