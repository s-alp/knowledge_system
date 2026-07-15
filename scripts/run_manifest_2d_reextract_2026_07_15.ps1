[CmdletBinding()]
param(
    [string]$ManifestPath = "C:\Users\s-iwata\Desktop\knowledge_system\output\souya_handoff\icad_extract_import_manifest_2026-07-15.json",
    [string]$RunnerPath = "C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe",
    [string]$SxNetDllPath = "C:\ICADSX\bin\sxnet.dll",
    [string]$OutputDirectory = "C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\manifest_2d_reextract_2026-07-15",
    [int]$MaxFiles = 0,
    [int]$TimeoutSeconds = 180,
    [string[]]$FileName = @(),
    [string[]]$ExcludeFileName = @(),
    [switch]$SkipExisting,
    [switch]$IncludeAllEntries
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "manifest not found: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $RunnerPath)) {
    throw "runner not found: $RunnerPath"
}
if (-not (Test-Path -LiteralPath $SxNetDllPath)) {
    throw "sxnet.dll not found: $SxNetDllPath"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$entries = if ($IncludeAllEntries) {
    @($manifest.entries)
}
else {
    @($manifest.entries | Where-Object { $PSItem.has2d -eq $true })
}
if ($FileName.Count -gt 0) {
    $entries = @(
        $entries | Where-Object {
            $FileName -contains [System.IO.Path]::GetFileName([string]$PSItem.sourcePath)
        }
    )
}
if ($ExcludeFileName.Count -gt 0) {
    $entries = @(
        $entries | Where-Object {
            $ExcludeFileName -notcontains [System.IO.Path]::GetFileName([string]$PSItem.sourcePath)
        }
    )
}
if ($MaxFiles -gt 0) {
    $entries = @($entries | Select-Object -First $MaxFiles)
}

$summary = foreach ($entry in $entries) {
    $sourcePath = [string]$entry.sourcePath
    $fileName = [System.IO.Path]::GetFileNameWithoutExtension($sourcePath)
    $safeName = ($fileName -replace '[\\/:*?"<>|]', '_')
    $outputPath = Join-Path $OutputDirectory "$safeName.latest_2d.json"
    $startedAt = Get-Date

    $record = [ordered]@{
        source_path = $sourcePath
        customer_hint = $entry.customerHint
        output_path = $outputPath
        exists = Test-Path -LiteralPath $sourcePath
        skipped = $false
        timed_out = $false
        exit_code = $null
        elapsed_ms = $null
        view_sheet_count = $null
        print_frame_count = $null
        layer_count = $null
        text_count = $null
        dimension_count = $null
        geometry_primitive_count = $null
        inside_print_area_count = $null
        outside_print_area_count = $null
        unknown_print_area_count = $null
        warning_count = $null
        stdout = $null
        stderr = $null
        error = $null
    }

    if (-not $record.exists) {
        $record.error = "file_not_found"
        [pscustomobject]$record
        continue
    }

    if ($SkipExisting -and (Test-Path -LiteralPath $outputPath)) {
        $record.skipped = $true
        [pscustomobject]$record
        continue
    }

    try {
        $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = $RunnerPath
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.WorkingDirectory = (Get-Location).Path
        foreach ($argument in @(
            "extract",
            "--input-path", $sourcePath,
            "--source-kind", "2d",
            "--output-path", $outputPath,
            "--sxnet-dll-path", $SxNetDllPath,
            "--shutdown-icad-if-autostarted", "false"
        )) {
            $startInfo.ArgumentList.Add([string]$argument)
        }

        $runnerProcess = [System.Diagnostics.Process]::Start($startInfo)
        $stdoutTask = $runnerProcess.StandardOutput.ReadToEndAsync()
        $stderrTask = $runnerProcess.StandardError.ReadToEndAsync()
        if (-not $runnerProcess.WaitForExit($TimeoutSeconds * 1000)) {
            try {
                $runnerProcess.Kill($true)
            }
            catch {
                $runnerProcess.Kill()
            }
            $runnerProcess.WaitForExit()
            $record.timed_out = $true
            $record.exit_code = -2
            $record.error = "timeout_after_$($TimeoutSeconds)_seconds"
        }
        else {
            $record.exit_code = $runnerProcess.ExitCode
            if ($record.exit_code -ne 0) {
                $record.error = "runner_exit_code_$($record.exit_code)"
            }
        }
        $record.stdout = $stdoutTask.GetAwaiter().GetResult().Trim()
        $record.stderr = $stderrTask.GetAwaiter().GetResult().Trim()
        $record.elapsed_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds

        if ($record.exit_code -eq 0 -and (Test-Path -LiteralPath $outputPath)) {
            $json = Get-Content -LiteralPath $outputPath -Raw -Encoding utf8 | ConvertFrom-Json
            $raw = $json.raw_extract
            $items = @($raw.texts) + @($raw.dimensions) + @($raw.geometry_primitives) + @($raw.weld_notes) + @($raw.balloons) + @($raw.tolerances)

            $record.view_sheet_count = @($raw.view_sheets).Count
            $record.print_frame_count = @($raw.print_frames).Count
            $record.layer_count = @($raw.layers).Count
            $record.text_count = @($raw.texts).Count
            $record.dimension_count = @($raw.dimensions).Count
            $record.geometry_primitive_count = @($raw.geometry_primitives).Count
            $record.inside_print_area_count = @($items | Where-Object { $PSItem.inside_print_area -eq $true }).Count
            $record.outside_print_area_count = @($items | Where-Object { $PSItem.inside_print_area -eq $false }).Count
            $record.unknown_print_area_count = @($items | Where-Object { $null -eq $PSItem.inside_print_area }).Count
            $record.warning_count = @($json.warnings).Count
        }
    }
    catch {
        $record.exit_code = $LASTEXITCODE
        $record.elapsed_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds
        $record.error = $PSItem.Exception.Message
    }

    [pscustomobject]$record
}

$summaryPath = Join-Path $OutputDirectory "_summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
$summary | Format-Table source_path, exists, skipped, exit_code, view_sheet_count, print_frame_count, layer_count, text_count, dimension_count, geometry_primitive_count, inside_print_area_count, outside_print_area_count, unknown_print_area_count, warning_count, error -AutoSize
Write-Output "summary_path=$summaryPath"
