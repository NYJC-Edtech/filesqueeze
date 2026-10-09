# PowerShell COM diagnostic script
# Run this to test if PowerPoint COM automation is available

Write-Host "Testing PowerPoint COM Automation..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    # Test 1: Can we load the PowerPoint COM assembly?
    Write-Host "Test 1: Loading PowerPoint COM Assembly..." -ForegroundColor Yellow
    Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
    Write-Host "✓ PowerPoint COM Assembly loaded successfully" -ForegroundColor Green

    # Test 2: Can we create PowerPoint application object?
    Write-Host "Test 2: Creating PowerPoint Application Object..." -ForegroundColor Yellow
    $app = New-Object -ComObject powerpoint.application
    Write-Host "✓ PowerPoint Application created successfully" -ForegroundColor Green
    Write-Host "  PowerPoint Version:" $app.Version -ForegroundColor Gray

    # Test 3: Can we open a presentation?
    Write-Host "Test 3: Testing Presentation Open..." -ForegroundColor Yellow
    $testFile = "G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"

    if (Test-Path $testFile) {
        Write-Host "  Test file found: $testFile" -ForegroundColor Gray
        try {
            $pres = $app.Presentations.Open($testFile, $true, $false, $false)
            Write-Host "✓ Presentation opened successfully" -ForegroundColor Green
            Write-Host "  Slides:" $pres.Slides.Count -ForegroundColor Gray
            $pres.Close()
            Write-Host "✓ Presentation closed successfully" -ForegroundColor Green
        } catch {
            Write-Host "✗ Failed to open presentation:" $_.Exception.Message -ForegroundColor Red
        }
    } else {
        Write-Host "✗ Test file not found: $testFile" -ForegroundColor Red
    }

    # Test 4: Can we create video?
    if (Test-Path $testFile) {
        Write-Host "Test 4: Testing Video Creation..." -ForegroundColor Yellow
        try {
            $outputTest = "G:\Shared drives\compressor\compressed\test_output.mp4"
            $pres = $app.Presentations.Open($testFile, $true, $false, $false)

            Write-Host "  Starting video creation (this may take 30-60 seconds)..." -ForegroundColor Gray
            $pres.CreateVideo($outputTest)

            # Wait for completion with timeout
            $timeout = 120  # 2 minutes
            $elapsed = 0
            $videoDone = [Microsoft.Office.Interop.PowerPoint.PpMediaTaskStatus]::ppMediaTaskStatusDone

            while ($pres.CreateVideoStatus -ne $videoDone -and $elapsed -lt $timeout) {
                Start-Sleep -Seconds 5
                $elapsed += 5
                Write-Host "  Progress: $($pres.CreateVideoStatus.ToString()) ($elapsed seconds elapsed)" -ForegroundColor Gray
            }

            if ($pres.CreateVideoStatus -eq $videoDone) {
                Write-Host "✓ Video created successfully" -ForegroundColor Green

                if (Test-Path $outputTest) {
                    $size = (Get-Item $outputTest).Length
                    Write-Host "  Output file size: $size bytes" -ForegroundColor Gray
                } else {
                    Write-Host "✗ Output file not created" -ForegroundColor Red
                }
            } else {
                Write-Host "✗ Video creation timed out after $timeout seconds" -ForegroundColor Red
            }

            $pres.Close()
        } catch {
            Write-Host "✗ Video creation failed:" $_.Exception.Message -ForegroundColor Red
        }
    }

    # Clean up
    $app.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✓ PowerPoint COM Automation is working!" -ForegroundColor Green

} catch {
    Write-Host "✗ PowerPoint COM Automation Failed:" $_.Exception.Message -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Common solutions:" -ForegroundColor Yellow
    Write-Host "1. Install Microsoft PowerPoint (part of Microsoft Office)" -ForegroundColor White
    Write-Host "2. Repair Office installation: Control Panel → Programs → Microsoft Office → Repair" -ForegroundColor White
    Write-Host "3. Ensure no PowerPoint instances are running" -ForegroundColor White
    Write-Host "4. Run as Administrator if getting permission errors" -ForegroundColor White
}
