# FileSqueeze

Utility package for compressing videos, audio, PDFs, and images using FFmpeg, Ghostscript, and Pillow.

## Features

- **Video Compression**: FFmpeg-based with configurable quality (CRF), presets, and scaling
- **Audio Compression**: FFmpeg-based WAV → AAC in an M4A container at a configurable bitrate
- **PDF Compression**: Ghostscript-based with quality settings (screen, ebook, printer, prepress)
- **Image Compression**: Pillow-based conversion to JPG (quality 88, interlaced/progressive, 4:2:2 chroma subsampling); supports JPG, PNG, BMP, TIFF, WebP, and HEIC input
- **PPTX to Video**: Convert PowerPoint slideshows to MP4 (Windows + PowerPoint; feature-flagged, disables itself where unavailable)
- **OCR Support**: Add searchable text layer to scanned PDFs using Tesseract
- **Smart PDF Detection**: Automatically detects scanned vs generated PDFs
- **Watch Mode**: Real-time directory monitoring with automatic file processing
- **Standalone Mode**: Compress a single file to a chosen destination via a dialog (`compress --gui`, tray menu, or right-click → Send To)
- **Service Mode**: Background service with system tray icon (Windows)
- **Auto-Start**: Start automatically at login (no admin required)
- **One-Click Update**: Checks GitHub at startup (or via **Check for updates**) and notifies in the tray/GUI; one click downloads, installs via pip (no installer .exe, no admin), and restarts into the new version
- **Batch Processing**: Process entire directories at once
- **Binary Auto-Detection**: Automatically finds FFmpeg, Ghostscript, and Tesseract, plus the optional stcc captions package
## Quick Start

```bash
# System-wide installation (Windows) — from a release tag
git clone https://github.com/NYJC-Edtech/filesqueeze.git
cd filesqueeze
git checkout vX.Y.Z                  # the release tag you want (see Releases)
.\install.ps1

# Linux equivalent:
bash install.sh

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
  - [Method 2: From a Release Wheel](#method-2-from-a-release-wheel-advanced)
  - [Method 3: Development Installation](#method-3-development-installation-poetry)
  - [External Dependency Setup](#external-dependency-setup)
  - [Locked-Down Machines](#locked-down-machines-no-installers-no-admin-rights)
  - [Updating](#updating)
- [External Dependencies](#external-dependencies)
- [Configuration](#configuration)
- [Usage](#usage)
- [Uninstallation](#uninstallation)
- [Additional Documentation](#additional-documentation)

---

## Installation

The **canonical installation** is the installer script — `install.ps1` on Windows, `install.sh` on Linux. The scripts follow [Installation Principles](docs/INSTALLATION_PRINCIPLES.md): robust error handling, PATH refresh, and graceful fallbacks.

> **Install from a release tag.** The installer builds from the local checkout, so check out the tag you want first (`git checkout vX.Y.Z`, or download that release's source archive) — otherwise you install whatever the working copy happens to contain.

### Method 1: System-Wide Installer (Recommended for End Users)

**Best for:** Production use, end users who want `filesqueeze` command available everywhere

#### Prerequisites
- Python 3.11 or later
- Git (or a downloaded source archive of the release)
- FFmpeg (for video compression)
- Ghostscript (for PDF compression)
- Tesseract OCR (optional, for scanned PDFs)

#### Installation

```powershell
# Windows
git clone https://github.com/NYJC-Edtech/filesqueeze.git
cd filesqueeze
git checkout vX.Y.Z        # the release tag you want (see Releases)
.\install.ps1              # reinstall over an existing install with -Force
```

```bash
# Linux
git clone https://github.com/NYJC-Edtech/filesqueeze.git
cd filesqueeze
git checkout vX.Y.Z        # the release tag you want (see Releases)
bash install.sh
```

**What the installer does** (Windows):
- ✅ Checks Python 3.11+ installation
- ✅ Builds FileSqueeze from the checkout and installs it system-wide with pip
- ✅ Generates `~/.config/filesqueeze/config.toml` (preserves an existing config; prompts and backs up before overwriting)
- ✅ Creates Start Menu shortcuts (service, Compress dialog, uninstaller) and a right-click **Send To → FileSqueeze** entry
- ✅ Creates default input/output directories and offers auto-start on login
- ✅ Offers [external-dependency setup](#external-dependency-setup): detect FFmpeg/Ghostscript/Tesseract and optionally install portable builds into your binaries folder
- ✅ Stops a running service before reinstall and restarts it afterwards

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

### Method 2: From a Release Wheel (Advanced)

**Best for:** scripted or pip-only setups where the installer's extras (shortcuts, config generation, auto-start) are handled separately

FileSqueeze is **not published on PyPI** — `pip install filesqueeze` will not work. Every [GitHub release](https://github.com/NYJC-Edtech/filesqueeze/releases) publishes a wheel; its primary consumer is the built-in one-click updater (see [Updating](#updating)), but you can install one manually:

```bash
# 1. Copy the .whl asset URL from the latest release:
#    https://github.com/NYJC-Edtech/filesqueeze/releases/latest
# 2. Install it with the SAME interpreter that will run FileSqueeze.
#    Use `python -m pip`, not bare `pip` — on machines with several Pythons,
#    bare `pip` often belongs to a different one, and the package lands in
#    an environment the app never runs from.
python -m pip install --force-reinstall "<wheel-url>"

# 3. Generate the config (installed copies write to ~/.config/filesqueeze/config.toml)
python -m filesqueeze init-config
```

A manual wheel install swaps code only: no Start Menu / Send To shortcuts, no auto-start, no default directories, and no service stop/restart on reinstall. For a complete setup, prefer the installer (Method 1). Once installed this way, subsequent updates arrive through the in-app updater like any other install.

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

### External Dependency Setup

Both installers offer to run `filesqueeze setup-deps` after installation, and you can run it again any time. The flow:

1. **Pick your binaries folder** — a native dialog asks for an *existing* directory (the one you keep portable tools in; the picker starts at `~/FileSqueeze/bin` when it exists). Nothing outside this folder is touched.
2. **Detect** — FileSqueeze scans the folder (a few levels deep) for FFmpeg, Ghostscript, Tesseract, and the stcc captions package and reports what is already there.
3. **Choose what to install** — for the missing ones, a checklist offers any combination, including **Install none**. Required dependencies are pre-checked; Tesseract (optional) is not.
4. **Portable install** — chosen dependencies are downloaded from the canonical sources listed under [External Dependencies](#external-dependencies) and unpacked into your folder. Ghostscript and Tesseract ship only as installer `.exe` files, so **7-Zip is downloaded too if it's missing** (into `<folder>/7-Zip`) to unpack them — no installers are ever run, and no admin rights are used.
5. **Config wiring** — the located paths are written into `~/.config/filesqueeze/config.toml` (backed up first), so they take priority over PATH auto-detection.

Headless or scripted use skips the dialogs:

```powershell
filesqueeze setup-deps --dir "D:\Tools\bin" --install ffmpeg,ghostscript --yes
filesqueeze setup-deps --dir "D:\Tools\bin" --install none --yes    # detect only
```

On Linux the flow is detect-and-advise: missing dependencies get the matching package-manager command, since no portable builds are published for them.

### Locked-Down Machines (No Installers, No Admin Rights)

FileSqueeze itself is pure Python — installing it never requires running an .exe installer. The only installer-based pieces are the [external binaries](#external-dependencies), and each has an installer-free route:

- **FFmpeg** ships as a portable archive, not an installer. Direct, always-current links (no version hunting, no wrong-version risk):
  - gyan.dev release build (recommended): <https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip> — a permanent URL that always serves the newest release build; it's a plain `.zip`, so even 7-Zip isn't needed
  - BtbN build (alternative): <https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip>
  
  Extract into your portable-tools folder (any folder works — the examples below use `C:\Users\you\FileSqueeze\bin\`) and point the config at it (below). No PATH changes needed.
- **Ghostscript** has no official portable zip — its official downloads are installer `.exe` files, always current at <https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/latest> (the Windows 64-bit asset is named `gs<version>w64.exe`, e.g. `gs10080w64.exe` for 10.08.0). The installer can be opened like an archive with [7-Zip](https://www.7-zip.org/) (*Open archive*), and the extracted folder works standalone.
- **Tesseract** is optional — skip it unless you need OCR for scanned PDFs. If you do need it, the canonical Windows builds are the [UB-Mannheim installers](https://github.com/UB-Mannheim/tesseract/wiki) (also just an `.exe`; same 7-Zip extraction trick works).

All of this is automated by [`filesqueeze setup-deps`](#external-dependency-setup): it picks the folder, detects what's there, downloads these exact portable builds, and bootstraps 7-Zip itself when it's missing — the manual routes above remain the fallback when even that can't run.

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

### Updating

FileSqueeze checks GitHub for a newer release when the service starts (cached for 6 hours, so it never hammers the API). When one is found you get a tray notification, a tray menu entry, and a banner in the Status window and Compress dialog. You can also check manually any time: **Check for updates** in the tray menu, or the **Check for updates** button on the Status window's **About** tab — which also shows the current version and, when a newer release is found, the latest version, a link to the GitHub release page, and an **Update Now** button (greyed out until an update is available).

**One click, no installer:** choose **Update to vX now** in the tray menu (or **Update now** in the Status window / Compress dialog banner). FileSqueeze downloads the release wheel, verifies it, quits, installs it with `pip install --force-reinstall --no-deps`, and starts again with the new version. Your config (`~/.config/filesqueeze/config.toml`) and watched folders are untouched, and no admin rights are needed — pip falls back to a user install when the Python site-packages folder isn't writable. The download is cancellable; if it fails, the banner keeps a *Release notes* link.

**Tasks finish first:** if a compression is running or the service is mid-file, FileSqueeze does not quit right away — a buttonless notice tells you it *will close and install the update after all tasks complete*, and the quit happens automatically once everything finishes. You can still cancel during the wait. In a dialog-only launch (`compress --gui`, no tray running) the update installs when you close the dialog.

Notes:

- **Dev checkouts never self-update** — update with `git pull` instead (the app tells you so if you try).
- **Releases without a wheel asset** degrade to a *Release notes* link.
- Fully locked-down setups where pip can't write anywhere still get the *Release notes* link to download the wheel manually.
- **Failed updates don't strand you**: the installed version is backed up before pip runs; if the install fails, the previous version is restored and FileSqueeze tells you the update failed the next time it starts — it stays fully usable and you can retry from the tray menu.

---

## External Dependencies

### Required

#### FFmpeg
**Purpose:** Video compression (image compression uses Pillow, no external binary needed)

**Windows:**
```bash
# Direct download (portable — always the latest release build, no version hunting):
# https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
#   (alternative: https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip)
# Extract to C:\Program Files\ffmpeg (or anywhere)
# Add <extracted>\bin to your PATH, or set the path in your config (see Configuration)

# Or use chocolatey:
choco install ffmpeg

# Or use winget:
winget install ffmpeg
```

> Keep `ffprobe.exe` alongside `ffmpeg.exe` — both ship in every archive, and
> FileSqueeze uses ffprobe for video analysis.

**Linux:**
```bash
# Portable static build (no root needed — direct, always-latest link):
# https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
#   (also available for arm64; extract anywhere and set the path in your config)

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
# Direct download (always the current release page):
# https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/latest
# The Windows 64-bit asset is named gs<version>w64.exe (e.g. gs10080w64.exe = 10.08.0)

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
# Canonical Windows builds (UB-Mannheim) — wiki with links to every build:
# https://github.com/UB-Mannheim/tesseract/wiki
# Direct directory listing (filenames are versioned, e.g. tesseract-ocr-w64-setup-5.4.0.exe):
# https://digi.bib.uni-mannheim.de/tesseract/

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

#### stcc speech-to-captions (Windows only)
**Purpose:** Video transcription / SRT closed captions (via the [filesqueeze-stcc](https://github.com/NYJC-Edtech/filesqueeze-stcc) package: Fluid Speech Mini model + parakeet.cpp runtime)

**Setup:** `setup-deps` installs stcc into your binaries folder (checksum-pinned zip from the FileSqueeze project's own releases, ~290 MB) and fills in `stcc_path`. Caption generation is **off by default** — set `[transcription] enabled = true` in your config; compressed videos then get a sidecar `.srt` next to the output (and the SRT embedded as a toggleable soft subtitle track for MP4 outputs). Transcription runs on the original video after compression succeeds; if stcc is missing or fails, a warning is logged and the compressed video is unaffected. English audio only.

---

## Configuration

### Quick Setup

Generate an example configuration file with auto-detected binary paths:

```bash
filesqueeze init-config                      # installed copy
poetry run python -m filesqueeze init-config # dev checkout
```

The output location depends on how FileSqueeze is running: an **installed copy** writes the user config at `~/.config/filesqueeze/config.toml` — the one location the service reads regardless of its working directory — while a **dev checkout** creates `./filesqueeze.toml` (the project config for that checkout). The system installer generates the user config for you on first install, so this command is only needed for manual setups.

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

[updates]
# Check GitHub at startup for a newer release and notify in the tray/GUI
check_on_startup = true

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

Settings from each source override the ones below it (highest priority first):

1. **Environment variables**: `FILESQUEEZE_*` (see above)
2. **Project config**: `filesqueeze.toml` in the working directory the app starts from
3. **User config**: `~/.config/filesqueeze/config.toml` — the location the installer writes and the only one read regardless of working directory
4. **Code defaults**: bundled `default.toml`

> Because the project config is working-directory-relative, the user config is the dependable place for personal settings: it applies no matter where FileSqueeze starts from.

---

## Usage

### Python API

```python
import filesqueeze

# Compress single files
output_path = filesqueeze.make_video('input.mp4')
output_path = filesqueeze.make_audio('input.wav')
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

### Audio Compression

Uncompressed audio is transcoded to AAC in an M4A container with FFmpeg
(audio content is left otherwise untouched — no loudness normalization or
resampling).

**Accepted input formats:** `wav`

Output is always `compressed_<name>.m4a` (e.g. `lecture.wav` →
`compressed_lecture.m4a`). The bitrate comes from `ffmpeg.audio_bitrate`
(default `96k`), the same setting videos use for their audio tracks — a 10
minute 44.1 kHz stereo WAV (~100 MB) typically compresses to under 10 MB.

### CLI Commands

#### Compress Single File

```bash
poetry run python -m filesqueeze compress video.mp4
poetry run python -m filesqueeze compress document.pdf -o compressed.pdf
```

Default output is `compressed_<name>.<ext>` next to the input (images convert
to JPG output, e.g. `photo.png` → `compressed_photo.jpg`), matching the watch
mode naming convention. A collision never overwrites — the new file is
renamed with a `_1`, `_2`, ... suffix.

#### Standalone Mode (Compress a File dialog)

```bash
poetry run python -m filesqueeze compress --gui                # empty dialog
poetry run python -m filesqueeze compress --gui video.mp4     # pre-selected
```

Pick a file, pick a destination ("Same folder as the original" by default),
and FileSqueeze compresses it with your configured quality settings — the
same pipeline and naming as watch mode. The dialog:

- previews the output name before you start, and warns when a name
  collision will trigger an auto-rename
- rejects unsupported types up front (`.pptx` is not supported in
  standalone mode yet)
- shows an honest progress state (no fake percentages) plus a size
  comparison when done

The system installer also creates a **FileSqueeze Compress** Start Menu
shortcut and a **Send To → FileSqueeze** entry (right-click any file) that
open this dialog with the file pre-selected. The dialog can be used while
the monitoring service runs — the two do not interfere.

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
| **File Extension** | `mp4, wmv, avi, mkv, mov, flv, wav, pdf, jpg, jpeg, png, bmp, tif, tiff, webp, heic, heif, pptx` | Only these file types are processed |
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
extensions = ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv', 'wav', 'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tif', 'tiff', 'webp', 'heic', 'heif']

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
- **Build tool missing**: The installer installs Poetry's alternative — the `build` module — automatically; if that step failed, run `python -m pip install build` and re-run the installer
- **PATH not updated**: Restart your shell or use `python -m` syntax

### Application Issues

For common issues and solutions, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

For quick diagnosis:
```bash
poetry run python -m filesqueeze doctor
```

---

## Uninstallation

### Windows

The easiest route is the **Uninstall FileSqueeze** shortcut the installer created in the Start Menu (FileSqueeze folder). It runs `uninstall.ps1`, which removes the package, auto-start, Start Menu / Send To shortcuts, and the default input/output directories — while **preserving your configuration** at `~/.config/filesqueeze/config.toml`.

From a checkout you can run the same script directly:

```powershell
.\uninstall.ps1 -Force
```

To remove everything including settings:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.config\filesqueeze"
```

### Linux

```bash
# Stop and disable the user service
systemctl --user stop filesqueeze.service
systemctl --user disable filesqueeze.service
rm ~/.config/systemd/user/filesqueeze.service

# Remove the installation directory (repo clone and generated scripts)
rm -rf ~/FileSqueeze

# Remove the Poetry environment used by the install
poetry env remove --all

# Remove settings (optional)
rm -rf ~/.config/filesqueeze
```

---

## Additional Documentation

For development, testing, and deployment information, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

For troubleshooting and common issues, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## License

MIT License - See LICENSE file for details
