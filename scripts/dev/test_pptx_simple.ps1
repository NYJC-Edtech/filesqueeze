# Simple PowerPoint COM diagnostic script
# Run this to test if PowerPoint COM automation is available

Write-Host "Testing PowerPoint COM Automation..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    # Test 1: Load PowerPoint COM assembly
    Write-Host "Test 1: Loading PowerPoint COM Assembly..." -ForegroundColor Yellow
    Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
    Write-Host "[OK] PowerPoint COM Assembly loaded" -ForegroundColor Green

    # Test 2: Create PowerPoint application object
    Write-Host "Test 2: Creating PowerPoint Application..." -ForegroundColor Yellow
    $app = New-Object -ComObject powerpoint.application
    Write-Host "[OK] PowerPoint Application created" -ForegroundColor Green
    Write-Host "  Version: $($app.Version)" -ForegroundColor Gray

    # Test 3: Try to open a presentation
    Write-Host "Test 3: Opening Presentation..." -ForegroundColor Yellow
    $testFile = "G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"

    if (Test-Path $testFile) {
        Write-Host "  Found: $testFile" -ForegroundColor Gray
        try {
            $pres = $app.Presentations.Open($testFile, $true, $false, $false)
            Write-Host "[OK] Presentation opened" -ForegroundColor Green
            Write-Host "  Slides: $($pres.Slides.Count)" -ForegroundColor Gray
            $pres.Close()
            Write-Host "[OK] Presentation closed" -ForegroundColor Green
        } catch {
            Write-Host "[FAIL] Could not open: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "[SKIP] Test file not found: $testFile" -ForegroundColor Yellow
    }

    # Clean up
    $app.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[SUCCESS] PowerPoint COM works!" -ForegroundColor Green

} catch {
    Write-Host "[FAIL] PowerPoint COM Failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "1. Install Microsoft PowerPoint" -ForegroundColor White
    Write-Host "2. Repair Office: Control Panel -> Programs -> Office -> Repair" -ForegroundColor White
    Write-Host "3. Close all PowerPoint instances" -ForegroundColor White
    Write-Host "4. Run as Administrator" -ForegroundColor White
}
