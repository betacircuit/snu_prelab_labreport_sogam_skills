param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Output,
    [ValidateRange(1,4)][int]$Scale = 3
)
$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$outputPath = [System.IO.Path]::GetFullPath($Output)
if ([System.IO.Path]::GetExtension($sourcePath) -ine '.emf') { throw 'Source must be an LTspice-exported .emf file.' }
if ([System.IO.Path]::GetExtension($outputPath) -ine '.png') { throw 'Output must be .png.' }
if (Test-Path -LiteralPath $outputPath) { throw 'Use a new output path; existing files are preserved.' }
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($outputPath)) | Out-Null
Add-Type -AssemblyName System.Drawing
$metafile = [System.Drawing.Image]::FromFile($sourcePath)
$bitmap = $null
$graphics = $null
try {
    $bitmap = [System.Drawing.Bitmap]::new($metafile.Width * $Scale, $metafile.Height * $Scale)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.DrawImage($metafile, [System.Drawing.Rectangle]::new(0,0,$bitmap.Width,$bitmap.Height))
    $bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $outputPath
} finally {
    if ($graphics) { $graphics.Dispose() }
    if ($bitmap) { $bitmap.Dispose() }
    $metafile.Dispose()
}
