# Cloud Claude Code 検証パッケージ

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
| registered drawing | 42 |
| extraction job | 84 |
| snapshot | 84 |
| audit log | 160 |

## data JSON

- `drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json`: OK (264060 bytes)
- `drawing_metadata_fixture_all_shared_review_summary_validation_2026-07-17.json`: OK (298 bytes)
- `icad_shared_sample_current_audit_2026-07-16.json`: OK (132679 bytes)
- `icad_shared_sample_completion_2026-07-15.json`: OK (51168 bytes)
- `icad_2d_view_layer_print_frame_audit_current.json`: OK (10574 bytes)
- `icad_3d_structure_material_mass_audit_current.json`: OK (13070 bytes)
- `icad_goal_completion_coverage_audit_current.json`: OK (13047 bytes)
- `icad_handoff_numeric_consistency_audit_current.json`: OK (590 bytes)
- `icad_delivery_readiness_full_latest.json`: OK (22034 bytes)

## Cloudでの起動例

```powershell
cd C:\path\to\knowledge_system
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-base.txt
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe handoff\claude_cloud\tools\apply_seed_sql.py
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8001
```

別ターミナル:

```powershell
cd C:\path\to\knowledge_system\integrations\2D_3D_CAD_VIEWR\frontend
npm ci
$env:VITE_DEV_PROXY_TARGET="http://127.0.0.1:8001"
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
