param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$Destination,

    [string[]]$ExcludedExtensions = @('.icd'),

    [string]$EstimatePattern = '見積|金額|原価|費用|工数|単価|価格|quotation|quote|cost'
)

$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$excludedExtensionSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($extension in $ExcludedExtensions) {
    if (-not [string]::IsNullOrWhiteSpace($extension)) {
        [void]$excludedExtensionSet.Add($extension.ToLowerInvariant())
    }
}

$sourceItem = Get-Item -LiteralPath $Source -ErrorAction Stop
[System.IO.Directory]::CreateDirectory($Destination) | Out-Null

$copiedCount = 0
$copiedSize = 0L
$skippedEstimateCount = 0
$skippedEstimateSize = 0L
$skippedExtensionCount = 0
$skippedExtensionSize = 0L

foreach ($path in [System.IO.Directory]::EnumerateFiles($sourceItem.FullName, '*', [System.IO.SearchOption]::AllDirectories)) {
    try {
        $file = [System.IO.FileInfo]::new($path)
        if (-not $file.Exists) {
            continue
        }

        $extension = $file.Extension.ToLowerInvariant()
        $isEstimate = $file.Name -match $EstimatePattern -or $file.DirectoryName -match $EstimatePattern
        $isExcludedExtension = $excludedExtensionSet.Contains($extension)

        if ($isEstimate) {
            $skippedEstimateCount += 1
            $skippedEstimateSize += $file.Length
            continue
        }

        if ($isExcludedExtension) {
            $skippedExtensionCount += 1
            $skippedExtensionSize += $file.Length
            continue
        }

        $relativePath = $file.FullName.Substring($sourceItem.FullName.Length).TrimStart('\')
        $destinationPath = Join-Path -Path $Destination -ChildPath $relativePath
        $destinationDir = Split-Path -Parent $destinationPath
        if (-not [string]::IsNullOrWhiteSpace($destinationDir)) {
            [System.IO.Directory]::CreateDirectory($destinationDir) | Out-Null
        }

        [System.IO.File]::Copy($file.FullName, $destinationPath, $true)
        $copiedCount += 1
        $copiedSize += $file.Length
    }
    catch {
        throw
    }
}

[pscustomobject]@{
    Source = $sourceItem.FullName
    Destination = [System.IO.Path]::GetFullPath($Destination)
    CopiedCount = $copiedCount
    CopiedSizeBytes = $copiedSize
    SkippedEstimateCount = $skippedEstimateCount
    SkippedEstimateSizeBytes = $skippedEstimateSize
    SkippedExtensionCount = $skippedExtensionCount
    SkippedExtensionSizeBytes = $skippedExtensionSize
    ExcludedExtensions = $ExcludedExtensions
} | ConvertTo-Json -Depth 4
