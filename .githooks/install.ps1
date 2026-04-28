# Install FileSqueeze pre-commit hooks (Windows)

Write-Host "🔧 Installing FileSqueeze pre-commit hooks..." -ForegroundColor Yellow

# Copy the pre-commit hook to .git/hooks/
Copy-Item -Path ".githooks\pre-commit" -Destination ".git\hooks\pre-commit" -Force

# Note: Windows Git will automatically make the file executable

Write-Host "✅ Pre-commit hooks installed successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Smoke tests will now run automatically before each commit."
Write-Host "To test manually: pytest tests/smoke/ -v"