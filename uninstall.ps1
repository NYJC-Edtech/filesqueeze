# FileSqueeze System Uninstaller for Windows
# Removes Start Menu shortcuts and uninstalls FileSqueeze
#
# For development uninstall, manually remove Poetry environment
#
# Run with: .\uninstall.ps1
# Run with: .\uninstall.ps1 -Force to skip confirmation

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Set UTF-8 encoding for proper character display
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Status {
    param([string]$Message, [string]$Color = "Green")
    Write-Host "==> $Message" -ForegroundColor $Color
}

# Configuration
$StartMenuFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\FileSqueeze"
$UserConfigDir = "$env:USERPROFILE\.config\filesqueeze"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FileSqueeze Uninstaller" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Status "Removing FileSqueeze system-wide installation" "Cyan"
Write-Host "  This will:"
Write-Host "  - Stop FileSqueeze service if running"
Write-Host "  - Remove auto-start (if installed)"
Write-Host "  - Remove Start Menu shortcuts"
Write-Host "  - Uninstall FileSqueeze package"
Write-Host "  - Keep user configuration and logs"
Write-Host ""

# Confirm uninstallation (skip if -Force is used)
if (-not $Force) {
    $confirm = Read-Host "Uninstall FileSqueeze? [Y/n]"
    if ($confirm -eq "N" -or $confirm -eq "n") {
        Write-Host ""
        Write-Status "Uninstall cancelled." "Yellow"
        exit 0
    }
}

Write-Host ""

# Stop FileSqueeze if running
Write-Status "Stopping FileSqueeze service..."
try {
    # Stop any Python processes running FileSqueeze
    $processes = Get-WmiObject Win32_Process | Where-Object {
        $_.CommandLine -like "*filesqueeze*service*"
    }

    if ($processes) {
        foreach ($process in $processes) {
            Write-Host "  Stopping process PID $($process.ProcessId)..." -ForegroundColor Gray
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  Service stopped" -ForegroundColor Gray
    } else {
        Write-Host "  No running service found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  No running service found" -ForegroundColor Yellow
}

# Remove auto-start if installed
Write-Status "Removing auto-start..."
try {
    $AutostartScript = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\FileSqueeze.lnk"
    if (Test-Path $AutostartScript) {
        Remove-Item -Path $AutostartScript -Force -ErrorAction SilentlyContinue
        Write-Host "  Auto-start removed" -ForegroundColor Gray
    } else {
        Write-Host "  No auto-start found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Could not remove auto-start" -ForegroundColor Yellow
}

# Remove Start Menu shortcuts
Write-Status "Removing Start Menu shortcuts..."
if (Test-Path $StartMenuFolder) {
    Remove-Item -Path $StartMenuFolder -Recurse -Force
    Write-Host "  Shortcuts removed" -ForegroundColor Gray
} else {
    Write-Host "  No shortcuts found" -ForegroundColor Yellow
}

# Uninstall FileSqueeze package
Write-Status "Uninstalling FileSqueeze package..."
try {
    & python -m pip show filesqueeze 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        python -m pip uninstall filesqueeze -y --quiet
        Write-Host "  Package uninstalled" -ForegroundColor Gray
    } else {
        Write-Host "  Package not installed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Failed to uninstall package" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Uninstallation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Removed:" -ForegroundColor Yellow
Write-Host "  • FileSqueeze service (stopped)"
Write-Host "  • Auto-start (if installed)"
Write-Host "  • Start Menu shortcuts"
Write-Host "  • FileSqueeze package"
Write-Host ""
Write-Host "Preserved:" -ForegroundColor Green
Write-Host "  • User configuration: $UserConfigDir"
Write-Host "  • Logs (check your config for location)"
Write-Host ""
Write-Host "To completely remove FileSqueeze:" -ForegroundColor Yellow
Write-Host "  • Delete user config: $UserConfigDir"
Write-Host "  • Delete logs (see config file for location)"
Write-Host ""
Write-Status "Thank you for using FileSqueeze!" "Cyan"
Write-Host ""
