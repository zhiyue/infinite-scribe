"""Unit test configuration - excludes integration test fixtures."""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Only load fixtures needed for unit tests (no testcontainers, no autouse mocks)
pytest_plugins = []
