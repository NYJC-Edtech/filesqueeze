# FileSqueeze System Installer for Windows
# Installs FileSqueeze system-wide using pip
#
# For development installation using Poetry, see install-dev.ps1
#
# Run with: .\install.ps1

param(
    [string]$InstallDir = "$env:USERPROFILE\\FileSqueeze",
    [switch]$Force,
    [switch]$SkipDeps,
    [string]$OverwriteConfig = "prompt"  # "prompt" = ask user, "yes" = always overwrite, "no" = never overwrite
)

$ErrorActionPreference = "Stop"

# Set UTF-8 encoding for proper character display
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Detect if FileSqueeze service is currently running (before uninstall)
# This allows us to restart it after reinstallation
$script:ServiceWasRunning = $false
try {
    $processes = Get-WmiObject Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -like "*filesqueeze*service*"
    }
    if ($processes) {
        $script:ServiceWasRunning = $true
    }
} catch {
    # Ignore detection errors
}

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
Write-Host "  FileSqueeze System Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Status "System-wide installation using pip" "Cyan"
Write-Host "  This installer will:"
Write-Host "  - Check Python 3.11+ installation"
Write-Host "  - Build FileSqueeze package"
Write-Host "  - Install system-wide with pip"
Write-Host "  - Create Start Menu shortcuts"
Write-Host "  - Generate configuration file (preserved if exists)"
Write-Host ""
Write-Host "  Options: -Force (reinstall), -OverwriteConfig yes/no/prompt" -ForegroundColor Gray
Write-Host ""

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Variable to store wheel file path (script-level scope)
$script:WheelFilePath = $null

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

# Get Python installation path for shortcuts
$PythonInstallPath = python -c "import sys, os; print(os.path.dirname(sys.executable))" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error-Status "Failed to detect Python installation path"
}
Write-Host "  Python path: $PythonInstallPath" -ForegroundColor Gray

# Build the package
Write-Status "Building FileSqueeze package..."
try {
    # Check if poetry is available for building
    $poetryAvailable = $null -ne (Get-Command poetry -ErrorAction SilentlyContinue)

    if ($poetryAvailable) {
        Write-Host "  Using Poetry to build..." -ForegroundColor Gray
        poetry build --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Poetry build failed"
        }
    } else {
        Write-Host "  Poetry not found, using Python build module..." -ForegroundColor Gray
        python -m build --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Python build failed. Install Poetry or build module: pip install build"
        }
    }

    # Find the built wheel file
    $script:WheelFilePath = Get-ChildItem -Path "dist" -Filter "*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if (-not $script:WheelFilePath) {
        Write-Error-Status "Failed to find built wheel file in dist/ directory"
    }

    Write-Host "  Built: $($script:WheelFilePath.Name)" -ForegroundColor Gray
} catch {
    Write-Error-Status "Failed to build package. Error: $_`n`nTry running: poetry build"
}

# Install FileSqueeze system-wide
Write-Status "Installing FileSqueeze system-wide..."

# Get the wheel file path (already found during build)
$WheelFile = $script:WheelFilePath

if (-not $WheelFile) {
    Write-Error-Status "Wheel file not found. Please build the package first."
}

$WheelPath = $WheelFile.FullName
Write-Host "  Installing from: $WheelPath" -ForegroundColor Gray

# Temporarily set ErrorActionPreference to allow warnings
$PrevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"

# Uninstall existing version if present (suppress error if not installed)
try {
    & python -m pip show filesqueeze 2>&1 | Out-Null
    $pipExitCode = $LASTEXITCODE

    # pip show returns exit code 0 if package is installed, non-zero if not
    if ($pipExitCode -eq 0) {
        if (-not $Force) {
            $ErrorActionPreference = $PrevErrorAction
            Write-Error-Status "FileSqueeze is already installed.`nUse -Force to reinstall, or uninstall first with: .\uninstall.ps1"
        }
        Write-Host "  Uninstalling existing version..." -ForegroundColor Yellow
        # Use uninstall.ps1 for consistent uninstallation
        & "$ScriptDir\uninstall.ps1" -Force
    }
} finally {
    $ErrorActionPreference = $PrevErrorAction
}

# Install using absolute path
Write-Host "  Installing FileSqueeze..." -ForegroundColor Gray

# Use temporary files to capture output
$TempOut = [System.IO.Path]::GetTempFileName()
$TempErr = [System.IO.Path]::GetTempFileName()

try {
    # Run pip install with --force-reinstall to ensure latest code is used
    Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "--force-reinstall", "$WheelPath" -NoNewWindow -Wait -RedirectStandardOutput $TempOut -RedirectStandardError $TempErr
    $InstallExitCode = $LASTEXITCODE

    # Read the output
    $StdOut = Get-Content $TempOut -Raw
    $StdErr = Get-Content $TempErr -Raw
    $Output = "$StdOut$StdErr"

    # Check if installation actually succeeded by verifying the package is installed
    & python -m pip show filesqueeze > $null 2>&1
    $InstallSuccess = ($LASTEXITCODE -eq 0)

    if ($InstallSuccess) {
        Write-Host "  FileSqueeze installed successfully" -ForegroundColor Gray

        # Refresh PATH environment variable to make filesqueeze command available in current session
        $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  PATH refreshed for current session" -ForegroundColor Gray
    } else {
        Write-Error-Status "Failed to install FileSqueeze. Exit code: $InstallExitCode`nOutput: $Output"
    }
} finally {
    # Clean up temp files
    if (Test-Path $TempOut) {
        Remove-Item $TempOut -Force
    }
    if (Test-Path $TempErr) {
        Remove-Item $TempErr -Force
    }
}

# Verify installation
Write-Status "Verifying installation..."
try {
    $version = filesqueeze --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Command 'filesqueeze' is available" -ForegroundColor Gray
    } else {
        Write-Host "  Warning: Version check failed, but installation may have succeeded" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Warning: Could not verify installation" -ForegroundColor Yellow
}

# Detect binaries
Write-Status "Detecting FFmpeg, Ghostscript, and Tesseract..."
try {
    filesqueeze detect
} catch {
    Write-Host "  Warning: Binary detection had issues" -ForegroundColor Yellow
}

# Generate configuration
Write-Status "Generating configuration file..."
$ConfigPath = "$env:USERPROFILE\\.config\\filesqueeze\\config.toml"
$ConfigExists = Test-Path $ConfigPath

try {
    New-Item -ItemType Directory -Path (Split-Path $ConfigPath) -Force | Out-Null

    if ($ConfigExists) {
        # Config already exists - check what to do based on $OverwriteConfig parameter
        if ($OverwriteConfig -eq "no") {
            Write-Host "  Existing config preserved: $ConfigPath" -ForegroundColor Gray
        } elseif ($OverwriteConfig -eq "yes") {
            filesqueeze init-config --output $ConfigPath --force
            Write-Host "  Configuration overwritten: $ConfigPath" -ForegroundColor Gray
        } else {
            # Default: prompt user
            Write-Host ""
            Write-Host "  Configuration file already exists: $ConfigPath" -ForegroundColor Yellow
            $overwrite = Read-Host "  Overwrite existing config? [y/N]"
            if ($overwrite -eq "Y" -or $overwrite -eq "y") {
                filesqueeze init-config --output $ConfigPath --force
                Write-Host "  Configuration overwritten: $ConfigPath" -ForegroundColor Gray
            } else {
                Write-Host "  Existing config preserved: $ConfigPath" -ForegroundColor Gray
            }
        }
    } else {
        # No existing config - create new one
        filesqueeze init-config --output $ConfigPath --force
        Write-Host "  Configuration created: $ConfigPath" -ForegroundColor Gray
    }
} catch {
    Write-Host "  Warning: Config generation failed. You can create it manually." -ForegroundColor Yellow
}

# Create default input/output directories
Write-Status "Creating default directories..."
$InputDir = Join-Path $env:USERPROFILE "FileSqueeze\upload"
$OutputDir = Join-Path $env:USERPROFILE "FileSqueeze\compressed"
try {
    New-Item -ItemType Directory -Path $InputDir -Force | Out-Null
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "  Created: $InputDir" -ForegroundColor Gray
    Write-Host "  Created: $OutputDir" -ForegroundColor Gray
} catch {
    Write-Host "  Warning: Failed to create default directories" -ForegroundColor Yellow
}

# Create Start Menu folder
$StartMenuFolder = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\FileSqueeze"
Write-Status "Creating Start Menu shortcuts..."
New-Item -ItemType Directory -Path $StartMenuFolder -Force | Out-Null

$WshShell = New-Object -ComObject WScript.Shell

# Shortcut: FileSqueeze
# Use pythonw.exe (windowless Python) to avoid console window
# This allows the tray icon to work properly
$PythonwPath = Join-Path $PythonInstallPath "pythonw.exe"
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\\FileSqueeze.lnk")
$Shortcut.TargetPath = $PythonwPath
$Shortcut.Arguments = "-m filesqueeze service run"
$Shortcut.Description = "Start FileSqueeze compression service with system tray icon"
# Set working directory to user home to avoid using Start Menu folder as cwd
$Shortcut.WorkingDirectory = $env:USERPROFILE
$Shortcut.Save()
Write-Host "  Created: FileSqueeze" -ForegroundColor Gray

# Shortcut: Uninstall FileSqueeze
$Shortcut = $WshShell.CreateShortcut("$StartMenuFolder\\Uninstall FileSqueeze.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$ScriptDir\uninstall.ps1`""
$Shortcut.Description = "Uninstall FileSqueeze"
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Save()
Write-Host "  Created: Uninstall FileSqueeze" -ForegroundColor Gray

# Prompt for auto-start installation
Write-Host ""
Write-Status "Auto-start Configuration" "Cyan"
$autostart = Read-Host "Enable FileSqueeze to start automatically on boot? [Y/n]"
# Empty input (just Enter) defaults to Yes
if ($autostart -eq "" -or $autostart -eq "Y" -or $autostart -eq "y") {
    Write-Host ""
    Write-Host "Installing auto-start..." -ForegroundColor Yellow
    try {
        # Get input/output directories from config
        # If config doesn't exist or can't be read, use default directories
        $inputDir = $null
        $outputDir = $null
        if (Test-Path $ConfigPath) {
            try {
                # Read config to get directories using more robust pattern matching
                $configContent = Get-Content $ConfigPath -Raw -ErrorAction Stop
                # Try different patterns for input (handle [directories], [service], or root level)
                if ($configContent -match '\[directories\]([\s\S]*?)\[.*?\]' -or $configContent -match '\[directories\]([\s\S]*?)$') {
                    $directoriesSection = $matches[1]
                    if ($directoriesSection -match 'input\s*=\s*"([^"]+)"') {
                        $inputDir = $matches[1]
                    }
                } elseif ($configContent -match 'input\s*=\s*"([^"]+)"') {
                    $inputDir = $matches[1]
                } elseif ($configContent -match '\[service\]([\s\S]*?)\[.*?\]' -or $configContent -match '\[service\]([\s\S]*?)$') {
                    $serviceSection = $matches[1]
                    if ($serviceSection -match 'input\s*=\s*"([^"]+)"') {
                        $inputDir = $matches[1]
                    }
                }

                # Try different patterns for output (handle [directories], [service], or root level)
                if ($configContent -match '\[directories\]([\s\S]*?)\[.*?\]' -or $configContent -match '\[directories\]([\s\S]*?)$') {
                    $directoriesSection = $matches[1]
                    if ($directoriesSection -match 'output\s*=\s*"([^"]+)"') {
                        $outputDir = $matches[1]
                    }
                } elseif ($configContent -match 'output\s*=\s*"([^"]+)"') {
                    $outputDir = $matches[1]
                } elseif ($configContent -match '\[service\]([\s\S]*?)\[.*?\]' -or $configContent -match '\[service\]([\s\S]*?)$') {
                    $serviceSection = $matches[1]
                    if ($serviceSection -match 'output\s*=\s*"([^"]+)"') {
                        $outputDir = $matches[1]
                    }
                }
            } catch {
                # If config can't be read, will use defaults
                Write-Host "  Note: Using default directories (config not readable)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  Note: Using default directories (config not found)" -ForegroundColor Yellow
        }

        # Use filesqueeze service install command
        # If input/output not found, command will use defaults from config module
        $cmd = "filesqueeze service install"
        if ($inputDir) { $cmd += " --input `"$inputDir`"" }
        if ($outputDir) { $cmd += " --output `"$outputDir`"" }

        # Log the command for debugging
        Write-Host "  Running: $cmd" -ForegroundColor Gray

        # Try to run the command, with fallback to python -m filesqueeze
        $success = $false
        $output = ""

        try {
            # First try: direct filesqueeze command
            $output = Invoke-Expression $cmd 2>&1
            $exitCode = $LASTEXITCODE

            # Check if command failed due to "not recognized" error
            if ($exitCode -ne 0 -and $output -match "not recognized") {
                throw "Command not found"
            }

            if ($exitCode -eq 0) {
                $success = $true
            }
        } catch {
            # Second try: use python -m filesqueeze
            Write-Host "  filesqueeze command not found, trying python -m filesqueeze..." -ForegroundColor Yellow
            $cmd = $cmd -replace "^filesqueeze", "python -m filesqueeze"
            Write-Host "  Running: $cmd" -ForegroundColor Gray

            $output = Invoke-Expression $cmd 2>&1
            $exitCode = $LASTEXITCODE

            if ($exitCode -eq 0) {
                $success = $true
            }
        }

        if (-not $success) {
            throw "Command failed with exit code $exitCode. Output: $output"
        }

        Write-Host "  Auto-start installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "  Auto-start installation failed:" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "  You can enable auto-start later by running:" -ForegroundColor Yellow
        Write-Host "        filesqueeze service install" -ForegroundColor Gray
    }
} else {
    Write-Host "  Skipped. You can enable auto-start later by running:" -ForegroundColor Gray
    Write-Host "  filesqueeze service install" -ForegroundColor Gray
}

# Restart service if it was running before reinstall
if ($script:ServiceWasRunning) {
    Write-Host ""
    Write-Status "Service was running before reinstall - restarting..." "Yellow"
    try {
        # Start the service in background using pythonw.exe (no console window)
        $PythonwPath = Join-Path $PythonInstallPath "pythonw.exe"
        $processParams = @{
            FilePath = $PythonwPath
            ArgumentList = "-m", "filesqueeze", "service", "run"
            WindowStyle = "Hidden"
        }
        Start-Process @processParams -ErrorAction Stop
        Write-Host "  Service restarted - look for the 'FS' icon in your system tray" -ForegroundColor Gray
    } catch {
        Write-Host "  Note: Could not restart service automatically. Start it manually:" -ForegroundColor Yellow
        Write-Host "        filesqueeze service run" -ForegroundColor Gray
    }
}

# Success message
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "FileSqueeze has been installed system-wide." -ForegroundColor Cyan
Write-Host ""
Write-Host "Start Menu shortcuts created:" -ForegroundColor Yellow
Write-Host "  • FileSqueeze           - Start the service with tray icon"
Write-Host "  • Uninstall FileSqueeze - Remove the application"
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  1. Press Windows key and type: FileSqueeze"
Write-Host "  2. Click 'FileSqueeze'"
Write-Host "  3. Look for the green 'FS' icon in your system tray"
Write-Host "  4. Double-click the tray icon to show status window"
Write-Host ""
Write-Host "Or run from command line:" -ForegroundColor Yellow
Write-Host "  filesqueeze service run"
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Edit: $ConfigPath"
Write-Host "  Set input/output directories"
Write-Host "  Configure log location"
Write-Host ""
Write-Host "Common commands:" -ForegroundColor Yellow
Write-Host "  filesqueeze service run     # Start service with tray icon"
Write-Host "  filesqueeze service install # Install auto-start on boot"
Write-Host "  filesqueeze watch           # Monitor directory (foreground)"
Write-Host "  filesqueeze scan            # Batch process files"
Write-Host "  filesqueeze doctor          # Run diagnostics"
Write-Host "  filesqueeze --help          # Show all commands"
Write-Host ""
Write-Status "To start FileSqueeze:" "Cyan"
Write-Host "  • Press Windows key and type 'FileSqueeze'" -ForegroundColor White
Write-Host "  • Click 'FileSqueeze'" -ForegroundColor White
Write-Host "  • Or open PowerShell/CMD and run: filesqueeze service run" -ForegroundColor White
Write-Host ""
Write-Host "  The service will run in the background with a tray icon." -ForegroundColor Gray
Write-Host "  Right-click the tray icon and select 'Quit' to stop the service." -ForegroundColor Gray
Write-Host ""
Write-Status "Thank you for installing FileSqueeze!" "Cyan"
Write-Host ""
