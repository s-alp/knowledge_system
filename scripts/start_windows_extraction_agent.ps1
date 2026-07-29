# このファイルは、`start_windows_extraction_agent`として必要な環境変数を確認して常駐プロセスを起動する補助スクリプトである。
# 初めて読むときは、公開されている入口から呼び出し先を順に追う。
# 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
[CmdletBinding()]
param(
    [string]$ApiBaseUrl = $env:DRAWING_METADATA_AGENT_API_BASE_URL,
    [string]$ApiToken = $env:DRAWING_METADATA_AGENT_TOKEN,
    [string]$WorkerName = $env:DRAWING_METADATA_AGENT_WORKER_NAME,
    [ValidateSet("2d", "3d", "all")]
    [string]$Mode = "all",
    [string]$RunnerPath = "",
    [string]$SxNetDllPath = $env:DRAWING_METADATA_SXNET_DLL_PATH,
    [string]$IcadExecutablePath = $env:DRAWING_METADATA_ICAD_EXECUTABLE,
    [int]$PollSeconds = 5,
    [int]$HeartbeatSeconds = 10,
    [string]$WorkRoot = $env:DRAWING_METADATA_AGENT_WORK_ROOT,
    [bool]$ShutdownIcadIfAutostarted = $true,
    [switch]$Once,
    [switch]$KeepWorkFiles
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
    $RunnerPath = Join-Path $repositoryRoot "src\IcadExtraction.Runner\bin\Release\net48\IcadExtraction.Runner.exe"
}
if ([string]::IsNullOrWhiteSpace($SxNetDllPath)) {
    $SxNetDllPath = Join-Path $repositoryRoot "sxnet.dll"
}
if ([string]::IsNullOrWhiteSpace($WorkerName)) {
    $WorkerName = $env:COMPUTERNAME
}
if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
    $WorkRoot = Join-Path ([System.IO.Path]::GetTempPath()) "IcadExtractionAgent"
}

if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    throw "ApiBaseUrlまたはDRAWING_METADATA_AGENT_API_BASE_URLを設定してください。"
}
if ([string]::IsNullOrWhiteSpace($ApiToken)) {
    throw "ApiTokenまたはDRAWING_METADATA_AGENT_TOKENを設定してください。"
}
if (-not (Test-Path -LiteralPath $RunnerPath -PathType Leaf)) {
    throw "Runnerが見つかりません。先にnet48 Releaseをpublishしてください: $RunnerPath"
}
if (-not (Test-Path -LiteralPath $SxNetDllPath -PathType Leaf)) {
    throw "sxnet.dllが見つかりません: $SxNetDllPath"
}
if (-not [string]::IsNullOrWhiteSpace($IcadExecutablePath) -and
    -not (Test-Path -LiteralPath $IcadExecutablePath -PathType Leaf)) {
    throw "icad.exeが見つかりません: $IcadExecutablePath"
}

$agentArguments = @(
    "agent",
    "--api-base-url", $ApiBaseUrl,
    "--api-token", $ApiToken,
    "--worker-name", $WorkerName,
    "--mode", $Mode,
    "--sxnet-dll-path", $SxNetDllPath,
    "--poll-seconds", $PollSeconds.ToString(),
    "--heartbeat-seconds", $HeartbeatSeconds.ToString(),
    "--work-root", $WorkRoot,
    "--shutdown-icad-if-autostarted", $ShutdownIcadIfAutostarted.ToString(),
    "--once", $Once.IsPresent.ToString(),
    "--keep-work-files", $KeepWorkFiles.IsPresent.ToString()
)
if (-not [string]::IsNullOrWhiteSpace($IcadExecutablePath)) {
    $agentArguments += @("--icad-executable-path", $IcadExecutablePath)
}

& $RunnerPath @agentArguments
if ($LASTEXITCODE -ne 0) {
    throw "Windows抽出agentが終了コード $LASTEXITCODE で停止しました。"
}
