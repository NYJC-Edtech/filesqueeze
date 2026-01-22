# FileSqueeze Installation Guide

## Installation Options

### Option 1: System-Wide Installation (Recommended for Production)

**Script:** `install.ps1`

**Best for:**
- Production deployment
- End-user machines
- System-wide availability
- No Poetry/venv required

**What it does:**
- Installs FileSqueeze using `pip install -e .`
- Creates Start Menu folder with shortcuts
- Sets up user configuration
- No virtual environment (uses system Python)

**How to install:**
```powershell
cd d:\nyjc-edtech\filesqueeze
.\install.ps1
```

**Shortcuts created:**
- Start Menu → Programs → FileSqueeze → **Start FileSqueeze Service**
- Start Menu → Programs → FileSqueeze → **FileSqueeze Doctor**
- Start Menu → Programs → FileSqueeze → **Open Configuration Folder**
- Start Menu → Programs → FileSqueeze → **Open Logs Folder**
- Start Menu → Programs → FileSqueeze → **Uninstall FileSqueeze**

**How to run:**
```powershell
# Via Start Menu:
# Windows Key → Type "FileSqueeze" → Click "Start FileSqueeze Service"

# Or via command line:
python -m filesqueeze service
```

**How to uninstall:**
```powershell
.\uninstall.ps1
```

---

### Option 2: Development Installation

**Script:** `install-dev.ps1`

**Best for:**
- Development and testing
- Multiple Python versions
- Isolated dependencies
- Working on FileSqueeze code

**What it does:**
- Installs Poetry (if needed)
- Clones Git repository
- Uses `poetry install` (creates virtual environment)
- Creates desktop shortcut

**How to install:**
```powershell
cd d:\nyjc-edtech\filesqueeze
.\install-dev.ps1
```

**How to run:**
```powershell
poetry run python -m filesqueeze service
```

---

## Quick Start (System Installation)

1. **Install FileSqueeze:**
   ```powershell
   cd d:\nyjc-edtech\filesqueeze
   .\install.ps1
   ```

2. **Access via Start Menu:**
   - Press **Windows Key**
   - Type: **FileSqueeze**
   - Click: **Start FileSqueeze Service**

3. **Configuration:**
   - Start Menu → FileSqueeze → **Open Configuration Folder**
   - Edit `C:\Users\ICT Department\.config\filesqueeze\config.toml`

4. **View Logs:**
   - Start Menu → FileSqueeze → **Open Logs Folder**

---

## File Structure

### Installers
```
filesqueeze/
├── install.ps1           # System installer (production)
├── install-dev.ps1       # Development installer (Poetry)
└── uninstall.ps1         # System uninstaller
```

### Configuration
```
C:\Users\ICT Department\.config\filesqueeze\
└── config.toml           # User configuration (overrides defaults)

G:\Shared drives\compressor\config\
└── filesqueeze.toml      # Backup configuration
```

### Logs
```
G:\Shared drives\compressor\logs\
├── filesqueeze.log                      # Current day
├── filesqueeze.log_2026-01-21.log       # Previous days
├── filesqueeze.log_2026-01-20.log
└── ...                                   (up to 365 days)
```

### Start Menu
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\FileSqueeze\
├── Start FileSqueeze Service.lnk
├── FileSqueeze Doctor.lnk
├── Open Configuration Folder.lnk
├── Open Logs Folder.lnk
└── Uninstall FileSqueeze.lnk
```

---

## Troubleshooting

### ModuleNotFoundError: No module named 'pystray'

**Problem:** FileSqueeze dependencies not installed.

**Solution:**
```powershell
cd d:\nyjc-edtech\filesqueeze
python -m pip install -e .
```

### Start Menu shortcuts not appearing

**Problem:** Installation incomplete or permissions issue.

**Solution:**
1. Run installer as Administrator:
   ```powershell
   # Right-click PowerShell → Run as Administrator
   cd d:\nyjc-edtech\filesqueeze
   .\install.ps1
   ```

2. Manually check Start Menu folder:
   ```
   %APPDATA%\Microsoft\Windows\Start Menu\Programs\FileSqueeze
   ```

### Configuration not being applied

**Problem:** User config location incorrect.

**Solution:**
1. Check user config exists:
   ```
   C:\Users\ICT Department\.config\filesqueeze\config.toml
   ```

2. Verify log file location in config:
   ```toml
   [logging]
   file = "G:/Shared drives/compressor/logs/filesqueeze.log"
   ```

### Service not starting

**Problem:** Python path or dependencies issue.

**Solution:**
1. Run diagnostics:
   ```powershell
   python -m filesqueeze doctor
   ```

2. Check logs:
   - Start Menu → FileSqueeze → Open Logs Folder
   - Open `filesqueeze.log`

---

## Uninstallation

### System Installation
```powershell
cd d:\nyjc-edtech\filesqueeze
.\uninstall.ps1
```

This removes:
- ✅ Start Menu shortcuts
- ✅ FileSqueeze package

Keeps:
- ✅ User configuration
- ✅ Logs

To completely remove FileSqueeze, manually delete:
```
C:\Users\ICT Department\.config\filesqueeze
G:\Shared drives\compressor\logs
G:\Shared drives\compressor\config
```

---

## Development vs Production

| Feature | install.ps1 (Production) | install-dev.ps1 (Development) |
|---------|-------------------------|-------------------------------|
| Target | End users | Developers |
| Package Manager | pip | Poetry |
| Environment | System Python | Virtual environment |
| Shortcuts | Start Menu folder | Desktop only |
| How to Run | `python -m filesqueeze service` | `poetry run python -m filesqueeze service` |
| Uninstaller | Yes (`uninstall.ps1`) | No |

---

## Support

For issues or questions:
1. Check logs: Start Menu → FileSqueeze → Open Logs Folder
2. Run diagnostics: Start Menu → FileSqueeze → FileSqueeze Doctor
3. View configuration: Start Menu → FileSqueeze → Open Configuration Folder
