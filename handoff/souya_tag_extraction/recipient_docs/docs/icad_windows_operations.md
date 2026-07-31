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

## 3. ICADからDXF／STEPへの変換

### 3.1 設定確認

最初は`-ValidateOnly`を付け、ICADを起動せずに入力、Runner、SXNET、出力先を確認します。

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "dxf" `
  -OutputDirectory "C:\CAD\converted" `
  -RunnerPath ".\csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe" `
  -SxNetDllPath "C:\ICAD\sxnet.dll" `
  -ValidateOnly
```

### 3.2 DXF変換

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "dxf" `
  -OutputDirectory "C:\CAD\converted" `
  -RunnerPath ".\csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

### 3.3 STEP変換

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\CAD\sample.icd" `
  -OutputFormat "step" `
  -OutputDirectory "C:\CAD\converted" `
  -RunnerPath ".\csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe" `
  -SxNetDllPath "C:\ICAD\sxnet.dll"
```

既存の変換先ファイルは、既定では上書きしません。上書きする場合だけ`-Overwrite`を指定してください。

STEPの拡張子はSXNETの版により`.step`または`.stp`になります。後続処理では、変換結果JSONの`converted_asset.file_path`を使用してください。

## 4. ICADの直接抽出

C# Runnerは`extract`コマンドでICAD 2D／3Dを抽出します。引数と出力JSONの機械契約は、`schemas\icad-csharp-raw-extraction.v1.schema.json`を参照してください。

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
  -RunnerPath ".\csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe" `
  -Once
```

### 5.3 常駐起動

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\start_windows_extraction_agent.ps1" `
  -RunnerPath ".\csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe"
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
