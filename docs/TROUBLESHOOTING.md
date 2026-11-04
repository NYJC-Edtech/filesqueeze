# Troubleshooting

This guide covers common issues and their solutions.

## Quick Diagnosis

Run the built-in diagnostic tool to check your installation:

```bash
poetry run python -m filesqueeze doctor
```

This will check:
- Python version
- Required Python modules
- External binaries (FFmpeg, Ghostscript, Tesseract) — resolved exactly like at compression time, so configured paths are honored and validated, and each `[OK]` line says whether the binary came from your config or auto-detection
- Configuration files (reports which config files were loaded)
- Directory permissions
- Auto-start configuration (Windows)

The doctor command provides specific fix suggestions for any issues found.

When a compression failure is caused by a missing binary, the log carries a single parseable line instead of a traceback — grep it for `binary_not_found:` (`binary_not_found: <name> (<reason>; searched: <where>)`).

When a binary path resolves but cannot be launched, the error names the path instead of a bare `WinError 2`: `<Tool> could not be launched: '<path>' — <reason>. Check that the configured binary path points at the executable itself.`

Failed jobs also show an inline **Error details** button in the status window's Processed Files list. The dialog displays the captured diagnostics, and **Copy details** puts a support-ready report (version, platform, file, error, traceback) on the clipboard — paste it when reporting an issue.

### The Compress a File dialog freezes on Browse

Native Windows pickers block while enumerating the folder they start in. If that
folder lives on a cloud mount (Google Drive shared drive, OneDrive) whose sync
client is stalled, or on an unplugged removable drive, the picker never paints
and the window ghosts as "(Not Responding)". FileSqueeze avoids this two ways:
the Browse buttons only seed their start location from local internal drives
(remembered local folder → Documents folder → the dialog default), and the tray
runs the dialog as its own process — if a picker ever does stall, closing the
dialog leaves the service untouched.

## Common Issues

### Python Not Found

**Error:** `python: command not found`

**Solution:** Install Python 3.11+ from https://python.org
- Make sure to check "Add Python to PATH" during installation

### Poetry Not Found

**Error:** `poetry: command not found`

**Solution:** Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### FFmpeg Not Found

**Error:** `FFmpeg not found`

**Solution:**
1. Install FFmpeg (see [External Dependencies](README.md#external-dependencies)) — a portable archive works; no installer needed
2. Or set path in `filesqueeze.toml`:
```toml
[ffmpeg]
path = "C:/path/to/ffmpeg.exe"
```

Keep `ffprobe.exe` in the same folder as `ffmpeg.exe` (it ships in every FFmpeg archive) — FileSqueeze uses it for video analysis.

### Ghostscript Not Found

**Error:** `Ghostscript not found`

**Solution:**
1. Install Ghostscript (see [External Dependencies](README.md#external-dependencies))
2. Or set path in `filesqueeze.toml`:
```toml
[document]
ghostscript_path = "C:/path/to/gswin64c.exe"
```

### FileSqueeze Doesn't Start After Reboot

**Check:** auto-start may not be installed. The installer's `-Force` reinstalls (before 0.9.7)
could silently remove the Startup shortcut, and the loss only surfaces at the next reboot.

**Diagnosis:**
```bash
filesqueeze service status    # says whether auto-start is installed
filesqueeze doctor            # warns when auto-start is missing or points at a missing script
```

**Solution:**
```bash
# Current user only (no admin needed)
filesqueeze service install --user-only

# All users (requires an elevated prompt)
filesqueeze service install --system-wide
```

Then reboot to confirm the tray icon comes back on its own.

### Files Not Being Processed

**Check:**
- File extensions are in the `file_detection.extensions` list
- Files meet minimum age requirement (`file_detection.min_age_seconds`)
- Files meet minimum size requirement (`file_detection.min_size_bytes`)

### OCR is Slow

**Solution:**
- Reduce OCR DPI: set `ocr.ocr_dpi = 200` (default is 300)
- Disable OCR: set `ocr.enable_ocr = false`

### Git LFS Warning During Commits

**Error:** `This repository is configured for Git LFS but 'git-lfs' was not found on your path.`

**Solution:** Remove Git LFS configuration (this project doesn't use Git LFS):

```bash
# Remove Git LFS hooks
rm .git/hooks/post-checkout .git/hooks/post-commit .git/hooks/post-merge

# Remove Git LFS configuration
git config --remove-section lfs

# Verify it's gone
git config --list | grep lfs  # Should output nothing
```

## File Detection Issues

### File Not Being Processed

1. **Check file extension**: Is it in the `extensions` list?
2. **Wait longer**: Network drives may take 5-7 minutes
3. **Check the log**: `filesqueeze.log` shows what files are detected
4. **Verify file stability**: Is the file still being uploaded/synced?
5. **Restart the service**: Forces an initial scan of all files

### Old File Being Processed Again

- This is normal behavior for files in the input directory
- Move processed files out of the input directory if you don't want them re-processed
- FileSqueeze removes the original file after successful compression

### File with Wrong Date Not Detected Immediately

- FileSqueeze will still process it, just not immediately via watchdog
- Wait for the periodic poll (every 5 minutes by default)
- Or restart the service to trigger an initial scan

For more information about file detection behavior, see the [File Detection Behavior](README.md#file-detection-behavior) section in the main README.
