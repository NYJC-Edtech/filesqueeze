# FileSqueeze System Uninstaller for Windows
# Removes Start Menu shortcuts and uninstalls FileSqueeze
# Run with: .\uninstall-system.ps1

$ErrorActionPreference = "Stop"

# Set UTF-8 encoding for proper character display
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Configuration
$StartMenuFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\FileSqueeze"
$UserConfigDir = "$env:USERPROFILE\.config\filesqueeze"

Write-Host ""
Write-Host ("=" * 70)
Write-Host "FileSqueeze Uninstaller" -ForegroundColor Cyan
Write-Host ("=" * 70)
Write-Host ""

# Confirm uninstallation
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  • Remove Start Menu shortcuts" -ForegroundColor Yellow
Write-Host "  • Uninstall FileSqueeze package" -ForegroundColor Yellow
Write-Host "  • Keep user configuration and logs" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Continue with uninstallation? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Uninstall cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# Stop FileSqueeze if running
Write-Host "[1/4] Stopping FileSqueeze service..." -ForegroundColor Cyan
try {
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*filesqueeze*" -or $_.Path -like "*filesqueeze*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "      Service stopped" -ForegroundColor Green
} catch {
    Write-Host "      No running service found" -ForegroundColor Yellow
}

# Remove Start Menu shortcuts
Write-Host ""
Write-Host "[2/4] Removing Start Menu shortcuts..." -ForegroundColor Cyan
if (Test-Path $StartMenuFolder) {
    Remove-Item -Path $StartMenuFolder -Recurse -Force
    Write-Host "      Shortcuts removed" -ForegroundColor Green
} else {
    Write-Host "      No shortcuts found" -ForegroundColor Yellow
}

# Uninstall FileSqueeze package
Write-Host ""
Write-Host "[3/4] Uninstalling FileSqueeze package..." -ForegroundColor Cyan
try {
    python -m pip uninstall filesqueeze -y --quiet
    Write-Host "      Package uninstalled" -ForegroundColor Green
} catch {
    Write-Host "      Failed to uninstall package" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "[4/4] Uninstallation complete!" -ForegroundColor Green
Write-Host ""
Write-Host ("=" * 70)
Write-Host "Uninstallation Summary" -ForegroundColor Cyan
Write-Host ("=" * 70)
Write-Host ""
Write-Host "Removed:" -ForegroundColor Yellow
Write-Host "  • Start Menu shortcuts" -ForegroundColor Yellow
Write-Host "  • FileSqueeze package" -ForegroundColor Yellow
Write-Host ""
Write-Host "Preserved:" -ForegroundColor Green
Write-Host "  • User configuration: $UserConfigDir" -ForegroundColor Green
Write-Host "  • Logs: G:\Shared drives\compressor\logs" -ForegroundColor Green
Write-Host "  • Config backup: G:\Shared drives\compressor\config" -ForegroundColor Green
Write-Host ""
Write-Host "To completely remove FileSqueeze, manually delete:" -ForegroundColor Yellow
Write-Host "  • $UserConfigDir" -ForegroundColor Yellow
Write-Host "  • G:\Shared drives\compressor\logs" -ForegroundColor Yellow
Write-Host "  • G:\Shared drives\compressor\config" -ForegroundColor Yellow
Write-Host ""
