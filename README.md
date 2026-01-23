# FileSqueeze

Utility package for compressing videos, PDFs, and images using FFmpeg and Ghostscript.

## Features

- **Video Compression**: FFmpeg-based with configurable quality (CRF), presets, and scaling
- **PDF Compression**: Ghostscript-based with quality settings (screen, ebook, printer, prepress)
- **Image Compression**: FFmpeg-based compression with quality control
- **OCR Support**: Add searchable text layer to scanned PDFs using Tesseract
- **Smart PDF Detection**: Automatically detects scanned vs generated PDFs
- **Watch Mode**: Real-time directory monitoring with automatic file processing
- **Service Mode**: Background service with system tray icon (Windows)
- **Auto-Start**: Install as Windows service for automatic startup on boot
- **Batch Processing**: Process entire directories at once
- **Binary Auto-Detection**: Automatically finds FFmpeg, Ghostscript, and Tesseract

## Quick Start

```bash
# System-wide installation (Windows)
cd filesqueeze
.\install.ps1

# Or for development: Poetry installation
.\install-dev.ps1

# Start the service
filesqueeze service run          # System install
# OR
poetry run python -m filesqueeze service run  # Development install
```

---

## Table of Contents

- [Installation](#installation)
  - [Method 1: One-Click Installer](#method-1-one-click-installer-recommended)
  - [Method 2: PyPI Package](#method-2-pypi-package-recommended-for-python-users)
  - [Method 3: Manual Installation](#method-3-manual-installation-for-developers)
- [External Dependencies](#external-dependencies)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)
- [Deployment](#deployment-for-maintainers)

---

## Installation

FileSqueeze supports two installation methods:

### Method 1: System-Wide Installer (Recommended for End Users)

**Best for:** Production use, end users who want `filesqueeze` command available everywhere

#### Prerequisites
- Python 3.11 or later
- FFmpeg (for video/image compression)
- Ghostscript (for PDF compression)
- Tesseract OCR (optional, for scanned PDFs)

#### Installation

```powershell
# Navigate to FileSqueeze directory
cd filesqueeze

# Run system installer
.\install.ps1
```

**What the installer does:**
- ✅ Checks Python 3.11+ installation
- ✅ Builds FileSqueeze package (wheel)
- ✅ Installs system-wide with pip
- ✅ Creates Start Menu shortcuts
- ✅ Generates configuration file
- ✅ Detects FFmpeg, Ghostscript, Tesseract

**After installation:**
```bash
# Command available from anywhere
filesqueeze --help

# Start service
filesqueeze service run

# Install auto-start on boot
filesqueeze service install

# Run diagnostics
filesqueeze doctor
```

### Method 2: Development Installer (For Developers)

**Best for:** Developers working on FileSqueeze code, need editable installation

#### Prerequisites
- Python 3.11 or later
- Poetry (dependency manager)
- FFmpeg, Ghostscript, Tesseract

#### Installation

```powershell
# Navigate to FileSqueeze directory
cd filesqueeze

# Run development installer
.\install-dev.ps1
```

**What the installer does:**
- ✅ Checks Python 3.11+ installation
- ✅ Installs Poetry if needed
- ✅ Installs dependencies in editable mode
- ✅ Detects FFmpeg, Ghostscript, Tesseract
- ✅ Generates configuration file
- ✅ Creates desktop shortcut

**After installation:**
```bash
# Must use poetry run prefix
poetry run python -m filesqueeze --help

# Start service
poetry run python -m filesqueeze service run

# Install auto-start
poetry run python -m filesqueeze service install
```

### Method 2: PyPI Package (Recommended for Python Users)

**Best for:** Python developers and users familiar with pip

```bash
# Install FileSqueeze
pip install filesqueeze

# Generate configuration
filesqueeze-init

# Edit configuration
nano filesqueeze.toml

# Start service
filesqueeze-service
```

**Commands available:**
```bash
filesqueeze              # Main CLI
filesqueeze-compress     # Compress files
filesqueeze-scan         # Batch processing
filesqueeze-watch        # Monitor directory
filesqueeze-service      # Run with tray icon
filesqueeze-init         # Generate config
filesqueeze-detect       # Detect binaries
```

**Update:**
```bash
pip install --upgrade filesqueeze
```

**Uninstall:**
```bash
pip uninstall filesqueeze
```

### Method 3: Manual Installation (For Developers)

**Best for:** Developers who want full control

#### Prerequisites

- Python 3.11 or later
- Git
- Poetry (for dependency management)
- FFmpeg (for video/image compression)
- Ghostscript (for PDF compression)
- Tesseract OCR (optional, for scanned PDFs)

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/yourusername/filesqueeze.git
cd filesqueeze

# 2. Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install

# 4. Generate configuration
poetry run python -m filesqueeze init-config

# 5. Edit configuration
nano filesqueeze.toml

# 6. Test installation
poetry run python -m filesqueeze detect
```

---

## External Dependencies

### Required

#### FFmpeg
**Purpose:** Video and image compression

**Windows:**
```bash
# Download ffmpeg-release-essentials.7z from:
# https://www.gyan.dev/ffmpeg/builds/#release-builds
# Extract to C:\Program Files\ffmpeg
# Add C:\Program Files\ffmpeg\bin to your PATH

# Or use chocolatey:
choco install ffmpeg

# Or use winget:
winget install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

#### Ghostscript
**Purpose:** PDF compression

**Windows:**
```bash
# Download from:
# https://ghostscript.com/releases/index.html
# Or use chocolatey:
choco install ghostscript
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install ghostscript

# Fedora
sudo dnf install ghostscript

# Arch
sudo pacman -S ghostscript
```

### Optional

#### Tesseract OCR
**Purpose:** Add text layer to scanned PDFs

**Windows:**
```bash
# Download from:
# https://tesseract-ocr.com/#download
# Or use chocolatey:
choco install tesseract
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Fedora
sudo dnf install tesseract

# Arch
sudo pacman -S tesseract-ocr
```

---

## Configuration

### Quick Setup

Generate an example configuration file:

```bash
poetry run python -m filesqueeze init-config
```

This creates a `filesqueeze.toml` file with auto-detected binary paths.

### Key Configuration Options

```toml
[directories]
# Where to look for files to compress
input = "G:/Shared drives/compressor/upload"

# Where to save compressed files
output = "G:/Shared drives/compressor/compressed"

[ffmpeg]
# Video quality: lower = better quality, larger file (18-28 recommended)
crf = 28
# Maximum video height (videos taller than this will be downscaled)
max_height = 720

[document]
# PDF quality: "screen" (smallest), "ebook", "printer", "prepress" (largest)
pdf_quality = "printer"

[ocr]
# Enable OCR for scanned PDFs
enable_ocr = true
# OCR language (eng=English, chi_sim=Simplified Chinese)
language = "eng"

[logging]
# Log file location
file = "G:/Shared drives/compressor/logs/filesqueeze.log"
level = "INFO"
```

### Configuration File Locations

FileSqueeze looks for configuration files in this order:

1. **Project config**: `filesqueeze.toml` in your working directory
2. **User config**: `~/.config/filesqueeze/config.toml`
3. **Code defaults**: Built-in defaults

---

## Usage

### Python API

```python
import filesqueeze

# Compress single files
output_path = filesqueeze.make_video('input.mp4')
output_path = filesqueeze.make_pdf('input.pdf')
output_path = filesqueeze.make_image('input.jpg')
```

### CLI Commands

#### Compress Single File

```bash
poetry run python -m filesqueeze compress video.mp4
poetry run python -m filesqueeze compress document.pdf -o compressed.pdf
```

#### Batch Processing

```bash
# Process all files in configured directory
poetry run python -m filesqueeze scan

# Use custom directories
poetry run python -m filesqueeze scan --input ./upload --output ./compressed
```

#### Watch Mode (Continuous Monitoring)

```bash
# Monitor input directory for new files
poetry run python -m filesqueeze watch

# Use custom directories
poetry run python -m filesqueeze watch --input ./upload --output ./compressed
```

#### Service Mode with Tray Icon

```bash
# Run with system tray icon (Windows)
poetry run python -m filesqueeze service run

# Install auto-start on boot (Windows)
poetry run python -m filesqueeze service install

# Check installation status
poetry run python -m filesqueeze service status

# Uninstall auto-start
poetry run python -m filesqueeze service uninstall
```

**Note:** Hyphenated versions (`service-run`, `service-install`, etc.) are still supported for backward compatibility.

#### Detect Binaries

```bash
# Check if FFmpeg, Ghostscript, and Tesseract are detected
poetry run python -m filesqueeze detect
```

---

## File Detection Behavior

### How FileSqueeze Detects New Files

FileSqueeze uses a multi-layered approach to detect and process files:

#### 1. Real-Time File System Events (Watchdog)
- **Immediate detection** when files are added to the input directory
- Uses the `watchdog` library to monitor file system events
- Works best for local drives and well-behaved network drives

#### 2. Periodic Polling (Fallback)
- **Scans every 5 minutes** (configurable via `service.poll_interval`)
- Catches files missed by watchdog events
- Essential for network drives with delayed or unreliable file system events

#### 3. Initial Scan on Startup
- **Scans existing files** when the service starts
- Only processes files older than 5 seconds (to avoid race conditions)
- Prevents re-processing files that were already handled

### File Validation Rules

Before processing, files must meet these criteria:

| Requirement | Default | Description |
|-------------|---------|-------------|
| **File Extension** | `mp4, wmv, avi, mkv, mov, flv, pdf, jpg, jpeg, png, pptx` | Only these file types are processed |
| **Minimum Age** | 5 seconds | Files must be at least this old (prevents processing incomplete uploads) |
| **Minimum Size** | 1 KB | Files smaller than this are skipped |
| **File Stability** | 2 seconds unchanged | File size must remain stable for 2 seconds |

### Understanding File Dates

⚠️ **Important**: FileSqueeze relies on the file system's modification time (`mtime`), not the actual creation time.

**Common Issues:**

1. **Files with old dates**: If you copy a file from last year into the upload folder, it will have last year's modification time. FileSqueeze will still process it because:
   - The initial scan on startup picks it up
   - The periodic polling catches it within 5 minutes

2. **Network drive delays**: On Google Shared Drives, Dropbox, OneDrive, etc.:
   - File system events may be delayed or unreliable
   - The polling mechanism (every 5 minutes) ensures files are eventually processed
   - Files may take up to **5-7 minutes** to be processed (5s age check + 2s stability + polling interval)

3. **Recently modified files**: If you edit a file and save it again:
   - FileSqueeze treats it as a "new" file based on its `mtime`
   - It will be processed again if it's in the input directory

### Configuring File Detection

Edit your `filesqueeze.toml` to adjust detection behavior:

```toml
[file_detection]
# File extensions to process (add/remove as needed)
extensions = ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv', 'pdf', 'jpg', 'jpeg', 'png']

# Minimum file age in seconds (prevents processing incomplete uploads)
min_age_seconds = 5

# Minimum file size in bytes (skip tiny files)
min_size_bytes = 1024

[service]
# Polling interval in seconds (fallback for missed watchdog events)
# Set to 0 to disable polling
poll_interval = 300
```

### Network Drive Considerations

For Google Shared Drives, Dropbox, OneDrive, or other cloud-synced folders:

- ✅ **Keep polling enabled** (default: 300 seconds)
- ✅ **Increase `min_age_seconds`** to 30-60 seconds for slow connections
- ✅ **Expect delays** of 5-7 minutes for file processing
- ❌ **Don't disable polling** - watchdog events are unreliable on network drives

### Troubleshooting File Detection

**Problem**: File not being processed

1. **Check file extension**: Is it in the `extensions` list?
2. **Wait longer**: Network drives may take 5-7 minutes
3. **Check the log**: `filesqueeze.log` shows what files are detected
4. **Verify file stability**: Is the file still being uploaded/synced?
5. **Restart the service**: Forces an initial scan of all files

**Problem**: Old file being processed again

- This is normal behavior for files in the input directory
- Move processed files out of the input directory if you don't want them re-processed
- FileSqueeze removes the original file after successful compression

**Problem**: File with wrong date not detected immediately

- FileSqueeze will still process it, just not immediately via watchdog
- Wait for the periodic poll (every 5 minutes by default)
- Or restart the service to trigger an initial scan

---

## System Invariants

FileSqueeze guarantees these non-negotiable behaviors:

### Service Launch Behavior

**When launched from Start Menu or command line:**
- ✅ System tray icon appears immediately
- ✅ Status window opens automatically to show service status

**Rationale:** Users launching FileSqueeze expect immediate visual feedback that the service is running. The status window shows:
- Service state (running/stopped)
- Input/output directories
- Processing statistics
- Currently processing files

**Implementation:** The `filesqueeze service run` command starts the tray icon AND automatically opens the status window. This ensures:
- Users can immediately see the service is working
- Clear visual confirmation of launch
- Easy access to service status and directories

### Single Instance Enforcement

- Only one FileSqueeze service instance can run at a time
- Attempting to start a second instance displays a helpful error message
- Ensures no conflicts from multiple services watching the same directories

### Singleton Status Window

- Clicking the tray icon repeatedly opens only ONE status window
- If the status window is already open, subsequent clicks bring it to the foreground (TODO: not yet implemented)
- Prevents window clutter from multiple status windows

### Configuration Management

- User configuration file (`~/.config/filesqueeze/config.toml`) is the single source of truth
- Configuration paths (especially `~` home directory) are expanded once at initialization
- Runtime uses absolute paths, no re-expansion on every access

---

## Troubleshooting

### Quick Diagnosis

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
1. Install FFmpeg (see [External Dependencies](#external-dependencies))
2. Or set path in `filesqueeze.toml`:
```toml
[ffmpeg]
path = "C:/path/to/ffmpeg.exe"
```

### Ghostscript Not Found

**Error:** `Ghostscript not found`

**Solution:**
1. Install Ghostscript (see [External Dependencies](#external-dependencies))
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

---

## Uninstallation

### Windows (One-Click Installer)

```powershell
# Uninstall auto-start
poetry run python -m filesqueeze service uninstall

# Remove installation directory
Remove-Item -Recurse -Force "$env:USERPROFILE\FileSqueeze"

# Remove desktop shortcut
Remove-Item "$env:USERPROFILE\Desktop\FileSqueeze.lnk"
```

### Linux (One-Click Installer)

```bash
# Stop and disable systemd service
systemctl --user stop filesqueeze.service
systemctl --user disable filesqueeze.service

# Remove installation directory
rm -rf ~/FileSqueeze

# Remove systemd service file
rm ~/.config/systemd/user/filesqueeze.service
```

### PyPI Package

```bash
# Uninstall auto-start (Windows)
filesqueeze service uninstall

# Uninstall package
pip uninstall filesqueeze

# Remove configuration (optional)
rm filesqueeze.toml
```

---

## Deployment (For Maintainers)

If you're maintaining FileSqueeze and need to deploy the installation system:

### 1. Update Repository URLs

Replace placeholder URLs in install scripts:

**In `install.ps1` (line 11):**
```powershell
[string]$RepoUrl = "https://github.com/YOUR_USERNAME/filesqueeze.git"
```

**In `install.sh` (line 10):**
```bash
REPO_URL="https://github.com/YOUR_USERNAME/filesqueeze.git"
```

### 2. Host Install Scripts

**Option A: Host on website**
```bash
# Upload install.ps1 and install.sh to:
# https://yourdomain.com/filesqueeze/install
```

**Option B: Use GitHub Raw**
```powershell
# Windows
irm https://raw.githubusercontent.com/USERNAME/filesqueeze/main/install.ps1 | iex

# Linux
curl -sSL https://raw.githubusercontent.com/USERNAME/filesqueeze/main/install.sh | bash
```

**Option C: Use GitHub Gist**
- Create a Gist with install.ps1 and install.sh
- Use Gist raw URL for distribution

### 3. Publish to PyPI

```bash
# Build package
poetry build

# Test on TestPyPI first
poetry publish -r test-pypi

# Publish to PyPI (requires API token)
poetry publish
```

### 4. Create GitHub Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0

# Create release on GitHub with:
# - Installation instructions
# - Release notes
```

### Deployment Checklist

- [ ] Update repository URLs in install scripts
- [ ] Upload install scripts to web server/GitHub
- [ ] Test installer on fresh Windows machine
- [ ] Test installer on fresh Linux machine
- [ ] Publish to PyPI (or TestPyPI for testing)
- [ ] Create GitHub release
- [ ] Update documentation with actual URLs
- [ ] Test PyPI installation: `pip install filesqueeze`

---

## Development

See [plans/filesqueeze-implementation-plan.md](../plans/filesqueeze-implementation-plan.md) for implementation details.

See [FILE-LAYOUT.md](FILE-LAYOUT.md) for detailed information about file locations during installation.

## License

MIT License - See LICENSE file for details
