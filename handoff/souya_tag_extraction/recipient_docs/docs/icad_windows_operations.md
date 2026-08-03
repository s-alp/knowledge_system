# ICAD抽出・DXF／STEP変換・Windows agent

## 1. 必要な環境

- Windows
- PowerShell 7以上
- ICAD
- 使用するICADの版に対応した`sxnet.dll`
- .NET SDK
- .NET Framework 4.8

ICADとSXNETは、ICADファイルの抽出または変換を実行するWindows PCに必要です。PythonによるSTEP／DXF処理には不要です。

## 2. C# Runnerのビルド

パッケージのルートで実行します。

```powershell
dotnet publish `
  ".\csharp\src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" `
  -c Release `
  -f net48 `
  --no-self-contained
```

実行ファイルは次のフォルダーに作成されます。

```text
csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\
```

`IcadExtraction.Runner.exe`だけでなく、同じフォルダー内のDLLも一緒に配置してください。

各PowerShellスクリプトの全引数と例は、パッケージのルートで`Get-Help ".\scripts\対象スクリプト.ps1" -Full`を実行して確認できます。`-RunnerPath`を省略した場合は、上記publishフォルダーを自動的に使用します。

## 3. ICADからDXF／STEPへの変換

### 3.1 設定確認

最初は`-ValidateOnly`を付け、ICADを起動せずに入力、Runner、SXNET、出力先を確認します。

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "dxf" `
  -OutputDirectory "C:\CAD\converted" `
  -SxNetDllPath "C:\ICAD\sxnet.dll" `
  -ValidateOnly
```

### 3.2 DXF変換

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "dxf" `
  -OutputDirectory "C:\CAD\converted" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

### 3.3 STEP変換

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "step" `
  -OutputDirectory "C:\CAD\converted" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

既存の変換先ファイルは、既定では上書きしません。上書きする場合だけ`-Overwrite`を指定してください。

STEPの拡張子はSXNETの版により`.step`または`.stp`になります。後続処理では、変換結果JSONの`converted_asset.file_path`を使用してください。

## 4. ICADの直接抽出

### 4.1 設定確認

2D図面を例に、ICADを起動せずパスと設定だけを確認します。

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\extract_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -SourceKind "2d" `
  -OutputPath "C:\CAD\result\sample.raw.json" `
  -SxNetDllPath "C:\ICAD\sxnet.dll" `
  -ValidateOnly
```

### 4.2 2D図面の抽出

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\extract_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -SourceKind "2d" `
  -OutputPath "C:\CAD\result\sample.raw.json" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

### 4.3 3Dモデルの抽出

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\extract_icad_standalone.ps1" `
  -InputPath "C:\CAD\assembly.icd" `
  -SourceKind "3d" `
  -OutputPath "C:\CAD\result\assembly.raw.json" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

結果JSONは`schemas\icad-csharp-raw-extraction.v1.schema.json`の機械契約に従います。`source_kind`、`warnings`、`raw_extract`を確認した後、Python CLIへ入力してください。既存JSONは既定で上書きしないため、置き換える場合だけ`-Overwrite`を指定します。

ICADの起動、SXNETセッション、同時実行、長い入力パスの一時退避はRunnerが管理します。処理に失敗した場合は終了コード`0`以外で停止し、詳細を標準エラーへ出力します。

## 5. Windows agent

Windows agentは、HTTP APIから抽出ジョブを取得し、ICADで処理して結果を返す常駐プロセスです。

### 5.1 必須設定

```powershell
$env:DRAWING_METADATA_AGENT_API_BASE_URL = "https://example.invalid"
$env:DRAWING_METADATA_AGENT_TOKEN = "<十分に長いランダムな値>"
$env:DRAWING_METADATA_AGENT_WORKER_NAME = "icad-worker-01"
$env:DRAWING_METADATA_SXNET_DLL_PATH = "C:\ICAD\sxnet.dll"
```

実際のURL、token、PC名、社内パスはソースコードや共有文書へ記録せず、実行環境の安全な設定領域で管理してください。

### 5.2 1回だけ接続して確認

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\start_windows_extraction_agent.ps1" `
  -ValidateOnly

pwsh -NoLogo -NoProfile -File ".\scripts\start_windows_extraction_agent.ps1" `
  -Once
```

### 5.3 常駐起動

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\start_windows_extraction_agent.ps1"
```

起動時に、必須設定、URL、数値、`sxnet.dll`、Runner、指定されたICAD実行ファイルを検証します。不正な設定では起動しません。

## 6. Windows agentのHTTP契約

agentはBearer tokenを付けて、次のAPIを使用します。

| 処理 | メソッドとパス |
|---|---|
| ジョブ取得 | `POST /api/v1/drawing-metadata/agent/jobs/claim` |
| heartbeat | `POST /api/v1/drawing-metadata/agent/heartbeat` |
| 入力取得 | `GET /api/v1/drawing-metadata/agent/jobs/{jobId}/source` |
| プレビュー送信 | `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/assets` |
| 完了通知 | `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/complete` |
| 失敗通知 | `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/fail` |

接続先が別のDB、ジョブ管理、認証方式を使用する場合は、このHTTP契約へ変換するAPIアダプターを実装してください。

### 6.1 job取得の入出力例

agentは次のJSONを`POST /api/v1/drawing-metadata/agent/jobs/claim`へ送ります。

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "mode": "all",
  "runnerVersion": "1.0.0",
  "processId": 1234
}
```

処理対象がある場合、APIは`200 OK`で次の構造を返します。対象がない場合は`204 No Content`でbodyを返しません。

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
    "downloadUrl": "https://example.invalid/source?workerName=WINDOWS-AGENT-01",
    "downloadAvailable": false
  },
  "preview": {
    "baseUrl": "https://example.invalid/preview-assets/11111111-1111-1111-1111-111111111111"
  }
}
```

`extractionMode`は`2d`または`3d`、`source.format`は`icad`です。`source.sha256`に値がある場合、agentは抽出前に入力ファイルと照合します。

### 6.2 heartbeatの入力例

処理中は次のJSONを`POST /api/v1/drawing-metadata/agent/heartbeat`へ送り、ジョブのleaseを延長します。

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

### 6.3 完了・失敗の入力例

成功時はSchemaを満たすC# raw JSONを`result`へ入れ、`POST /api/v1/drawing-metadata/agent/jobs/{jobId}/complete`へ送ります。

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

`result`の全必須項目と型は`schemas/icad-csharp-raw-extraction.v1.schema.json`を正として実装してください。

失敗時は空の成功結果を送らず、`POST /api/v1/drawing-metadata/agent/jobs/{jobId}/fail`へ原因を送ります。

```json
{
  "workerName": "WINDOWS-AGENT-01",
  "errorMessage": "例外型、message、inner exception、stack traceを含むエラー全文"
}
```

## 7. 導入時の動作確認

1. C# Runnerをnet48 Releaseでpublishできる。
2. 使用するICAD版に対応した`sxnet.dll`を指定している。
3. `-ValidateOnly`が成功する。
4. 架空または共有許可済みのICADでDXFとSTEPを生成できる。
5. 生成結果JSONの`completed`が`true`である。
6. `converted_asset.status`が`ready`で、出力ファイルが存在する。
7. agent利用時はclaim、heartbeat、completeまたはfailを確認できる。
8. エラー時にC#コンソールと接続先ジョブの両方で原因を確認できる。

## 8. 注意事項

- DXF／STEPは交換形式であり、ICADの材質、質量、付加情報、内部／外部パーツ区分を常に保持するとは限りません。
- 材質、質量、正式な部品名が必要な場合は、ICADからSXNETで直接抽出してください。
- ICAD操作は同時実行せず、1図面ずつ処理してください。
- tokenをコマンド履歴やログへ表示しないでください。
- 実図面を動作確認に使う場合は、ファイルの共有・保管ルールを確認してください。
