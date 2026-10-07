"""Locate application assets in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Return an asset path from the project root or PyInstaller bundle."""
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / relative_path
