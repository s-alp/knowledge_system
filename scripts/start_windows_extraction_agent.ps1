<#
.SYNOPSIS
ICAD抽出ジョブを処理するWindows agentを起動します。

.DESCRIPTION
接続先、token、Runner、SXNETの設定を検証し、C# Runnerのagentコマンドへ渡します。
RunnerPathを省略すると、配布パッケージまたはソース一式のpublish先を探します。
設定不足やファイル不在では起動せず、原因をエラーとして返します。

.PARAMETER ApiBaseUrl
ジョブAPIのベースURLです。環境変数DRAWING_METADATA_AGENT_API_BASE_URLでも指定できます。

.PARAMETER ApiToken
Bearer tokenです。環境変数DRAWING_METADATA_AGENT_TOKENでも指定できます。

.PARAMETER Once
ジョブ取得を1回だけ試して終了します。初回疎通確認に使用します。

.PARAMETER ValidateOnly
agentを起動せず、必須設定とパスの確認結果だけを表示します。

.EXAMPLE
pwsh -File .\scripts\start_windows_extraction_agent.ps1 -Once

.EXAMPLE
pwsh -File .\scripts\start_windows_extraction_agent.ps1 -ValidateOnly
#>
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
    [switch]$KeepWorkFiles,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "このスクリプトはPowerShell 7以降で実行してください。"
}

$packageRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
    $runnerCandidates = @(
        (Join-Path $packageRoot "csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe"),
        (Join-Path $packageRoot "src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe")
    )
    $RunnerPath = $runnerCandidates |
        Where-Object { Test-Path -LiteralPath $PSItem -PathType Leaf } |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
        $RunnerPath = $runnerCandidates[0]
    }
}
if ([string]::IsNullOrWhiteSpace($SxNetDllPath)) {
    $SxNetDllPath = Join-Path $packageRoot "sxnet.dll"
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

if ($ValidateOnly) {
    Write-Output ([pscustomobject]@{
        ApiBaseUrl = $ApiBaseUrl
        WorkerName = $WorkerName
        Mode = $Mode
        RunnerPath = [System.IO.Path]::GetFullPath($RunnerPath)
        SxNetDllPath = [System.IO.Path]::GetFullPath($SxNetDllPath)
        IcadExecutablePath = $IcadExecutablePath
        WorkRoot = [System.IO.Path]::GetFullPath($WorkRoot)
        TokenConfigured = $true
        ValidationOnly = $true
    })
    return
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
