# FileSqueeze Tests

This directory contains all tests for the FileSqueeze project.

## Test Structure

- `test_config.py` - Tests for the configuration module
- `test_logger.py` - Tests for the logging module
- More test files will be added as the project grows

## Running Tests

### Run all tests:
```bash
poetry run pytest
```

### Run specific test file:
```bash
poetry run pytest tests/test_config.py
```

### Run with coverage:
```bash
poetry run pytest --cov=filesqueeze --cov-report=html
```

### Run with verbose output:
```bash
poetry run pytest -v
```

## Test Organization

Tests are organized by module/functionality:
- Each major module has its own test file
- Test files follow the pattern `test_<module>.py`
- Test functions follow the pattern `test_<functionality>()`

## Adding New Tests

When adding new functionality:
1. Create a new test file in this directory
2. Import necessary modules
3. Write test functions using pytest
4. Run tests to verify they pass

Example:
```python
"""Test my new module."""

import pytest
from filesqueeze.mymodule import my_function

def test_my_function_basic():
    """Test basic functionality."""
    result = my_function()
    assert result is not None
```
