# CI/CD Pipeline for FileSqueeze

## Overview

This CI pipeline ensures code quality, test coverage, and integration testing for the FileSqueeze project.

## Workflow Structure

### 1. Quick Checks (Every Push)
Runs on every push to any branch:
- **Smoke Tests**: Critical imports and basic functionality
- **Unit Tests**: Fast, isolated component tests  
- **System Tests**: Configuration, circular imports, logger tests
- **Code Quality**: Ruff formatting + linting + type checking

### 2. Integration Tests (PRs Only)
Runs on pull requests to main/develop branches:
- **Integration Tests**: Real file compression with FFmpeg/Ghostscript
- **Regression Tests**: Behavioral baseline checks
- Platform: Linux only (GUI/service tests excluded)

### 3. Coverage Report (PRs Only)
Runs on pull requests to main/develop branches:
- Generates coverage reports for unit/smoke/system tests
- Uploads to Codecov for tracking

## Test Categories

### ✅ Run in CI
- `tests/smoke/` - Critical functionality validation
- `tests/unit/` - Component-level testing
- `tests/system/` - Configuration and import testing
- `tests/integration/` - Real binary testing (Linux only)
- `tests/regression/` - Behavioral baseline validation

### ❌ Skip in CI
- GUI tests (require display server)
- Service tests (require Windows services)
- Installer tests (require system-level access)

## Code Quality Tools

### Pre-commit Hooks
- **Purpose**: Automatically format and validate code before commits
- **Tools**: Ruff (formatting + linting + type checking)
- **Setup**: Run `bash .githooks/install.sh` (Linux/macOS) or `powershell .githooks\install.ps1` (Windows)
- **Action**: Auto-formats Python files and validates type annotations on every commit

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
- [ ] Add security scanning (bandit)
- [ ] Windows CI runner for GUI/service tests
- [ ] Documentation building tests