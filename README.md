# FileSqueeze

Utility package for compressing videos, PDFs, and images using FFmpeg, Ghostscript, and Pillow.

## Features

- **Video Compression**: FFmpeg-based with configurable quality (CRF), presets, and scaling
- **PDF Compression**: Ghostscript-based with quality settings (screen, ebook, printer, prepress)
- **Image Compression**: Pillow-based conversion to JPG (quality 88, interlaced/progressive, 4:2:2 chroma subsampling); supports JPG, PNG, BMP, TIFF, WebP, and HEIC input
- **PPTX to Video**: Convert PowerPoint slideshows to MP4 (Windows + PowerPoint; feature-flagged, disables itself where unavailable)
- **OCR Support**: Add searchable text layer to scanned PDFs using Tesseract
- **Smart PDF Detection**: Automatically detects scanned vs generated PDFs
- **Watch Mode**: Real-time directory monitoring with automatic file processing
- **Service Mode**: Background service with system tray icon (Windows)
- **Auto-Start**: Start automatically at login (no admin required)
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
  - [Method 1: System-Wide Installer](#method-1-system-wide-installer-recommended-for-end-users)
  - [Method 2: PyPI Package](#method-2-pypi-package-recommended-for-python-users)
  - [Method 3: Development Installation](#method-3-development-installation-poetry)
  - [Locked-Down Machines](#locked-down-machines-no-installers-no-admin-rights)
- [External Dependencies](#external-dependencies)
- [Configuration](#configuration)
- [Usage](#usage)
- [Uninstallation](#uninstallation)
- [Additional Documentation](#additional-documentation)

---

## Installation

FileSqueeze supports multiple installation methods. The scripts follow [Installation Principles](docs/INSTALLATION_PRINCIPLES.md): robust error handling, PATH refresh, and graceful fallbacks.

### Method 1: System-Wide Installer (Recommended for End Users)

**Best for:** Production use, end users who want `filesqueeze` command available everywhere

#### Prerequisites
- Python 3.11 or later
- FFmpeg (for video compression)
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

### Method 2: PyPI Package (Recommended for Python Users)

**Best for:** Python users who just want `pip install`

```bash
pip install filesqueeze
filesqueeze-init          # Generate configuration, then edit filesqueeze.toml
filesqueeze-service       # Start the service
```

**All commands:** `filesqueeze` (main CLI), `filesqueeze-compress`, `filesqueeze-scan`, `filesqueeze-watch`, `filesqueeze-service`, `filesqueeze-init`, `filesqueeze-detect`

```bash
pip install --upgrade filesqueeze   # Update
pip uninstall filesqueeze           # Uninstall
```

### Method 3: Development Installation (Poetry)

**Best for:** developing FileSqueeze (editable install)

Quick way — the dev installer checks Python, installs Poetry if needed, installs dependencies in editable mode, and generates configuration:

```powershell
.\install-dev.ps1
```

Or manually:

```bash
git clone https://github.com/NYJC-Edtech/filesqueeze.git
cd filesqueeze
curl -sSL https://install.python-poetry.org | python3 -   # if Poetry is missing
poetry install
poetry run python -m filesqueeze init-config
poetry run python -m filesqueeze detect                   # verify binaries
```

With a development install, prefix every command with `poetry run`, e.g. `poetry run python -m filesqueeze service run`.

### Locked-Down Machines (No Installers, No Admin Rights)

FileSqueeze itself is pure Python — installing it never requires running an .exe installer. The only installer-based pieces are the [external binaries](#external-dependencies), and each has an installer-free route:

- **FFmpeg** ships as a portable archive, not an installer: download the `.7z` (gyan.dev) or `.zip` (BtbN) build, extract anywhere, and point the config at it (below). No PATH changes needed.
- **Ghostscript**'s official installer can be opened like an archive with [7-Zip](https://www.7-zip.org/) (*Open archive*), and the extracted folder works standalone.
- **Tesseract** is optional — skip it unless you need OCR for scanned PDFs.

To install FileSqueeze and wire up the extracted binaries:

```powershell
# A .ps1 script, not an installer — per-invocation bypass, no admin needed
powershell -ExecutionPolicy Bypass -File .\install.ps1

# Auto-start without admin
python -m filesqueeze service install --user-only
```

Configured binary paths take priority over auto-detection, so the binaries don't need to be on PATH or in a standard location — set them in `~/.config/filesqueeze/config.toml`:

```toml
[ffmpeg]
path = "C:/Users/you/FileSqueeze/bin/ffmpeg/bin/ffmpeg.exe"  # keep ffprobe.exe alongside

[document]
ghostscript_path = "C:/Users/you/FileSqueeze/bin/gs/bin/gswin64c.exe"
```

Verify with `python -m filesqueeze detect` (where each binary was found) and `python -m filesqueeze doctor` (full diagnostic, including feature availability).

> If policy blocks *running* any .exe from user-writable folders (AppLocker default rules do), portable binaries won't start either — ask IT to install or whitelist `python.exe`, `ffmpeg.exe`, and `gswin64c.exe` rather than working around it.

---

## External Dependencies

### Required

#### FFmpeg
**Purpose:** Video compression (image compression uses Pillow, no external binary needed)

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

> Keep `ffprobe.exe` alongside `ffmpeg.exe` — both ship in every archive, and
> FileSqueeze uses ffprobe for video analysis.

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

No installer handy? The .exe installer can be opened as an archive with
7-Zip (*Open archive*) — the extracted folder works standalone.
[Locked-down machines](#locked-down-machines-no-installers-no-admin-rights) covers this in context.

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

#### Microsoft PowerPoint (Windows only)
**Purpose:** Convert PPTX slideshows to MP4 video (drives PowerPoint via COM automation)

Only needed for PowerPoint files — no download here; PowerPoint must already be installed on the machine (e.g. via Microsoft 365). Where PowerPoint isn't available, the `pptx_to_video` feature disables itself automatically (see `[features]` under [Configuration](#configuration)), slideshow files are skipped, and `filesqueeze doctor` reports it.

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
# Tilde (~) will be expanded to your home directory
input = "~/FileSqueeze/upload"

# Where to save compressed files
output = "~/FileSqueeze/compressed"

[ffmpeg]
# Video quality: lower = better quality, larger file (18-28 recommended)
crf = 28
# Maximum video height (videos taller than this will be downscaled)
max_height = 720

[document]
# PDF quality: "screen" (smallest), "ebook", "printer", "prepress" (largest)
pdf_quality = "printer"

# Image compression (output is JPG: quality 88, interlaced, 4:2:2)
image_quality = 88
convert_to_jpeg = true
jpeg_progressive = true
jpeg_subsampling = "4:2:2"
jpeg_flatten_background = "#ffffff"

[ocr]
# Enable OCR for scanned PDFs
enable_ocr = true
# OCR language (eng=English, chi_sim=Simplified Chinese)
language = "eng"

[features]
# Feature flags for optional capabilities. Platform-restricted features are
# disabled automatically when the OS cannot run them (e.g. on Linux),
# regardless of the setting here. Run `python -m filesqueeze doctor` to
# see why a feature is unavailable.
# Convert PPTX slideshows to MP4 video (requires Windows + PowerPoint)
pptx_to_video = true

[logging]
# Log file location (tilde will be expanded)
file = "~/.config/filesqueeze/filesqueeze.log"
level = "INFO"
```

**Environment Variables**

You can override configuration using environment variables (highest priority):

```bash
export FILESQUEEZE_INPUT_DIR="/path/to/input"
export FILESQUEEZE_OUTPUT_DIR="/path/to/output"
export FILESQUEEZE_LOG_FILE="/path/to/filesqueeze.log"
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

### Image Compression

Images are compressed with Pillow (no FFmpeg needed) and always target JPG
output at quality 88, interlaced (progressive), with 4:2:2 chroma subsampling.

**Accepted input formats:** `jpg`, `jpeg`, `png`, `bmp`, `tif`, `tiff`, `webp`, `heic`, `heif`

| Input | Behavior |
|-------|----------|
| JPG / JPEG | Re-encoded at the target settings; the original is kept if the re-encode isn't smaller |
| PNG / BMP / TIFF | Converted to JPG; the original is kept (with its extension) if the JPG would be larger |
| WebP / HEIC | Always converted to JPG, even when the result is larger (chosen for compatibility) |

Additional rules that apply to every image:

- Transparency is flattened onto a white background (`jpeg_flatten_background`)
- EXIF orientation is applied so rotated photos come out upright
- Images larger than `max_image_width` × `max_image_height` (default 1920×1080) are downscaled
- ICC colour profiles are preserved

Converted files are named with a `.jpg` extension (e.g. `photo.png` →
`compressed_photo.jpg`). When an original is kept instead, the output keeps
the original extension.

> HEIC support uses the bundled `pillow-heif` package — no extra install
> needed. Set `convert_to_jpeg = false` to restore the legacy behaviour where
> PNG files stay PNG (handled via FFmpeg).

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
# Default: System-wide for all users (requires admin privileges)
# Falls back to current user if admin privileges not available
poetry run python -m filesqueeze service install

# Install for current user only
poetry run python -m filesqueeze service install --user-only

# Check installation status
poetry run python -m filesqueeze service status

# Uninstall auto-start
poetry run python -m filesqueeze service uninstall
```

**Auto-Start Installation Notes:**
- **System-wide** (default): installs for all users; run from an elevated ("Run as Administrator") prompt
- **User-specific** (`--user-only`): no admin privileges required
- If system-wide installation fails due to permissions, it automatically falls back to user-specific

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
| **File Extension** | `mp4, wmv, avi, mkv, mov, flv, pdf, jpg, jpeg, png, bmp, tif, tiff, webp, heic, heif, pptx` | Only these file types are processed |
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
extensions = ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv', 'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tif', 'tiff', 'webp', 'heic', 'heif']

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

For file detection troubleshooting, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md#file-detection-issues).

---

## System Invariants

FileSqueeze guarantees these behaviors:

### Service Launch Behavior

When launched from the Start Menu or command line, the tray icon appears immediately and the status window opens automatically — showing service state, input/output directories, processing statistics, and currently processing files — so users get immediate visual confirmation that the service is running.

### Single Instance Enforcement

Only one service instance can run at a time; starting a second shows a helpful error. This prevents conflicts from multiple services watching the same directories.

### Singleton Status Window

Clicking the tray icon repeatedly opens only one status window, preventing window clutter.

### Configuration Management

- The user configuration file (`~/.config/filesqueeze/config.toml`) is the single source of truth
- Configuration paths (especially `~` home directory) are expanded once at initialization; runtime uses absolute paths

---

## Troubleshooting

### Installation Issues

If you encounter problems during installation, our scripts provide detailed error messages and recovery instructions. For information about our installation design principles and common issues, see [INSTALLATION_PRINCIPLES.md](docs/INSTALLATION_PRINCIPLES.md).

**Common installation issues:**
- **"Command not found" errors**: Use `python -m filesqueeze` instead of `filesqueeze`
- **Build tool missing**: Install Poetry (`pip install poetry`) or use the fallback build system
- **PATH not updated**: Restart your shell or use `python -m` syntax

### Application Issues

For common issues and solutions, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

For quick diagnosis:
```bash
poetry run python -m filesqueeze doctor
```

---

## Uninstallation

### Windows (System Installer)

```powershell
# Uninstall auto-start
poetry run python -m filesqueeze service uninstall

# Remove installation directory
Remove-Item -Recurse -Force "$env:USERPROFILE\FileSqueeze"

# Remove desktop shortcut
Remove-Item "$env:USERPROFILE\Desktop\FileSqueeze.lnk"
```

### Linux (System Installer)

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

## Additional Documentation

For development, testing, and deployment information, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

For troubleshooting and common issues, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## License

MIT License - See LICENSE file for details
