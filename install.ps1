# FileSqueeze One-Click Installer for Windows
# Run with: .\install.ps1
# Or download and run: irm https://nyjc.app/filesqueeze/install | iex

param(
    [string]$InstallDir = "$env:USERPROFILE\FileSqueeze",
    [string]$Branch = "main",
    [string]$RepoUrl = "https://github.com/yourusername/filesqueeze.git",
    [switch]$Force,
    [switch]$SkipDeps
)

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "FileSqueeze Installer"

function Write-Status {
    param([string]$Message, [string]$Color = "Green")
    Write-Host "==> $Message" -ForegroundColor $Color
}

function Write-Error-Status {
    param([string]$Message)
    Write-Host "==> ERROR: $Message" -ForegroundColor Red
    exit 1
}

# Welcome message
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FileSqueeze Installer for Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Status "Welcome to FileSqueeze!" "Cyan"
Write-Host "  This installer will:"
Write-Host "  - Check for Python 3.11+"
Write-Host "  - Install Poetry (if needed)"
Write-Host "  - Clone FileSqueeze repository"
Write-Host "  - Install dependencies"
Write-Host "  - Detect FFmpeg, Ghostscript, Tesseract"
Write-Host "  - Generate configuration file"
Write-Host "  - Create desktop shortcut"
Write-Host ""

# Check if installation directory exists
if (Test-Path $InstallDir) {
    if (-not $Force) {
        Write-Error-Status "Installation directory already exists: $InstallDir`nUse -Force to reinstall or remove the directory first."
    }
    Write-Status "Removing existing installation (force reinstall)..." "Yellow"
    Remove-Item -Path $InstallDir -Recurse -Force
}

# Create installation directory
Write-Status "Creating installation directory: $InstallDir"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Set-Location $InstallDir

# Check Python installation
Write-Status "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Gray

    # Check if Python 3.11+
    $versionParts = $pythonVersion -split ' '
    if ($versionParts.Length -ge 2) {
        $version = $versionParts[1].Substring(0, 4)
        $major, $minor = $version.Split('.')
        if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 11)) {
            Write-Error-Status "Python 3.11+ required. Found: $pythonVersion`nPlease install Python 3.11 or later from https://python.org"
        }
    }
} catch {
    Write-Error-Status "Python not found. Please install Python 3.11+ from https://python.org`nMake sure to check 'Add Python to PATH' during installation."
}

# Check Poetry installation
Write-Status "Checking Poetry installation..."
try {
    $poetryVersion = poetry --version 2>&1
    Write-Host "  Found: $poetryVersion" -ForegroundColor Gray
} catch {
    Write-Host "  Poetry not found. Installing..." -ForegroundColor Yellow
    Write-Status "Installing Poetry..."

    # Download Poetry installer
    $poetryInstaller = "$env:TEMP\install-poetry.py"
    Invoke-WebRequest -Uri "https://install.python-poetry.org" -OutFile $poetryInstaller

    # Run Poetry installer
    python $poetryInstaller

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path

    # Verify installation
    try {
        $poetryVersion = poetry --version 2>&1
        Write-Host "  Poetry installed: $poetryVersion" -ForegroundColor Gray
    } catch {
        Write-Error-Status "Poetry installation failed. Please install manually:`n  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
    }

    Remove-Item $poetryInstaller -Force
}

# Clone repository
Write-Status "Cloning FileSqueeze repository..."
try {
    git clone --branch $Branch --depth 1 $RepoUrl "$InstallDir\repo"
    if (-not $?) {
        throw "Git clone failed"
    }
    Set-Location "$InstallDir\repo"
    Write-Host "  Repository cloned successfully" -ForegroundColor Gray
} catch {
    Write-Error-Status "Failed to clone repository. Please check your internet connection and Git installation.`nError: $_"
}

# Install dependencies
if (-not $SkipDeps) {
    Write-Status "Installing dependencies (this may take a few minutes)..."
    try {
        poetry install
        Write-Host "  Dependencies installed successfully" -ForegroundColor Gray
    } catch {
        Write-Error-Status "Failed to install dependencies. Error: $_"
    }
} else {
    Write-Status "Skipping dependency installation (--SkipDeps)" "Yellow"
}

# Detect binaries and generate config
Write-Status "Detecting FFmpeg, Ghostscript, and Tesseract..."
try {
    poetry run python -m filesqueeze detect
} catch {
    Write-Host "  Warning: Binary detection had issues" -ForegroundColor Yellow
}

# Generate configuration
Write-Status "Generating configuration file..."
try {
    poetry run python -m filesqueeze init-config --output "$InstallDir\filesqueeze.toml"
    Write-Host "  Configuration created: $InstallDir\filesqueeze.toml" -ForegroundColor Gray
} catch {
    Write-Host "  Warning: Config generation failed. You can create it manually." -ForegroundColor Yellow
}

# Create desktop shortcut
Write-Status "Creating desktop shortcut..."
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\FileSqueeze.lnk")
    $Shortcut.TargetPath = "poetry"
    $Shortcut.Arguments = "run python -m filesqueeze service"
    $Shortcut.WorkingDirectory = "$InstallDir\repo"
    $Shortcut.Description = "FileSqueeze Compression Service"
    $Shortcut.Save()
    Write-Host "  Desktop shortcut created" -ForegroundColor Gray
} catch {
    Write-Host "  Warning: Could not create desktop shortcut" -ForegroundColor Yellow
}

# Create start scripts
Write-Status "Creating start scripts..."

# Watch mode script
$watchScript = @"
@echo off
title FileSqueeze Watch Mode
cd /d "$InstallDir\repo"
poetry run python -m filesqueeze service
pause
"@
$watchScript | Out-File -FilePath "$InstallDir\start-watch.bat" -Encoding ASCII

# Compress single file script
$compressScript = @"
@echo off
title FileSqueeze - Compress File
cd /d "$InstallDir\repo"
set /p FILE="Enter file path: "
poetry run python -m filesqueeze compress "%FILE%"
pause
"@
$compressScript | Out-File -FilePath "$InstallDir\compress-file.bat" -Encoding ASCII

Write-Host "  Start scripts created in $InstallDir" -ForegroundColor Gray

# Success message
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  1. Double-click 'FileSqueeze' on desktop to start service"
Write-Host "  2. Or run: cd $InstallDir\repo"
Write-Host "             poetry run python -m filesqueeze service"
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Start service:      poetry run python -m filesqueeze service"
Write-Host "  Watch mode:         poetry run python -m filesqueeze watch"
Write-Host "  Compress file:      poetry run python -m filesqueeze compress <file>"
Write-Host "  Batch process:      poetry run python -m filesqueeze scan"
Write-Host "  Install auto-start: poetry run python -m filesqueeze service-install"
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Edit: $InstallDir\filesqueeze.toml"
Write-Host "  Set input/output directories"
Write-Host "  Configure log location"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Edit filesqueeze.toml to configure directories"
Write-Host "  2. Run: poetry run python -m filesqueeze service-install"
Write-Host "  3. Reboot to test auto-start"
Write-Host ""
Write-Status "Thank you for installing FileSqueeze!" "Cyan"
Write-Host ""

# Offer to start service
$start = Read-Host "Start FileSqueeze service now? (Y/N)"
if ($start -eq "Y" -or $start -eq "y") {
    Write-Status "Starting FileSqueeze service..."
    Set-Location "$InstallDir\repo"
    poetry run python -m filesqueeze service
}
