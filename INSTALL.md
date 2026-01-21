# FileSqueeze Installation Guide

FileSqueeze supports three installation methods, from simple one-click installers to standard Python package installation.

## Installation Methods

### Method 1: One-Click Installer (Simple Mode)

**Best for:** Non-technical users who want to get started quickly

#### Windows

```powershell
# Download and run installer
irm https://nyjc.app/filesqueeze/install | iex

# Or download and run manually
curl -o install.ps1 https://nyjc.app/filesqueeze/install
.\install.ps1
```

**What it does:**
- ✅ Checks for Python 3.11+
- ✅ Installs Poetry (if needed)
- ✅ Clones FileSqueeze repository
- ✅ Installs all dependencies
- ✅ Detects FFmpeg, Ghostscript, Tesseract
- ✅ Generates configuration file
- ✅ Creates desktop shortcut
- ✅ Creates start scripts

**Installer options:**
```powershell
# Custom installation directory
.\install.ps1 -InstallDir "C:\FileSqueeze"

# Force reinstall
.\install.ps1 -Force

# Skip dependency installation (faster)
.\install.ps1 -SkipDeps

# Use specific branch
.\install.ps1 -Branch "develop"
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

---

### Method 2: PyPI Package (Controlled Mode)

**Best for:** Python developers, users familiar with pip

#### Installation

```bash
# Install FileSqueeze
pip install filesqueeze

# Or with OCR support
pip install filesqueeze[ocr]

# Or with dev tools
pip install filesqueeze[dev]
```

#### Post-Installation Setup

```bash
# 1. Generate configuration
filesqueeze-init

# 2. Edit configuration
nano filesqueeze.toml

# 3. Detect binaries
filesqueeze-detect

# 4. Install auto-start (Windows only)
filesqueeze-service-install
```

#### Commands

All commands are available as executables:

```bash
filesqueeze compress video.mp4
filesqueeze scan
filesqueeze watch
filesqueeze service
filesqueeze-init
filesqueeze-detect
```

#### Update

```bash
pip install --upgrade filesqueeze
```

#### Uninstall

```bash
pip uninstall filesqueeze
```

---

### Method 3: Manual Installation (Advanced Mode)

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

## Post-Installation Configuration

### 1. Edit Configuration File

Edit `filesqueeze.toml` (generated during installation):

```toml
[directories]
input = "G:/Shared drives/compressor/upload"
output = "G:/Shared drives/compressor/compressed"

[logging]
file = "G:/Shared drives/compressor/logs/filesqueeze.log"
level = "INFO"

[ffmpeg]
# Auto-detected, but you can override:
path = "C:/ffmpeg/bin/ffmpeg.exe"
crf = 28

[document]
# Auto-detected, but you can override:
ghostscript_path = "C:/Program Files/gs/gs10.06.0/bin/gswin64c.exe"
pdf_quality = "printer"
```

### 2. Verify Binary Detection

```bash
# Check if binaries are detected
poetry run python -m filesqueeze detect

# Or with PyPI installation
filesqueeze-detect
```

Expected output:
```
============================================================
FileSqueeze Binary Detection
============================================================
System: Windows 10 AMD64

[OK] FFmpeg: C:\ffmpeg\bin\ffmpeg.exe
[OK] Ghostscript: C:\Program Files\gs\gs10.06.0\bin\swin64c.exe
[OK] Tesseract OCR: C:\Program Files\Tesseract-OCR\tesseract.exe

[OK] All binaries found! FileSqueeze is ready to use.
============================================================
```

### 3. Test Compression

```bash
# Test single file compression
poetry run python -m filesqueeze compress test.mp4

# Or with PyPI
filesqueeze compress test.mp4
```

### 4. Install Auto-Start (Windows Only)

```bash
# Install auto-start on boot
poetry run python -m filesqueeze service-install

# Check installation status
poetry run python -m filesqueeze service-status
```

### 5. Start Service

**Option A: With Tray Icon (Recommended)**
```bash
poetry run python -m filesqueeze service
```

**Option B: Watch Mode (Foreground)**
```bash
poetry run python -m filesqueeze watch
```

**Option C: Auto-Start (Windows)**
```bash
# Reboot computer - service starts automatically
# Or start immediately:
poetry run python -m filesqueeze service
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

## Troubleshooting

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
1. Install FFmpeg (see External Dependencies above)
2. Or set path in `filesqueeze.toml`:
```toml
[ffmpeg]
path = "C:/path/to/ffmpeg.exe"
```

### Ghostscript Not Found

**Error:** `Ghostscript not found`

**Solution:**
1. Install Ghostscript (see External Dependencies above)
2. Or set path in `filesqueeze.toml`:
```toml
[document]
ghostscript_path = "C:/path/to/gswin64c.exe"
```

### Permission Denied

**Error:** `Permission denied` when installing

**Solution (Linux/Mac):**
```bash
# Use virtual environment instead of system install
python3 -m venv filesqueeze-env
source filesqueeze-env/bin/activate
pip install filesqueeze
```

**Solution (Windows):**
- Run PowerShell as Administrator

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'watchdog'`

**Solution:**
```bash
# With Poetry
poetry install

# With PyPI
pip install --upgrade filesqueeze
```

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

## Verification

Verify your installation:

```bash
# Check version
poetry run python -m filesqueeze --version

# Test all commands
poetry run python -m filesqueeze compress --help
poetry run python -m filesqueeze scan --help
poetry run python -m filesqueeze watch --help
poetry run python -m filesqueeze service --help

# Check binary detection
poetry run python -m filesqueeze detect
```

---

## Next Steps

After installation:

1. ✅ Edit `filesqueeze.toml` to set input/output directories
2. ✅ Test with a sample file
3. ✅ Install auto-start (if needed)
4. ✅ Start service and verify tray icon appears
5. ✅ Drop a test file in input directory
6. ✅ Check output directory for compressed file

---

## Support

For issues or questions:

1. Check logs at configured log path
2. Verify binary detection: `poetry run python -m filesqueeze detect`
3. Run with verbose logging: Set `level = "DEBUG"` in `filesqueeze.toml`
4. Open an issue on GitHub: https://github.com/yourusername/filesqueeze/issues
