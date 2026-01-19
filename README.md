# FileSqueeze

Utility package for compressing various file types including videos, PDFs, and images.

## Features

- Video compression using FFmpeg
- PDF compression using Ghostscript
- Image compression and resizing
- Batch processing
- File watching mode
- Background service with tray icon

## Installation

### Quick Start (For Non-Technical Users)

1. **Download and install Python 3.11+** from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Download and install FFmpeg** (for video/image processing)
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows) or use `winget install ffmpeg`
   - Add FFmpeg to your system PATH (the installer usually does this automatically)

3. **Download and install Ghostscript** (for PDF processing)
   - Windows: Download from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html)
   - Add Ghostscript to your system PATH (the installer usually does this automatically)

4. **Install FileSqueeze**
   ```bash
   poetry install
   ```

### For Developers

```bash
poetry install
```

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
python -m filesqueeze --init-config
```

This creates a `filesqueeze.toml` file in your current directory with all default settings and helpful comments.

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
pdf_quality = "ebook"

# Image quality: 1-100 (higher = better quality)
image_quality = 85
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

### Custom Paths for FFmpeg/Ghostscript

If FileSqueeze can't find FFmpeg or Ghostscript automatically, you can specify their locations:

```toml
[ffmpeg]
# Full path to ffmpeg.exe (leave empty if in PATH)
path = "C:/path/to/ffmpeg.exe"

[document]
# Full path to gswin64c.exe (Ghostscript for Windows)
ghostscript_path = "C:/path/to/gswin64c.exe"
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

**Solution**: Install FFmpeg and ensure it's in your system PATH, or set the `ffmpeg.path` in your config file.

### "Ghostscript not found" Error

**Solution**: Install Ghostscript and ensure it's in your system PATH, or set the `document.ghostscript_path` in your config file.

### Files Not Being Processed

**Check**:
- File extensions are in the `file_detection.extensions` list
- Files meet minimum age requirement (`file_detection.min_age_seconds`)
- Files meet minimum size requirement (`file_detection.min_size_bytes`)

## Development

See [plans/filesqueeze-implementation-plan.md](../plans/filesqueeze-implementation-plan.md) for implementation details.
