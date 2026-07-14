[CmdletBinding()]
param(
    [string]$RunnerPath = "C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe",
    [string]$SxNetDllPath = "C:\ICADSX\bin\sxnet.dll",
    [string]$OutputDirectory = "C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\latest_shared_detect_2026-07-14"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

$ErrorActionPreference = "Stop"

$samples = @(
    "T:\NTC\TF設計部\TD2\D-MAX_DK68\20230821_Automation\作業\COVER_A._DRIP_TRAY\9NK5E56H20-00-BRACKET-A0-3D-01.icd",
    "T:\NTC\TF設計部\TD2\GM_Bay\20240410_オートメーション(MOD3)\作業\OP128\DRIP_TRAY\LO横MC\マプラスデザイン\9NK5E51B70-00-BRACKET-A0-3D-01.icd",
    "T:\NTC\TF設計部\TD2\GM_Bay\20240410_オートメーション(MOD3)\作業\OP128\DRIP_TRAY\LO横MC\三宅設計\9NK5E51M00-00-COVER-A3-3D-01.icd",
    "J:\不二越\作業\U8729\STA_8\U8729_S81\U8718-S71-149_A4.icd",
    "J:\不二越\作業\U8729\STA_8\U8729_S81\U8718-S71-002_A3.icd",
    "J:\不二越5\260703_次期円筒研削盤開発(竹中様)\作業\18T5-10BF(8).icd",
    "J:\不二越5\260501_ブロック円研機_高さ調整機構\作業\G1630-S3000-502_A3a1.icd",
    "J:\不二越5\260501_ブロック円研機_高さ調整機構\作業\G1630-S3000-039_A0a1.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\FIL\20260511_General_Beverage\01_3Dモデル\32791729A01.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\FIL\20260511_General_Beverage\01_3Dモデル\36555211A01.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\6800DDU.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\4D-75.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\474300AC219.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\6051033A.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\47323023A01.icd",
    "\\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\47323200X40c.icd"
)

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$summary = foreach ($sample in $samples) {
    $fileName = [System.IO.Path]::GetFileNameWithoutExtension($sample)
    $safeName = ($fileName -replace '[\\/:*?"<>|]', '_')
    $outputPath = Join-Path $OutputDirectory "$safeName.detect.json"
    $startedAt = Get-Date

    $record = [ordered]@{
        file = $sample
        output_path = $outputPath
        exists = Test-Path -LiteralPath $sample
        exit_code = $null
        elapsed_ms = $null
        has_2d = $null
        has_3d = $null
        has_2d_container = $null
        view_sheet_count = $null
        print_frame_count = $null
        geometry_count = $null
        part_count = $null
        warning_count = $null
        error = $null
    }

    if (-not $record.exists) {
        $record.error = "file_not_found"
        [pscustomobject]$record
        continue
    }

    try {
        & $RunnerPath detect --input-path $sample --output-path $outputPath --sxnet-dll-path $SxNetDllPath --shutdown-icad-if-autostarted false
        $record.exit_code = $LASTEXITCODE
        $record.elapsed_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds

        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $outputPath)) {
            $json = Get-Content -LiteralPath $outputPath -Raw -Encoding utf8 | ConvertFrom-Json
            $record.has_2d = $json.detection.has_2d
            $record.has_3d = $json.detection.has_3d
            $record.has_2d_container = $json.detection.has_2d_container
            $record.view_sheet_count = $json.detection.two_d.view_sheet_count
            $record.print_frame_count = $json.detection.two_d.print_frame_count
            $record.geometry_count = $json.detection.two_d.geometry_count
            $record.part_count = $json.detection.three_d.part_count
            $record.warning_count = @($json.warnings).Count
        }
    }
    catch {
        $record.exit_code = $LASTEXITCODE
        $record.elapsed_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds
        $record.error = $_.Exception.Message
    }

    [pscustomobject]$record
}

$summaryPath = Join-Path $OutputDirectory "_summary.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryPath -Encoding utf8
$summary | Format-Table file, exists, exit_code, has_2d, has_3d, view_sheet_count, print_frame_count, geometry_count, part_count, warning_count -AutoSize
Write-Output "summary_path=$summaryPath"
