[CmdletBinding()]
param(
    [ValidateSet('update', 'check')]
    [string]$Mode = 'update'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$packageName = 'handover_package'
$packageRoot = Join-Path $repoRoot $packageName

$rootFiles = @(
    @{ Source = 'docs\handover-readme.md'; Destination = 'README.md' },
    @{ Source = '.env.example'; Destination = '.env.example' },
    @{ Source = '.gitignore'; Destination = '.gitignore' },
    @{ Source = '.dockerignore'; Destination = '.dockerignore' },
    @{ Source = 'docker-compose.yml'; Destination = 'docker-compose.yml' },
    @{ Source = 'docker-compose.dev.yml'; Destination = 'docker-compose.dev.yml' }
)

$docFiles = @(
    @{ Source = 'docs\viewer-specification.md'; Destination = 'viewer-specification.md' },
    @{ Source = 'docs\viewer-flow.md'; Destination = 'viewer-flow.md' },
    @{ Source = 'docs\code-map.md'; Destination = 'code-map.md' },
    @{ Source = 'docs\handover-technology-summary.md'; Destination = 'technology-summary.md' },
    @{ Source = 'docs\handover-integration-manual.md'; Destination = 'integration-manual.md' },
    @{ Source = 'docs\THIRD_PARTY_NOTICES.md'; Destination = 'THIRD_PARTY_NOTICES.md' }
)

function Test-ExcludedFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string[]]$Patterns
    )

    foreach ($pattern in $Patterns) {
        if ($Name -like $pattern) {
            return $true
        }
    }

    return $false
}

function Copy-TreeFiltered {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination,
        [Parameter(Mandatory = $true)]
        [string[]]$ExcludedDirectories,
        [Parameter(Mandatory = $true)]
        [string[]]$ExcludedFiles
    )

    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination | Out-Null
    }

    foreach ($item in Get-ChildItem -Force -LiteralPath $Source) {
        if ($item.PSIsContainer) {
            if ($ExcludedDirectories -contains $item.Name) {
                continue
            }

            Copy-TreeFiltered `
                -Source $item.FullName `
                -Destination (Join-Path $Destination $item.Name) `
                -ExcludedDirectories $ExcludedDirectories `
                -ExcludedFiles $ExcludedFiles
            continue
        }

        if (Test-ExcludedFile -Name $item.Name -Patterns $ExcludedFiles) {
            continue
        }

        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Destination $item.Name) -Force
    }
}

function New-HandoverPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    if (Test-Path -LiteralPath $DestinationRoot) {
        throw "Destination already exists: $DestinationRoot"
    }

    New-Item -ItemType Directory -Path $DestinationRoot | Out-Null

    foreach ($file in $rootFiles) {
        Copy-Item `
            -LiteralPath (Join-Path $repoRoot $file.Source) `
            -Destination (Join-Path $DestinationRoot $file.Destination) `
            -Force
    }

    $backendDestination = Join-Path $DestinationRoot 'backend'
    Copy-TreeFiltered `
        -Source (Join-Path $repoRoot 'backend') `
        -Destination $backendDestination `
        -ExcludedDirectories @('media', '.pytest_cache', '__pycache__', 'tests') `
        -ExcludedFiles @('db.sqlite3', '*.pyc', 'pytest.ini')

    $backendRequirementsPath = Join-Path $backendDestination 'requirements-base.txt'
    if (Test-Path -LiteralPath $backendRequirementsPath) {
        $runtimeRequirements = Get-Content -LiteralPath $backendRequirementsPath -Encoding utf8 |
            Where-Object { $PSItem -notmatch '^pytest($|[-=])' }
        Set-Content -LiteralPath $backendRequirementsPath -Value $runtimeRequirements -Encoding utf8
    }

    $frontendDestination = Join-Path $DestinationRoot 'frontend'
    Copy-TreeFiltered `
        -Source (Join-Path $repoRoot 'frontend') `
        -Destination $frontendDestination `
        -ExcludedDirectories @('node_modules', 'dist', 'coverage', '__pycache__', 'test') `
        -ExcludedFiles @('*.tsbuildinfo', 'vite.config.js', 'vite.config.d.ts', 'vitest.config.js', 'vitest.config.d.ts', 'vitest.config.ts', '*.test.ts', '*.test.tsx')

    $docsDestination = Join-Path $DestinationRoot 'docs'
    New-Item -ItemType Directory -Path $docsDestination | Out-Null

    foreach ($docFile in $docFiles) {
        Copy-Item `
            -LiteralPath (Join-Path $repoRoot $docFile.Source) `
            -Destination (Join-Path $docsDestination $docFile.Destination) `
            -Force
    }

    Copy-TreeFiltered `
        -Source (Join-Path $repoRoot 'docs\licenses') `
        -Destination (Join-Path $docsDestination 'licenses') `
        -ExcludedDirectories @('__pycache__') `
        -ExcludedFiles @('*.pyc')
}

function Get-TreeManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $manifest = @{}

    if (-not (Test-Path -LiteralPath $Root)) {
        return $manifest
    }

    foreach ($item in Get-ChildItem -Force -Recurse -LiteralPath $Root) {
        $relativePath = $item.FullName.Substring($Root.Length).TrimStart('\')
        $key = $relativePath.ToLowerInvariant()

        if ($item.PSIsContainer) {
            $manifest[$key] = @{
                RelativePath = $relativePath
                Type = 'Directory'
                Hash = $null
            }
            continue
        }

        $manifest[$key] = @{
            RelativePath = $relativePath
            Type = 'File'
            Hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
        }
    }

    return $manifest
}

function Compare-PackageTrees {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExpectedRoot,
        [Parameter(Mandatory = $true)]
        [string]$ActualRoot
    )

    $expectedManifest = Get-TreeManifest -Root $ExpectedRoot
    $actualManifest = Get-TreeManifest -Root $ActualRoot
    $differences = [System.Collections.Generic.List[string]]::new()
    $allKeys = @($expectedManifest.Keys + $actualManifest.Keys | Sort-Object -Unique)

    foreach ($key in $allKeys) {
        $expectedEntry = $expectedManifest[$key]
        $actualEntry = $actualManifest[$key]

        if ($null -eq $expectedEntry) {
            $differences.Add("Unexpected item: $($actualEntry.RelativePath)")
            continue
        }

        if ($null -eq $actualEntry) {
            $differences.Add("Missing item: $($expectedEntry.RelativePath)")
            continue
        }

        if ($expectedEntry.Type -ne $actualEntry.Type) {
            $differences.Add("Type mismatch: $($expectedEntry.RelativePath)")
            continue
        }

        if ($expectedEntry.Type -eq 'File' -and $expectedEntry.Hash -ne $actualEntry.Hash) {
            $differences.Add("Content mismatch: $($expectedEntry.RelativePath)")
        }
    }

    return @($differences)
}

function Assert-SafePackagePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathToCheck
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($PathToCheck)
    $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $packageName))

    if (-not $resolvedPath.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside $allowedRoot : $resolvedPath"
    }

    return $resolvedPath
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("handover-package-" + [System.Guid]::NewGuid().ToString('N'))
$tempPackageRoot = Join-Path $tempRoot $packageName

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    New-HandoverPackage -DestinationRoot $tempPackageRoot

    if ($Mode -eq 'check') {
        $differences = @(Compare-PackageTrees -ExpectedRoot $tempPackageRoot -ActualRoot $packageRoot)
        if ($differences.Count -gt 0) {
            Write-Host 'handover_package is not up to date.'
            foreach ($difference in $differences) {
                Write-Host " - $difference"
            }
            exit 1
        }

        Write-Host 'handover_package is up to date.'
        exit 0
    }

    if (Test-Path -LiteralPath $packageRoot) {
        $safePackagePath = Assert-SafePackagePath -PathToCheck $packageRoot
        Remove-Item -LiteralPath $safePackagePath -Recurse -Force
    }

    Move-Item -LiteralPath $tempPackageRoot -Destination $packageRoot
    Write-Host "handover_package has been updated at $packageRoot"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
