# FileSqueeze Tests

This directory contains all tests for the FileSqueeze project, organized by test type and scope.

## Test Structure

### Smoke Tests (`smoke/`) 🆕
**Fast critical system checks** (< 30 seconds) - Run as pre-commit hooks
- `test_critical_imports.py` - Verifies all critical modules can be imported
- `test_core_instantiation.py` - Verifies core classes can be instantiated
- `test_data_structure_integrity.py` - Verifies data structures are intact
- `test_api_integrity.py` - Verifies public API is functional

**Purpose**: Check for show-stopper issues that users cannot fix themselves (broken imports, corrupted codebase, missing API functions).

**Runtime**: ~4 seconds

### Unit Tests (`unit/`)
Tests for individual modules and components in isolation.
- `test_document.py` - Document compression functionality
- `test_video.py` - Video compression functionality
- `test_output.py` - Output path generation and metadata handling
- `test_scanner.py` - File scanner functionality
- `test_retention.py` - Retention manager functionality
- `test_cleanup_manual.py` - Manual trigger for retention cleanup testing

### Integration Tests (`integration/`)
Tests for system invariants, end-to-end behavior, and component integration.
- `test_invariants.py` - System invariant verification (PRD requirements)
- `test_integration.py` - Integration tests with real files and binaries
- `test_service.py` - Service module integration (StateProvider, DirectoryWatcher)
- `test_handlers.py` - Handlers and state machine integration
- `test_gui_behavior.py` - GUI behavioral tests at code level
- `test_single_instance.py` - Single instance enforcement tests
- `test_installers.py` - Installation and uninstallation testing

### System Tests (`system/`)
Tests for system-level components and infrastructure.
- `test_config_adapters.py` - Configuration adapter patterns
- `test_config.py` - Configuration module functionality
- `test_logger.py` - Logging module and system logger registration
- `test_circular_imports.py` - Dependency rule enforcement and import patterns

### Regression Tests (`regression/`)
Tests to prevent regression of fixed bugs and establish behavioral baselines.
- `test_behavioral_baseline.py` - Behavioral baseline for refactoring validation

## Running Tests

### Run all tests:
```bash
poetry run pytest
```

### Run smoke tests (recommended pre-commit):
```bash
# Quick smoke test
pytest tests/smoke/ -v

# Ultra-fast smoke test (critical imports only)
pytest tests/smoke/test_critical_imports.py -v
```

### Run specific test category:
```bash
# Unit tests only
poetry run pytest tests/unit/

# Integration tests only
poetry run pytest tests/integration/

# System tests only
poetry run pytest tests/system/

# Regression tests only
poetry run pytest tests/regression/
```

### Run specific test file:
```bash
poetry run pytest tests/unit/test_document.py
```

### Run with coverage:
```bash
poetry run pytest --cov=filesqueeze --cov-report=html
```

### Run with verbose output:
```bash
poetry run pytest -v
```

## Pre-Commit Hooks 🆕

FileSqueeze includes automatic pre-commit hooks that run smoke tests before each commit to ensure you don't break critical system functionality.

### Install pre-commit hooks:

**Linux/Mac:**
```bash
bash .githooks/install.sh
```

**Windows:**
```powershell
powershell .githooks/install.ps1
```

### Manual installation:
```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Smoke tests will:
- Run automatically before each commit
- Take ~4 seconds
- Only check critical system health (imports, API integrity, core classes)
- Block commits that break basic functionality
- NOT check user-fixable issues (missing binaries, config problems, etc.)

### Bypass smoke tests (if needed):
```bash
git commit --no-verify
```

## Test Organization Philosophy

**Smoke Tests (`smoke/`) 🆕**
- **Fastest** (< 30 seconds, currently ~4 seconds)
- **Critical path only** - basic system health
- **No external dependencies** - works even without binaries
- **Pre-commit integration** - fail fast on broken code
- **User focus** - checks only unfixable-by-user issues

**Unit Tests (`unit/`)**
- Test individual modules in isolation
- Focus on single functionality per test
- Use mocks/stubs for external dependencies
- Fast execution, no external dependencies

**Integration Tests (`integration/`)**
- Test multiple components working together
- Verify system invariants and PRD requirements
- Use real files, binaries, and system components
- May be slower but validate actual system behavior

**System Tests (`system/`)**
- Test infrastructure and cross-cutting concerns
- Configuration, logging, dependency management
- System-level patterns and conventions
- Verify architectural constraints

**Regression Tests (`regression/`)**
- Prevent previously fixed bugs from recurring
- Establish behavioral baselines before refactoring
- Compare before/after behavior for major changes
- Document and validate expected behavior

## Adding New Tests

When adding new functionality:

1. **Smoke tests** 🆕: Add to `tests/smoke/` for critical system health checks
2. **Unit tests**: Add to `tests/unit/test_<module>.py` for isolated component testing
3. **Integration tests**: Add to `tests/integration/` for cross-component behavior
4. **System tests**: Add to `tests/system/` for infrastructure concerns
5. **Regression tests**: Add to `tests/regression/` when fixing bugs or refactoring

Example smoke test:
```python
"""Test critical module availability."""

def test_my_module_imports():
    """Critical module must be importable."""
    from filesqueeze import my_module
    assert my_module is not None
```

Example unit test:
```python
"""Test my new module."""

import pytest
from filesqueeze.mymodule import my_function

def test_my_function_basic():
    """Test basic functionality."""
    result = my_function()
    assert result is not None
```

Example integration test:
```python
"""Test integration of multiple components."""

import pytest
from filesqueeze.service import DirectoryWatcher
from filesqueeze.config import Config

def test_service_integration(tmp_path):
    """Test service components working together."""
    config = Config()
    watcher = DirectoryWatcher(tmp_path, tmp_path / "output", config)
    # Test actual integration behavior
```

## Continuous Integration

Test execution order in CI/CD:
1. **Smoke tests** (4s) - Fail fast on critical issues
2. **Unit tests** (30s) - Verify component behavior
3. **Integration tests** (60s) - Validate system behavior
4. **Full test suite** (2-3min) - Complete validation
