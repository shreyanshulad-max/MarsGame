"""Central resource and executable path helpers for development and PyInstaller builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def executable_dir() -> Path:
    """Directory containing the running executable or the main script."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """
    Root for bundled read-only game resources (assets/, etc.).

    - Development: project root (folder containing main.py)
    - PyInstaller onedir/onefile: sys._MEIPASS extraction / bundle root
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    # Prefer the directory of main.py when available
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if main_file and not is_frozen():
        candidate = Path(main_file).resolve().parent
        if (candidate / "assets").is_dir() or (candidate / "main.py").is_file():
            return candidate
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return resource_root() / "assets"


def research_data_dir() -> Path:
    return assets_dir() / "research_data"


def resource_path(*parts: str) -> Path:
    """Join path parts under the resource root."""
    return resource_root().joinpath(*parts)


def can_write_resources() -> bool:
    """Bundled resources are read-only; never mkdir/write into them when frozen."""
    return not is_frozen()
