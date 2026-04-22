"""Utility modules for Tegufox GUI"""

from .styles import DarkPalette
from .config import (
    PLATFORM_TEMPLATES,
    generate_random_seed,
    create_profile_data,
)

__all__ = [
    "DarkPalette",
    "PLATFORM_TEMPLATES",
    "generate_random_seed",
    "create_profile_data",
]
