"""
Pytest configuration file for test discovery and path setup.

This file is automatically loaded by pytest and allows us to:
- Add the parent directory to the Python path so tests can import the app module
- Configure shared test fixtures and settings
"""

import sys
from pathlib import Path

# Add parent directory to Python path so we can import app module
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
