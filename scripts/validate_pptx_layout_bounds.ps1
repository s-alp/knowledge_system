param(
    [Parameter(Mandatory = $true)]
    [string]$LayoutDirectory,

    [Parameter(Mandatory = $true)]
    [string]$PptxPath
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues["*:Encoding"] = "utf8"

$slideWidth = 1280.0
$slideHeight = 720.0
$tolerance = 1.0
$issues = [System.Collections.Generic.List[string]]::new()

$layoutFiles = Get-ChildItem -LiteralPath $LayoutDirectory -Filter "slide-*.layout.json" -File |
    Sort-Object Name

foreach ($layoutFile in $layoutFiles) {
    $layout = Get-Content -LiteralPath $layoutFile.FullName -Encoding utf8 -Raw | ConvertFrom-Json

    foreach ($element in $layout.elements) {
        if ($null -eq $element.bbox -or $null -eq $element.text) {
            continue
        }

        $left = [double]$element.bbox[0]
        $top = [double]$element.bbox[1]
        $width = [double]$element.bbox[2]
        $height = [double]$element.bbox[3]
        $right = $left + $width
        $bottom = $top + $height

        if (
            $left -lt -$tolerance -or
            $top -lt -$tolerance -or
            $right -gt ($slideWidth + $tolerance) -or
            $bottom -gt ($slideHeight + $tolerance)
        ) {
            $issues.Add(
                "$($layoutFile.Name): text element '$($element.name)' is outside the slide " +
                "[$left,$top,$width,$height]"
            )
        }
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($PptxPath)

try {
    $slideEntries = $archive.Entries |
        Where-Object { $PSItem.FullName -match "^ppt/slides/slide\d+\.xml$" } |
        Sort-Object FullName

    foreach ($entry in $slideEntries) {
        $stream = $entry.Open()
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)

        try {
            [xml]$xml = $reader.ReadToEnd()
        }
        finally {
            $reader.Dispose()
            $stream.Dispose()
        }

        $namespaceManager = [System.Xml.XmlNamespaceManager]::new($xml.NameTable)
        $namespaceManager.AddNamespace(
            "p",
            "http://schemas.openxmlformats.org/presentationml/2006/main"
        )
        $namespaceManager.AddNamespace(
            "a",
            "http://schemas.openxmlformats.org/drawingml/2006/main"
        )

        $placeholders = $xml.SelectNodes(
            "//p:sp[p:nvSpPr/p:nvPr/p:ph]",
            $namespaceManager
        )

        foreach ($placeholder in $placeholders) {
            $textNodes = $placeholder.SelectNodes(".//a:t", $namespaceManager)
            $text = ($textNodes | ForEach-Object { $PSItem.InnerText }) -join ""

            if ([string]::IsNullOrWhiteSpace($text)) {
                $issues.Add("$($entry.FullName): empty structural placeholder remains")
            }
        }
    }
}
finally {
    $archive.Dispose()
}

if ($issues.Count -gt 0) {
    $issues | ForEach-Object { Write-Error $PSItem }
    exit 1
}

$message = "OK: validated {0} layouts and {1} slide XML files; " +
    "no text-boundary violations or empty structural placeholders found."
Write-Output ($message -f $layoutFiles.Count, $slideEntries.Count)
