# Install FileSqueeze git hooks (Windows)

Write-Host "🔧 Installing FileSqueeze git hooks..." -ForegroundColor Yellow

# Copy the hooks to .git/hooks/
Copy-Item -Path ".githooks\pre-commit" -Destination ".git\hooks\pre-commit" -Force
Copy-Item -Path ".githooks\post-edit" -Destination ".git\hooks\post-edit" -Force
Copy-Item -Path ".githooks\pre-push" -Destination ".git\hooks\pre-push" -Force

# Note: Windows Git will automatically make the files executable

Write-Host "✅ Git hooks installed successfully" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Installed hooks:"
Write-Host "  • pre-commit: Ruff type checking + smoke tests"
Write-Host "  • post-edit: Auto-format Python files with ruff"
Write-Host "  • pre-push: Poetry lockfile synchronization check"
Write-Host ""
Write-Host "To test manually:"
Write-Host "  • pytest tests/smoke/ -v"
Write-Host "  • ruff check . --select ANN"
Write-Host "  • poetry lock --check"