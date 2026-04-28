# Smoke Tests for FileSqueeze

Fast, critical tests that verify basic system functionality. These tests check for show-stopper issues that users cannot fix themselves.

## Purpose

Smoke tests provide quick validation (under 30 seconds) that:
- The FileSqueeze installation is not corrupted
- All critical modules can be imported
- Core classes can be instantiated
- Data structures are intact
- The public API is functional

## What These Tests Check

✅ **Critical System Health**
- Import failures and circular dependencies
- Core module loading issues
- Basic class instantiation
- Data structure integrity
- API availability

❌ **What These Tests Do NOT Check** (User-Fixable Issues)
- Missing external binaries (ffmpeg, gs, etc.)
- Configuration file problems
- Permission issues
- Network connectivity
- Disk space issues

## Running Smoke Tests

### Run all smoke tests:
```bash
# Fast smoke test (default)
pytest tests/smoke/ -v

# Ultra-fast smoke test (critical imports only)
pytest tests/smoke/test_critical_imports.py -v
```

### Run as pre-commit check:
```bash
# Automatically runs before each commit
pytest tests/smoke/ -q
```

## Test Files

- **`test_critical_imports.py`** - Verifies all critical modules can be imported
- **`test_core_instantiation.py`** - Verifies core classes can be instantiated
- **`test_data_structure_integrity.py`** - Verifies data structures are intact
- **`test_api_integrity.py`** - Verifies public API is functional

## Expected Runtime

- **Critical imports**: ~2 seconds
- **Core instantiation**: ~1 second
- **Data structure integrity**: ~1 second
- **API integrity**: ~1 second
- **Total smoke test suite**: ~5 seconds

## Pre-Commit Integration

These smoke tests are designed to run as pre-commit hooks to ensure commits don't break basic system functionality.

### Add to pre-commit hook:
```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/smoke/ -q || exit 1
```

### Install pre-commit hook:
```bash
# Copy the pre-commit hook to .git/hooks/
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Failure Diagnostics

If smoke tests fail, it indicates:

1. **Import Failures** → Broken installation, circular dependencies, or corrupted codebase
2. **Instantiation Failures** → Broken class definitions or missing dependencies
3. **Data Structure Failures** → Corrupted dataclass definitions or type issues
4. **API Failures** → Broken exports or missing functions

All of these require developer intervention - users cannot fix these issues themselves.

## Continuous Integration

Smoke tests should run:
- **Before every commit** (pre-commit hook)
- **In CI/CD pipeline** (first line of defense)
- **After installation** (verify installation succeeded)
- **Before full test suite** (fail fast on critical issues)

## Maintenance

When adding new critical modules or APIs:
1. Add corresponding smoke test
2. Keep tests fast (no external dependencies)
3. Focus on show-stopper issues only
4. Update this README if test scope changes