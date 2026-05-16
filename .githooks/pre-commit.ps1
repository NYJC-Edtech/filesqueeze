# FileSqueeze pre-commit hook (Windows PowerShell)
# Runs formatting, type checking and smoke tests to ensure commits don't break functionality

$ErrorActionPreference = "Stop"

# Ensure we're in the project root where pyproject.toml is located
$projectRoot = git rev-parse --show-toplevel
Set-Location $projectRoot

Write-Host "🎨 Auto-formatting with Ruff..." -ForegroundColor Yellow

# Auto-format all files using poetry to ensure config is picked up
& poetry run ruff format .

Write-Host "🔧 Auto-fixing Ruff issues (including line length where possible)..." -ForegroundColor Yellow

# Auto-fix issues where possible, including line length violations that can be fixed
& poetry run ruff check . --fix --exit-zero

Write-Host "🔍 Running Ruff type checking..." -ForegroundColor Yellow

# Run ruff type checking using poetry to ensure config is picked up
# Note: We don't use --select ANN to allow the ignore rules in pyproject.toml to work
$process = Start-Process -FilePath "poetry" -ArgumentList "run", "ruff", "check", "." -Wait -PassThru -NoNewWindow

if ($process.ExitCode -eq 0) {
    Write-Host "✅ Type checking passed" -ForegroundColor Green
} else {
    Write-Host "❌ Type checking failed - commit rejected" -ForegroundColor Red
    Write-Host ""
    Write-Host "Ruff found type annotation issues. Please fix them before committing."
    Write-Host "Run 'poetry run ruff check .' for details, or 'poetry run ruff check . --fix' to auto-fix."
    exit 1
}

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