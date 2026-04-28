param(
    [string] $Path,
    [string] $FilePath
)


## IMPORTS
Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint



## PARAMETER VALIDATION
if (-Not ($Path)) {
    Write-Error "Missing argument -Path"
}
if (-Not ($FilePath)) {
    Write-Error "Missing argument -FilePath"
}
if (-Not (Test-Path -Path $Path)) {
    Write-Error "${Path}: File does not exist"
    Exit
}
if ([System.IO.Path]::GetExtension($Path) -ne ".pptx") {
    Write-Error "${Path}: Not a PPTX file"
    Exit
}



## CONSTANTS
# https://docs.microsoft.com/en-us/office/vba/api/powerpoint.ppsaveasfiletype
$mp4 = [Microsoft.Office.Interop.PowerPoint.PpSaveAsFileType]::ppSaveAsMP4
# https://docs.microsoft.com/en-us/office/vba/api/powerpoint.ppmediataskstatus
$videoDone = [Microsoft.Office.Interop.PowerPoint.PpMediaTaskStatus]::ppMediaTaskStatusDone



## APPLICATION
$Application = New-Object -ComObject powerpoint.application

$Presentation = $Application.Presentations.Open($Path, $true, $false, $false)  # FileName, ReadOnly, Untitled, WithWindow
$Presentation.CreateVideo($FilePath)
while ($Presentation.CreateVideoStatus -ne $videoDone) {
    Start-Sleep -Seconds 1
}
$Presentation.Close()
$Application.Quit()