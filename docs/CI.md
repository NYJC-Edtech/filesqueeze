# CI/CD Pipeline for FileSqueeze

## Overview

This CI pipeline ensures code quality, test coverage, and integration testing for the FileSqueeze project.

## Workflow Structure

All jobs run on every push to any branch (see `.github/workflows/ci.yml`
for the source of truth):

- **Smoke Tests**: Critical imports and basic functionality
- **Unit Tests**: Fast, isolated component tests
- **System Tests**: Configuration, circular imports, logger tests (with FFmpeg/Ghostscript installed)
- **GUI Widget Tests**: In-process tkinter tests for CompressDialog, run under xvfb (headless display); the tests skip cleanly where no display exists
- **Code Quality**: Ruff formatting + linting + type checking (on `filesqueeze/`)
- **Coverage Report**: Coverage over unit/smoke/system tests, uploaded to Codecov

## Test Categories

### ✅ Run in CI
- `tests/smoke/` - Critical functionality validation
- `tests/unit/` - Component-level testing
- `tests/system/` - Configuration and import testing
- `tests/integration/test_gui_widgets.py` - Real tkinter widget tests (under xvfb)

### ❌ Not in CI
- `tests/integration/` (except the widget tests) and `tests/regression/` —
  real-binary, service, installer, and single-instance tests; the
  integration job exists in `ci.yml` but is commented out. Run the full
  suite locally (`poetry run pytest`) or via the pre-push hook.

## Code Quality Tools

### Git Hooks

**Pre-commit Hook:**
- **Purpose**: Automatically format and validate code before commits
- **Tools**: Ruff (formatting + type checking) + pytest (smoke tests)
- **Action**: Auto-formats code, validates type annotations, and runs smoke tests

**Post-edit Hook:**
- **Purpose**: Auto-format Python files after editing
- **Tools**: Ruff formatter
- **Action**: Formats Python files when saved

**Pre-push Hook:**
- **Purpose**: Prevent pushing desynchronized poetry lockfiles
- **Tools**: Poetry lock check
- **Action**: Blocks push if poetry.lock is out of sync with pyproject.toml

**Setup:**
```bash
# Linux/macOS
bash .githooks/install.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .githooks\install.ps1
```

### Ruff
- **Purpose**: All-in-one Python formatting and linting
- **Formatting**: 127 character line length, double quotes, Python 3.11 target
- **Linting**: Major code quality issues and correctness checks
- **Type Checking**: Type annotation validation (ANN rules)
- **Action**: Runs via git hooks and CI for comprehensive code quality

## Platform Support

### Primary
- **Linux (Ubuntu)**: All non-GUI tests
- **Python 3.11**: Target Python version

### Secondary  
- **Windows**: Local development, full testing
- **macOS**: Not currently tested in CI

## Dependencies

### System-Level (Installed in CI)
- **FFmpeg**: Video/image compression
- **Ghostscript**: PDF compression

### Python-Level
- Managed via Poetry
- Cached for faster builds

## Troubleshooting

### Common Issues

**Ruff formatting failures:**
```bash
# Locally format code
poetry run ruff format filesqueeze/ tests/

# Check formatting without making changes
poetry run ruff format --check filesqueeze/ tests/
```

**Ruff linting warnings:**
```bash
# Run linting locally
poetry run ruff check filesqueeze/ tests/

# Auto-fix issues where possible
poetry run ruff check --fix filesqueeze/ tests/
```

**Type annotation failures:**
```bash
# Check type annotations locally
poetry run ruff check filesqueeze/ tests/ --select ANN

# Auto-fix issues where possible
poetry run ruff check --fix filesqueeze/ tests/ --select ANN
```

**Integration test failures:**
- Ensure test fixtures are present in `tests/fixtures/`
- Check that FFmpeg/Ghostscript are installed locally
- Some tests are platform-specific and may skip on Linux

### CI Performance

- **Poetry cache**: Speeds up dependency installation
- **Parallel jobs**: Quick checks run independently
- **Conditional execution**: Integration tests only run on PRs

## Local Testing

### Setup Git Hooks (Recommended)
```bash
# Install git hooks for auto-formatting and validation
# Linux/macOS:
bash .githooks/install.sh

# Windows PowerShell:
powershell -ExecutionPolicy Bypass -File .githooks\install.ps1

# Now your code will be automatically formatted and validated before each commit
```

### Quick Check (What runs on push)
```bash
# Pre-commit hooks handle formatting automatically
# Just run tests
poetry run pytest tests/smoke/ tests/unit/ tests/system/ -v
```

### Manual Formatting (If needed)
```bash
# Format all files manually
poetry run ruff format filesqueeze/ tests/

# Check formatting without making changes
poetry run ruff format --check filesqueeze/ tests/

# Run all quality checks
poetry run ruff format filesqueeze/ tests/ && poetry run ruff check filesqueeze/ tests/
```

### Full Test Suite (What runs on PR)
```bash
# Install system dependencies first
sudo apt-get install ffmpeg ghostscript

# Run all tests
poetry run pytest tests/ -v --ignore=tests/integration/test_gui_behavior.py
```

## Future Improvements

- [x] Add git hooks for auto-formatting and type checking
- [x] Replace Black with Ruff for all-in-one formatting and linting
- [ ] Windows CI runner for GUI/service tests