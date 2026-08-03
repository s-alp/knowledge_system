<#
.SYNOPSIS
ICADファイルをDXFまたはSTEPへ1件変換します。

.DESCRIPTION
Djangoやデータベースを使わず、C# Runnerの引数を検証して変換します。
既存成果物は保護し、-Overwriteを指定した場合だけ置き換えます。
RunnerPathを省略すると、配布パッケージまたはソース一式のpublish先を探します。

.PARAMETER InputPath
変換する.icdファイルです。

.PARAMETER OutputFormat
dxf、step、stpのいずれかです。

.PARAMETER OutputDirectory
変換ファイルと既定の結果JSONを保存するフォルダーです。

.PARAMETER SxNetDllPath
使用するICAD版に対応したsxnet.dllです。環境変数でも指定できます。

.PARAMETER ValidateOnly
ICADを起動せず、入力・Runner・SXNET・出力先の解決結果だけを表示します。

.EXAMPLE
pwsh -File .\scripts\convert_icad_standalone.ps1 -InputPath C:\CAD\sample.icd -OutputFormat dxf -OutputDirectory C:\CAD\converted -SxNetDllPath C:\ICAD\sxnet.dll -ValidateOnly
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet("dxf", "step", "stp")]
    [string]$OutputFormat,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputDirectory,

    [string]$OutputBaseName,

    [string]$ResultJsonPath,

    [string]$RunnerPath = $env:ICAD_CONVERTER_RUNNER_PATH,

    [string]$SxNetDllPath = $env:ICAD_CONVERTER_SXNET_DLL_PATH,

    [string]$IcadExecutablePath = $env:ICAD_CONVERTER_ICAD_EXECUTABLE_PATH,

    [ValidateRange(1, 3600)]
    [int]$IcadStartupWaitSeconds = 30,

    [ValidateRange(1, 300)]
    [int]$IcadShutdownTimeoutSeconds = 30,

    [ValidateRange(30, 86400)]
    [int]$RunnerTimeoutSeconds = 600,

    [ValidateRange(1, 120)]
    [int]$CompletionGraceSeconds = 5,

    [Nullable[int]]$ExportFileType,

    [switch]$KeepAutostartedIcadOpen,

    [switch]$ForceSxNetStagedInput,

    [switch]$Overwrite,

    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "このスクリプトは、引数を安全に子プロセスへ渡すためPowerShell 7以降で実行してください。"
}

function Resolve-RequiredFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$DisplayName
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "$DisplayName が指定されていません。引数または対応する環境変数を設定してください。"
    }

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "$DisplayName が見つかりません: $fullPath"
    }

    return $fullPath
}

function Resolve-OptionalFilePath {
    param(
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$DisplayName
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    return Resolve-RequiredFilePath -Path $Path -DisplayName $DisplayName
}

function Resolve-DefaultRunnerPath {
    # scriptsの親が配布ルートならcsharp配下、開発用ルートならsrc配下にある。
    # publish成果物だけを候補にし、Debugビルドを誤って配布運用へ使わない。
    $packageRoot = Split-Path -Parent $PSScriptRoot
    $candidates = @(
        (Join-Path $packageRoot "csharp\src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe"),
        (Join-Path $packageRoot "src\IcadExtraction.Runner\bin\Release\net48\publish\IcadExtraction.Runner.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return $candidates[0]
}

function Get-CompletedConversionResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [DateTime]$StartedAtUtc
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    $resultFile = Get-Item -LiteralPath $Path
    if ($resultFile.LastWriteTimeUtc -lt $StartedAtUtc.AddSeconds(-1)) {
        # -Overwrite時に残っていた古い成功JSONを、今回の完了結果として誤認しない。
        return $null
    }

    try {
        $candidate = Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
    }
    catch {
        # Runnerが中間JSONを書き換えている瞬間は一時的に読めないため、次の監視周期で再確認する。
        return $null
    }
    $completedProperty = $candidate.PSObject.Properties["completed"]
    $assetProperty = $candidate.PSObject.Properties["converted_asset"]
    if (
        $null -eq $completedProperty -or
        $completedProperty.Value -ne $true -or
        $null -eq $assetProperty -or
        $null -eq $assetProperty.Value -or
        $assetProperty.Value.status -ne "ready"
    ) {
        return $null
    }

    $candidateAssetPath = [System.IO.Path]::GetFullPath([string]$assetProperty.Value.file_path)
    if (-not (Test-Path -LiteralPath $candidateAssetPath -PathType Leaf)) {
        return $null
    }
    if ((Get-Item -LiteralPath $candidateAssetPath).Length -le 0) {
        return $null
    }

    return $candidate
}

function Invoke-AutostartedIcadShutdown {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExecutablePath,

        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds
    )

    # 変換Runnerを成果物完成後に終了した場合、そのRunnerのusing後処理は走らない。
    # 別Runnerの安全終了コマンドを使い、保存確認を拒否した上で自動起動分のICADだけを閉じる。
    $shutdownStartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $shutdownStartInfo.FileName = $ExecutablePath
    $shutdownStartInfo.UseShellExecute = $false
    $shutdownStartInfo.CreateNoWindow = $true
    [void]$shutdownStartInfo.ArgumentList.Add("shutdown-icad")
    [void]$shutdownStartInfo.ArgumentList.Add("--timeout-seconds")
    [void]$shutdownStartInfo.ArgumentList.Add($TimeoutSeconds.ToString())

    $shutdownProcess = [System.Diagnostics.Process]::new()
    $shutdownProcess.StartInfo = $shutdownStartInfo
    if (-not $shutdownProcess.Start()) {
        throw "自動起動したICADの保存なし終了コマンドを起動できませんでした。"
    }
    if (-not $shutdownProcess.WaitForExit(($TimeoutSeconds + 10) * 1000)) {
        $shutdownProcess.Kill()
        [void]$shutdownProcess.WaitForExit(10000)
        $shutdownProcess.Dispose()
        throw "変換は完了しましたが、自動起動したICADを${TimeoutSeconds}秒以内に終了できませんでした。"
    }

    $shutdownExitCode = $shutdownProcess.ExitCode
    $shutdownProcess.Dispose()
    if ($shutdownExitCode -ne 0) {
        throw "変換は完了しましたが、ICADの保存なし終了が失敗しました: exit=$shutdownExitCode"
    }
}

# STEPとSTPは同じ変換形式として扱う。出力拡張子はSXNETの実装差により .step または .stp になる。
$normalizedOutputFormat = $OutputFormat.ToLowerInvariant()
if ($normalizedOutputFormat -eq "stp") {
    $normalizedOutputFormat = "step"
}

$resolvedInputPath = Resolve-RequiredFilePath -Path $InputPath -DisplayName "入力ICADファイル"
if ([System.IO.Path]::GetExtension($resolvedInputPath).ToLowerInvariant() -ne ".icd") {
    throw "入力は拡張子 .icd のICADファイルを指定してください: $resolvedInputPath"
}

if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
    $RunnerPath = Resolve-DefaultRunnerPath
}
$resolvedRunnerPath = Resolve-RequiredFilePath -Path $RunnerPath -DisplayName "ICAD変換Runner"

if ([string]::IsNullOrWhiteSpace($SxNetDllPath)) {
    # 既存Windows agentと設定を共有する場合に限り、同じ環境変数も受け付ける。
    $SxNetDllPath = $env:DRAWING_METADATA_SXNET_DLL_PATH
}
$resolvedSxNetDllPath = Resolve-RequiredFilePath -Path $SxNetDllPath -DisplayName "sxnet.dll"
$resolvedIcadExecutablePath = Resolve-OptionalFilePath -Path $IcadExecutablePath -DisplayName "ICAD実行ファイル"

$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
if ([string]::IsNullOrWhiteSpace($OutputBaseName)) {
    $OutputBaseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInputPath)
}
if ([System.IO.Path]::GetFileName($OutputBaseName) -ne $OutputBaseName) {
    throw "OutputBaseName にはフォルダを含めず、ファイル名部分だけを指定してください: $OutputBaseName"
}

if ([string]::IsNullOrWhiteSpace($ResultJsonPath)) {
    $ResultJsonPath = Join-Path $resolvedOutputDirectory "$OutputBaseName.$normalizedOutputFormat.conversion.json"
}
$resolvedResultJsonPath = [System.IO.Path]::GetFullPath($ResultJsonPath)

# C#側は変換先を置き換えられるため、利用者が意図せず成果物を消さないよう実行前に衝突を止める。
$candidateOutputPaths = if ($normalizedOutputFormat -eq "step") {
    @(
        (Join-Path $resolvedOutputDirectory "$OutputBaseName.step"),
        (Join-Path $resolvedOutputDirectory "$OutputBaseName.stp")
    )
}
else {
    @((Join-Path $resolvedOutputDirectory "$OutputBaseName.dxf"))
}
$protectedPaths = @($candidateOutputPaths) + @($resolvedResultJsonPath)
$existingPaths = @($protectedPaths | Where-Object { Test-Path -LiteralPath $PSItem })
if ($existingPaths.Count -gt 0 -and -not $Overwrite) {
    throw "既存ファイルを保護するため変換を中断しました。上書きする場合だけ -Overwrite を指定してください: $($existingPaths -join ', ')"
}

$runnerArguments = @(
    "convert-cad",
    "--input-path", $resolvedInputPath,
    "--output-path", $resolvedResultJsonPath,
    "--output-dir", $resolvedOutputDirectory,
    "--output-format", $normalizedOutputFormat,
    "--output-base-name", $OutputBaseName,
    "--sxnet-dll-path", $resolvedSxNetDllPath,
    "--icad-startup-wait-seconds", $IcadStartupWaitSeconds.ToString(),
    "--shutdown-icad-if-autostarted", $(if ($KeepAutostartedIcadOpen) { "false" } else { "true" }),
    "--force-sxnet-staged-input", $(if ($ForceSxNetStagedInput) { "true" } else { "false" })
)
if ($null -ne $resolvedIcadExecutablePath) {
    $runnerArguments += @("--icad-executable-path", $resolvedIcadExecutablePath)
}
if ($null -ne $ExportFileType) {
    # PowerShellはNullable[int]へ値が入ると通常のInt32として公開するため、Valueプロパティを経由しない。
    $runnerArguments += @("--export-file-type", $ExportFileType.ToString())
}

$validationResult = [pscustomobject]@{
    InputPath = $resolvedInputPath
    OutputFormat = $normalizedOutputFormat
    OutputDirectory = $resolvedOutputDirectory
    OutputBaseName = $OutputBaseName
    ResultJsonPath = $resolvedResultJsonPath
    RunnerPath = $resolvedRunnerPath
    SxNetDllPath = $resolvedSxNetDllPath
    IcadExecutablePath = $resolvedIcadExecutablePath
    IcadStartupWaitSeconds = $IcadStartupWaitSeconds
    IcadShutdownTimeoutSeconds = $IcadShutdownTimeoutSeconds
    RunnerTimeoutSeconds = $RunnerTimeoutSeconds
    CompletionGraceSeconds = $CompletionGraceSeconds
    ValidationOnly = [bool]$ValidateOnly
}
if ($ValidateOnly) {
    # 実ファイルを生成せず、配布先PCの設定とパス解決だけを事前確認できる。
    Write-Output $validationResult
    return
}

if (-not $PSCmdlet.ShouldProcess(
    "$resolvedInputPath -> $resolvedOutputDirectory",
    "ICADを${normalizedOutputFormat}形式へ変換"
)) {
    return
}

[System.IO.Directory]::CreateDirectory($resolvedOutputDirectory) | Out-Null
$resultParentDirectory = [System.IO.Path]::GetDirectoryName($resolvedResultJsonPath)
if (-not [string]::IsNullOrWhiteSpace($resultParentDirectory)) {
    [System.IO.Directory]::CreateDirectory($resultParentDirectory) | Out-Null
}

# SXNETは成果物を書き終えた後、モデルclose/deleteで長時間待つ版がある。
# 結果JSONと実ファイルが完成してから猶予時間を置き、Runnerだけが残る場合はその子プロセスを終了する。
# ICAD本体は別プロセスなので、この終了処理で強制終了しない。
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $resolvedRunnerPath
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
foreach ($argument in $runnerArguments) {
    [void]$startInfo.ArgumentList.Add([string]$argument)
}
$runnerProcess = [System.Diagnostics.Process]::new()
$runnerProcess.StartInfo = $startInfo
$startedAtUtc = [DateTime]::UtcNow
if (-not $runnerProcess.Start()) {
    throw "ICAD変換Runnerを起動できませんでした: $resolvedRunnerPath"
}

$completedResult = $null
$completedResultDetectedAtUtc = $null
$runnerTerminatedAfterCompletedResult = $false
$runnerTimedOut = $false
while (-not $runnerProcess.WaitForExit(500)) {
    $completedResult = Get-CompletedConversionResult -Path $resolvedResultJsonPath -StartedAtUtc $startedAtUtc
    if ($null -ne $completedResult) {
        if ($null -eq $completedResultDetectedAtUtc) {
            $completedResultDetectedAtUtc = [DateTime]::UtcNow
        }
        elseif (([DateTime]::UtcNow - $completedResultDetectedAtUtc).TotalSeconds -ge $CompletionGraceSeconds) {
            $runnerProcess.Kill()
            $runnerTerminatedAfterCompletedResult = $true
            [void]$runnerProcess.WaitForExit(10000)
            break
        }
    }

    if (
        $null -eq $completedResult -and
        ([DateTime]::UtcNow - $startedAtUtc).TotalSeconds -ge $RunnerTimeoutSeconds
    ) {
        $runnerProcess.Kill()
        $runnerTimedOut = $true
        [void]$runnerProcess.WaitForExit(10000)
        break
    }
}

$runnerExitCode = if ($runnerProcess.HasExited) { $runnerProcess.ExitCode } else { $null }
$runnerProcess.Dispose()
if ($runnerTimedOut) {
    throw "ICAD変換が${RunnerTimeoutSeconds}秒以内に完了しなかったため、Runnerを終了しました: $resolvedResultJsonPath"
}

try {
    $result = Get-Content -LiteralPath $resolvedResultJsonPath -Raw -Encoding utf8 | ConvertFrom-Json
}
catch {
    throw "結果JSONを読み取れません: $resolvedResultJsonPath`n$($PSItem.Exception.Message)"
}

if ($result.completed -ne $true -or $result.converted_asset.status -ne "ready") {
    throw "Runner終了コード $runnerExitCode の処理結果が変換完了を示していません: $resolvedResultJsonPath"
}
if (-not $runnerTerminatedAfterCompletedResult -and $runnerExitCode -ne 0) {
    throw "変換結果は生成されましたが、Runnerが終了コード $runnerExitCode を返しました。標準エラーを確認してください: $resolvedResultJsonPath"
}
$convertedPath = [System.IO.Path]::GetFullPath([string]$result.converted_asset.file_path)
if (-not (Test-Path -LiteralPath $convertedPath -PathType Leaf)) {
    throw "結果JSONに記録された変換ファイルが見つかりません: $convertedPath"
}
$convertedFile = Get-Item -LiteralPath $convertedPath
if ($convertedFile.Length -le 0) {
    throw "変換ファイルのサイズが0バイトです: $convertedPath"
}

$icadShutdownAfterRunnerTermination = $false
if (
    $runnerTerminatedAfterCompletedResult -and
    [bool]$result.icad_autostarted -and
    -not $KeepAutostartedIcadOpen
) {
    Invoke-AutostartedIcadShutdown `
        -ExecutablePath $resolvedRunnerPath `
        -TimeoutSeconds $IcadShutdownTimeoutSeconds
    $icadShutdownAfterRunnerTermination = $true
}

# 後続バッチが文字列解析に依存しないよう、成功時は主要情報をプロパティとして返す。
Write-Output ([pscustomobject]@{
    InputPath = $resolvedInputPath
    OutputFormat = [string]$result.output_format
    ConvertedPath = $convertedPath
    SizeBytes = $convertedFile.Length
    ResultJsonPath = $resolvedResultJsonPath
    WarningCount = @($result.warnings).Count
    IcadAutostarted = [bool]$result.icad_autostarted
    RunnerExitCode = $runnerExitCode
    RunnerTerminatedAfterCompletedResult = $runnerTerminatedAfterCompletedResult
    IcadShutdownAfterRunnerTermination = $icadShutdownAfterRunnerTermination
    Completed = $true
})
