# FileSqueeze System Installer for Windows
# Installs FileSqueeze system-wide and creates Start Menu shortcuts
#
# For development installation using Poetry, see install-dev.ps1
#
# Run with: .\install.ps1

$ErrorActionPreference = "Stop"

# Configuration
$ProjectDir = "d:\nyjc-edtech\filesqueeze"
$StartMenuFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\FileSqueeze"
$ConfigDir = "G:\Shared drives\compressor\config"
$UserConfigDir = "$env:USERPROFILE\.config\filesqueeze"

Write-Host ""
Write-Host "=" * 70
Write-Host "FileSqueeze System Installer" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Cyan
try {
    $PythonVersion = python --version 2>&1
    $PythonPath = python -c "import sys; print(sys.executable)"
    Write-Host "      Found: $PythonVersion" -ForegroundColor Green
    Write-Host "      Location: $PythonPath" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Install FileSqueeze system-wide
Write-Host ""
Write-Host "[2/6] Installing FileSqueeze system-wide..." -ForegroundColor Cyan
Set-Location $ProjectDir
python -m pip install -e . --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "      FileSqueeze installed successfully" -ForegroundColor Green
} else {
    Write-Host "      ERROR: Failed to install FileSqueeze" -ForegroundColor Red
    exit 1
}

# Create Start Menu folder
Write-Host ""
Write-Host "[3/6] Creating Start Menu folder..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $StartMenuFolder -Force | Out-Null
Write-Host "      Location: $StartMenuFolder" -ForegroundColor Green

# Create shortcuts
Write-Host ""
Write-Host "[4/6] Creating Start Menu shortcuts..." -ForegroundColor Cyan

$WshShell = New-Object -ComObject WScript.Shell

# Shortcut: Start Service
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\Start FileSqueeze Service.lnk")
$Shortcut.TargetPath = $PythonPath
$Shortcut.Arguments = '-m filesqueeze service'
$Shortcut.Description = "Start FileSqueeze background service with system tray icon"
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Save()
Write-Host "      Created: Start FileSqueeze Service" -ForegroundColor Green

# Shortcut: Doctor
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\FileSqueeze Doctor.lnk")
$Shortcut.TargetPath = $PythonPath
$Shortcut.Arguments = '-m filesqueeze doctor'
$Shortcut.Description = "Run FileSqueeze diagnostic tool"
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Save()
Write-Host "      Created: FileSqueeze Doctor" -ForegroundColor Green

# Shortcut: Config Folder
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\Open Configuration Folder.lnk")
$Shortcut.TargetPath = "explorer.exe"
$Shortcut.Arguments = $ConfigDir
$Shortcut.Description = "Open FileSqueeze configuration folder"
$Shortcut.Save()
Write-Host "      Created: Open Configuration Folder" -ForegroundColor Green

# Shortcut: Logs Folder
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\Open Logs Folder.lnk")
$Shortcut.TargetPath = "explorer.exe"
$Shortcut.Arguments = "G:\Shared drives\compressor\logs"
$Shortcut.Description = "Open FileSqueeze logs folder"
$Shortcut.Save()
Write-Host "      Created: Open Logs Folder" -ForegroundColor Green

# Shortcut: Uninstall
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\Uninstall FileSqueeze.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$ProjectDir\uninstall.ps1`""
$Shortcut.Description = "Uninstall FileSqueeze"
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Save()
Write-Host "      Created: Uninstall FileSqueeze" -ForegroundColor Green

# Setup user configuration
Write-Host ""
Write-Host "[5/6] Setting up user configuration..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $UserConfigDir -Force | Out-Null
$ConfigSource = "$ConfigDir\filesqueeze.toml"
$ConfigDest = "$UserConfigDir\config.toml"

if (Test-Path $ConfigSource) {
    Copy-Item -Path $ConfigSource -Destination $ConfigDest -Force
    Write-Host "      Configuration copied from shared drive" -ForegroundColor Green
} else {
    Write-Host "      WARNING: Configuration not found on shared drive" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "[6/6] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "=" * 70
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host ""
Write-Host "Start Menu shortcuts created:" -ForegroundColor Yellow
Write-Host "  • Start FileSqueeze Service   - Start the background service"
Write-Host "  • FileSqueeze Doctor          - Run diagnostics"
Write-Host "  • Open Configuration Folder   - Edit settings"
Write-Host "  • Open Logs Folder            - View logs"
Write-Host "  • Uninstall FileSqueeze       - Remove the application"
Write-Host ""
Write-Host "To start the service:" -ForegroundColor Yellow
Write-Host "  1. Press Windows key"
Write-Host "  2. Type: FileSqueeze"
Write-Host "  3. Click: Start FileSqueeze Service"
Write-Host ""
