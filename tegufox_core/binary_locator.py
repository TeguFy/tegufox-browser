"""
Tegufox Binary Locator

Single source of truth for finding the locally built Tegufox/Camoufox
browser binary. Used by both the automation runtime (session launch)
and the GUI settings page (display detected path).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Search order: ./build/ first (post-Makefile copy), then in-tree obj-dir,
# then a flat Tegufox.app at the repo root. Both Tegufox- and Camoufox-named
# bundles are accepted because `make rebuild` is sometimes still needed to
# rename the bundle after the first build.
_CANDIDATES = (
    PROJECT_ROOT / "build" / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
    PROJECT_ROOT / "build" / "Camoufox.app" / "Contents" / "MacOS" / "camoufox",
    PROJECT_ROOT / "camoufox-source" / "camoufox-146.0.1-beta.25" / "obj-aarch64-apple-darwin" / "dist" / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
    PROJECT_ROOT / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
)


def auto_detect_binary() -> Optional[str]:
    """Return the first existing browser binary path, or None."""
    for cand in _CANDIDATES:
        if cand.exists():
            return str(cand)
    return None


def search_paths() -> list[str]:
    """Return all candidate paths in priority order (for diagnostics/UI)."""
    return [str(p) for p in _CANDIDATES]
