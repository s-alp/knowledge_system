# C# Windows ICAD抽出エージェント連携仕様

- ステータス: **現行実装の正本**
- 契約バージョン: `1.0.0`
- 最終更新日: 2026-07-30
- 対象:
  - Docker / Linux上のDjango Web・API
  - Windows上の`IcadExtraction.Runner.exe agent`
  - ICAD / SXNETを使う2D・3D抽出

本資料は、C#へ渡す情報、C#から返る情報、HTTP API、起動設定、ファイル転送、エラー処理を1つに統合した連携仕様である。

創屋側は本資料のHTTP契約をDjango側で維持すれば、C#ソースの変更や再ビルドを行う必要はない。創屋側のDB・認証・ジョブモデルが異なる場合は、Django側のadapterで本契約へ変換する。

## 1. 正本と参照資料

### 1.1 本資料の位置づけ

| 対象 | 正本 |
|---|---|
| Windows agentの起動・環境変数 | 本資料 |
| DjangoからC#へ渡すjob情報 | 本資料 |
| agent APIのrequest / response | 本資料 |
| C#が返す抽出JSON | 本資料 |
| lease、heartbeat、失敗処理 | 本資料 |
| Django正規化後の属性・タグ | `docs/extraction_result_schema_2026-05-28.md`のDjango保存スキーマ |
| 抽出からタグ付与・UI・運用までの全体 | `docs/tag_extraction_and_assignment_current_spec_2026-07-29.md` |
| C# / Djangoの設計理由 | `docs/icad_csharp_python_architecture_2026-05-27.md` |

旧資料と本資料が矛盾する場合は、本資料と現行コードを優先する。

### 1.2 実装照合先

| 実装 | 確認内容 |
|---|---|
| `src/IcadExtraction.Runner/WindowsExtractionAgent.cs` | agent設定、API payload、入力解決、heartbeat、asset upload |
| `src/IcadExtraction.Runner/Program.cs` | `agent` / `extract`コマンド、C#内部呼び出し |
| `src/IcadExtraction.Contracts/Models.cs` | 抽出結果DTO |
| `src/IcadExtraction.Contracts/SchemaVersions.cs` | 抽出器名、契約バージョン |
| `schemas/tag_extraction/icad-csharp-raw-extraction.v1.schema.json` | C#出力JSONの機械可読な境界契約 |
| `scripts/generate_tag_extraction_schemas.py` | `Models.cs`から境界Schemaを再生成・検査 |
| `src/IcadExtraction.SxNet/ExtractionConditionOptions.cs` | 抽出オプション |
| `backend/apps/drawing_metadata/api/agent_views.py` | 認証、serializer、API応答 |
| `backend/apps/drawing_metadata/tasks/extraction_tasks.py` | claim、lease、complete、fail |
| `backend/knowledge_system_backend/settings.py` | Django設定値 |

## 2. 責務境界

| 処理 | Windows C# agent | Django / Docker |
|---|---:|---:|
| ICADファイルをSXNETで開く | ○ | - |
| ICADの2D・3D要素を走査 | ○ | - |
| 生抽出JSONを生成 | ○ | - |
| preview用ファイルを生成・upload | ○ | 保存・配信 |
| 抽出ジョブ登録・排他claim | API利用 | ○ |
| 正規化、辞書適用、タグ生成 | - | 独立Pythonコア。Djangoまたは単体CLI/Dockerから実行 |
| snapshot、手動補正、監査ログ | - | ○ |
| viewer / RAG連携 | - | ○ |
| STEP / DXF抽出 | - | Docker generic worker |

C#は業務辞書やタグ確定処理を持たない。C#が返すのは、ICADから取得した生情報と抽出条件・警告である。

## 3. 処理フロー

1. DjangoがICAD図面と2D / 3D抽出ジョブを登録する。
2. Windows agentがBearer token付きでjobをclaimする。
3. agentは`source.path`をWindowsから直接参照する。
4. 直接参照できない場合は`source.downloadUrl`から図面を取得する。
5. SHA-256が渡された場合は、抽出前にファイル内容を照合する。
6. agentは同じEXEの`extract`処理を`1図面 = 1回`実行する。
7. 抽出中はheartbeatを送り、Djangoがjob leaseを延長する。
8. agentはpreview assetを先にuploadする。
9. agentは生抽出JSONをcomplete APIへ送る。
10. Djangoが独立Pythonコアを呼び、正規化、タグ生成、snapshot、監査ログを保存する。
11. 失敗時はagentがfail APIへエラー全文を返す。

## 4. 配置・実行要件

### 4.1 Windows側

- Windows上で動作すること
- `.NET Framework 4.8`版の`IcadExtraction.Runner.exe`
- ICAD本体
- ICADと互換性のある`sxnet.dll`
- Django APIへHTTP(S)接続できること
- 元図面を直接参照する場合は、そのWindows実行ユーザーがドライブまたはUNCパスを読めること
- ICADライセンスとWindowsセッションが利用可能であること

人が操作するICADとは分離し、Windows agent専用セッションまたは専用端末での常駐を推奨する。

### 4.2 publish

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; dotnet publish "src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" -c Release -f net48 --no-self-contained'
```

### 4.3 起動

```powershell
pwsh -NoLogo -NoProfile -File "scripts\start_windows_extraction_agent.ps1"
```

キューが空なら疎通確認だけを行い、ジョブがあれば1件処理して終了する場合:

```powershell
pwsh -NoLogo -NoProfile -File "scripts\start_windows_extraction_agent.ps1" -Once
```

## 5. Windows agentへ設定する情報

コマンドライン引数が環境変数より優先される。

| CLI引数 | 環境変数 | 必須 | 既定値・制約 |
|---|---|---:|---|
| `--api-base-url` | `DRAWING_METADATA_AGENT_API_BASE_URL` | ○ | 絶対HTTP(S) URL |
| `--api-token` | `DRAWING_METADATA_AGENT_TOKEN` | ○ | Django側と同じtoken |
| `--worker-name` | `DRAWING_METADATA_AGENT_WORKER_NAME` | - | Windowsマシン名 |
| `--mode` | `DRAWING_METADATA_AGENT_MODE` | - | `all`。`2d` / `3d` / `all` |
| `--sxnet-dll-path` | `DRAWING_METADATA_SXNET_DLL_PATH` | ○ | 存在する`sxnet.dll` |
| `--icad-executable-path` | `DRAWING_METADATA_ICAD_EXECUTABLE` | - | 指定時は存在する`icad.exe` |
| `--icad-startup-wait-seconds` | `DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS` | - | `8`、正の整数 |
| `--shutdown-icad-if-autostarted` | `DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED` | - | `true` |
| `--poll-seconds` | `DRAWING_METADATA_AGENT_POLL_SECONDS` | - | `5`、正の整数 |
| `--heartbeat-seconds` | `DRAWING_METADATA_AGENT_HEARTBEAT_SECONDS` | - | `10`、正の整数 |
| `--api-timeout-seconds` | `DRAWING_METADATA_AGENT_API_TIMEOUT_SECONDS` | - | `120`、正の整数 |
| `--work-root` | `DRAWING_METADATA_AGENT_WORK_ROOT` | - | `%TEMP%\IcadExtractionAgent` |
| `--once` | `DRAWING_METADATA_AGENT_ONCE` | - | `false` |
| `--keep-work-files` | `DRAWING_METADATA_AGENT_KEEP_WORK_FILES` | - | `false` |

起動時に必須値、URL形式、数値、真偽値、`sxnet.dll`、指定された`icad.exe`を検証する。不正な場合はagentを起動しない。

### 5.1 設定例

```powershell
$env:DRAWING_METADATA_AGENT_API_BASE_URL = "http://127.0.0.1:8000/"
$env:DRAWING_METADATA_AGENT_TOKEN = "<Django側と同じランダムtoken>"
$env:DRAWING_METADATA_AGENT_WORKER_NAME = $env:COMPUTERNAME
$env:DRAWING_METADATA_SXNET_DLL_PATH = "C:\path\to\sxnet.dll"
$env:DRAWING_METADATA_ICAD_EXECUTABLE = "C:\ICADSX\bin\icad.exe"
```

token、実際のAPI URL、社内パス、ライセンス情報はリポジトリへコミットしない。

## 6. Django側の設定

| 環境変数 | 必須 | 既定値・役割 |
|---|---:|---|
| `DRAWING_METADATA_AGENT_TOKEN` | ○ | agentと共有するBearer token。未設定時はagent APIを`503`で停止 |
| `DRAWING_METADATA_AGENT_MAX_ASSET_BYTES` | - | `536870912` bytes |
| `DRAWING_METADATA_ALLOW_REMOTE_AGENT_PATHS` | - | `false`。Dockerから存在確認できないWindows / UNCパスの登録を許可する場合は`true` |
| `DRAWING_METADATA_JOB_LEASE_SECONDS` | - | `180`秒 |
| `DRAWING_METADATA_STORAGE_ROOT` | - | upload、raw result等の保存ルート |
| `DRAWING_METADATA_PREVIEW_ASSET_ROOT` | - | preview asset保存ルート |

Docker構成では、Windowsから参照する原本パスをDjangoへ登録できるよう`DRAWING_METADATA_ALLOW_REMOTE_AGENT_PATHS=true`を設定する。

## 7. HTTP共通契約

- ベースURL例: `http://docker-host:8000/`
- 認証:

```http
Authorization: Bearer <DRAWING_METADATA_AGENT_TOKEN>
```

- JSON requestは`Content-Type: application/json; charset=utf-8`
- asset uploadは`multipart/form-data`
- `workerName`はjob所有者の識別子として使用する
- asset、complete、fail、job付きheartbeatは、`processing`かつ同一`workerName`のjobだけ受け付ける
- 日時はDjango REST FrameworkのISO 8601形式
- UUIDは文字列で送受信する

## 8. agent API

### 8.1 job claim

`POST /api/v1/drawing-metadata/agent/jobs/claim`

request:

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "mode": "all",
  "runnerVersion": "1.0.0",
  "processId": 1234
}
```

| 項目 | 型 | 必須 | 説明 |
|---|---|---:|---|
| `workerName` | string | ○ | agent識別子、最大255文字 |
| `mode` | string | - | `2d` / `3d` / `all`、既定`all` |
| `runnerVersion` | string | - | 現行`1.0.0`、最大64文字 |
| `processId` | integer/null | - | 正のプロセスID |

ICADジョブがある場合は`200 OK`:

```json
{
  "jobId": "11111111-1111-1111-1111-111111111111",
  "drawingId": "22222222-2222-2222-2222-222222222222",
  "extractionMode": "3d",
  "extractionProfile": "default",
  "extractionOptions": {
    "scanPartTree": true,
    "scanPartMaterials": true
  },
  "leaseExpiresAt": "2026-07-29T12:34:56+09:00",
  "source": {
    "path": "\\\\server\\cad\\sample.icd",
    "filename": "sample.icd",
    "format": "icad",
    "sha256": "64文字のSHA-256または空文字",
    "downloadUrl": "http://docker-host:8000/api/v1/drawing-metadata/agent/jobs/11111111-1111-1111-1111-111111111111/source?workerName=WINDOWS-AGENT-01",
    "downloadAvailable": false
  },
  "preview": {
    "baseUrl": "http://docker-host:8000/api/v1/drawing-metadata-preview-assets/11111111-1111-1111-1111-111111111111"
  }
}
```

| response項目 | C#での扱い |
|---|---|
| `jobId` | work directory、API URL、previewファイル名に使用 |
| `drawingId` | Django側の追跡情報。現行C#処理では未使用 |
| `extractionMode` | `extract --source-kind`へ渡す。`2d`または`3d` |
| `extractionProfile` | 抽出条件の識別名。空なら`default` |
| `extractionOptions` | C#抽出オプション |
| `leaseExpiresAt` | Django側のlease情報。agentはheartbeatで延長 |
| `source.path` | Windowsから直接読める場合の第一候補 |
| `source.filename` | download時の安全なファイル名、原本メタデータ |
| `source.format` | `icad`。Django側の情報であり現行C#処理では未使用 |
| `source.sha256` | 値がある場合は抽出前に内容を照合 |
| `source.downloadUrl` | Docker保存領域からのdownload URL |
| `source.downloadAvailable` | download可否 |
| `preview.baseUrl` | 抽出JSONへ設定するpreview公開URL |

対象jobがない場合は`204 No Content`でbodyを返さない。

Windows agentのclaim対象は`source_format=icad`だけである。STEP / DXFはclaimしない。

### 8.2 heartbeat

`POST /api/v1/drawing-metadata/agent/heartbeat`

request:

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "mode": "all",
  "state": "processing",
  "jobId": "11111111-1111-1111-1111-111111111111",
  "runnerVersion": "1.0.0",
  "processId": 1234,
  "lastError": ""
}
```

| 項目 | 型 | 必須 | 説明 |
|---|---|---:|---|
| `workerName` | string | ○ | agent識別子 |
| `mode` | string | - | `2d` / `3d` / `all` |
| `state` | string | ○ | `starting` / `claiming` / `idle` / `processing` / `stopping` / `error` |
| `jobId` | UUID/null | - | `processing`時の所有job |
| `runnerVersion` | string | - | agentバージョン |
| `processId` | integer/null | - | agentプロセスID |
| `lastError` | string | - | エラー全文または空文字 |

job付きheartbeatはjob leaseを延長する。

response `200 OK`:

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "state": "processing",
  "updatedAt": "2026-07-29T12:34:00+09:00"
}
```

### 8.3 source download

`GET /api/v1/drawing-metadata/agent/jobs/{jobId}/source?workerName={workerName}`

- request bodyなし
- `workerName` query parameter必須
- Django保存領域内に実ファイルがある場合だけdownloadできる
- 成功時は`200 OK`のバイナリ
- `Content-Disposition`へ元ファイル名を設定
- SHA-256が登録されている場合は`X-Content-SHA256` response headerを設定
- DockerにファイルがなくWindows原本パスだけの場合は`404`

### 8.4 preview asset upload

`POST /api/v1/drawing-metadata/agent/jobs/{jobId}/assets`

`multipart/form-data`:

| part名 | 型 | 必須 | 説明 |
|---|---|---:|---|
| `workerName` | text | ○ | job所有agent |
| `relativePath` | text | ○ | preview work directoryからの相対パス |
| `file` | binary | ○ | asset本体 |

response `201 Created`:

```json
{
  "relativePath": "sample.stl",
  "sizeBytes": 130547
}
```

`relativePath`は絶対パス、空要素、`.`、`..`を受け付けない。保存先jobディレクトリ外への解決も拒否する。ファイルサイズ上限超過は`400`で拒否する。

### 8.5 complete

`POST /api/v1/drawing-metadata/agent/jobs/{jobId}/complete`

request:

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "result": {
    "input_path": "\\\\server\\cad\\sample.icd",
    "source_file": {},
    "source_format": "icad",
    "source_kind": "3d",
    "extraction_profile": "default",
    "extraction_options": {},
    "condition_diagnostics": {},
    "extractor_name": "icad-csharp-extractor",
    "extractor_version": "1.0.0",
    "elapsed_ms": 4027,
    "warnings": [],
    "raw_extract": {}
  }
}
```

`result`はJSON object必須であり、`schemas/tag_extraction/icad-csharp-raw-extraction.v1.schema.json`を満たす。Djangoは受信後に独立Pythonコアへ渡し、次を実行する。

1. `raw_extract`の正規化
2. 2Dの場合は必要に応じて図枠候補分類
3. 派生タグ生成
4. snapshot保存
5. jobを`succeeded`へ更新
6. 監査情報に`windows-agent:{workerName}`を保存

response `200 OK`:

```json
{
  "jobId": "11111111-1111-1111-1111-111111111111",
  "status": "succeeded"
}
```

### 8.6 fail

`POST /api/v1/drawing-metadata/agent/jobs/{jobId}/fail`

request:

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "errorMessage": "例外型、message、inner exception、stack traceを含むエラー全文"
}
```

`errorMessage`は必須、最大20,000文字。agent側でも上限に収めて送る。

response `200 OK`:

```json
{
  "jobId": "11111111-1111-1111-1111-111111111111",
  "status": "failed"
}
```

## 9. APIステータス・エラー

| HTTP | 条件 |
|---:|---|
| `200` | claim成功、heartbeat、source download、complete、fail |
| `201` | asset upload成功 |
| `204` | claim対象なし |
| `400` | JSON、field、mode、state、relativePath、asset size等が不正 |
| `401` | Bearer tokenなし・不一致 |
| `404` | jobまたはdownload可能なsourceがない |
| `409` | jobが`processing`ではない、または別workerが所有 |
| `503` | Django側に`DRAWING_METADATA_AGENT_TOKEN`が未設定 |

エラー時にagentはHTTP statusとresponse bodyをコンソールへ出す。抽出中の例外はfail APIへ送り、Django jobにも残す。

## 10. 入力ファイルの決定規則

1. `source.path`が空でなく、Windowsから`File.Exists`で確認できる場合はその原本を使用する。
2. 参照できない場合、`downloadAvailable=true`かつ`downloadUrl`ありならwork directoryへdownloadする。
3. どちらも利用できない場合は失敗する。
4. `source.sha256`が空でなければ、使用するファイルをSHA-256で照合する。
5. 不一致なら抽出せずfailする。

downloadは次の場所へ保存する。

```text
{workRoot}\{jobId}\input\{安全化したfilename}
```

抽出結果とpreviewは同じjob directory配下へ作る。既定では成功・失敗後に削除し、`keep-work-files=true`の場合だけ診断用に残す。

## 11. C#内部の`extract`入力

agentはclaim responseを次の`extract`入力へ変換する。

| `extract`引数 | 値 |
|---|---|
| `--input-path` | 直接参照またはdownloadしたICADパス |
| `--source-kind` | `extractionMode` |
| `--output-path` | `{workRoot}\{jobId}\result.json` |
| `--sxnet-dll-path` | agent設定値 |
| `--icad-executable-path` | agent設定値。設定時のみ |
| `--icad-startup-wait-seconds` | agent設定値 |
| `--shutdown-icad-if-autostarted` | agent設定値 |
| `--extraction-profile` | `extractionProfile`、空なら`default` |
| `--extraction-options-json` | `extractionOptions` |
| `--preview-output-dir` | `{workRoot}\{jobId}\preview` |
| `--preview-public-base-url` | `preview.baseUrl` |
| `--preview-file-name-prefix` | `jobId` |

## 12. 抽出プロファイル・オプション

`extractionProfile`は抽出条件の識別・監査用文字列であり、挙動は`extractionOptions`の値で決まる。未指定項目の既定値はすべて`true`である。

| option | 対象 | 型 | 説明 |
|---|---|---|---|
| `scanAllViews` | 2D | boolean | 全ビューを走査 |
| `scanAllLayers` | 2D | boolean | 全レイヤーを走査 |
| `classifyPrintFrame` | 2D | boolean | 印刷図枠内外を分類 |
| `recordOutsidePrintFrame` | 2D | boolean | 図枠外要素を記録 |
| `recordUnknownPrintArea` | 2D | boolean | 図枠内外不明の要素を記録 |
| `scanPartTree` | 3D | boolean | 部品ツリーを走査 |
| `scanPartMaterials` | 3D | boolean | 部品材質を取得 |
| `scanPartExtendedInfo` | 3D | boolean | 付加情報を取得 |
| `scanMassProperties` | 3D | boolean | 質量特性を取得 |

契約上、値はJSON booleanだけを使用する。未知のキーは将来拡張用としてC#出力の`condition_diagnostics.optionKeys`へ残るが、現行抽出動作には使用しない。

## 13. C#出力JSON共通部

JSON property名は`snake_case`である。

完全なDTO契約は`src/IcadExtraction.Contracts/Models.cs`、機械検証用契約は`schemas/tag_extraction/icad-csharp-raw-extraction.v1.schema.json`を正とする。Schema変更時は`python scripts\generate_tag_extraction_schemas.py --check`でC# DTOとの一致と2D/3D例の妥当性を確認する。

```json
{
  "input_path": "\\\\server\\cad\\sample.icd",
  "source_file": {
    "full_path": "\\\\server\\cad\\sample.icd",
    "directory_path": "\\\\server\\cad",
    "file_name": "sample.icd",
    "file_name_without_extension": "sample",
    "extension": "icd",
    "sx_net_input_path": "C:\\temporary-or-original\\sample.icd",
    "sx_net_input_strategy": "original",
    "used_sx_net_alternate_path": false,
    "original_path_length": 24,
    "sx_net_input_path_length": 31
  },
  "source_format": "icad",
  "source_kind": "2d",
  "extraction_profile": "default",
  "extraction_options": {},
  "condition_diagnostics": {},
  "extractor_name": "icad-csharp-extractor",
  "extractor_version": "1.0.0",
  "elapsed_ms": 0,
  "warnings": [],
  "raw_extract": {}
}
```

| 項目 | 型 | 説明 |
|---|---|---|
| `input_path` | string | 原本ICADパス。download時もcomplete前に登録原本パスへ戻す |
| `source_file` | object | 原本とSXNET実入力の追跡情報 |
| `source_format` | string | `icad` |
| `source_kind` | string | `2d` / `3d` |
| `extraction_profile` | string | claimで受けたprofile |
| `extraction_options` | object | claimで受けたoptions |
| `condition_diagnostics` | object | 実際に適用した抽出条件 |
| `extractor_name` | string | `icad-csharp-extractor` |
| `extractor_version` | string | 現行`1.0.0` |
| `elapsed_ms` | integer | 抽出処理時間、ミリ秒 |
| `warnings` | array | 非致命の警告。各要素は`code`、`message` |
| `raw_extract` | object | 2D / 3D生抽出結果 |

### 13.1 `source_file`

| 項目 | 型 |
|---|---|
| `full_path` | string |
| `directory_path` | string/null |
| `file_name` | string |
| `file_name_without_extension` | string |
| `extension` | string |
| `sx_net_input_path` | string |
| `sx_net_input_strategy` | `original` / `windows_short_path` / `temporary_copy` / `temporary_copy_forced` |
| `used_sx_net_alternate_path` | boolean |
| `original_path_length` | integer |
| `sx_net_input_path_length` | integer |

長いパス等でSXNETが原本を直接開けない場合、Windows短縮パスまたは一時コピーを使う。原本パスは`input_path`と`source_file.full_path`へ維持する。一時コピーは外部参照解決へ影響し得るため、`warnings`へ記録する。

## 14. `raw_extract` 3D契約

```json
{
  "model_info": {},
  "top_part": {},
  "parts": [],
  "viewer_assets": {},
  "condition_diagnostics": {},
  "mass_probe_status": "not_attempted",
  "mass_properties": null,
  "material_probe_status": "not_attempted",
  "materials": []
}
```

### 14.1 3D直下

| 項目 | 型 | 説明 |
|---|---|---|
| `model_info` | object | モデル基本情報 |
| `top_part` | object | 最上位部品 |
| `parts` | array | 階層を平坦化した部品一覧 |
| `viewer_assets` | object | modeをキーにしたpreview asset配列 |
| `condition_diagnostics` | object | 3Dで適用した条件 |
| `mass_probe_status` | string | `not_attempted` / `attempted` / `available` / `no_entities` / `failed` / `skipped_by_options`等 |
| `mass_properties` | object/null | 質量特性 |
| `material_probe_status` | string | `not_attempted` / `attempted` / `available` / `no_entities` / `no_materials` / `failed` / `skipped_by_options`等 |
| `materials` | array | モデル全体で取得した材質 |

### 14.2 `model_info`

`name`, `comment`, `path`, `is_read_only`, `view_sheet_count`, `work_plane_count`

### 14.3 `top_part`

`name`, `comment`, `ex_info`, `ex_info_fields`

`ex_info_fields`は付加情報のfield名をキー、取得値をvalueとするobjectである。

### 14.4 `parts[]`

| 項目 | 型 |
|---|---|
| `node_id`, `parent_node_id` | string/null |
| `depth`, `child_count` | integer |
| `entity_kind` | string |
| `tree_path` | string[] |
| `name`, `comment`, `ex_info` | string/null |
| `ex_info_fields` | object |
| `ref_model_name`, `ref_model_path` | string/null |
| `is_external`, `is_mirror`, `is_read_only`, `is_unloaded` | boolean |
| `materials` | material[] |

### 14.5 material

| 項目 | 型 |
|---|---|
| `matid`, `name` | string/null |
| `specific_gravity` | number/null |
| `element_count` | integer |
| `raw_fields` | object |

`parts[].materials`は当該部品ノードの根拠であり、親子を自動合算しない。

### 14.6 `mass_properties`

| 分類 | 項目 |
|---|---|
| 件数・単位 | `element_count`, `unit_name`, `unit_type`, `is_si` |
| 基本値 | `density`, `area`, `volume`, `mass`, `weight`, `length` |
| 重心 | `center_of_gravity_x`, `center_of_gravity_y`, `center_of_gravity_z` |
| 慣性 | `global_moment`, `gravity_moment`, `main_moment` |
| 生値 | `raw_fields` |

数値は取得できない場合`null`。momentと`raw_fields`はobjectで保持する。

## 15. `raw_extract` 2D契約

```json
{
  "model_info": {},
  "condition_diagnostics": {},
  "viewer_assets": {},
  "view_sheets": [],
  "print_frames": [],
  "layers": [],
  "texts": [],
  "dimensions": [],
  "geometry_primitives": [],
  "weld_notes": [],
  "balloons": [],
  "tolerances": [],
  "referenced_parts": []
}
```

### 15.1 2D直下

| 項目 | 型 | 説明 |
|---|---|---|
| `model_info` | object | 14.2と同じ |
| `condition_diagnostics` | object | 2Dで適用した条件 |
| `viewer_assets` | object | modeをキーにしたpreview asset配列 |
| `view_sheets` | array | ビュー・シート |
| `print_frames` | array | 印刷図枠 |
| `layers` | array | レイヤー |
| `texts` | array | 一般文字・ラベル |
| `dimensions` | array | 寸法 |
| `geometry_primitives` | array | 記号・線・円弧等の図形要素 |
| `weld_notes` | array | 溶接注記 |
| `balloons` | array | バルーン |
| `tolerances` | array | 公差 |
| `referenced_parts` | array | 2D参照部品 |

### 15.2 共通位置・監査項目

文字、寸法、図形、溶接注記、バルーン、公差、参照部品は、取得可能な範囲で次を持つ。

`view_name`, `layer_no`, `position_x`, `position_y`, `position_z`, `inside_print_area`, `print_frame_no`

値を取得できない項目は`null`にする。別要素間の汎用座標ペアリングはC#で行わず、座標は根拠・監査用に保持する。

### 15.3 `view_sheets[]`

`name`, `comment`, `scale`, `angle`, `type`, `view_type`, `geometry_count`

### 15.4 `print_frames[]`

`no`, `size`, `vertical`, `dinfo`, `drawing_scale`, `range_min_x`, `range_min_y`, `range_max_x`, `range_max_y`

### 15.5 `layers[]`

`no`, `name`, `is_displayed`, `is_searchable`

### 15.6 `texts[]`

共通位置項目に加えて、`text_lines`, `line_count`, `source_type`, `joined_text`を持つ。`source_type`は`text`または`label`。

### 15.7 `dimensions[]`

共通位置項目に加えて、`value_1`, `value_2`, `front_word`, `back_word`, `upper_tol`, `lower_tol`, `mark_2`, `mark_3`, `summary`を持つ。

### 15.8 `geometry_primitives[]`

| 分類 | 項目 |
|---|---|
| 識別 | `geometry_type`, `summary` |
| 始点・終点 | `position_x`, `position_y`, `position_z`, `end_x`, `end_y`, `end_z` |
| 中心 | `center_x`, `center_y`, `center_z` |
| 曲線 | `radius`, `radius_1`, `radius_2`, `start_angle`, `end_angle`, `point_count` |
| 記号 | `mark_type`, `side_length`, `width`, `color` |
| 根拠 | `view_name`, `layer_no`, `inside_print_area`, `print_frame_no` |

### 15.9 `weld_notes[]`

共通位置項目と`text`を持つ。

### 15.10 `balloons[]`

共通位置項目と`text`を持つ。

### 15.11 `tolerances[]`

共通位置項目と`text`を持つ。

### 15.12 `referenced_parts[]`

共通位置項目に加えて次を持つ。

`entity_type`, `name`, `comment`, `part3d_name`, `ref_model_name`, `ref_vs_name`, `kind`, `is_empty`, `is_mirror`, `scale`, `angle`, `summary`

## 16. viewer asset契約

`viewer_assets`はobjectで、`2d`または`3d`等のmodeをキーとし、次のasset object配列を持つ。

| 項目 | 型 |
|---|---|
| `mode`, `status`, `source` | string |
| `filename`, `extension`, `mime_type`, `model_format` | string/null |
| `file_path`, `url` | string/null |
| `size_bytes` | integer/null |
| `message` | string/null |

agentはupload前に`file_path`をWindows絶対パスからpreview directory基準の相対パスへ書き換える。`url`はclaim responseの`preview.baseUrl`を基準にする。

asset uploadが1件でも失敗した場合はcompleteせず、job全体をfailする。

## 17. C#が返さない情報

次はC#の責務ではなく、独立Pythonコアが生成し、Django統合時はcomplete後に保存する。

- `canonical_attributes`
- `derived_tags`
- `manual_overrides`
- 客先・案件・装置の辞書確定
- RAG用本文・チャンク・index
- viewer画面用の合成detail

C#の`result`へこれらを要求しない。創屋側で必要な形が異なる場合も、独立Python結果の後段アダプターで変換する。

## 18. lease・再実行

- claim時にDjangoが`DRAWING_METADATA_JOB_LEASE_SECONDS`後の期限を設定する
- `processing` heartbeatごとにleaseを延長する
- agent停止等でleaseが切れたjobだけを別agentが再claimできる
- lease切れjobの再claim時は`retry_count`を加算する
- complete済み・fail済みjobは再度complete / failできない
- job所有者が違う操作は`409`で拒否する

## 19. ICADプロセスと終了

- ICADが動いていない場合、`icad-executable-path`があればagentが起動する
- agentが自動起動したICADだけを終了対象とする
- 既に人または別処理が起動していたICADをagentが勝手に終了しない
- `shutdown-icad-if-autostarted=true`が既定
- 起動待機時間の既定は8秒

## 20. セキュリティ・運用

- tokenは十分に長いランダム値を使用する
- token比較はDjango側で定数時間比較する
- 本番・別端末間通信はHTTPSまたは信頼できる閉域網を使う
- Djangoの許可ホストへWindows agentから使うホスト名・IPを追加する
- Windows agent実行ユーザーには必要な図面共有だけを読み取り許可する
- assetの相対パス検証とサイズ上限を無効化しない
- `keep-work-files`は調査時だけ有効にし、通常運用では`false`にする
- tokenや社内フルパスをログ・外部資料へ無制限に転載しない

## 21. 互換性ルール

C#を変更せずに運用するには、Django側が次を維持する。

1. API pathとHTTP method
2. Bearer token認証
3. camelCaseのagent API field名
4. complete内のC#結果はsnake_case
5. `2d` / `3d` / `all`の値
6. `204 No Content`を空キューとして返すこと
7. `processing` jobと`workerName`による所有権
8. source直接参照またはdownloadの少なくとも一方
9. preview assetをcompleteより前に受け付けること

創屋側の内部モデル名が異なっても問題ない。外部契約だけをadapterで合わせる。契約を破壊的に変更する場合は、先に契約バージョンを更新し、C#側の対応要否を判断する。

## 22. 実機・自動テスト確認

2026-07-29時点で次を確認済み。

- Django system check成功
- Django test 174件成功
- C# test 40件成功
- `net48` / `net8.0` build成功
- Docker compose構成検証成功
- Docker backend healthy、generic worker running
- generic workerがICAD jobをclaimしない
- Windows agentの空キュー疎通成功
- Windows agentがICAD 3D jobをclaimしてSXNET抽出
- Djangoでjobが`succeeded`
- 抽出器`icad-csharp-extractor`、抽出時間4,027ms
- STL 130,547 bytesをuploadし、preview APIからHTTP 200
- agentが自動起動したICADの終了を確認

## 23. 創屋側受入チェックリスト

- [ ] agent APIの6 endpointを実装または移植
- [ ] request / response field名が本資料と一致
- [ ] Bearer token未設定時に安全側で停止
- [ ] Windows / UNC原本パスを登録できる
- [ ] Docker保存ファイルをdownloadできる
- [ ] SHA-256をclaim responseへ返す
- [ ] ICAD jobだけをWindows agentへ渡す
- [ ] STEP / DXFはDocker generic workerへ渡す
- [ ] heartbeatでleaseを延長
- [ ] 同一`workerName`のjobだけcomplete / fail / assetを許可
- [ ] asset path traversalとサイズ超過を拒否
- [ ] completeで正規化・タグ・snapshot保存を実行
- [ ] failでjobとagent heartbeatへエラーを保存
- [ ] API名、引数名、JSON casingを本資料と照合
- [ ] エラーを握り潰さず、C#コンソールとDjango jobの両方へ残す

## 24. 完了チェックリスト

- [x] C#へ入れる設定値を最新実装から反映
- [x] claim responseの全項目を反映
- [x] heartbeat、source、asset、complete、failのpayloadを反映
- [x] C#共通出力へ追加済みfieldを反映
- [x] 2D / 3D DTOを現行`Models.cs`と照合
- [x] 抽出オプションを現行`ExtractionConditionOptions.cs`と照合
- [x] HTTP statusと所有権条件を現行Django実装と照合
- [x] C#とDjangoの責務境界を明記
- [x] 創屋側がC#を変更しないための互換性条件を明記
