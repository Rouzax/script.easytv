"""Shared pytest configuration for EasyTV tests."""
import os
import sys

import pytest

# Add project root to sys.path so 'from resources.lib...' imports work
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture(autouse=True, scope="session")
def reset_logger():
    """Reset StructuredLogger between test sessions to prevent cross-test pollution."""
    from resources.lib.utils import StructuredLogger
    StructuredLogger._initialized = False
    yield
    StructuredLogger._initialized = False
