<#
.SYNOPSIS
配布パッケージのファイル一覧・サイズ・SHA-256をmanifest.jsonと照合します。

.DESCRIPTION
パッケージ受領時や別PCへのコピー後に、欠落、追加、破損、意図しない変更を検出します。
ファイルは読み取りだけで、内容やmanifest.jsonを変更しません。
不一致が1件でもあればエラー終了し、対象パスと理由を表示します。

.PARAMETER PackagePath
manifest.jsonがある配布パッケージのルートフォルダーです。既定値はスクリプトの親です。

.EXAMPLE
pwsh -NoLogo -NoProfile -File .\scripts\verify_handoff_manifest.ps1

.EXAMPLE
pwsh -NoLogo -NoProfile -File .\scripts\verify_handoff_manifest.ps1 -PackagePath C:\handoff\cad-tag-extraction
#>
[CmdletBinding()]
param(
    [string]$PackagePath = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "このスクリプトはPowerShell 7以降で実行してください。"
}

$resolvedPackagePath = [System.IO.Path]::GetFullPath($PackagePath)
if (-not (Test-Path -LiteralPath $resolvedPackagePath -PathType Container)) {
    throw "パッケージフォルダーが見つかりません: $resolvedPackagePath"
}
$manifestPath = Join-Path $resolvedPackagePath "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "manifest.jsonが見つかりません: $manifestPath"
}

try {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
}
catch {
    throw "manifest.jsonを読み取れません: $($PSItem.Exception.Message)"
}
if ($manifest.schemaVersion -ne "souya_tag_extraction_handoff_manifest.v1") {
    throw "未対応のmanifest schemaVersionです: $($manifest.schemaVersion)"
}

$expected = @{}
foreach ($entry in @($manifest.files)) {
    $relativePath = [string]$entry.path
    if ([string]::IsNullOrWhiteSpace($relativePath) -or $expected.ContainsKey($relativePath)) {
        throw "manifest.jsonに空または重複したpathがあります: $relativePath"
    }
    $expected[$relativePath] = $entry
}
if ([int]$manifest.fileCount -ne $expected.Count) {
    throw "manifest.jsonのfileCountとfiles件数が一致しません: fileCount=$($manifest.fileCount) files=$($expected.Count)"
}

$actual = @{}
foreach ($file in Get-ChildItem -LiteralPath $resolvedPackagePath -Recurse -File) {
    if ($file.FullName -eq $manifestPath) {
        continue
    }
    $relativePath = [System.IO.Path]::GetRelativePath(
        $resolvedPackagePath,
        $file.FullName
    ).Replace("\", "/")
    $actual[$relativePath] = $file
}

$errors = [System.Collections.Generic.List[string]]::new()
foreach ($relativePath in $expected.Keys) {
    if (-not $actual.ContainsKey($relativePath)) {
        $errors.Add("不足: $relativePath")
        continue
    }
    $file = $actual[$relativePath]
    $entry = $expected[$relativePath]
    if ($file.Length -ne [long]$entry.sizeBytes) {
        $errors.Add("サイズ不一致: $relativePath expected=$($entry.sizeBytes) actual=$($file.Length)")
        continue
    }
    $actualHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedHash = ([string]$entry.sha256).ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        $errors.Add("SHA-256不一致: $relativePath")
    }
}
foreach ($relativePath in $actual.Keys) {
    if (-not $expected.ContainsKey($relativePath)) {
        $errors.Add("manifestにないファイル: $relativePath")
    }
}

if ($errors.Count -gt 0) {
    throw "manifest確認で不一致を検出しました。$([Environment]::NewLine)$($errors -join [Environment]::NewLine)"
}

Write-Output ([pscustomobject]@{
    PackagePath = $resolvedPackagePath
    PackageName = [string]$manifest.packageName
    FileCount = $expected.Count
    ManifestSchemaVersion = [string]$manifest.schemaVersion
    Verified = $true
})
