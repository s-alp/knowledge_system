[CmdletBinding()]
param(
    [string]$AuditPath = "C:\Users\s-iwata\Desktop\knowledge_system\output\souya_handoff\icad_shared_sample_current_audit_2026-07-16.json",
    [string]$RunnerPath = "C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe",
    [string]$SxNetDllPath = "C:\ICADSX\bin\sxnet.dll",
    [string]$OutputDirectory = "C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\missing_print_frame_probe_2026-07-16",
    [int]$TimeoutSeconds = 120
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"
$ErrorActionPreference = "Stop"

foreach ($path in @($AuditPath, $RunnerPath, $SxNetDllPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "required path not found: $path"
    }
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$audit = Get-Content -LiteralPath $AuditPath -Raw -Encoding utf8 | ConvertFrom-Json
$targets = @($audit.rows | Where-Object {
    $PSItem.twoDContentStatus -eq "content" -and $PSItem.printFrameCount -eq 0
})

$summary = foreach ($target in $targets) {
    $sourcePath = [string]$target.sourcePath
    $safeName = ([System.IO.Path]::GetFileNameWithoutExtension($sourcePath) -replace '[\/:*?"<>|]', '_')
    $outputPath = Join-Path $OutputDirectory "$safeName.print.json"
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $RunnerPath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in @(
        "probe-2d-print",
        "--input-path", $sourcePath,
        "--output-path", $outputPath,
        "--sxnet-dll-path", $SxNetDllPath,
        "--shutdown-icad-if-autostarted", "false"
    )) {
        $startInfo.ArgumentList.Add([string]$argument)
    }

    $startedAt = Get-Date
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
    if ($timedOut) {
        try { $process.Kill($true) } catch { $process.Kill() }
        $process.WaitForExit()
    }
    $payload = if (-not $timedOut -and $process.ExitCode -eq 0 -and (Test-Path -LiteralPath $outputPath)) {
        Get-Content -LiteralPath $outputPath -Raw -Encoding utf8 | ConvertFrom-Json
    } else {
        $null
    }
    [pscustomobject]@{
        sourcePath = $sourcePath
        outputPath = $outputPath
        timedOut = $timedOut
        exitCode = if ($timedOut) { -2 } else { $process.ExitCode }
        printFrameCount = @($payload.print_probe.print_frames).Count
        plotterCount = @($payload.print_probe.plotters).Count
        warningCount = @($payload.warnings).Count
        stdout = $stdoutTask.GetAwaiter().GetResult().Trim()
        stderr = $stderrTask.GetAwaiter().GetResult().Trim()
        elapsedMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
    }
}

$summaryPath = Join-Path $OutputDirectory "_summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
$summary | Format-Table sourcePath, exitCode, timedOut, printFrameCount, plotterCount, warningCount, elapsedMs -AutoSize
Write-Output "summary_path=$summaryPath"
