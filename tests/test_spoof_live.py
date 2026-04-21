#!/usr/bin/env python3
"""Run this to verify UA spoofing is working. Opens a browser and checks."""
import sys
from pathlib import Path

profile = sys.argv[1] if len(sys.argv) > 1 else 'chrome-win-01'
headless = '--headless' in sys.argv

print(f'Testing profile: {profile}  headless={headless}')

from tegufox_automation import TegufoxSession, SessionConfig

with TegufoxSession(profile, config=SessionConfig(headless=headless)) as sess:
    # Navigate to the test HTML page
    test_page = Path('test_ua_spoof.html').resolve().as_uri()
    sess.page.goto(test_page)
    sess.page.wait_for_load_state('load')

    # Collect all key signals
    result = sess.page.evaluate("""
    () => ({
        userAgent:        navigator.userAgent,
        platform:         navigator.platform,
        vendor:           navigator.vendor,
        productSub:       navigator.productSub,
        hasChromeObj:     typeof window.chrome !== 'undefined',
        hasInstallTrigger:typeof InstallTrigger !== 'undefined',
        mozCSS:           CSS.supports('-moz-appearance','none'),
    })
    """)

    print()
    print('=== FINGERPRINT RESULT ===')
    for k, v in result.items():
        print(f'  {k:22s}: {v}')
    print()

    if not headless:
        print('Browser is open. Press Enter to close...')
        input()
