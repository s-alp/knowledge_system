param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$Destination,

    [Parameter(Mandatory = $true)]
    [string[]]$IncludeExtensions,

    [string]$EstimatePattern = '見積|金額|原価|費用|工数|単価|価格|quotation|quote|cost'
)

$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$sourceItem = Get-Item -LiteralPath $Source -ErrorAction Stop
[System.IO.Directory]::CreateDirectory($Destination) | Out-Null

$excludeNamePatterns = @(
    '*見積*',
    '*金額*',
    '*原価*',
    '*費用*',
    '*工数*',
    '*単価*',
    '*価格*',
    '*quotation*',
    '*quote*',
    '*cost*'
)

$copiedFiles = 0
$copiedSize = 0L
$copiedExtensions = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
$filters = New-Object System.Collections.Generic.List[string]

foreach ($extension in $IncludeExtensions) {
    if ([string]::IsNullOrWhiteSpace($extension)) {
        continue
    }

    $normalized = $extension.Trim().ToLowerInvariant()
    $filter = if ($normalized.StartsWith('.')) { '*' + $normalized } else { '*.' + $normalized }
    $filters.Add($filter) | Out-Null
    [void]$copiedExtensions.Add($normalized)
}

& robocopy `
    $sourceItem.FullName `
    $Destination `
    $filters.ToArray() `
    /S /R:0 /W:0 /MT:16 /FFT /NFL /NDL /NJH /NJS /NP `
    /XF $excludeNamePatterns `
    /XD $excludeNamePatterns

$exitCode = $LASTEXITCODE
if ($exitCode -gt 7) {
    throw "robocopy failed with exit code $exitCode"
}

foreach ($path in [System.IO.Directory]::EnumerateFiles($Destination, '*', [System.IO.SearchOption]::AllDirectories)) {
    $file = [System.IO.FileInfo]::new($path)
    if (-not $file.Exists) {
        continue
    }

    $copiedFiles += 1
    $copiedSize += $file.Length
}

[pscustomobject]@{
    Source = $sourceItem.FullName
    Destination = [System.IO.Path]::GetFullPath($Destination)
    CopiedCount = $copiedFiles
    CopiedSizeBytes = $copiedSize
    IncludedExtensions = @($copiedExtensions | Sort-Object)
    EstimatePattern = $EstimatePattern
} | ConvertTo-Json -Depth 4
