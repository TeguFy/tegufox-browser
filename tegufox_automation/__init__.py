"""
Tegufox Automation - Browser Automation Framework

High-level automation layer for anti-detection browser automation.
Can be used from both GUI and CLI interfaces.

Features:
- TegufoxSession: Playwright/Camoufox wrapper with anti-detection
- HumanMouse: Realistic mouse movements (Bezier curves, Fitts's Law)
- HumanKeyboard: Human-like typing with typos and timing variance
- ProfileRotator: Multi-account session management
- SessionManager: Persistent session state
"""

from .session import TegufoxSession, ProfileRotator, SessionManager, SessionConfig, SessionState
from .mouse import HumanMouse, MouseConfig, Point
from .keyboard import HumanKeyboard, KeyboardConfig

__all__ = [
    # Session Management
    "TegufoxSession",
    "ProfileRotator",
    "SessionManager",
    "SessionConfig",
    "SessionState",
    
    # Mouse Control
    "HumanMouse",
    "MouseConfig",
    "Point",
    
    # Keyboard Control
    "HumanKeyboard",
    "KeyboardConfig",
]
