"""Component test configuration."""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Component tests use aioresponses and real HTTP behavior patterns
pytest_plugins = []