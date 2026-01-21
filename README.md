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
# One-click installation (Windows)
irm https://nyjc.app/filesqueeze/install | iex

# Generate configuration
poetry run python -m filesqueeze init-config

# Edit configuration
nano filesqueeze.toml

# Start watching for files
poetry run python -m filesqueeze watch
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

FileSqueeze supports three installation methods:

### Method 1: One-Click Installer (Recommended)

**Best for:** Non-technical users who want to get started quickly

#### Windows

```powershell
# Download and run installer
irm https://nyjc.app/filesqueeze/install | iex

# Or download and run manually
curl -o install.ps1 https://nyjc.app/filesqueeze/install
.\install.ps1
```

**Installer options:**
```powershell
# Custom installation directory
.\install.ps1 -InstallDir "C:\FileSqueeze"

# Force reinstall
.\install.ps1 -Force

# Skip dependency installation (faster)
.\install.ps1 -SkipDeps
```

#### Linux

```bash
# Download and run installer
curl -sSL https://nyjc.app/filesqueeze/install | bash

# Or download and run manually
wget https://nyjc.app/filesqueeze/install -O install.sh
chmod +x install.sh
./install.sh
```

**Installer options:**
```bash
# Custom installation directory
./install.sh --install-dir ~/FileSqueeze

# Force reinstall
./install.sh --force

# Skip dependency installation
./install.sh --skip-deps
```

**What the installer does:**
- ✅ Checks for Python 3.11+
- ✅ Installs Poetry (dependency manager) if needed
- ✅ Clones FileSqueeze repository
- ✅ Installs all dependencies
- ✅ Detects FFmpeg, Ghostscript, Tesseract paths
- ✅ Generates configuration file with detected paths
- ✅ Creates desktop shortcut (Windows)
- ✅ Creates start scripts
- ✅ Creates systemd service file (Linux)

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
# Download from https://ffmpeg.org/download.html
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
# Download from https://www.ghostscript.com/download.html
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
# Download from https://github.com/UB-Mannheim/tesseract/wiki
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
poetry run python -m filesqueeze service

# Install auto-start on boot (Windows)
poetry run python -m filesqueeze service-install

# Check installation status
poetry run python -m filesqueeze service-status

# Uninstall auto-start
poetry run python -m filesqueeze service-uninstall
```

#### Detect Binaries

```bash
# Check if FFmpeg, Ghostscript, and Tesseract are detected
poetry run python -m filesqueeze detect
```

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
poetry run python -m filesqueeze service-uninstall

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
filesqueeze-service-uninstall

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
