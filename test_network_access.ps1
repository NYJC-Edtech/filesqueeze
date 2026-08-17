# Test network drive access from current PowerShell context
Write-Host "Testing network drive access..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Can we access the G: drive?
Write-Host "Test 1: Can we access G: drive?" -ForegroundColor Yellow
if (Test-Path "G:\") {
    Write-Host "[OK] G: drive is accessible" -ForegroundColor Green
} else {
    Write-Host "[FAIL] G: drive is not accessible" -ForegroundColor Red
    Write-Host "  This means the network drive isn't mapped in this context" -ForegroundColor Yellow
    exit 1
}

# Test 2: Can we access the specific input directory?
Write-Host "Test 2: Can we access input directory?" -ForegroundColor Yellow
$inputDir = "G:\Shared drives\compressor\upload"
if (Test-Path $inputDir) {
    Write-Host "[OK] Input directory accessible: $inputDir" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Cannot access: $inputDir" -ForegroundColor Red
    exit 1
}

# Test 3: Can we access the specific file?
Write-Host "Test 3: Can we access the PPTX file?" -ForegroundColor Yellow
$testFile = "G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"
if (Test-Path $testFile) {
    Write-Host "[OK] PPTX file accessible: $testFile" -ForegroundColor Green
    $file = Get-Item $testFile
    Write-Host "  Size: $([math]::Round($file.Length / 1MB, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "[FAIL] Cannot access: $testFile" -ForegroundColor Red
    exit 1
}

# Test 4: Can we access the output directory?
Write-Host "Test 4: Can we access output directory?" -ForegroundColor Yellow
$outputDir = "G:\Shared drives\compressor\compressed"
if (Test-Path $outputDir) {
    Write-Host "[OK] Output directory accessible: $outputDir" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Cannot access: $outputDir" -ForegroundColor Red
    exit 1
}

# Test 5: Try to create a test file in output directory?
Write-Host "Test 5: Can we write to output directory?" -ForegroundColor Yellow
try {
    $testOutput = "G:\Shared drives\compressor\compressed\test_write.txt"
    "Test file" | Out-File -FilePath $testOutput -Force
    Write-Host "[OK] Can write to output directory" -ForegroundColor Green
    Remove-Item $testOutput -Force
} catch {
    Write-Host "[FAIL] Cannot write to output directory: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] All drive access tests passed!" -ForegroundColor Green
Write-Host "The issue is specifically with PowerPoint COM, not drive access." -ForegroundColor Yellow
