"""
Tegufox Generator v2 — market-weighted profile sampling.

Phase 1's `ProfileManager.generate_template()` is deterministic — caller
picks browser + OS explicitly. Real traffic follows a market distribution,
so a fleet of uniformly-generated profiles stands out. Generator v2 samples
`(browser, os)` tuples from a weighted distribution to match the audience
mix the user expects to blend into.

Extend `MARKET_DISTRIBUTIONS` to reflect your target region. The default
should track https://gs.statcounter.com/browser-market-share but the user
is the source of truth — e.g. Etsy-seller audience skews macOS higher than
global average.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .profile_manager import BROWSER_TEMPLATES, DOH_PROVIDERS, ProfileManager

# TODO USER: Fill in desktop browser+OS weighted distributions (5-8 entries).
# Format: {(browser_template_key, os): probability_weight}
# browser_template_key must exist in BROWSER_TEMPLATES
# os must be one of "windows", "macos", "linux"
# Weights will be normalised automatically, so exact 1.0 sum is not required —
# but keep them proportional to real-world share.
#
# Starter guide (global desktop share, Q1 2026 statcounter approximation):
#   Chrome on Windows ~ 0.42
#   Chrome on macOS   ~ 0.08
#   Safari on macOS   ~ 0.16
#   Firefox on Windows ~ 0.05
#   Firefox on Linux   ~ 0.02
#   Firefox on macOS   ~ 0.01
#   Chrome on Linux    ~ 0.03
#   (Edge/Opera/etc. not modeled here)
MARKET_DISTRIBUTIONS: dict = {
    # Chrome versions (50% total)
    ("chrome-144",  "windows"): 0.22,
    ("chrome-144",  "macos"):   0.05,
    ("chrome-135",  "windows"): 0.12,
    ("chrome-135",  "macos"):   0.03,
    ("chrome-135",  "linux"):   0.02,
    ("chrome-131",  "windows"): 0.04,
    ("chrome-120",  "windows"): 0.02,
    
    # Safari versions (25% total - macOS only)
    ("safari-19",   "macos"):   0.09,
    ("safari-18",   "macos"):   0.10,
    ("safari-17",   "macos"):   0.04,
    ("safari-16",   "macos"):   0.02,
    
    # Firefox versions (25% total)
    ("firefox-145", "windows"): 0.05,
    ("firefox-145", "macos"):   0.01,
    ("firefox-145", "linux"):   0.02,
    ("firefox-140", "windows"): 0.04,
    ("firefox-140", "linux"):   0.02,
    ("firefox-130", "windows"): 0.03,
    ("firefox-128", "windows"): 0.02,
    ("firefox-128", "linux"):   0.01,
    ("firefox-125", "windows"): 0.02,
    ("firefox-120", "windows"): 0.01,
    ("firefox-115", "linux"):   0.02,
}


_SCREEN_BY_OS = {
    "windows": [
        (1920, 1080),
        (1366, 768),
        (2560, 1440),
        (1536, 864),
    ],
    "macos": [
        (2560, 1600),
        (1440, 900),
        (3024, 1964),
        (1920, 1080),
    ],
    "linux": [
        (1920, 1080),
        (2560, 1440),
        (1366, 768),
    ],
}


def sample_browser_os(
    rng: Optional[random.Random] = None,
) -> Tuple[str, str]:
    """Weighted sample of (browser_key, os) from MARKET_DISTRIBUTIONS."""
    if not MARKET_DISTRIBUTIONS:
        raise RuntimeError(
            "MARKET_DISTRIBUTIONS is empty. "
            "Fill in at least one (browser, os) → weight entry in generator_v2.py"
        )

    rng = rng or random
    keys: List[Tuple[str, str]] = list(MARKET_DISTRIBUTIONS.keys())
    weights: List[float] = [MARKET_DISTRIBUTIONS[k] for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]


def sample_screen(os: str, rng: Optional[random.Random] = None) -> Tuple[int, int]:
    rng = rng or random
    choices = _SCREEN_BY_OS.get(os)
    if not choices:
        raise ValueError(f"No screen pool for os={os!r}")
    return rng.choice(choices)


def generate_profile(
    manager: ProfileManager,
    rng: Optional[random.Random] = None,
    doh_provider: Optional[str] = None,
) -> dict:
    """Generate a single profile sampled from market distribution."""
    browser, os = sample_browser_os(rng)
    width, height = sample_screen(os, rng)
    return manager.generate_template(
        browser=browser,
        os=os,
        screen_width=width,
        screen_height=height,
        doh_provider=doh_provider,
    )


def generate_fleet(
    manager: ProfileManager,
    count: int,
    rng: Optional[random.Random] = None,
) -> List[dict]:
    """Generate `count` profiles following the market distribution."""
    rng = rng or random
    return [generate_profile(manager, rng) for _ in range(count)]
