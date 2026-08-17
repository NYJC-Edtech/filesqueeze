param(
    [string] $Path,
    [string] $FilePath
)


## IMPORTS
Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint



## PARAMETER VALIDATION
if (-Not ($Path)) {
    Write-Error "Missing argument -Path"
    Exit 1
}
if (-Not ($FilePath)) {
    Write-Error "Missing argument -FilePath"
    Exit 1
}
# Test if input path exists and is accessible
if (-Not (Test-Path -Path $Path)) {
    Write-Error "${Path}: File does not exist"
    try {
        $resolvedPath = Resolve-Path $Path -ErrorAction Stop
        $Path = $resolvedPath
    } catch {
        Write-Error "Could not resolve path: ${Path}"
        Exit 1
    }
}

# Test output directory
$outputDir = Split-Path -Parent $FilePath
if (-Not (Test-Path -Path $outputDir)) {
    try {
        New-Item -ItemType Directory -Path $outputDir -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-Error "Could not create output directory: ${outputDir}"
        Exit 1
    }
}

if (-Not (Test-Path -Path $Path)) {
    Write-Error "${Path}: File does not exist"
    Exit 1
}
if ([System.IO.Path]::GetExtension($Path) -ne ".pptx") {
    Write-Error "${Path}: Not a PPTX file"
    Exit 1
}



## CONSTANTS
# https://docs.microsoft.com/en-us/office/vba/api/powerpoint.ppsaveasfiletype
$mp4 = [Microsoft.Office.Interop.PowerPoint.PpSaveAsFileType]::ppSaveAsMP4
# https://docs.microsoft.com/en-us/office/vba/api/powerpoint.ppmediataskstatus
$videoDone = [Microsoft.Office.Interop.PowerPoint.PpMediaTaskStatus]::ppMediaTaskStatusDone



## APPLICATION
try {
    $Application = New-Object -ComObject powerpoint.application
    if (-Not $Application) {
        Write-Error "Failed to create PowerPoint application object"
        Exit 1
    }

    $Presentation = $Application.Presentations.Open($Path, $true, $false, $false)  # FileName, ReadOnly, Untitled, WithWindow
    if (-Not $Presentation) {
        Write-Error "Failed to open presentation: ${Path}"
        $Application.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Application) | Out-Null
        Exit 1
    }

    $Presentation.CreateVideo($FilePath)
    while ($Presentation.CreateVideoStatus -ne $videoDone) {
        Start-Sleep -Seconds 1
    }

    $Presentation.Close()
    $Application.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Presentation) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Application) | Out-Null

    # Verify output file was created and has reasonable size
    if (-Not (Test-Path -Path $FilePath)) {
        Write-Error "Output file not created: ${FilePath}"
        Exit 1
    }

    $outputSize = (Get-Item $FilePath).Length
    if ($outputSize -lt 1000) {
        Write-Error "Output file too small (${outputSize} bytes): ${FilePath}"
        Exit 1
    }

    Exit 0
}
catch {
    Write-Error "PowerPoint conversion failed: $_"
    # Clean up COM objects
    if ($Presentation) {
        try { $Presentation.Close() } catch {}
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Presentation) | Out-Null
    }
    if ($Application) {
        try { $Application.Quit() } catch {}
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Application) | Out-Null
    }
    Exit 1
}