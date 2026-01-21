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

Write-Host "Starting FileSqueeze service..." -ForegroundColor Green

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the script directory
Set-Location $ScriptDir

# Start the service in a minimized window
Start-Process -FilePath "cmd" `
    -ArgumentList "/c", "poetry run python -m filesqueeze service" `
    -WindowStyle Minimized `
    -WorkingDirectory $ScriptDir

Write-Host "FileSqueeze service started!" -ForegroundColor Green
Write-Host "Look for the green 'FS' icon in your system tray." -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop the service, right-click the tray icon and select 'Quit'" -ForegroundColor Yellow
