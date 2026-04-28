# FileSqueeze pre-commit hook (Windows PowerShell)
# Runs smoke tests to ensure commits don't break critical system functionality

$ErrorActionPreference = "Stop"

Write-Host "🔥 Running FileSqueeze smoke tests..." -ForegroundColor Yellow

# Run smoke tests with quiet output
$process = Start-Process -FilePath "python" -ArgumentList "-m", "pytest", "tests/smoke/", "-q" -Wait -PassThru -NoNewWindow

if ($process.ExitCode -eq 0) {
    Write-Host "✅ Smoke tests passed - commit approved" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Smoke tests failed - commit rejected" -ForegroundColor Red
    Write-Host ""
    Write-Host "Smoke tests check for critical system issues that users cannot fix themselves."
    Write-Host "Please fix the failing tests before committing."
    Write-Host ""
    Write-Host "Run 'pytest tests/smoke/ -v' to see detailed failure information."
    exit 1
}