"""Pytest configuration for FileSqueeze tests."""

import sys
from pathlib import Path

# Add parent directory to path so we can import filesqueeze
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
