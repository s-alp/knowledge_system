# knowledge_system

ナレッジシステムのRAG精度検証、CAD 2D/3Dからのタグ・属性抽出、Django統合、Windows ICAD抽出agent、2D/3D統合フロントをまとめるリポジトリです。

## 現在の位置づけ

- 共同開発先からナレッジシステム本体ソースコードは共有されていません。
- 本リポジトリには、本体へ後で移植しやすい独立Django app、C#抽出器、Windows agent、統合Viteフロントが実装されています。
- ローカルDB、fixture、画面は抽出・正規化・タグ付与・連携payloadの検証用であり、共同開発先の本番DB/APIを置き換えるものではありません。
- タグ抽出・付与の現行仕様は [CADタグ抽出・属性正規化・タグ付与 現行仕様](./docs/tag_extraction_and_assignment_current_spec_2026-07-29.md) を正とします。

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
  - 現行仕様と関連ドキュメント索引
  - 抽出結果スキーマ、Windows agent契約、創屋向け抽出元カタログ
  - 調査・設計・検証snapshot
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

## 現在の実装

- Django backend:
  - `backend/knowledge_system_backend/`
  - `backend/apps/drawing_metadata/`
- 主要 API:
  - `GET/POST /api/v1/drawing-metadata/registrations`
  - `GET /api/v1/drawing-metadata/registrations/{drawing_id}`
  - `POST /api/v1/drawing-metadata/registrations/{drawing_id}/extract`
  - `PATCH /api/v1/drawing-metadata/registrations/{drawing_id}/overrides`
  - `GET /api/v1/drawing-metadata/jobs/{job_id}`
  - `GET/POST /api/v1/drawing-metadata/tag-dictionaries`
  - `GET /api/v1/knowledge-entities`
  - `POST /api/v1/drawing-metadata/agent/jobs/claim`
- 管理導線:
  - 利用者向け統合フロント: `http://127.0.0.1:5173/`
  - Django内部確認: `/internal/drawing-metadata/`
  - Djangoルート: API専用状態JSON
- C# 抽出 CLI:
  - `src/IcadExtraction.Runner`
  - `extract --input-path ... --source-kind 2d|3d --output-path ... --sxnet-dll-path ...`
  - `convert-cad --input-path ... --output-format dxf|step --output-dir ... --output-path ... --sxnet-dll-path ...`
  - `self-check --sxnet-dll-path ...`
- Django非依存のICAD変換入口:
  - `scripts/convert_icad_standalone.ps1`
  - 入力・Runner・SXNETの事前確認、既存成果物の保護、結果JSONと生成ファイルの完了確認を行う
- 3D 抽出 PoC:
  - `SxFileModel.open(true)` でモデルを開く
  - `SxModel.getGlobalWF()` -> `SxWF.getInfPartTree()` / `getInfExTopPart()`
- 2D 抽出 PoC:
  - 同じ `.icd` に対して `source-kind=2d` を指定し、`SxModel.getGlobalVS()` -> `SxVS.getSegList(...)` -> `SxEntSeg.getGeomList(...)`
  - 未検証の geometry は warning に逃がす

## Linux / Docker 方針

- Django backend 自体は Linux / Docker に載せる前提
- STEP / DXF を扱う generic CAD worker も Docker 化する
- ただし `sxnet.dll` と `net48` 抽出器は Windows / iCAD 実行環境前提
- そのため本 PoC は
  - Docker 上の Django API / SQLite / generic CAD worker
  - Windows 上の `IcadExtraction.Runner.exe agent`
  に境界を分けている
- Django側で `DrawingMetadataExtractionJob` をDBに積み、Windows agentがBearer token付きHTTP APIでICADジョブをclaimする
- agentはWindows側の元パスを優先し、参照できない場合はDjangoから入力をdownloadする
- preview assetをuploadし、生抽出JSONをcomplete APIへ返した後、Django側で正規化・タグ生成・保存する
- agentは抽出中もheartbeatを送り、job leaseを延長する
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

- `backend`はWeb/API、`worker`はSTEP/DXF専用であり、LinuxコンテナからWindows EXEは起動しない
- `backend/.env`の`DRAWING_METADATA_AGENT_TOKEN`へ十分に長いランダム値を設定する
- Windows agentが別PCの場合は、`DJANGO_ALLOWED_HOSTS`へDockerホストのホスト名またはIPアドレスを追加する
- SQLiteと図面メタデータ保存領域は`drawing-metadata-data` volumeへ永続化する
- ICADジョブはWindows agentがAPI経由で処理する

## Djangoを使わないICAD→DXF／STEP変換

変換コアと`IcadExtraction.Runner.exe convert-cad`はDjango、DB、HTTP APIに依存しません。手動実行や創屋側バッチでは、低水準引数と上書き確認を共通化したPowerShell入口を使用します。

初回はファイルを生成しない`-ValidateOnly`で実行環境を確認します。

```powershell
pwsh -NoLogo -NoProfile -File "scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\drawing\sample.icd" `
  -OutputFormat dxf `
  -OutputDirectory "C:\converted" `
  -SxNetDllPath "C:\path\to\sxnet.dll" `
  -IcadExecutablePath "C:\path\to\icad.exe" `
  -ValidateOnly
```

確認後、`-ValidateOnly`を外すとDXFを生成します。STEPの場合は`-OutputFormat step`へ変更します。既存成果物は保護され、置き換える場合だけ`-Overwrite`が必要です。

配布物、環境変数、結果JSON、終了判定、SXNET版差、創屋側の組み込み方は、[ICAD→DXF／STEP 独立変換 利用・引継ぎ手順](./docs/icad_dxf_step_standalone_conversion_guide_2026-07-29.md)を正本とします。

## Windows ICAD抽出agent

現在の同一PC構成から、同一社内ネットワーク上の別PCへICAD抽出を分離する場合は、
[別PCのICADをWindows抽出Agentとして接続する手順（創屋向け）](./docs/icad_remote_windows_agent_setup_for_souya_2026-07-30.md)を参照してください。

### 1. net48版をpublish

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; dotnet publish "src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" -c Release -f net48 --no-self-contained'
```

### 2. Windows側の環境変数

Docker側`backend/.env`とWindows側の`DRAWING_METADATA_AGENT_TOKEN`は同じ値にする。token、API URL、ICAD実行ファイル等はリポジトリへコミットしない。

```powershell
$token = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$token
$env:DRAWING_METADATA_AGENT_API_BASE_URL = "http://127.0.0.1:8000/"
$env:DRAWING_METADATA_AGENT_TOKEN = "<生成してbackend/.envへ設定したtoken>"
$env:DRAWING_METADATA_AGENT_WORKER_NAME = $env:COMPUTERNAME
$env:DRAWING_METADATA_SXNET_DLL_PATH = "C:\path\to\sxnet.dll"
$env:DRAWING_METADATA_ICAD_EXECUTABLE = "C:\ICADSX\bin\icad.exe"
```

### 3. 常駐起動

```powershell
pwsh -NoLogo -NoProfile -File "scripts\start_windows_extraction_agent.ps1"
```

疎通だけを確認するときは、キューが空の状態で`-Once`を付ける。ジョブがある場合は1件処理して終了する。

```powershell
pwsh -NoLogo -NoProfile -File "scripts\start_windows_extraction_agent.ps1" -Once
```

agent APIは以下を提供する。

- `POST /api/v1/drawing-metadata/agent/jobs/claim`
- `GET /api/v1/drawing-metadata/agent/jobs/{jobId}/source`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/assets`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/complete`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/fail`
- `POST /api/v1/drawing-metadata/agent/heartbeat`

起動設定、全API payload、C#入出力JSON、異常時の扱いは、正本である
[C# Windows ICAD抽出エージェント連携仕様](./docs/windows_extraction_agent_api_design_2026-07-29.md)を参照する。

## 重要ドキュメント

- [CADタグ抽出・属性正規化・タグ付与 現行仕様（全体の正本）](./docs/tag_extraction_and_assignment_current_spec_2026-07-29.md)
- [タグ抽出・付与関連ドキュメント索引](./docs/tag_extraction_documentation_index_2026-07-29.md)
- [抽出結果スキーマ（Django保存・正規化の正本）](./docs/extraction_result_schema_2026-05-28.md)
- [C# Windows ICAD抽出エージェント連携仕様（現行契約の正本）](./docs/windows_extraction_agent_api_design_2026-07-29.md)
- [CADタグ・属性抽出 抽出元カタログと具体例（創屋様向け）](./docs/cad_tag_extraction_sources_for_souya_2026-07-28.md)
- [ICAD→DXF／STEP 独立変換 利用・引継ぎ手順](./docs/icad_dxf_step_standalone_conversion_guide_2026-07-29.md)

2026-05月の調査、設計計画、バックログ、Django/UI計画、PoCセットアップ、HTML報告は履歴資料です。読み分けはドキュメント索引を参照してください。

## 次に進めること

1. 幾何公差種別・溶接記号種別・PRFX実フィールド等をWindows実機で継続確認
2. 客先横断の辞書語彙と抽出率を検証
3. Windows agent専用セッションまたは専用マシンで連続運転を確認
4. 創屋本番の属性保存API、タグ保存口、属性マスタID、RAG更新契約を確定
5. 手動補正・レビュー・監査ログを創屋本体へ移植する境界を確定

## 補足

- 現時点のプロジェクト前提・検証方針は [AGENTS.md](./AGENTS.md) を正とします。
- `CLAUDE.md` は `AGENTS.md` と同期維持します。
