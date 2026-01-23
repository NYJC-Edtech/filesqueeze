#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start FileSqueeze service in background with system tray icon.

.DESCRIPTION
    Starts the FileSqueeze watch mode service with a system tray icon
    for easy control. The service runs in a minimized window and will
    continue running even after this terminal is closed.

.EXAMPLE
    .\start-service.ps1
#>

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the script directory
Set-Location $ScriptDir

# Check if Poetry is available (development install)
$PoetryAvailable = $null -ne (Get-Command poetry -ErrorAction SilentlyContinue)

if ($PoetryAvailable) {
    # Development install: use poetry
    $Command = "poetry run python -m filesqueeze service run"
} else {
    # System install: use python directly
    $Command = "python -m filesqueeze service run"
}

# Start the service completely hidden (no console window)
$Process = Start-Process -FilePath "powershell" `
    -ArgumentList "-ExecutionPolicy Bypass -Command", $Command `
    -WindowStyle Hidden `
    -WorkingDirectory $ScriptDir `
    -PassThru

# Wait a moment to check if process started successfully
Start-Sleep -Seconds 2

if ($Process.HasExited) {
    Write-Host "ERROR: FileSqueeze service failed to start. Exit code: $($Process.ExitCode)" -ForegroundColor Red
    Write-Host "Try running manually: python -m filesqueeze service run" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "FileSqueeze service started successfully (PID: $($Process.Id))" -ForegroundColor Green
    Write-Host "Look for the green 'FS' icon in your system tray." -ForegroundColor Cyan
}
