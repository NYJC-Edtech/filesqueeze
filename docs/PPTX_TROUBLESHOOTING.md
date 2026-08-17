# PowerPoint Conversion Error Troubleshooting

## Common PPTX Conversion Failures and Solutions

### 1. PowerPoint Not Installed
**Log Pattern:**
```
PowerShell failed to convert presentation: [filename]
New-Object: Cannot find type [Microsoft.Office.Interop.PowerPoint]
```
**Solution:** Install Microsoft PowerPoint (part of Microsoft Office)

---

### 2. COM Automation Permission Issues
**Log Pattern:**
```
PowerShell failed to convert presentation: [filename]
Exception calling "Open" with "4" argument(s): "Application is not installed"
```
**Solution:** Run FileSqueeze service with appropriate permissions, or ensure PowerPoint is properly registered for COM automation

---

### 3. PowerPoint File Corrupted/Invalid
**Log Pattern:**
```
PowerPoint failed to convert presentation: [filename]
Exception calling "Open" with "4" argument(s): "The file appears to be corrupted"
```
**Solution:** Try opening the file in PowerPoint manually to repair it, or use a backup copy

---

### 4. PowerPoint Busy/Already Running
**Log Pattern:**
```
PowerShell failed to convert presentation: [filename]
Exception calling "Open" with "4" argument(s): "Presentation is already open"
```
**Solution:** Close any open PowerPoint instances, or wait for current operations to complete

---

### 5. Protected View/Security Settings
**Log Pattern:**
```
PowerShell failed to convert presentation: [filename]
Exception calling "Open" with "4" argument(s): "File is in Protected View"
```
**Solution:**
- Lower PowerPoint security settings
- Add the source directory to Trusted Locations
- Enable editing for files from internet

---

### 6. Insufficient Memory/Resources
**Log Pattern:**
```
PowerShell timeout converting presentation: [filename]
```
**Solution:**
- Increase timeout in config: `[processing] timeout_seconds = 3600`
- Close other applications to free memory
- Try converting smaller presentations first

---

### 7. Invalid PowerPoint File Structure
**Log Pattern:**
```
PowerShell failed to convert presentation: [filename]
Exception calling "CreateVideo" with "1" argument(s): "Invalid presentation format"
```
**Solution:** Ensure the file is a valid .pptx file (not .ppt, .pps, etc.)

---

## Getting More Detailed Error Information

### Check Full Log File
```bash
# View the most recent errors
tail -100 ~/.config/filesqueeze/filesqueeze.log | grep -A 10 -B 5 "PowerPoint\|pptx\|presentation"
```

### Enable Debug Logging
Add to your `~/.config/filesqueeze/config.toml`:
```toml
[logging]
level = "DEBUG"
```

### Test PowerPoint Conversion Manually
```powershell
# Test the PowerShell script directly
powershell -ExecutionPolicy Bypass -File "path\to\filesqueeze\bin\pptx2mp4.ps1" -Path "test.pptx" -FilePath "output.mp4"
```

---

## Common Solutions

### Solution 1: Install/Repair PowerPoint
- Ensure Microsoft Office/PowerPoint is properly installed
- Run Office repair if needed: "Control Panel" → "Programs" → "Microsoft Office" → "Change" → "Repair"

### Solution 2: Configure PowerPoint Security
1. Open PowerPoint → File → Options → Trust Center → Trust Center Settings
2. Add your input directory to "Trusted Locations"
3. Disable "Protected View" for trusted locations

### Solution 3: Run with Elevated Permissions
```bash
# Run FileSqueeze service as administrator
powershell -ExecutionPolicy Bypass -Command "Start-Process python -ArgumentList '-m filesqueeze service run' -Verb RunAs"
```

### Solution 4: Increase Timeout
In `~/.config/filesqueeze/config.toml`:
```toml
[processing]
timeout_seconds = 3600  # 1 hour for large presentations

[presentation]
timeout = 3600  # Can also set specifically for presentations
```

---

## Testing if PowerPoint is Available

### Quick PowerShell Test
```powershell
try {
    Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
    $app = New-Object -ComObject powerpoint.application
    Write-Host "PowerPoint COM automation available: YES"
    Write-Host "PowerPoint Version:" $app.Version
    $app.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null
} catch {
    Write-Host "PowerPoint COM automation available: NO"
    Write-Host "Error:" $_.Exception.Message
}
```

### Quick File Test
```powershell
# Test if a specific file can be opened
$testFile = "path\to\your\file.pptx"
try {
    Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
    $app = New-Object -ComObject powerpoint.application
    $pres = $app.Presentations.Open($testFile, $true, $false, $false)
    Write-Host "File can be opened: YES"
    Write-Host "Slides:" $pres.Slides.Count
    $pres.Close()
    $app.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($app) | Out-Null
} catch {
    Write-Host "File can be opened: NO"
    Write-Host "Error:" $_.Exception.Message
}
```
