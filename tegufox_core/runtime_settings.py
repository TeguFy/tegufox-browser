"""Centralised access to data/settings.conf — single source of truth.

The file is the same `ast.literal_eval`-parseable dict the Settings page
already writes. This module gives every other component (TegufoxSession,
flow runtime, GUI pages) a stable read path so we don't duplicate the
load logic in five places.

Schema is open: callers ask for a key + default. The currently used keys:

  profiles_dir         (str)   — where profile JSON lives
  api_port             (int)   — REST API server port
  browser_binary       (str)   — path to Camoufox binary
  rules                (dict)  — fingerprint rule toggles
  market_weights       (dict)  — profile-generation weights
  disable_popups       (bool)  — global window.open override toggle
                                 (NEW, default True)
"""

from __future__ import annotations
import ast
from pathlib import Path
from typing import Any, Dict


SETTINGS_PATH = Path("data/settings.conf")


def load_settings() -> Dict[str, Any]:
    """Read and return the settings dict; empty dict on error / absent."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        raw = ast.literal_eval(SETTINGS_PATH.read_text())
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Read-modify-write a single key. Used by tests and one-off CLI flags."""
    import pprint
    current = load_settings()
    current[key] = value
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(pprint.pformat(current, sort_dicts=True))
