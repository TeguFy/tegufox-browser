"""
Browser version pools and UA builders.

Keeps a single source of truth for "what versions are realistic today" so every
call site (profile_generator, profile_manager, session, generator_v2) rotates
through the same current-year pool.

Pools as of 2026-04-24:
- Firefox: 137 .. 146  (CAPPED at the Tegufox binary's real base version,
           Camoufox 146.0.1-beta.25. Claiming 147+ in UA while the Gecko engine
           is 146 is detectable via JS feature probes — which is exactly the
           `browser claims 150 / detect 146` mismatch the detection site caught.
           Bump this ceiling only when you rebuild the binary on a newer base.)
- Chrome:  138 .. 147  (147 stable 2026-04-07). Tegufox doesn't ship a Chrome
           build; this pool is only used for synthetic profile templates, never
           for the launched browser.
- Safari:  mixed 18.x (macOS 15 Sequoia) and 26.x (macOS 26 Tahoe), 10 entries
           covering the real macOS_token / Safari version pairs people ship.
           Tegufox doesn't ship a Safari build either — same caveat as Chrome.

UA contracts that cannot vary (freezes):
- Firefox on macOS: token pinned at "Intel Mac OS X 10.15" since Firefox 79 (bug 1679929).
- Chrome  on macOS: token pinned at "Intel Mac OS X 10_15_7" since Chrome 90+.
- Windows NT: frozen at "Windows NT 10.0" for both Win10 and Win11 (MS compat).

Safari is the one browser that still varies the macOS token — so its pool pairs
a Safari version with a plausible macOS token.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

# IMPORTANT: these MUST match the Gecko engine exactly.
# Tegufox ships `camoufox-source/camoufox-146.0.1-beta.25/` whose
# `config/milestone.txt` is `146.0.1`. Any UA version *other than* a real
# 146.0.x point release is detectable via JS feature probes — we saw both
# "claims 150 / detect 146" and "claims 143 / detect 146" banners, proving
# the detector bypasses UA and reads engine-level feature presence.
#
# When the binary is rebuilt on a newer base: update BOTH this constant AND
# the camoufox-source directory name. They are the single source of truth.
TEGUFOX_FIREFOX_BASE_MAJOR = 146
TEGUFOX_FIREFOX_MILESTONE  = "146.0.1"
# Real Firefox 146.0.x point releases (Mozilla normally ships 146.0 + 1-3
# dot-patches before advancing to 147). We rotate only across shipped
# point releases so every profile's UA remains feature-consistent with
# the engine.
FIREFOX_LATEST_VERSIONS: List[str] = ["146.0", "146.0.1"]
CHROME_LATEST_VERSIONS:  List[int] = [138, 139, 140, 141, 142, 143, 144, 145, 146, 147]

# Safari observed-in-the-wild desktop pairs. Each entry:
#   version      -> Version/<x> Safari/605.1.15 in UA
#   macos_token  -> the "Intel Mac OS X <token>" value
#   macos_label  -> informational only, for debugging/UI surfaces
# macOS Tahoe 26.4.1 is current (2026-04-09). Heavy bias toward 26.x Tahoe; keep
# two Sequoia entries for users who haven't upgraded to Tahoe yet.
SAFARI_LATEST_COMBOS: List[Dict[str, str]] = [
    {"version": "18.4",   "macos_token": "15_4",   "macos_label": "macOS Sequoia 15.4"},
    {"version": "18.5",   "macos_token": "15_5",   "macos_label": "macOS Sequoia 15.5"},
    {"version": "26.0",   "macos_token": "26_0",   "macos_label": "macOS Tahoe 26.0"},
    {"version": "26.0.1", "macos_token": "26_0_1", "macos_label": "macOS Tahoe 26.0.1"},
    {"version": "26.1",   "macos_token": "26_1",   "macos_label": "macOS Tahoe 26.1"},
    {"version": "26.1.1", "macos_token": "26_1_1", "macos_label": "macOS Tahoe 26.1.1"},
    {"version": "26.2",   "macos_token": "26_2",   "macos_label": "macOS Tahoe 26.2"},
    {"version": "26.3",   "macos_token": "26_3",   "macos_label": "macOS Tahoe 26.3"},
    {"version": "26.4",   "macos_token": "26_4",   "macos_label": "macOS Tahoe 26.4"},
    {"version": "26.4.1", "macos_token": "26_4_1", "macos_label": "macOS Tahoe 26.4.1"},
]

# Frozen UA tokens — do NOT override these from profile data.
FIREFOX_MAC_TOKEN_FROZEN = "10.15"
CHROME_MAC_TOKEN_FROZEN  = "10_15_7"


def random_firefox_version(rng: Optional[random.Random] = None) -> str:
    """Return a Firefox version string like '146.0' or '146.0.1'."""
    return (rng or random).choice(FIREFOX_LATEST_VERSIONS)


def _firefox_rv_token(version: str) -> str:
    """Extract the `rv:` token — Firefox keeps `rv:MAJOR.0` even on dot-patches."""
    major = version.split(".")[0]
    return f"{major}.0"


def random_chrome_version(rng: Optional[random.Random] = None) -> int:
    return (rng or random).choice(CHROME_LATEST_VERSIONS)


def random_safari_combo(rng: Optional[random.Random] = None) -> Dict[str, str]:
    return dict((rng or random).choice(SAFARI_LATEST_COMBOS))


def build_firefox_ua(os_name: str, version: Optional[str] = None) -> str:
    """Build a Firefox UA.

    `version` accepts either a full point release like '146.0.1' or a major-only
    string like '146'. The `rv:` token always renders as MAJOR.0 (Mozilla
    convention); `Firefox/` renders the full version as provided.
    """
    v = str(version) if version is not None else random_firefox_version()
    # Back-compat: accept int-like values by round-tripping through str().
    rv = _firefox_rv_token(v)
    if os_name == "windows":
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{rv}) Gecko/20100101 Firefox/{v}"
    if os_name == "macos":
        return (
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X {FIREFOX_MAC_TOKEN_FROZEN}; rv:{rv}) "
            f"Gecko/20100101 Firefox/{v}"
        )
    if os_name == "linux":
        return f"Mozilla/5.0 (X11; Linux x86_64; rv:{rv}) Gecko/20100101 Firefox/{v}"
    raise ValueError(f"Unknown os: {os_name!r}")


def firefox_build_id_for(version: str) -> str:
    """Return a plausible 20YYMMDDHHMMSS buildID that matches the engine.

    Tegufox's real Gecko is 146.0.1. Firefox 146 line released ~2025-12-30,
    146.0.1 ~2026-01-08. Using a single date-of-build keeps navigator.buildID
    self-consistent with the engine, so detectors that cross-check buildID
    against Mozilla's release calendar get a plausible answer.
    """
    calendar = {
        "146.0":   "20251230000000",
        "146.0.1": "20260108000000",
        "146.0.2": "20260122000000",
    }
    return calendar.get(str(version), "20260108000000")


def build_chrome_ua(os_name: str, version: Optional[int] = None) -> str:
    v = version if version is not None else random_chrome_version()
    if os_name == "windows":
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"
        )
    if os_name == "macos":
        return (
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X {CHROME_MAC_TOKEN_FROZEN}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"
        )
    if os_name == "linux":
        return (
            f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"
        )
    raise ValueError(f"Unknown os: {os_name!r}")


def build_safari_ua(combo: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return a Safari UA + the combo dict used, so callers can store metadata."""
    c = combo or random_safari_combo()
    ua = (
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X {c['macos_token']}) "
        f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{c['version']} Safari/605.1.15"
    )
    return {"userAgent": ua, "version": c["version"], "macos_token": c["macos_token"], "macos_label": c["macos_label"]}


if __name__ == "__main__":
    print("Firefox pool:", FIREFOX_LATEST_VERSIONS)
    print("Chrome pool: ", CHROME_LATEST_VERSIONS)
    print("Safari pool: ", [c["version"] + " on " + c["macos_label"] for c in SAFARI_LATEST_COMBOS])
    print()
    for os_ in ("windows", "macos", "linux"):
        print(f"Firefox/{os_}:", build_firefox_ua(os_))
        print(f"Chrome/{os_}: ", build_chrome_ua(os_))
    for _ in range(3):
        s = build_safari_ua()
        print("Safari:      ", s["userAgent"])
