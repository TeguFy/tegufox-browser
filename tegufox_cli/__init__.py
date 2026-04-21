"""
Tegufox CLI - Command-Line Tools

Command-line interface and REST API server for Tegufox.
Automation functionality is now in tegufox_automation package.
"""

# Re-export automation classes for backward compatibility
from tegufox_automation import (
    TegufoxSession,
    ProfileRotator,
    SessionManager,
    HumanMouse,
    HumanKeyboard,
)

__all__ = [
    "TegufoxSession",
    "ProfileRotator",
    "SessionManager",
    "HumanMouse",
    "HumanKeyboard",
]
