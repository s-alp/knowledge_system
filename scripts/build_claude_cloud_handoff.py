from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "db.sqlite3"
PACKAGE_ROOT = ROOT / "handoff" / "claude_cloud"
SQL_DIR = PACKAGE_ROOT / "sql"
DATA_DIR = PACKAGE_ROOT / "data"
TOOLS_DIR = PACKAGE_ROOT / "tools"

HANDOFF_OUTPUTS = [
    "drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json",
    "drawing_metadata_fixture_all_shared_review_summary_validation_2026-07-17.json",
    "icad_shared_sample_current_audit_2026-07-16.json",
    "icad_shared_sample_completion_2026-07-15.json",
    "icad_2d_view_layer_print_frame_audit_current.json",
    "icad_3d_structure_material_mass_audit_current.json",
    "icad_goal_completion_coverage_audit_current.json",
    "icad_handoff_numeric_consistency_audit_current.json",
    "icad_delivery_readiness_full_latest.json",
]

DRAWING_TABLES = [
    "drawing_metadata_drawingmetadataauditlog",
    "drawing_metadata_drawingmetadatasnapshot",
    "drawing_metadata_drawingmetadataextractionjob",
    "drawing_metadata_registereddrawing",
]

SEED_TABLES_IN_INSERT_ORDER = [
    "drawing_metadata_registereddrawing",
    "drawing_metadata_drawingmetadataextractionjob",
    "drawing_metadata_drawingmetadatasnapshot",
    "drawing_metadata_drawingmetadataauditlog",
]


def _json_text(value: Any) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _quote(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _rows(con: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return list(con.execute(query, params))


def _schema_sql(con: sqlite3.Connection) -> str:
    statements: list[str] = [
        "-- Cloud Claude Code 検証用: drawing_metadata 関連テーブルの参照スキーマ",
        "-- 通常は Django migrate 後に seed_drawing_metadata_minimal.sql を投入してください。",
    ]
    for row in con.execute(
        """
        select type, name, sql
        from sqlite_master
        where name like 'drawing_metadata_%'
          and type in ('table', 'index')
          and sql is not null
        order by case type when 'table' then 0 else 1 end, name
        """
    ):
        statements.append(row["sql"].rstrip(";") + ";")
    return "\n\n".join(statements) + "\n"


def _compact_snapshots(con: sqlite3.Connection) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for row in _rows(con, 'select * from "drawing_metadata_drawingmetadatasnapshot" order by drawing_id, extraction_mode'):
        item = dict(row)
        # raw_extract_json is very large and requires Windows ICAD/SXNET context.
        # Cloud review uses canonical attributes, tags, manual overrides, and review state.
        item["raw_extract_json"] = json.dumps(
            {
                "cloudSeedNotice": "raw_extract_json is intentionally omitted in cloud seed; use data/*.json audits for extraction coverage.",
                "sourceMode": item.get("extraction_mode"),
            },
            ensure_ascii=False,
        )
        snapshots.append(item)
    return snapshots


def _seed_rows(con: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    snapshots = _compact_snapshots(con)
    drawing_ids = sorted({row["drawing_id"] for row in snapshots})
    latest_job_ids = sorted({row["latest_job_id"] for row in snapshots if row.get("latest_job_id")})

    drawings = [dict(row) for row in _rows(
        con,
        f'''
        select *
        from "drawing_metadata_registereddrawing"
        where id in ({",".join("?" for _ in drawing_ids)})
        order by filename, id
        ''',
        tuple(drawing_ids),
    )]
    jobs = [dict(row) for row in _rows(
        con,
        f'''
        select *
        from "drawing_metadata_drawingmetadataextractionjob"
        where id in ({",".join("?" for _ in latest_job_ids)})
        order by created_at, id
        ''',
        tuple(latest_job_ids),
    )] if latest_job_ids else []

    audit_rows: list[dict[str, Any]] = []
    if drawing_ids:
        for row in _rows(
            con,
            f'''
            select *
            from "drawing_metadata_drawingmetadataauditlog"
            where drawing_id in ({",".join("?" for _ in drawing_ids)})
            order by executed_at desc, id desc
            limit 160
            ''',
            tuple(drawing_ids),
        ):
            item = dict(row)
            item["before_json"] = "{}"
            item["after_json"] = "{}"
            audit_rows.append(item)
        audit_rows.reverse()

    return {
        "drawing_metadata_registereddrawing": drawings,
        "drawing_metadata_drawingmetadataextractionjob": jobs,
        "drawing_metadata_drawingmetadatasnapshot": snapshots,
        "drawing_metadata_drawingmetadataauditlog": audit_rows,
    }


def _insert_sql(table: str, rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    columns = list(rows[0].keys())
    lines = [f'-- {table}: {len(rows)} rows']
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            if column.endswith("_json"):
                value = _json_text(value)
            values.append(_quote(value))
        column_sql = ", ".join(f'"{column}"' for column in columns)
        value_sql = ", ".join(values)
        lines.append(f'INSERT INTO "{table}" ({column_sql}) VALUES ({value_sql});')
    return lines


def _seed_sql(seed: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "-- Cloud Claude Code 検証用 seed SQL",
        "-- Django migrate 済みの空SQLiteへ投入してください。",
        "-- 本番DB、創屋DB、実ICADファイル、APIキーは含みません。",
        "PRAGMA foreign_keys=OFF;",
    ]
    for table in DRAWING_TABLES:
        lines.append(f'DELETE FROM "{table}";')
    for table in SEED_TABLES_IN_INSERT_ORDER:
        lines.extend(_insert_sql(table, seed[table]))
    lines.append("PRAGMA foreign_keys=ON;")
    return "\n".join(lines) + "\n"


def _copy_data_outputs() -> list[dict[str, Any]]:
    source_dir = ROOT / "output" / "souya_handoff"
    copied: list[dict[str, Any]] = []
    for name in HANDOFF_OUTPUTS:
        src = source_dir / name
        if not src.exists():
            copied.append({"name": name, "copied": False, "reason": "missing"})
            continue
        dst = DATA_DIR / name
        shutil.copy2(src, dst)
        copied.append({"name": name, "copied": True, "bytes": dst.stat().st_size})
    return copied


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _readme(seed_counts: dict[str, int], copied: list[dict[str, Any]]) -> str:
    copied_lines = "\n".join(
        f"- `{item['name']}`: {'OK' if item.get('copied') else '欠落'}"
        + (f" ({item.get('bytes')} bytes)" if item.get("bytes") else "")
        for item in copied
    )
    return f"""# Cloud Claude Code 検証パッケージ

このフォルダは、Cloud版 Claude Code に ICADタグ・属性自動取得の実装を検証させるための最小パッケージです。

## 目的

- Cloud環境で `ICAD/SXNET/社内Jドライブ/Tドライブ/Windows実機` が無くても、画面・API・タグ/属性の設計妥当性を確認できるようにする。
- 実ICAD再抽出ではなく、既にローカルWindows環境で作成済みの抽出結果・監査JSON・seed DBで検証する。
- 創屋の本番DBや本番ナレッジシステムへ登録・変更・削除しない。

## 含めているもの

- `sql/schema_drawing_metadata.sql`: drawing_metadata 関連テーブルの参照スキーマ
- `sql/seed_drawing_metadata_minimal.sql`: Django migrate 後のSQLiteへ投入する検証用seed
- `tools/apply_seed_sql.py`: SQLiteへseed SQLを投入する小さな補助スクリプト
- `data/*.json`: 39件共有サンプル、2D/3D抽出、タグ・属性、ゴールカバレッジの監査結果
- `VALIDATION_CHECKLIST.md`: Cloud側に確認してほしい観点
- `PROMPT_FOR_CLAUDE.md`: そのままCloud Claude Codeへ渡す指示文

## seed SQL の件数

| テーブル | 件数 |
|---|---:|
| registered drawing | {seed_counts.get('drawing_metadata_registereddrawing', 0)} |
| extraction job | {seed_counts.get('drawing_metadata_drawingmetadataextractionjob', 0)} |
| snapshot | {seed_counts.get('drawing_metadata_drawingmetadatasnapshot', 0)} |
| audit log | {seed_counts.get('drawing_metadata_drawingmetadataauditlog', 0)} |

## data JSON

{copied_lines}

## Cloudでの起動例

```powershell
cd C:\\path\\to\\knowledge_system
python -m venv backend\\.venv
backend\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements-base.txt
backend\\.venv\\Scripts\\python.exe backend\\manage.py migrate
backend\\.venv\\Scripts\\python.exe handoff\\claude_cloud\\tools\\apply_seed_sql.py
backend\\.venv\\Scripts\\python.exe backend\\manage.py runserver 127.0.0.1:8001
```

別ターミナル:

```powershell
cd C:\\path\\to\\knowledge_system\\integrations\\2D_3D_CAD_VIEWR\\frontend
npm ci
$env:VITE_DEV_PROXY_TARGET=\"http://127.0.0.1:8001\"
npm run dev -- --host 127.0.0.1 --port 5173
```

## Cloud検証で対象外にすること

- `.icd` ファイルをSXNETで開いて再抽出すること
- ICADを起動すること
- workerで実抽出すること
- 創屋の本番DB/本番ナレッジシステムへ書き込むこと
- `.env` やGemini APIキーを要求すること

## 注意

`seed_drawing_metadata_minimal.sql` の `raw_extract_json` は軽量化のため意図的に省略しています。抽出カバレッジや2D/3D根拠は `data/*.json` を確認してください。
"""


def _checklist() -> str:
    return """# Cloud検証チェックリスト

## 画面

- `http://127.0.0.1:5173/` がフロントの入口として機能すること
- 図面管理、製品・装置・ユニット、部品、システム設定の導線が破綻していないこと
- 製品・装置・ユニット/部品は、一覧画面と詳細画面があり、詳細にタグ・属性・根拠が見えること
- 検索条件、検索結果、基本情報、関連情報が白枠のセクションとして見えること
- 図面管理は画像2D図/中間3Dファイルのビューア導線を壊していないこと
- ICAD抽出管理はユーザー画面ではなくシステム設定側に分離されていること

## データ

- 1 ICD = 1 登録単位になっていること
- 製品・装置・ユニットはサブアセンブリ/アセンブリ相当、部品は部品相当として扱われていること
- サブアセンブリ判定を「子階層がある」だけで決めていないこと。外部参照/参照モデルの有無を重く見ること
- タグが材質だけに偏っていないこと
- タグ・属性に source/evidence/reason/confidence があること
- 重量/質量はkgで小数点以下2桁表示になっていること
- 2D/3Dの両方にある項目は照合結果または差異が確認できること
- 図枠、全ビュー、レイヤー、印刷枠に関する未抽出理由が監査JSONで追えること

## API/実装

- `backend/apps/drawing_metadata` のAPIが本番DB前提の書き込みを行っていないこと
- seed投入後、`/api/v1/drawing-metadata/registrations/` と `/api/v1/knowledge-entities/` が200を返すこと
- worker未起動やCloud環境で、実抽出できないことがUI上で誤解されないこと
- Gemini APIキーが無い状態でも、既存抽出結果の表示・検証は可能であること

## 禁止

- 創屋本番DBへの接続、登録、変更、削除
- APIキーや認証情報をログ/fixture/READMEへ書くこと
- Cloud環境でICAD/SXNET実抽出ができたように見せること
"""


def _prompt_for_claude() -> str:
    return """# Cloud Claude Code への依頼文

このリポジトリは ICAD 2D/3D からタグ・属性候補を抽出し、ナレッジシステム風の図面管理、製品・装置・ユニット、部品ページへ表示する検証実装です。

あなたには Cloud 環境で検証してほしいです。Cloudでは ICAD/SXNET/社内ファイルサーバ/Jドライブ/Tドライブ/本番ナレッジシステムDB にはアクセスできません。したがって `.icd` の再抽出は検証対象外です。

## セットアップ

1. `handoff/claude_cloud/README.md` に従って backend/frontend を起動してください。
2. `handoff/claude_cloud/sql/seed_drawing_metadata_minimal.sql` を `tools/apply_seed_sql.py` で投入してください。
3. `handoff/claude_cloud/data/*.json` を、実ICAD抽出済みの監査根拠として読んでください。

## 検証してほしいこと

- `handoff/claude_cloud/VALIDATION_CHECKLIST.md` の項目を確認してください。
- UIが創屋ナレッジシステム風の一覧/詳細/関連情報の構造になっているか見てください。
- 製品・装置・ユニット/部品/図面管理でタグ・属性・根拠・履歴が自然に確認できるか見てください。
- タグ生成ルールが材質だけ、または意味の薄い加工指示タグに偏っていないか確認してください。
- 1 ICD = 1登録単位の考え方が壊れていないか確認してください。
- Cloudで実抽出できない箇所と、既存抽出結果から検証できる箇所を分けて報告してください。

## 絶対にしないこと

- 創屋本番DB、本番ナレッジシステムへの書き込み
- APIキーや `.env` の要求
- ICAD/SXNET再抽出がCloudでできる前提の評価

## 報告形式

重大な問題、仕様と違う問題、見た目/UXの問題、残リスク、追加でローカルWindows環境に確認してほしいこと、の順で簡潔に報告してください。
"""


def _apply_seed_script() -> str:
    return '''from __future__ import annotations

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
'''


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    SQL_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        seed = _seed_rows(con)
        _write_text(SQL_DIR / "schema_drawing_metadata.sql", _schema_sql(con))
        _write_text(SQL_DIR / "seed_drawing_metadata_minimal.sql", _seed_sql(seed))
    finally:
        con.close()

    copied = _copy_data_outputs()
    seed_counts = {table: len(rows) for table, rows in seed.items()}
    manifest = {
        "schemaVersion": "claude_cloud_handoff_manifest.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCommitNote": "Run git rev-parse HEAD in the receiving repo for the exact commit.",
        "seedCounts": seed_counts,
        "copiedData": copied,
        "cloudLimitations": [
            "ICAD/SXNET extraction is not runnable in cloud.",
            "raw_extract_json is compacted in seed SQL.",
            "Use data/*.json for real extraction coverage evidence.",
            "No production DB writes are allowed.",
        ],
    }
    _write_text(PACKAGE_ROOT / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    _write_text(PACKAGE_ROOT / "README.md", _readme(seed_counts, copied))
    _write_text(PACKAGE_ROOT / "VALIDATION_CHECKLIST.md", _checklist())
    _write_text(PACKAGE_ROOT / "PROMPT_FOR_CLAUDE.md", _prompt_for_claude())
    _write_text(TOOLS_DIR / "apply_seed_sql.py", _apply_seed_script())

    print(f"wrote {PACKAGE_ROOT}")


if __name__ == "__main__":
    main()
