#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Stop the running FileSqueeze service.

.DESCRIPTION
    Finds and stops all FileSqueeze Python processes.
    Use this if you need to stop the service without using
    the tray icon.

.EXAMPLE
    .\stop-service.ps1
#>

Write-Host "Stopping FileSqueeze service..." -ForegroundColor Yellow

# Find Python processes running FileSqueeze service
# (name filter so shells whose command text merely mentions these words are never killed)
$processes = Get-WmiObject Win32_Process | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*filesqueeze*service*"
}

if ($processes) {
    foreach ($process in $processes) {
        Write-Host "Stopping process PID $($process.ProcessId)..." -ForegroundColor Red
        Stop-Process -Id $process.ProcessId -Force
    }
    Write-Host "FileSqueeze service stopped." -ForegroundColor Green
} else {
    Write-Host "No FileSqueeze service found running." -ForegroundColor Cyan
}
