# FileSqueeze Installation File Layout

## What Happens During Installation

### Method 1: One-Click Installer (install.ps1 / install.sh)

#### Process Overview:

1. **System Checks**
   - Validates Python 3.11+ is installed
   - Checks for Poetry installation
   - Checks system PATH

2. **Poetry Installation** (if missing)
   - Downloads Poetry installer from https://install.python-poetry.org
   - Installs Poetry to `~/.local/bin/poetry` (Linux) or `%APPDATA%\Poetry` (Windows)
   - Adds Poetry to PATH for current session

3. **Repository Clone**
   - Clones FileSqueeze repository from GitHub
   - Default location: `$USERPROFILE/FileSqueeze` (Windows) or `~/FileSqueeze` (Linux)
   - Uses `git clone --branch main --depth 1` (shallow clone)

4. **Dependency Installation**
   - Runs `poetry install` in repository directory
   - Creates virtual environment: `.venv/` in repository root
   - Installs all Python packages from `pyproject.toml`:
     - watchdog (file system monitoring)
     - pystray (system tray icon)
     - tomli/tomli-w (TOML config files)
     - pillow (image processing, dependency of pystray)
     - pdfminer-six (optional OCR support)

5. **Binary Detection**
   - Runs `poetry run python -m filesqueeze detect`
   - Searches for FFmpeg, Ghostscript, Tesseract in:
     - System PATH
     - Common installation directories
     - Registry (Windows) or standard paths (Linux)

6. **Configuration Generation**
   - Runs `poetry run python -m filesqueeze init-config`
   - Creates `filesqueeze.toml` with:
     - Auto-detected binary paths
     - Default directories
     - Default compression settings
     - Logging configuration

7. **Desktop Integration**
   - **Windows**: Creates desktop shortcut `FileSqueeze.lnk`
     - Target: `poetry run python -m filesqueeze service`
     - Working directory: Repository path
     - Icon: Generated green circle with "FS"
   - **Linux**: Creates systemd service file
     - Location: `~/.config/systemd/user/filesqueeze.service`
     - Requires: `systemctl --user enable filesqueeze.service`

8. **Start Scripts**
   - Creates start scripts in installation directory:
     - `start-watch.bat` / `start-watch.sh`: Launches watch mode
     - `compress-file.bat` / `compress-file.sh`: Interactive compression

#### Final File Structure:

```
$USERPROFILE/FileSqueeze/           (Windows) or ~/FileSqueeze (Linux)
├── repo/                             # Git repository
│   ├── .venv/                        # Poetry virtual environment
│   │   ├── bin/                       # Python executables (Linux)
│   │   ├── Scripts/                  # Python executables (Windows)
│   │   ├── Lib/                      # Installed Python packages
│   │   │   ├── site-packages/
│   │   │   │   ├── watchdog/         # File system monitoring
│   │   │   │   ├── pystray/          # System tray icon
│   │   │   │   ├── PIL/              # Pillow (image processing)
│   │   │   │   ├── tomli/            # TOML parser
│   │   │   │   ├── tomli_w/          # TOML writer
│   │   │   │   ├── filesqueeze/      # Main package
│   │   │   │   │   ├── __pycache__/
│   │   │   │   │   ├── *.py          # All source files
│   │   │   │   │   ├── default.toml   # Default configuration
│   │   │   │   │   ├── fsm/           # State machine
│   │   │   │   │   ├── service.py
│   │   │   │   │   ├── doctor.py
│   │   │   │   │   └── ...
│   │   │   │   └── ...
│   │   └── pyvenv.cfg                 # Virtual environment config
│   ├── poetry.lock                   # Dependency lock file
│   ├── pyproject.toml                # Project configuration
│   ├── filesqueeze.toml              # Generated configuration
│   ├── start-watch.bat/sh            # Start scripts
│   ├── compress-file.bat/sh
│   └── ... (all source files)
├── FileSqueeze.lnk                   # Desktop shortcut (Windows only)
└── ... (installer scripts if downloaded)
```

---

### Method 2: PyPI Package (`pip install filesqueeze`)

#### Process Overview:

1. **Package Download**
   - Downloads wheel/source from PyPI
   - Package name: `filesqueeze`
   - Version: `0.1.0` (from setup.py)

2. **Dependency Installation**
   - Installs to Python environment:
     - **System Python**: `/usr/lib/python3.11/` (Linux) or `C:\Python311\Lib\` (Windows)
     - **Virtual Environment**: `venv/lib/python3.11/site-packages/`
     - **User Environment**: `~/.local/lib/python3.11/site-packages/`
   - Dependencies installed:
     - watchdog >=6.0.0,<7.0.0
     - pystray >=0.19.5,<0.20.0
     - tomli-w >=1.0.0
     - pillow (via pystray)

3. **Console Scripts Installation**
   Creates executable scripts:

   **Windows:**
   - `Scripts/filesqueeze.exe`
   - `Scripts/filesqueeze-compress.exe`
   - `Scripts/filesqueeze-scan.exe`
   - `Scripts/filesqueeze-watch.exe`
   - `Scripts/filesqueeze-service.exe`
   - `Scripts/filesqueeze-init.exe`
   - `Scripts/filesqueeze-doctor.exe`
   - `Scripts/filesqueeze-detect.exe`

   **Linux:**
   - `bin/filesqueeze`
   - `bin/filesqueeze-compress`
   - `bin/filesqueeze-scan`
   - `bin/filesqueeze-watch`
   - `bin/filesqueeze-service`
   - `bin/filesqueeze-init`
   - `bin/filesqueeze-doctor`
   - `bin/filesqueeze-detect`

4. **Package Data Installation**
   - `site-packages/filesqueeze/`: All source files
   - `site-packages/filesqueeze/default.toml`: Default configuration template
   - `site-packages/filesqueeze-<version>.dist-info/`: Package metadata

5. **Configuration** (Manual)
   - User runs: `filesqueeze-init`
   - Creates: `./filesqueeze.toml` in current directory
   - Or: `~/.config/filesqueeze/config.toml` for user-wide config

#### Final File Structure:

```
Python installation directory (e.g., C:\Python311\ or /usr/lib/python3.11/)
├── Scripts/ (Windows) or bin/ (Linux)
│   ├── filesqueeze                  # Main CLI
│   ├── filesqueeze-compress         # Commands
│   ├── filesqueeze-scan
│   ├── filesqueeze-watch
│   ├── filesqueeze-service
│   ├── filesqueeze-init
│   ├── filesqueeze-doctor
│   └── filesqueeze-detect
└── Lib/site-packages/
    ├── watchdog/                     # Dependencies
    ├── pystray/
    ├── PIL/
    ├── tomli_w/
    ├── filesqueeze/                  # Main package
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── service.py
    │   ├── doctor.py
    │   ├── default.toml              # Config template
    │   ├── video.py
    │   ├── document.py
    │   ├── scanner.py
    │   ├── binaries.py
    │   ├── config.py
    │   ├── logger.py
    │   ├── tray.py
    │   ├── autostart.py
    │   ├── fsm/
    │   │   ├── __init__.py
    │   │   ├── enums.py
    │   │   └── default.py
    │   └── ...
    └── filesqueeze-<version>.dist-info/
        ├── METADATA
        ├── RECORD
        ├── WHEEL
        └── ...

User's home directory or working directory:
├── filesqueeze.toml                # Generated config (optional)
└── .config/filesqueeze/
    └── config.toml                  # User-wide config (optional)
```

---

### Method 3: Manual Installation (Poetry)

#### Process Overview:

1. **Repository Clone**
   ```bash
   git clone https://github.com/user/repo.git
   cd filesqueeze
   ```

2. **Poetry Installation** (if needed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```
   - Installs to: `~/.local/bin/poetry` (Linux/macOS) or `%APPDATA%\Poetry\bin\` (Windows)
   - Adds to PATH: modifies `.bashrc`, `.zshrc`, or Windows PATH

3. **Virtual Environment Creation**
   ```bash
   poetry install
   ```
   - Creates: `.venv/` directory in repository root
   - Installs all dependencies to `.venv/Lib/site-packages/`
   - Generates: `poetry.lock` lock file

4. **Configuration**
   ```bash
   poetry run python -m filesqueeze init-config
   ```
   - Generates: `filesqueeze.toml` in current directory or repository root

#### Final File Structure:

```
<repository-root>/
├── .venv/                            # Virtual environment
│   ├── bin/                           # Executables (Linux)
│   │   ├── python -> python3.11
│   │   ├── pip
│   │   └── ...
│   ├── Scripts/                       # Executables (Windows)
│   │   ├── python.exe
│   │   ├── pip.exe
│   │   └── ...
│   ├── Lib/
│   │   └── site-packages/           # All Python packages
│   │       ├── watchdog/
│   │       ├── pystray/
│   │       ├── PIL/
│   │       ├── filesqueeze/        # Your package (editable install)
│   │       │   ├── __init__.py
│   │       │   ├── *.py
│   │       │   └── ...
│   │       └── ...
│   └── pyvenv.cfg
├── filesqueeze/                     # Source code
│   ├── __init__.py
│   ├── __main__.py                 # Module entry point
│   ├── service.py
│   ├── doctor.py
│   ├── default.toml
│   ├── video.py
│   ├── document.py
│   ├── scanner.py
│   ├── binaries.py
│   ├── config.py
│   ├── logger.py
│   ├── tray.py
│   ├── autostart.py
│   ├── fsm/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   └── default.py
│   └── ...
├── tests/                           # Test files
│   ├── test_*.py
│   └── fixtures/
│       ├── testvideo61.mp4
│       ├── generated_pdf.pdf
│       ├── scanned_pdf.pdf
│       └── TDD080.jpg
├── poetry.lock                      # Dependency lock file
├── pyproject.toml                   # Project configuration
├── filesqueeze.toml                 # Generated configuration
├── main.py                          # CLI entry point
├── install.ps1                      # Windows installer
├── install.sh                       # Linux installer
├── setup.py                         # PyPI setup
├── MANIFEST.in                      # Package manifest
├── README.md                        # Documentation
└── .git/                           # Git repository

User directories:
├── ~/.config/filesqueeze/
│   └── config.toml                  # User-wide config (optional)
└── <working-dir>/filesqueeze.toml   # Project config (optional)
```

---

## Configuration File Locations

FileSqueeze searches for configuration in this order (later overrides earlier):

1. **Project Config** (optional)
   - Location: `./filesqueeze.toml` (current working directory)
   - Priority: 1 (highest for local overrides)
   - Use case: Project-specific settings

2. **User Config** (optional)
   - Location: `~/.config/filesqueeze/config.toml`
   - Priority: 2 (user-wide settings)
   - Use case: Personal default settings

3. **Code Defaults**
   - Location: Built into `filesqueeze/config.py`
   - Priority: 3 (fallback)
   - Use case: When no config file exists

---

## Runtime File Locations

### During Execution:

1. **Log Files**
   - Default: `./filesqueeze.log` (current working directory)
   - Configured via: `[logging.file]` in config
   - Rotation: 10MB max, 5 backup files
   - Backup naming: `filesqueeze.log.1`, `.2`, etc.

2. **Lock Files** (Not yet implemented - planned for multi-instance coordination)
   - Location: `<input_dir>/.filesqueeze_lock`
   - Purpose: Prevent duplicate processing
   - Timeout: Configurable via `[processing.lock_timeout_seconds]`

3. **Temporary Files**
   - Created during compression in temp directory
   - Cleaned up after processing
   - Location: OS temp dir (`%TEMP%` on Windows, `/tmp` on Linux)

### Output Files:

1. **Compressed Files**
   - Default naming: `compressed_<filename>`
   - Location: Configured output directory
   - Structure: Based on `[output.structure]` setting
     - `flat`: All files in output root
     - `by_type`: Organized by type (video/, document/, slideshow/)
     - `by_date`: Organized by date (YYYY-MM-DD/)
     - `mirror`: Preserves source directory structure

2. **Metadata Files** (optional)
   - Created when `[output.save_metadata] = true`
   - Location: `<output_file>.json`
   - Contains: Source path, processing timestamp, etc.

---

## Service Mode Files

### Windows Auto-Start:

1. **Startup Batch File**
   - Location: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\filesqueeze-start.bat`
   - Created by: `filesqueeze service-install`
   - Contains:
     ```batch
     @echo off
     cd "<install_dir>\repo"
     poetry run python -m filesqueeze service
     ```

2. **Tray Icon** (when running)
   - System tray icon (green circle with "FS")
   - Menu options: Show Status, Open Input/Output, Quit
   - Runs in background as separate process

### Linux Systemd Service:

1. **Service File**
   - Location: `~/.config/systemd/user/filesqueeze.service`
   - Created by: Installer script (manual)
   - Contents:
     ```ini
     [Unit]
     Description=FileSqueeze Compression Service
     After=network.target

     [Service]
     Type=simple
     WorkingDirectory=<install_dir>/repo
     ExecStart=poetry run python -m filesqueeze service
     Restart=on-failure

     [Install]
     WantedBy=default.target
     ```

2. **Enable Service**
   ```bash
   systemctl --user enable filesqueeze.service
   systemctl --user start filesqueeze.service
   ```

---

## Summary Table

| Component | One-Click Installer | PyPI Package | Manual (Poetry) |
|-----------|-------------------|--------------|-----------------|
| **Installation Directory** | `$USERPROFILE/FileSqueeze/repo` | Python site-packages | `<clone-dir>` |
| **Virtual Environment** | `.venv/` in repo | System Python | `.venv/` in repo |
| **Config File** | Generated in install dir | User creates | User creates |
| **Executables** | `poetry run python -m filesqueeze` | `filesqueeze` command | `poetry run python -m filesqueeze` |
| **Auto-Start** | Windows Startup folder | Not included | Manual setup |
| **Desktop Shortcut** | Yes (Windows) | No | No |
| **Start Scripts** | Yes | No | No |
| **Systemd Service** | Yes (Linux) | No | No |

---

## Clean Uninstallation Locations

To completely remove FileSqueeze, delete:

**One-Click Installer:**
1. Installation directory: `$USERPROFILE\FileSqueeze` or `~/FileSqueeze`
2. Desktop shortcut: `$USERPROFILE\Desktop\FileSqueeze.lnk`
3. Startup entry: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\filesqueeze-start.bat`
4. Config: `~/.config/filesqueeze/config.toml` (optional)

**PyPI Package:**
1. Package: `pip uninstall filesqueeze`
2. Config: `filesqueeze.toml` (optional)

**Manual Installation:**
1. Repository: `<clone-dir>`
2. Virtual environment: `<clone-dir>/.venv`
3. Poetry: `~/.local/bin/poetry` (optional)
4. Config: `~/.config/filesqueeze/` (optional)
