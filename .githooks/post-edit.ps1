# FileSqueeze post-edit hook (Windows PowerShell)
# Auto-formats Python files using ruff after editing

param(
    [Parameter(Position=0)]
    [string]$FilePath
)

# Only process Python files
if ($FilePath -like "*.py") {
    Write-Host "🎨 Auto-formatting $FilePath with ruff..." -ForegroundColor Yellow
    & ruff format $FilePath
    Write-Host "✅ Formatting complete" -ForegroundColor Green
}