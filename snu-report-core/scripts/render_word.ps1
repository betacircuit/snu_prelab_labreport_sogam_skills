param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference = 'Stop'
$reportInput = (Resolve-Path -LiteralPath $InputDocx).Path
$reportOutput = [IO.Path]::GetFullPath($OutputPdf)
if ([IO.Path]::GetExtension($reportInput) -ne '.docx' -or [IO.Path]::GetExtension($reportOutput) -ne '.pdf') {
    throw 'Expected DOCX input and PDF output.'
}
$reportWord = New-Object -ComObject Word.Application
try {
    $reportWord.Visible = $false
    $reportWord.DisplayAlerts = 0
    $reportWord.AutomationSecurity = 3
    # Read-only; no recent-file entry, no macro execution, no save to the DOCX.
    $reportDocument = $reportWord.Documents.Open($reportInput, $false, $true, $false)
    try {
        $reportDocument.ExportAsFixedFormat($reportOutput, 17)
    } finally {
        $reportDocument.Close(0)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($reportDocument)
    }
} finally {
    $reportWord.Quit(0)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($reportWord)
}
