"""
Migration: backfill `browser` column, repair malformed Firefox macOS UA,
and normalise legacy WebGL renderer strings (", or similar" suffix).

Idempotent. Run: python3 scripts/fix_profile_data.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tegufox_core.database import (
    ProfileDatabase,
    Profile,
    Navigator,
    WebGL,
    DNSConfig,
    FirefoxPreference,
)
from tegufox_core.browser_versions import (
    FIREFOX_LATEST_VERSIONS,
    SAFARI_LATEST_COMBOS,
    build_firefox_ua,
    build_safari_ua,
)


_FIREFOX_MAC_FALLBACK_VERSION = "115.0"
FIREFOX_MAC_UA_GOOD = (
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{_FIREFOX_MAC_FALLBACK_VERSION}) "
    f"Gecko/20100101 Firefox/{_FIREFOX_MAC_FALLBACK_VERSION}"
)
# Legacy mis-generated UA that spliced Chrome AppleWebKit token into a Firefox UA.
FIREFOX_MAC_UA_BAD = re.compile(
    r"Mozilla/5\.0 \(Macintosh; Intel Mac OS X [\d_\.]+\) "
    r"AppleWebKit/537\.36.+Firefox/[\d\.]+"
)
# Firefox freezes macOS version at 10.15 since v79. Any other value is a fingerprint leak.
FIREFOX_MAC_OS_WRONG = re.compile(
    r"^(Mozilla/5\.0 \(Macintosh; Intel Mac OS X )(?!10\.15;)([\d_\.]+)(;"
    r" rv:[\d\.]+\) Gecko/\d+ Firefox/[\d\.]+)$"
)


def detect_browser(ua: str) -> str | None:
    if not ua:
        return None
    if "Firefox/" in ua and "Gecko/" in ua:
        return "firefox"
    if "Safari/" in ua and "Version/" in ua and "Chrome/" not in ua:
        return "safari"
    if "Chrome/" in ua and "Edg/" not in ua and "OPR/" not in ua:
        return "chrome"
    return None


def normalise_renderer(renderer: str) -> str:
    if not renderer:
        return renderer
    cleaned = renderer.replace(", or similar", "")
    return re.sub(r"\s+", " ", cleaned).strip()


FIREFOX_VERSION_IN_UA = re.compile(r"Firefox/(\d+)\.")
SAFARI_VERSION_IN_UA = re.compile(r"Version/([\d\.]+) Safari/")


def _needs_firefox_refresh(ua: str) -> bool:
    """True if UA's Firefox version is outside the current pool (too old or
    above the Tegufox engine ceiling — both are spoof-detectable)."""
    m = FIREFOX_VERSION_IN_UA.search(ua or "")
    if not m:
        return False
    return int(m.group(1)) not in FIREFOX_LATEST_VERSIONS


def _needs_safari_refresh(ua: str) -> bool:
    m = SAFARI_VERSION_IN_UA.search(ua or "")
    if not m:
        return False
    current = {c["version"] for c in SAFARI_LATEST_COMBOS}
    return m.group(1) not in current


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--refresh-versions",
        action="store_true",
        help="Re-roll UA on any Firefox profile older than the latest-10 pool "
             "and any Safari profile whose version isn't in the current pool.",
    )
    args = ap.parse_args()

    db = ProfileDatabase()
    session = db.get_session()

    fixes = {
        "browser_backfill": 0,
        "ua_repair": 0,
        "ua_freeze_macos": 0,
        "ua_version_refresh": 0,
        "renderer_normalise": 0,
        "doh_provider_updated": 0,
    }

    try:
        profiles = session.query(Profile).all()
        for p in profiles:
            nav: Navigator | None = p.navigator
            wgl: WebGL | None = p.webgl

            if nav and FIREFOX_MAC_UA_BAD.match(nav.user_agent or ""):
                print(f"[ua]      {p.name}: repair malformed Firefox macOS UA")
                if not args.dry_run:
                    nav.user_agent = FIREFOX_MAC_UA_GOOD
                fixes["ua_repair"] += 1

            if nav:
                m = FIREFOX_MAC_OS_WRONG.match(nav.user_agent or "")
                if m:
                    fixed_ua = f"{m.group(1)}10.15{m.group(3)}"
                    print(f"[osver]   {p.name}: {m.group(2)!r} -> '10.15' (Firefox freezes macOS token)")
                    if not args.dry_run:
                        nav.user_agent = fixed_ua
                    fixes["ua_freeze_macos"] += 1

            if not p.browser and nav and nav.user_agent:
                ua_for_detect = (
                    FIREFOX_MAC_UA_GOOD
                    if FIREFOX_MAC_UA_BAD.match(nav.user_agent)
                    else nav.user_agent
                )
                inferred = detect_browser(ua_for_detect)
                if inferred:
                    print(f"[browser] {p.name}: None -> {inferred}")
                    if not args.dry_run:
                        p.browser = inferred
                    fixes["browser_backfill"] += 1

            if args.refresh_versions and nav and nav.user_agent:
                browser = p.browser or detect_browser(nav.user_agent)
                os_name = p.os
                if browser == "firefox" and _needs_firefox_refresh(nav.user_agent):
                    new_ua = build_firefox_ua(os_name)
                    print(f"[refresh] {p.name}: firefox UA -> {new_ua[:70]}...")
                    if not args.dry_run:
                        nav.user_agent = new_ua
                    fixes["ua_version_refresh"] += 1
                elif browser == "safari" and _needs_safari_refresh(nav.user_agent):
                    new_ua = build_safari_ua()["userAgent"]
                    print(f"[refresh] {p.name}: safari UA -> {new_ua[:70]}...")
                    if not args.dry_run:
                        nav.user_agent = new_ua
                    fixes["ua_version_refresh"] += 1

            # DoH provider refresh: standard Cloudflare endpoint
            # `cloudflare-dns.com` (NOT the `mozilla.` partner variant — it
            # has privacy filters that refuse certain domains, e.g. fv.pro).
            cloudflare_uri = "https://cloudflare-dns.com/dns-query"
            cloudflare_bootstrap = "1.1.1.1"
            dns_cfg: DNSConfig | None = p.dns_config
            if dns_cfg and dns_cfg.doh_uri and dns_cfg.doh_uri != cloudflare_uri:
                print(f"[doh]     {p.name}: {dns_cfg.doh_uri} -> {cloudflare_uri}")
                if not args.dry_run:
                    dns_cfg.doh_uri = cloudflare_uri
                    dns_cfg.doh_bootstrap_address = cloudflare_bootstrap
                    dns_cfg.provider = "cloudflare"
                fixes["doh_provider_updated"] += 1
            # Firefox prefs also carry trr.uri / trr.bootstrapAddress — update both.
            for pref in p.firefox_prefs or []:
                if pref.key == "network.trr.uri" and pref.value != f'"{cloudflare_uri}"':
                    if not args.dry_run:
                        pref.value = f'"{cloudflare_uri}"'
                if pref.key == "network.trr.bootstrapAddress" and pref.value != f'"{cloudflare_bootstrap}"':
                    if not args.dry_run:
                        pref.value = f'"{cloudflare_bootstrap}"'

            if wgl and wgl.renderer:
                norm = normalise_renderer(wgl.renderer)
                if norm != wgl.renderer:
                    print(f"[renderer] {p.name}: {wgl.renderer!r} -> {norm!r}")
                    if not args.dry_run:
                        wgl.renderer = norm
                    fixes["renderer_normalise"] += 1

        if not args.dry_run:
            session.commit()
            print("\nCommitted.")
        else:
            print("\nDry-run: no changes written.")

        print("Summary:", fixes)
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
