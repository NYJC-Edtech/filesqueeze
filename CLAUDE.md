# FileSqueeze - Claude Code Navigation Guide

This is a navigation guide for Claude Code (or other AI assistants) working on the FileSqueeze codebase.

## Project Overview

FileSqueeze is a utility package for compressing videos, PDFs, and images using FFmpeg and Ghostscript. It provides real-time directory monitoring, OCR support for scanned PDFs, and runs as a background service with system tray integration.

**Key Features:**
- Video/PDF/image compression with quality controls
- OCR support for scanned PDFs using Tesseract
- Real-time directory monitoring with watchdog
- Background service with system tray (Windows)
- Automatic file detection and batch processing

## Project Structure

```
filesqueeze/
├── system/              # Infrastructure services (logger, binaries, config adapters)
├── utils/               # Shared utilities (subprocess helpers)
├── ops/                 # Business logic (video, PDF, image compression)
├── fsm/                 # State machine for file processing
├── handlers.py          # FSM handlers integrating operations
├── service.py           # Background service with directory watching
├── cli.py               # Command-line interface
├── config.py            # Configuration management
├── scanner.py           # File scanner for batch processing
├── ocr.py               # OCR processing for PDFs
├── gui.py               # GUI status window
├── gui_compress.py      # Standalone "Compress a File" dialog (tkinter)
├── standalone.py        # Single-file compression logic (tkinter-free)
├── tray.py              # System tray service
└── autostart.py         # Auto-startup configuration
```

**Critical Rule**: `system/` must NEVER import from `ops/` (prevents circular dependencies).

## Important Commands

### Development Commands
```bash
# Run tests (automatically uses dev mode with production isolation)
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=filesqueeze --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/     # Unit tests only
poetry run pytest tests/integration/  # Integration tests
poetry run pytest tests/smoke/    # Smoke tests

# Static type checking and formatting
ruff check .                      # Type checking
ruff format .                     # Code formatting
ruff check . --fix                # Auto-fix issues
```

### Installation Commands
```bash
# Development installation (editable mode)
.\install-dev.ps1                 # Windows
bash install-dev.sh               # Linux

# System-wide installation
.\install.ps1                     # Windows
bash install.sh                   # Linux

# Generate configuration
poetry run python -m filesqueeze init-config
```

### Application Commands
```bash
# Compress single files
poetry run python -m filesqueeze compress video.mp4
poetry run python -m filesqueeze compress document.pdf

# Compress a single file via GUI dialog (standalone mode)
poetry run python -m filesqueeze compress --gui [file]

# Batch processing
poetry run python -m filesqueeze scan

# Watch mode (directory monitoring)
poetry run python -m filesqueeze watch

# Service mode with tray icon
poetry run python -m filesqueeze service run

# Detect binaries (FFmpeg, Ghostscript, Tesseract)
poetry run python -m filesqueeze detect

# Diagnostics
poetry run python -m filesqueeze doctor
```

## Development Workflow

### Dev Mode Isolation
Tests automatically run in "dev mode" which provides complete isolation from production:
- Separate mutex: `Global\\FileSqueeze_DevInstance_Mutex` (not production)
- No user config: Skips `~/.config/filesqueeze/config.toml`
- Safe directories: Uses `./dev_test_data/` instead of user directories
- Isolated logs: Logs to `./dev_test_data/filesqueeze_dev.log`

**This means you can run tests on a machine where FileSqueeze runs in production!**

### Testing Strategy
- **Unit tests**: Test individual functions in isolation
- **Integration tests**: Test multiple components working together
- **Smoke tests**: Verify core functionality works
- **Regression tests**: Establish baseline behavior
- **System tests**: Test infrastructure components

**Always use `tmp_path` fixture for test files** - never write to user config or production directories.

### Code Quality
- **Pre-commit hooks**: Auto-format with `ruff format` and type check with `ruff check`
- **Git hooks**: Run smoke tests and lockfile checks before pushing
- **Static checking**: Use Ruff for both linting and formatting (replaces Black)

## Documentation Index

### Core Documentation
- [README.md](README.md) - User documentation and quick start guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and design patterns
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development setup and deployment
- [docs/TESTING.md](docs/TESTING.md) - Testing guidelines and safety rules

### Specialized Documentation
- [docs/INSTALLATION_PRINCIPLES.md](docs/INSTALLATION_PRINCIPLES.md) - Installation system design
- [docs/PATH_HANDLING.md](docs/PATH_HANDLING.md) - Cross-platform path handling
- [docs/LOGGING.md](docs/LOGGING.md) - Logging system design
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [docs/CI.md](docs/CI.md) - CI/CD pipeline documentation
- [docs/AGENTS.md](docs/AGENTS.md) - AI agent integration guidelines

### Test Documentation
- [tests/README.md](tests/README.md) - Test structure and organization
- [tests/integration/README.md](tests/integration/README.md) - Integration test documentation
- [tests/regression/README.md](tests/regression/README.md) - Regression test documentation
- [tests/smoke/README.md](tests/smoke/README.md) - Smoke test documentation

## Key Architectural Patterns

### Dependency Injection
Services (logger, binary finder) are registered at startup and accessed via `get_*()` functions throughout the codebase.

### Configuration Cascade
Priority (highest to lowest):
1. Environment variables (`FILESQUEEZE_*`)
2. User config (`~/.config/filesqueeze/config.toml`)
3. Project config (`./filesqueeze.toml`)
4. Default config (`filesqueeze/default.toml`)

### State Machine
File processing uses a state machine pattern defined in `fsm/` with handlers in `handlers.py`. States include: `NEW` → `ANALYZING` → `COMPRESSING` → `OCR` → `DONE`.

## External Dependencies

### Required
- **FFmpeg** - Video and image compression
- **Ghostscript** - PDF compression
- **Python 3.11+** - Runtime environment

### Optional
- **Tesseract OCR** - OCR for scanned PDFs (tests will skip if not installed)

## Common Issues

### Import Errors
- Use `from filesqueeze.ops.video import compress` (not `from filesqueeze.video`)
- Use `from filesqueeze.system.binaries import BinaryFinder` (not `from filesqueeze.binaries`)

### Test Failures
- OCR tests will fail if Tesseract is not installed - this is expected
- Use `pytest -k "not ocr"` to skip OCR tests
- GUI/service tests may fail in headless environments - use `pytest --ignore=tests/integration/test_gui_behavior.py`

### Path Handling
- All paths with `~` are expanded once during config initialization
- Use `config.get()` which returns expanded paths
- No need for `expanduser()` calls throughout codebase

## Status Window Behavior

**When launched from Start Menu or command line:**
- ✅ System tray icon appears immediately
- ✅ Status window opens automatically to show service status

This provides immediate visual feedback that the service is running.

## Single Instance Enforcement

Only one FileSqueeze service instance can run at a time. Attempting to start a second instance displays a helpful error message.

## License

MIT License - See LICENSE file for details