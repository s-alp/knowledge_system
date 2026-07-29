"""創屋引継ぎ用seed SQLを検証用SQLiteへ適用する。

固定されたSQLファイルだけを読み込み、対象DBが存在しない場合やSQL実行に失敗した場合は
処理を中断する。本番DBや外部APIには接続しない。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "backend" / "db.sqlite3"
SQL_PATH = ROOT / "handoff" / "claude_cloud" / "sql" / "seed_drawing_metadata_minimal.sql"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}. Run backend/manage.py migrate first.")
    sql = SQL_PATH.read_text(encoding="utf-8")
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(sql)
        con.commit()
    finally:
        con.close()
    print(f"applied seed SQL: {SQL_PATH}")


if __name__ == "__main__":
    main()
