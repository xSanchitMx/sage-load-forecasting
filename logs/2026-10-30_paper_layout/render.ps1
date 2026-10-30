$ErrorActionPreference = "Stop"
$src = "C:\Users\mukhe\AppData\Local\Temp\sage_render\paper_copy.docx"
$pdf = "C:\Users\mukhe\AppData\Local\Temp\sage_render\paper_copy.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $true)   # ConfirmConversions=false, ReadOnly=true
$doc.ExportAsFixedFormat($pdf, 17)
$pages = $doc.ComputeStatistics(2)
$doc.Close(0)
if ($word.Documents.Count -eq 0) { $word.Quit() }
Write-Output "pages=$pages"
