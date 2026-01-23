# FileSqueeze Agents - Command Reference

This document documents the proper FileSqueeze commands to use instead of ad-hoc bash/shell commands.

## Available FileSqueeze Commands

### Configuration Management

**Generate user config:**
```powershell
filesqueeze init-config --output "$env:USERPROFILE\.config\filesqueeze\config.toml"
```

**Detect binaries (FFmpeg, Ghostscript, Tesseract):**
```powershell
filesqueeze detect
```

**Run diagnostics:**
```powershell
filesqueeze doctor
```

### Service Management

**Start service with tray icon:**
```powershell
filesqueeze service run
```

**Install auto-start on boot:**
```powershell
filesqueeze service install
```

**Uninstall auto-start:**
```powershell
filesqueeze service uninstall
```

**Check service status:**
```powershell
filesqueeze service status
```

### File Processing

**Compress a single file:**
```powershell
filesqueeze compress <input_file>
```

**Batch process directory:**
```powershell
filesqueeze scan <input_dir> <output_dir>
```

**Watch directory for new files:**
```powershell
filesqueeze watch <input_dir> <output_dir>
```

---

## Agent Usage Guidelines

### ✅ DO: Use FileSqueeze Commands

**Generate config instead of manual creation:**
```powershell
# GOOD - Use filesqueeze init-config
filesqueeze init-config --output "$env:USERPROFILE\.config\filesqueeze\config.toml"

# BAD - Don't manually create config
New-Item -ItemType Directory -Path "$env:USERPROFILE\.config\filesqueeze" -Force
```

**Use service commands instead of direct python execution:**
```powershell
# GOOD - Use filesqueeze service command
filesqueeze service run

# BAD - Don't run python directly
python -m filesqueeze service run
```

**Use filesqueeze doctor for diagnostics:**
```powershell
# GOOD - Use built-in diagnostics
filesqueeze doctor

# BAD - Don't manually check paths
Test-Path "C:\Program Files\ffmpeg\bin\ffmpeg.exe"
```

### ❌ DON'T: Ad-Hoc Commands

**Don't manually create directories:**
```powershell
# BAD - Don't do this
New-Item -ItemType Directory -Path "$env:USERPROFILE\FileSqueeze\upload" -Force

# GOOD - Let install.ps1 handle it, or use init-config
```

**Don't manually stop processes (use uninstall script):**
```powershell
# BAD - Don't manually kill processes
taskkill /F /IM filesqueeze.exe

# GOOD - Use uninstall script for clean removal
powershell -Command "echo Y | .\uninstall.ps1"
```

**Don't use pip directly (use install/uninstall scripts):**
```powershell
# BAD - Don't use pip directly
pip install filesqueeze
pip uninstall filesqueeze -y

# GOOD - Use PowerShell scripts
.\install.ps1
powershell -Command "echo Y | .\uninstall.ps1"
```

---

## Build and Install Workflow

### For Development (Poetry)

**When making code changes to FileSqueeze:**

1. **Stop service (if running):**
   ```powershell
   powershell -Command "echo Y | .\uninstall.ps1"
   ```

2. **Build package:**
   ```powershell
   poetry build --quiet
   ```

3. **Reinstall:**
   ```powershell
   .\install.ps1
   ```

4. **Test:**
   ```powershell
   filesqueeze service run
   ```

**Why this workflow?**
- `uninstall.ps1` properly stops processes and cleans up
- `install.ps1` builds the package AND installs it
- Scripts handle all the edge cases (process locks, permissions, etc.)
- Prevents "file in use" errors

### For Testing

**Run integration tests:**
```powershell
# All tests
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_invariants.py -v

# Run in isolation (for mutex tests)
pytest tests/integration/test_single_instance.py -v
```

**Run unit tests:**
```powershell
pytest tests/ -v
```

---

## Common Scenarios

### Scenario 1: User wants to change directory paths

**Option A - Use init-config to regenerate:**
```powershell
filesqueeze init-config --output "$env:USERPROFILE\.config\filesqueeze\config.toml"
# Then edit the file to change paths
```

**Option B - Edit existing config directly:**
```powershell
notepad "$env:USERPROFILE\.config\filesqueeze\config.toml"
```

**Option C - Use environment variables (highest priority):**
```powershell
$env:FILESQUEEZE_INPUT_DIR = "G:/Shared drives/compressor/upload"
$env:FILESQUEEZE_OUTPUT_DIR = "G:/Shared drives/compressor/compressed"
filesqueeze service run
```

### Scenario 2: Service won't start

**Use diagnostics:**
```powershell
filesqueeze doctor
```

This will check:
- Python installation
- Required modules
- Binary paths (FFmpeg, Ghostscript, Tesseract)
- Configuration files
- Directory permissions

### Scenario 3: Need to check configuration

**View current config:**
```powershell
notepad "$env:USERPROFILE\.config\filesqueeze\config.toml"
```

**Regenerate from defaults:**
```powershell
filesqueeze init-config --output "$env:USERPROFILE\.config\filesqueeze\config.toml" --force
```

---

## Quick Reference

| Task | Command |
|------|--------|
| Generate config | `filesqueeze init-config` |
| Detect binaries | `filesqueeze detect` |
| Run diagnostics | `filesqueeze doctor` |
| Start service | `filesqueeze service run` |
| Install auto-start | `filesqueeze service install` |
| Uninstall auto-start | `filesqueeze service uninstall` |
| Compress file | `filesqueeze compress <file>` |
| Scan directory | `filesqueeze scan <input> <output>` |
| Watch directory | `filesqueeze watch <input> <output>` |

---

## Installation Scripts Reference

### install.ps1
**Purpose**: System-wide installation with auto-detection

**What it does:**
- Checks Python 3.11+ installation
- Builds package with Poetry
- Installs system-wide with pip
- Creates Start Menu shortcuts
- Generates user config
- Detects FFmpeg, Ghostscript, Tesseract
- Creates default directories

**Usage:**
```powershell
.\install.ps1
```

### uninstall.ps1
**Purpose**: Clean removal of FileSqueeze

**What it does:**
- Stops all FileSqueeze processes
- Removes Start Menu shortcuts
- Uninstalls package
- Preserves user config and logs

**Usage:**
```powershell
powershell -Command "echo Y | .\uninstall.ps1"
```

---

## Important Notes

1. **Always use FileSqueeze commands** - They handle edge cases properly
2. **Never use pip directly** - Use install.ps1/uninstall.ps1 instead
3. **Config location** - User config at `~/.config/filesqueeze/config.toml` is single source of truth
4. **Tilde expansion** - Tilde (`~`) in config files is expanded automatically at runtime
5. **Environment variables** - Provide highest priority override for configuration

---

## Examples

### Example 1: First-time setup
```powershell
# Install FileSqueeze
.\install.ps1

# Verify installation
filesqueeze doctor

# Start service
filesqueeze service run
```

### Example 2: After code changes
```powershell
# Uninstall old version
powershell -Command "echo Y | .\uninstall.ps1"

# Rebuild and reinstall (install.ps1 handles build)
.\install.ps1

# Test
filesqueeze service run
```

### Example 3: Configure for network drives
```powershell
# Generate config
filesqueeze init-config --output "$env:USERPROFILE\.config\filesqueeze\config.toml"

# Edit to use network drives
notepad "$env:USERPROFILE\.config\filesqueeze\config.toml"
# Change input/output to network paths

# Restart service to pick up new config
filesqueeze service run
```

---

**Last Updated**: 2025-01-23
**FileSqueeze Version**: 0.1.0
