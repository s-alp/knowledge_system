<#
.SYNOPSIS
ICAD 2D／3DファイルからC# raw JSONを1件抽出します。

.DESCRIPTION
C# Runnerのextractコマンドを、入力と出力を検証して実行します。
RunnerPathを省略すると、配布パッケージまたはソース一式のpublish先を探します。
既存の結果JSONは保護し、-Overwriteを指定した場合だけ置き換えます。

.PARAMETER InputPath
抽出する.icdファイルです。

.PARAMETER SourceKind
2D図面は2d、3Dモデルは3dを指定します。

.PARAMETER OutputPath
icad-csharp-raw-extraction Schemaに従う結果JSONの保存先です。

.PARAMETER SxNetDllPath
使用するICAD版に対応したsxnet.dllです。環境変数でも指定できます。

.PARAMETER ValidateOnly
ICADを起動せず、入力・Runner・SXNET・出力先の解決結果だけを表示します。

.EXAMPLE
pwsh -File .\scripts\extract_icad_standalone.ps1 -InputPath C:\CAD\sample.icd -SourceKind 2d -OutputPath C:\CAD\result.json -SxNetDllPath C:\ICAD\sxnet.dll -ValidateOnly

.EXAMPLE
pwsh -File .\scripts\extract_icad_standalone.ps1 -InputPath C:\CAD\assembly.icd -SourceKind 3d -OutputPath C:\CAD\assembly.raw.json -SxNetDllPath C:\ICAD\sxnet.dll
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet("2d", "3d")]
    [string]$SourceKind,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [string]$RunnerPath = $env:ICAD_EXTRACTION_RUNNER_PATH,

    [string]$SxNetDllPath = $env:DRAWING_METADATA_SXNET_DLL_PATH,

    [string]$IcadExecutablePath = $env:DRAWING_METADATA_ICAD_EXECUTABLE,

    [ValidateRange(1, 3600)]
    [int]$IcadStartupWaitSeconds = 30,

    [ValidateNotNullOrEmpty()]
    [string]$ExtractionProfile = "default",

    [string]$ExtractionOptionsJson,

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
    throw "このスクリプトはPowerShell 7以降で実行してください。"
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

function Resolve-DefaultRunnerPath {
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

$resolvedInputPath = Resolve-RequiredFilePath -Path $InputPath -DisplayName "入力ICADファイル"
if ([System.IO.Path]::GetExtension($resolvedInputPath).ToLowerInvariant() -ne ".icd") {
    throw "入力は拡張子.icdのICADファイルを指定してください: $resolvedInputPath"
}

if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
    $RunnerPath = Resolve-DefaultRunnerPath
}
$resolvedRunnerPath = Resolve-RequiredFilePath -Path $RunnerPath -DisplayName "ICAD抽出Runner"
$resolvedSxNetDllPath = Resolve-RequiredFilePath -Path $SxNetDllPath -DisplayName "sxnet.dll"
$resolvedIcadExecutablePath = $null
if (-not [string]::IsNullOrWhiteSpace($IcadExecutablePath)) {
    $resolvedIcadExecutablePath = Resolve-RequiredFilePath -Path $IcadExecutablePath -DisplayName "ICAD実行ファイル"
}

$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
if ($resolvedOutputPath -eq $resolvedInputPath) {
    throw "入力ICADと結果JSONには異なるパスを指定してください。"
}
if ((Test-Path -LiteralPath $resolvedOutputPath) -and -not $Overwrite) {
    throw "既存の結果JSONを保護するため中断しました。置き換える場合だけ-Overwriteを指定してください: $resolvedOutputPath"
}

if (-not [string]::IsNullOrWhiteSpace($ExtractionOptionsJson)) {
    try {
        $parsedOptions = $ExtractionOptionsJson | ConvertFrom-Json -AsHashtable
    }
    catch {
        throw "ExtractionOptionsJsonはJSON objectで指定してください: $($PSItem.Exception.Message)"
    }
    if ($parsedOptions -isnot [hashtable]) {
        throw "ExtractionOptionsJsonはJSON objectで指定してください。"
    }
}

$validationResult = [pscustomobject]@{
    InputPath = $resolvedInputPath
    SourceKind = $SourceKind
    OutputPath = $resolvedOutputPath
    RunnerPath = $resolvedRunnerPath
    SxNetDllPath = $resolvedSxNetDllPath
    IcadExecutablePath = $resolvedIcadExecutablePath
    ExtractionProfile = $ExtractionProfile
    ValidationOnly = [bool]$ValidateOnly
}
if ($ValidateOnly) {
    Write-Output $validationResult
    return
}

if (-not $PSCmdlet.ShouldProcess(
    "$resolvedInputPath -> $resolvedOutputPath",
    "ICAD $SourceKind 属性を抽出"
)) {
    return
}

$outputDirectory = [System.IO.Path]::GetDirectoryName($resolvedOutputPath)
if (-not [string]::IsNullOrWhiteSpace($outputDirectory)) {
    [System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
}

$runnerArguments = @(
    "extract",
    "--input-path", $resolvedInputPath,
    "--source-kind", $SourceKind,
    "--output-path", $resolvedOutputPath,
    "--sxnet-dll-path", $resolvedSxNetDllPath,
    "--icad-startup-wait-seconds", $IcadStartupWaitSeconds.ToString(),
    "--shutdown-icad-if-autostarted", $(if ($KeepAutostartedIcadOpen) { "false" } else { "true" }),
    "--extraction-profile", $ExtractionProfile,
    "--force-sxnet-staged-input", $(if ($ForceSxNetStagedInput) { "true" } else { "false" })
)
if ($null -ne $resolvedIcadExecutablePath) {
    $runnerArguments += @("--icad-executable-path", $resolvedIcadExecutablePath)
}
if (-not [string]::IsNullOrWhiteSpace($ExtractionOptionsJson)) {
    $runnerArguments += @("--extraction-options-json", $ExtractionOptionsJson)
}

& $resolvedRunnerPath @runnerArguments
if ($LASTEXITCODE -ne 0) {
    throw "ICAD抽出Runnerが終了コード $LASTEXITCODE で停止しました。標準エラーを確認してください。"
}
if (-not (Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf)) {
    throw "Runnerは正常終了しましたが、結果JSONが見つかりません: $resolvedOutputPath"
}
if ((Get-Item -LiteralPath $resolvedOutputPath).Length -le 0) {
    throw "結果JSONのサイズが0バイトです: $resolvedOutputPath"
}
try {
    $result = Get-Content -LiteralPath $resolvedOutputPath -Raw -Encoding utf8 | ConvertFrom-Json
}
catch {
    throw "結果JSONを読み取れません: $resolvedOutputPath $($PSItem.Exception.Message)"
}
if ([string]$result.source_kind -ne $SourceKind) {
    throw "結果JSONのsource_kindが要求値と一致しません: expected=$SourceKind actual=$($result.source_kind)"
}

Write-Output ([pscustomobject]@{
    InputPath = $resolvedInputPath
    SourceKind = $SourceKind
    OutputPath = $resolvedOutputPath
    SizeBytes = (Get-Item -LiteralPath $resolvedOutputPath).Length
    WarningCount = @($result.warnings).Count
    Completed = $true
})
