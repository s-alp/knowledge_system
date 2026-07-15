param(
    [Parameter(Mandatory = $true)]
    [string[]]$Roots,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [string[]]$ExcludedExtensions = @('.icd')
)

$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$estimatePattern = '見積|金額|原価|費用|工数|単価|価格|quotation|quote|cost'
$excludedExtensionSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($extension in $ExcludedExtensions) {
    if (-not [string]::IsNullOrWhiteSpace($extension)) {
        [void]$excludedExtensionSet.Add($extension.ToLowerInvariant())
    }
}

function Get-InspectionSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $extensionMap = @{}
    $topLevelMap = @{}
    $estimateCandidates = New-Object System.Collections.Generic.List[string]

    $totalFiles = 0
    $totalSize = 0L
    $excludedExtensionCount = 0
    $excludedExtensionSize = 0L
    $estimateCount = 0
    $estimateSize = 0L
    $copyCount = 0
    $copySize = 0L
    $missingEntries = 0

    $rootItem = Get-Item -LiteralPath $Root -ErrorAction Stop

    foreach ($path in [System.IO.Directory]::EnumerateFiles($rootItem.FullName, '*', [System.IO.SearchOption]::AllDirectories)) {
        try {
            $file = [System.IO.FileInfo]::new($path)
            if (-not $file.Exists) {
                $missingEntries += 1
                continue
            }

            $relative = $file.FullName.Substring($rootItem.FullName.Length).TrimStart('\')
            $topName = if ($relative.Contains('\')) { $relative.Split('\')[0] } else { '[root files]' }
            if (-not $topLevelMap.ContainsKey($topName)) {
                $topLevelMap[$topName] = [pscustomobject]@{
                    Name = $topName
                    FileCount = 0
                    SizeBytes = 0L
                }
            }

            $extension = $file.Extension.ToLowerInvariant()
            if ([string]::IsNullOrWhiteSpace($extension)) {
                $extension = '[no extension]'
            }

            if ($extensionMap.ContainsKey($extension)) {
                $extensionMap[$extension] += 1
            }
            else {
                $extensionMap[$extension] = 1
            }

            $isEstimate = $file.Name -match $estimatePattern -or $file.DirectoryName -match $estimatePattern
            $isExcludedExtension = $excludedExtensionSet.Contains($extension)

            $totalFiles += 1
            $totalSize += $file.Length
            $topLevelMap[$topName].FileCount += 1
            $topLevelMap[$topName].SizeBytes += $file.Length

            if ($isEstimate) {
                $estimateCount += 1
                $estimateSize += $file.Length
                $estimateCandidates.Add($file.FullName)
            }

            if ($isExcludedExtension) {
                $excludedExtensionCount += 1
                $excludedExtensionSize += $file.Length
            }

            if (-not $isExcludedExtension -and -not $isEstimate) {
                $copyCount += 1
                $copySize += $file.Length
            }
        }
        catch {
            $missingEntries += 1
        }
    }

    return [pscustomobject]@{
        Root = $rootItem.FullName
        ExcludedExtensions = $ExcludedExtensions
        TotalFiles = $totalFiles
        TotalSizeBytes = $totalSize
        ExcludedExtensionCount = $excludedExtensionCount
        ExcludedExtensionSizeBytes = $excludedExtensionSize
        EstimateCandidateCount = $estimateCount
        EstimateCandidateSizeBytes = $estimateSize
        CopyTargetCount = $copyCount
        CopyTargetSizeBytes = $copySize
        MissingEntriesSkipped = $missingEntries
        ExtensionBreakdown = @(
            $extensionMap.GetEnumerator() |
                Sort-Object Value -Descending |
                ForEach-Object {
                    [pscustomobject]@{
                        Extension = $PSItem.Key
                        Count = $PSItem.Value
                    }
                }
        )
        TopLevelDirectories = @(
            $topLevelMap.Values | Sort-Object @{ Expression = 'FileCount'; Descending = $true }, Name
        )
        EstimateCandidates = @(
            $estimateCandidates | Sort-Object
        )
    }
}

$results = New-Object System.Collections.Generic.List[object]
$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDir = [System.IO.Path]::GetDirectoryName($outputPath)
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    [System.IO.Directory]::CreateDirectory($outputDir) | Out-Null
}

foreach ($root in $Roots) {
    $results.Add((Get-InspectionSummary -Root $root))
    $results | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
    Write-Output ('completed: ' + $root)
}

Write-Output $outputPath
