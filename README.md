# FileSqueeze

Utility package for compressing various file types including videos, PDFs, and images.

## Features

- Video compression using FFmpeg
- PDF compression using Ghostscript
- OCR (Optical Character Recognition) for scanned PDFs using Tesseract
- Image compression and resizing
- Automatic binary detection (FFmpeg, Ghostscript, Tesseract)
- Intelligent PDF processing (detects scanned vs generated PDFs)
- Batch processing
- File watching mode
- Background service with tray icon

## Installation

FileSqueeze supports three installation methods:

### 🚀 Method 1: One-Click Installer (Recommended for Non-Technical Users)

**Windows:**
```powershell
# Download and run installer
irm https://nyjc.app/filesqueeze/install | iex
```

**Linux:**
```bash
# Download and run installer
curl -sSL https://nyjc.app/filesqueeze/install | bash
```

The installer will:
- ✅ Check for Python 3.11+
- ✅ Install Poetry (dependency manager)
- ✅ Clone FileSqueeze repository
- ✅ Install all dependencies
- ✅ Detect FFmpeg, Ghostscript, Tesseract
- ✅ Generate configuration file
- ✅ Create desktop shortcut

For detailed instructions, see [INSTALL.md](INSTALL.md)

### 📦 Method 2: PyPI Package (Recommended for Python Users)

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

### 🔧 Method 3: Manual Installation (For Developers)

```bash
# Clone repository
git clone https://github.com/yourusername/filesqueeze.git
cd filesqueeze

# Install dependencies
poetry install

# Generate configuration
poetry run python -m filesqueeze init-config

# Start service
poetry run python -m filesqueeze service
```

### External Dependencies

**Required:**
- **FFmpeg** - Video and image compression
  - Windows: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
  - Linux: `sudo apt-get install ffmpeg`

- **Ghostscript** - PDF compression
  - Windows: `choco install ghostscript` or download from [ghostscript.com](https://www.ghostscript.com)
  - Linux: `sudo apt-get install ghostscript`

**Optional:**
- **Tesseract OCR** - Add text layer to scanned PDFs
  - Windows: `choco install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

> **Note:** The one-click installer will detect these automatically. Make sure they're in your system PATH.

## Configuration

FileSqueeze uses configuration files to control how files are processed. You can customize:

- Input/output directories
- Compression quality settings
- File types to process
- Logging options
- And much more!

### Setting Up Your Configuration

The easiest way to get started is to generate an example configuration file:

```bash
python -m filesqueeze init-config
```

This creates a `filesqueeze.toml` file in your current directory with auto-detected binary paths and all default settings.

### Detecting Binaries

To check if FileSqueeze can detect your installed binaries:

```bash
python -m filesqueeze detect
```

This will show you the detected paths for FFmpeg, Ghostscript, and Tesseract.

### Configuration File Locations

FileSqueeze looks for configuration files in this order (later configs override earlier ones):

1. **Project config**: `filesqueeze.toml` in your working directory
2. **User config**: `~/.config/filesqueeze/config.toml` (your home directory)
3. **Default values**: Built-in defaults (used if no config file exists)

### Quick Configuration Guide

The most important settings you'll want to change:

#### Setting Directories

```toml
[directories]
# Where to look for files to compress
input = "G:/Shared drives/compressor/upload"

# Where to save compressed files
output = "G:/Shared drives/compressor/compressed"
```

#### Adjusting Compression Quality

```toml
[ffmpeg]
# Video quality: lower = better quality, larger file (18-28 recommended)
crf = 28

[document]
# PDF quality: "screen" (smallest), "ebook", "printer", "prepress" (largest)
pdf_quality = "printer"

# For generated PDFs: "printer" quality (readable, good compression)
# For scanned PDFs: automatically uses "ebook" quality (better compression)

# Image quality: 1-100 (higher = better quality)
image_quality = 85

[ocr]
# Enable automatic OCR for scanned PDFs (adds searchable text layer)
enable_ocr = true
# OCR language
language = "eng"
```

#### Choosing Output Organization

```toml
[output]
# How to organize output files:
# - "flat": All files in one folder
# - "by_type": Separate folders for videos, documents, etc.
# - "by_date": Organized by date (YYYY-MM-DD)
# - "mirror": Match your source folder structure
structure = "flat"
```

### Custom Paths for FFmpeg/Ghostscript/Tesseract

If FileSqueeze can't detect your binaries automatically, you can specify their locations:

```toml
[ffmpeg]
# Full path to ffmpeg.exe (leave empty if in PATH)
path = "C:/path/to/ffmpeg.exe"

[document]
# Full path to gswin64c.exe (Ghostscript for Windows)
ghostscript_path = "C:/path/to/gswin64c.exe"

[ocr]
# Full path to tesseract.exe (leave empty if in PATH)
tesseract_path = "C:/Program Files/Tesseract-OCR/tesseract.exe"
# OCR language (eng=English, chi_sim=Simplified Chinese)
language = "eng"
# Enable OCR for scanned PDFs
enable_ocr = true
```

## Usage

### Basic Usage (Process Files Once)

```bash
# Process all files in configured input directory
python -m filesqueeze --scan

# Use custom directories (overrides config file)
python -m filesqueeze --scan --input "C:/My Videos" --output "C:/Compressed"
```

### Watch Mode (Continuous Monitoring)

```bash
# Monitor input directory and automatically process new files
python -m filesqueeze --watch
```

### Background Service (Windows)

```bash
# Install as startup service (runs automatically on boot)
python -m filesqueeze --service-install

# Uninstall startup service
python -m filesqueeze --service-uninstall

# Run with system tray icon (manual control)
python -m filesqueeze --service
```

### Check Status

```bash
# Show queue status and recent files
python -m filesqueeze --status
```

## Configuration Options Reference

See the generated `filesqueeze.toml` file (run `--init-config`) for a complete list of all configuration options with detailed comments explaining each setting.

## Troubleshooting

### "FFmpeg not found" Error

**Solution**: Run `python -m filesqueeze detect` to see if FFmpeg is detected. If not:
- Install FFmpeg and ensure it's in your system PATH
- Or set `ffmpeg.path` in your config file to the full path

### "Ghostscript not found" Error

**Solution**: Run `python -m filesqueeze detect` to see if Ghostscript is detected. If not:
- Install Ghostscript and ensure it's in your system PATH
- Or set `document.ghostscript_path` in your config file

### "Tesseract not found" Warning

**Solution**: This is optional - only needed for OCR on scanned PDFs:
- Install Tesseract OCR from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Ensure it's in your system PATH
- Or set `ocr.tesseract_path` in your config file

### Files Not Being Processed

**Check**:
- File extensions are in the `file_detection.extensions` list
- Files meet minimum age requirement (`file_detection.min_age_seconds`)
- Files meet minimum size requirement (`file_detection.min_size_bytes`)

### Scanned PDFs Not Compressing Well

**Cause**: "Printer" quality preserves high-resolution images in scanned PDFs

**Solution**: FileSqueeze automatically detects scanned vs generated PDFs and uses appropriate compression:
- Generated PDFs: "printer" quality (readable text)
- Scanned PDFs: "ebook" quality (downsamples images for compression)

### OCR is Slow

**Solution**: OCR is computationally intensive:
- Reduce OCR DPI: set `ocr.ocr_dpi = 200` (default is 300)
- Disable OCR for scanned PDFs: set `ocr.enable_ocr = false`
- Process files in smaller batches

## Development

See [plans/filesqueeze-implementation-plan.md](../plans/filesqueeze-implementation-plan.md) for implementation details.
