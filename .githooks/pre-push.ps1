# FileSqueeze pre-push hook (Windows PowerShell)
# Checks for desynchronized poetry lockfile before pushing

$ErrorActionPreference = "Stop"

Write-Host "🔒 Checking Poetry lockfile synchronization..." -ForegroundColor Yellow

# Check if poetry.lock is out of sync with pyproject.toml
$process = Start-Process -FilePath "poetry" -ArgumentList "lock", "--check" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\poetry-lock-check-output.txt" -RedirectStandardError "$env:TEMP\poetry-lock-check-error.txt"

if ($process.ExitCode -eq 0) {
    Write-Host "✅ Poetry lockfile is synchronized" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Poetry lockfile is out of sync with pyproject.toml" -ForegroundColor Red
    Write-Host ""
    Write-Host "Your pyproject.toml has changed but poetry.lock has not been updated."
    Write-Host "This can cause dependency issues for other developers."
    Write-Host ""
    Write-Host "To fix this, run:"
    Write-Host "  poetry lock"
    Write-Host ""
    Write-Host "Then commit the updated poetry.lock file."
    exit 1
}