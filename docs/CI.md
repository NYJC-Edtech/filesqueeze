# CI/CD Pipeline for FileSqueeze

## Overview

This CI pipeline ensures code quality, test coverage, and integration testing for the FileSqueeze project.

## Workflow Structure

### 1. Quick Checks (Every Push)
Runs on every push to any branch:
- **Smoke Tests**: Critical imports and basic functionality
- **Unit Tests**: Fast, isolated component tests  
- **System Tests**: Configuration, circular imports, logger tests
- **Code Quality**: Black formatting checks + flake8 linting

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

### Black
- **Purpose**: Code formatting consistency
- **Config**: 127 character line length, Python 3.11 target
- **Action**: Fails if code isn't properly formatted

### flake8
- **Purpose**: Python linting
- **Config**: 127 character line length, ignores E203/E501/W503
- **Action**: Shows errors/warnings but doesn't fail on style issues

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

**Black formatting failures:**
```bash
# Locally format code
poetry run black filesqueeze/ tests/
```

**flake8 warnings:**
```bash
# Run linting locally
poetry run flake8 filesqueeze/ tests/
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

### Quick Check (What runs on push)
```bash
poetry run pytest tests/smoke/ tests/unit/ tests/system/ -v
poetry run black --check filesqueeze/ tests/
poetry run flake8 filesqueeze/ tests/
```

### Full Test Suite (What runs on PR)
```bash
# Install system dependencies first
sudo apt-get install ffmpeg ghostscript

# Run all tests
poetry run pytest tests/ -v --ignore=tests/integration/test_gui_behavior.py
```

## Future Improvements

- [ ] Add pre-commit hooks configuration
- [ ] Add security scanning (bandit)
- [ ] Add type checking (mypy)
- [ ] Windows CI runner for GUI/service tests
- [ ] Performance benchmarking tests
- [ ] Documentation building tests