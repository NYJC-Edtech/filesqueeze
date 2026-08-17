# Test PowerPoint video creation specifically
# This is the operation that's failing in FileSqueeze

Write-Host "Testing PowerPoint Video Creation..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    # Load assembly
    Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
    $app = New-Object -ComObject powerpoint.application

    Write-Host "PowerPoint Version: $($app.Version)" -ForegroundColor Gray

    # Test file
    $testFile = "G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"

    if (-not (Test-Path $testFile)) {
        Write-Host "[ERROR] Test file not found: $testFile" -ForegroundColor Red
        $app.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null
        exit 1
    }

    Write-Host "Opening presentation: $testFile" -ForegroundColor Yellow
    $pres = $app.Presentations.Open($testFile, $true, $false, $false)

    Write-Host "Slides: $($pres.Slides.Count)" -ForegroundColor Gray

    # Create video
    $outputTest = "G:\Shared drives\compressor\compressed\test_video.mp4"

    # Ensure output directory exists
    $outputDir = Split-Path $outputTest -Parent
    if (-not (Test-Path $outputDir)) {
        Write-Host "Creating output directory: $outputDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }

    Write-Host "Starting video creation to: $outputTest" -ForegroundColor Yellow
    Write-Host "This may take 60-90 seconds..." -ForegroundColor Gray

    $startTime = Get-Date

    # Start video creation
    try {
        $pres.CreateVideo($outputTest)
        Write-Host "[OK] Video creation started" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] CreateVideo call failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Exception details: $($_.Exception)" -ForegroundColor Red
        $pres.Close()
        $app.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null
        exit 1
    }

    # Wait for completion
    $videoDone = [Microsoft.Office.Interop.PowerPoint.PpMediaTaskStatus]::ppMediaTaskStatusDone
    $timeout = 180  # 3 minutes
    $elapsed = 0
    $lastStatus = ""

    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 5
        $elapsed += 5

        try {
            $status = $pres.CreateVideoStatus
            if ($null -ne $status) {
                $statusStr = $status.ToString()
                if ($statusStr -ne $lastStatus) {
                    Write-Host "  Status: $statusStr ($elapsed seconds elapsed)" -ForegroundColor Gray
                    $lastStatus = $statusStr
                }

                if ($status -eq $videoDone) {
                    break
                }
            } else {
                Write-Host "[WARNING] CreateVideoStatus is null after $elapsed seconds" -ForegroundColor Yellow
                Write-Host "  Video creation may have failed or presentation was closed" -ForegroundColor Yellow
                break
            }
        } catch {
            Write-Host "[ERROR] Error checking CreateVideoStatus: $($_.Exception.Message)" -ForegroundColor Red
            break
        }
    }

    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds

    if ($pres.CreateVideoStatus -eq $videoDone) {
        Write-Host "[OK] Video creation completed in $([int]$duration) seconds" -ForegroundColor Green

        if (Test-Path $outputTest) {
            $size = (Get-Item $outputTest).Length
            $sizeMB = [math]::Round($size / 1MB, 2)
            Write-Host "  Output file: $outputTest" -ForegroundColor Gray
            Write-Host "  File size: $sizeMB MB" -ForegroundColor Gray
        } else {
            Write-Host "[ERROR] Video creation reported success but file not found" -ForegroundColor Red
        }
    } else {
        Write-Host "[ERROR] Video creation timed out after $timeout seconds" -ForegroundColor Red
        Write-Host "  Final status: $($pres.CreateVideoStatus)" -ForegroundColor Red
    }

    # Cleanup
    $pres.Close()
    $app.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[SUCCESS] Video creation test completed!" -ForegroundColor Green

} catch {
    Write-Host "[FAIL] Video creation failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
}
