# knowledge_system

ナレッジシステムの RAG 精度検証、ICAD 2D/3D からのタグ・属性抽出設計、Django 統合計画、および PoC 実装をまとめるリポジトリです。

## 現在の位置づけ

- 共同開発先からナレッジシステム本体ソースコードは共有されていません。
- そのため本リポジトリは、本体へ後で移植しやすい形で
  - 調査
  - 設計
  - 実装準備
  - 検証資料作成
  を進めるための作業場です。

## 主な内容

- `backend/`
  - Django / DRF ベースの standalone backend
  - `apps/drawing_metadata/` に API / service / task / template を集約
- `src/`
  - `IcadExtraction.Contracts`
  - `IcadExtraction.SxNet`
  - `IcadExtraction.Runner`
- `tests/`
  - C# 抽出 PoC 向けの単体テスト
- `docs/`
  - ICAD タグ・属性設計資料
  - Django 統合計画
  - 抽出結果スキーマ
  - タグ・属性管理 UI 計画
  - 実装セットアップ手順
- `scripts/`
  - RAG 検証結果の集計・追記スクリプト
- `local_test_materials/`
  - 検証用に最小限コピーした元資料
- `output/`
  - 集計済み Excel、画像、検証成果物
- `sxnet/`
  - ICAD `sxnet` リファレンス一式
- `docker-compose.backend.yml`
  - Docker に載せやすい Django / worker 側の最小構成

## 実装方針の要点

- ICAD ネイティブ抽出コアは `C#`
- 正規化、タグ生成、保存、RAG 連携は `Django(Python)` の service / task 層
- `Python -> C#` は `1図面 = 1回呼び出し` の一括実行
- `図面管理` をタグ・属性の正本とし、viewer と RAG は利用側に寄せる
- Django / worker は Linux や Docker に載せやすくし、`sxnet` を使う抽出器は Windows 側へ閉じ込める
- Windows worker が ICAD を自動起動した場合は、その worker が起こした ICAD だけを終了対象にできる

## 現在の PoC 実装

- Django backend:
  - `backend/knowledge_system_backend/`
  - `backend/apps/drawing_metadata/`
- 主要 API:
  - `GET/POST /api/v1/drawing-metadata/registrations`
  - `GET /api/v1/drawing-metadata/registrations/{drawing_id}`
  - `POST /api/v1/drawing-metadata/registrations/{drawing_id}/extract`
  - `PATCH /api/v1/drawing-metadata/registrations/{drawing_id}/overrides`
  - `GET /api/v1/drawing-metadata/jobs/{job_id}`
- 管理導線:
  - `/drawing-metadata/`
  - `/drawing-metadata/{drawing_id}/`
  - `/drawing-metadata/jobs/{job_id}/`
- C# 抽出 CLI:
  - `src/IcadExtraction.Runner`
  - `extract --input-path ... --source-kind 2d|3d --output-path ... --sxnet-dll-path ...`
  - `self-check --sxnet-dll-path ...`
- 3D 抽出 PoC:
  - `SxFileModel.open(true)` でモデルを開く
  - `SxModel.getGlobalWF()` -> `SxWF.getInfPartTree()` / `getInfExTopPart()`
- 2D 抽出 PoC:
  - 同じ `.icd` に対して `source-kind=2d` を指定し、`SxModel.getGlobalVS()` -> `SxVS.getSegList(...)` -> `SxEntSeg.getGeomList(...)`
  - 未検証の geometry は warning に逃がす

## Linux / Docker 方針

- Django backend 自体は Linux / Docker に載せる前提
- DB-backed worker も同様に Docker 化可能
- ただし `sxnet.dll` と `net48` 抽出器は Windows / iCAD 実行環境前提
- そのため本 PoC は
  - Docker 化しやすい Python/Django 側
  - 外出し可能な Windows 抽出 CLI
  に境界を分けている
- また、live 抽出では `sxnet.dll` の存在だけでなく **ICAD 本体の起動**も必要だった
- `C:\ICADSX\bin\icadsx.exe` は存在せず、少なくとも今回の環境では起動対象は `C:\ICADSX\bin\icad.exe` だった
- 最適構成としては、**人が触る ICAD と抽出 worker が使う ICAD を同居させない**。Windows worker 専用セッション、または専用マシンで運用するのが安全

## 実測メモ

- 同じ `.icd` から
  - `source-kind=3d`
  - `source-kind=2d`
  の両方で抽出できた
- つまり `.icd` を 2D 用と 3D 用で別ファイル扱いするより、**同一 source に対して抽出モードを切り替える**設計が自然
- 現行実装では `RegisteredDrawing.source_kind` を廃止し、`job / snapshot` 単位の `extraction_mode` に切り替えた
- `detail` API は `snapshotsByMode` と `composedMetadata` を返す

## ローカル起動

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; python -m venv "backend\.venv"'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe -m pip install -r "backend\requirements-base.txt"'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" migrate'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" runserver'
```

## Docker 起動

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; docker compose -f "docker-compose.backend.yml" up --build'
```

注意:

- `backend` / `worker` は Docker 化できる
- `DRAWING_METADATA_EXTRACTOR_EXECUTABLE` と `DRAWING_METADATA_SXNET_DLL_PATH` は別途設定が必要
- Linux コンテナの中で `sxnet` 抽出器まで完結させる前提ではない

## 重要ドキュメント

- [ICADタグ・属性 調査結果](./docs/icad_tag_attribute_investigation_2026-05-26.md)
- [ICADタグ・属性 設計計画](./docs/icad_tag_attribute_design_plan_2026-05-26.md)
- [ICADタグ・属性 実装引継ぎ](./docs/icad_tag_attribute_implementation_backlog_2026-05-26.md)
- [ICAD抽出の C# / Python 分担アーキテクチャ案](./docs/icad_csharp_python_architecture_2026-05-27.md)
- [Django統合計画](./docs/django_integration_plan_2026-05-28.md)
- [抽出結果スキーマ定義案](./docs/extraction_result_schema_2026-05-28.md)
- [タグ・属性管理UI計画](./docs/tag_attribute_management_ui_plan_2026-05-28.md)
- [ICAD抽出PoCセットアップ](./docs/icad_extraction_poc_setup_2026-05-28.md)
- [HTML要約報告](./docs/icad_tag_attribute_report_2026-05-26.html)

## 次に進めること

1. `sxnet.dll` の正式配置と起動条件を確定
2. 実サンプル 3D / 2D で live 抽出確認
3. Windows 抽出 worker との接続方式を確定
4. viewer detail / RAG 側の正式接続契約を詰める
5. 手動補正 UI を本体側へどう移植するか決める

## 補足

- 現時点のプロジェクト前提・検証方針は [AGENTS.md](./AGENTS.md) を正とします。
- `CLAUDE.md` は `AGENTS.md` と同期維持します。
