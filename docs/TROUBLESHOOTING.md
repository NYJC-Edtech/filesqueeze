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
- External binaries (FFmpeg, Ghostscript, Tesseract)
- Configuration files
- Directory permissions

The doctor command provides specific fix suggestions for any issues found.

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
1. Install FFmpeg (see [External Dependencies](README.md#external-dependencies))
2. Or set path in `filesqueeze.toml`:
```toml
[ffmpeg]
path = "C:/path/to/ffmpeg.exe"
```

### Ghostscript Not Found

**Error:** `Ghostscript not found`

**Solution:**
1. Install Ghostscript (see [External Dependencies](README.md#external-dependencies))
2. Or set path in `filesqueeze.toml`:
```toml
[document]
ghostscript_path = "C:/path/to/gswin64c.exe"
```

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
