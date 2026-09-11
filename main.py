"""
QueryPilot — Root Entry Point

Allows running uvicorn directly from the workspace root:
    uvicorn main:app --reload --port 8000
or
    uvicorn app.main:app --reload --port 8000
"""

import os
import sys

# Ensure src directory and subpackages are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_current_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

_agents_dir = os.path.join(_src_dir, "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

# Import the master FastAPI application from app.main
from app.main import app  # noqa: E402

__all__ = ["app"]
