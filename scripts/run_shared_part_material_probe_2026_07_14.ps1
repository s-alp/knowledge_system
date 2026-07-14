[CmdletBinding()]
param(
    [string]$RunnerPath = "C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe",
    [string]$SxNetDllPath = "C:\ICADSX\bin\sxnet.dll",
    [string]$OutputDirectory = "C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\part_material_probe_2026-07-14"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

$ErrorActionPreference = "Stop"

$samples = @(
    "J:\SBY\アイソレータ\210126_エーザイ_アイソレータ_RAA4844\作業フォルダ\開閉扉\U8105111315.icd",
    "J:\NKS\2109_部品図バラシ\作業\40J_レール部\217008-41J-3004.icd",
    "J:\DNPE\作業\220627_DFR-CM1(AA)フィーダー部品図作成\DNP滝本部品図\DFR-CM1-AA0305300011.icd",
    "J:\ZCSET\300P_210312\作業\2_ロードカップ部\XH30-A08001-R03-JP_ロードカップ部改造.icd",
    "J:\ZCSET\300P_210312\作業\2_ロードカップ部\XH3001-M08007-01.icd",
    "J:\アースエンジニアリング\251216_ツネイシカムテックス\作業\6月度分(フォルダ移動禁止)\優先1\AR05-A05-B04_No.2 F-FスクリーンスクリーンSシュート組立図\03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd",
    "J:\シブヤパッケージングシステム\25_9R_膨潤パレットアキューム部\作業\SPS送付用\RAR0116_260618_膨潤パレットアキューム部_作成データ\TR1D9Q00027.icd",
    "J:\シブヤパッケージングシステム\25_9R_膨潤パレットアキューム部\作業\SPS送付用\RAR0116_260618_膨潤パレットアキューム部_作成データ\部品図(新規、訂正)\9K\TR1D9K99027.icd",
    "J:\スギノマシン\260513_マルチスズキ乾燥機上部カバー部品図作成(金山様)\作業\M26A07720.icd",
    "J:\ライズ\240603_FCマウント組立装置\作業\34000_供給台部\CAA5012-02434006P1R1.icd",
    "J:\ライズ\240603_FCマウント組立装置\作業\34000_供給台部\CAA5012-02434000K1R1.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\11_クリーニング駆動\PSG011-PA1100_クリーニング駆動.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\13_ベース\PSG011-PA1300_ベース.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\13_ベース\部品\PSG011-PA13001.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\13_ベース\部品\PSG011-PA13002.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\05_コラム\PSG011-PA0500_コラム.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\05_コラム\部品\PSG011-P05008.icd",
    "J:\ラップマスターウォルターズジャパン\PLPG1000_260201\作業\05_コラム\部品\PSG011-P05010.icd",
    "J:\宮本工業所\231109_燃焼ユニット部品図作成\作業\1215_修正部品図\23022-007_231218.icd",
    "J:\宮本工業所\231109_燃焼ユニット部品図作成\作業\1215_修正部品図\23022-013_231218.icd",
    "J:\ライズ\240603_FCマウント組立装置\作業\30000_FC投入部\CAA5012-02430002P1R1.icd",
    "J:\ライズ\240603_FCマウント組立装置\作業\30000_FC投入部\CAA5012-02430012P1R1.icd",
    "J:\ライズ\240603_FCマウント組立装置\作業\35000_位置決め部\CAA5012-02435010P1R1.icd",
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
    $outputPath = Join-Path $OutputDirectory "$safeName.3d.json"
    $startedAt = Get-Date

    $record = [ordered]@{
        file = $sample
        output_path = $outputPath
        exists = Test-Path -LiteralPath $sample
        exit_code = $null
        elapsed_ms = $null
        part_count = $null
        global_material_count = $null
        parts_with_materials = $null
        part_material_count = $null
        part_material_ids = @()
        part_material_probe_warning_count = 0
        warning_count = $null
        error = $null
    }

    if (-not $record.exists) {
        $record.error = "file_not_found"
        [pscustomobject]$record
        continue
    }

    try {
        & $RunnerPath extract --input-path $sample --source-kind 3d --output-path $outputPath --sxnet-dll-path $SxNetDllPath --shutdown-icad-if-autostarted false
        $record.exit_code = $LASTEXITCODE
        $record.elapsed_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds

        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $outputPath)) {
            $json = Get-Content -LiteralPath $outputPath -Raw -Encoding utf8 | ConvertFrom-Json
            $parts = @($json.raw_extract.parts)
            $materials = @($json.raw_extract.materials)
            $partMaterials = @(
                foreach ($part in $parts) {
                    foreach ($material in @($part.materials)) {
                        [pscustomobject]@{
                            part_path = (@($part.tree_path) -join ".")
                            part_name = $part.name
                            matid = $material.mat_id
                            name = $material.name
                            specific_gravity = $material.specific_gravity
                            element_count = $material.element_count
                        }
                    }
                }
            )
            $warnings = @($json.warnings)

            $record.part_count = $parts.Count
            $record.global_material_count = $materials.Count
            $record.parts_with_materials = @($parts | Where-Object { @($_.materials).Count -gt 0 }).Count
            $record.part_material_count = $partMaterials.Count
            $record.part_material_ids = @($partMaterials | ForEach-Object { $_.matid } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            $record.part_material_probe_warning_count = @($warnings | Where-Object { $_.code -eq "part_material_probe_failed" }).Count
            $record.warning_count = $warnings.Count
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
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
$summary | Format-Table file, exists, exit_code, part_count, global_material_count, parts_with_materials, part_material_count, part_material_probe_warning_count, warning_count, error -AutoSize
Write-Output "summary_path=$summaryPath"
