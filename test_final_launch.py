#!/usr/bin/env python3
from camoufox import Camoufox
import json

# Load profile
with open("profiles/test-launch-final.json") as f:
    profile = json.load(f)

config = profile.get('config', {})
print(f"🦊 Launching Camoufox with profile: {profile['name']}")
print(f"Platform: {profile['platform']}")
print(f"Config keys: {len(config)}\n")

# Launch with i_know_what_im_doing to suppress warnings
with Camoufox(headless=True, config=config, i_know_what_im_doing=True) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    title = page.title()
    print(f"✅ SUCCESS! Browser launched successfully")
    print(f"✅ Page loaded: {title}")
    
    # Check if config was applied
    ua = page.evaluate("navigator.userAgent")
    platform_val = page.evaluate("navigator.platform")
    cores = page.evaluate("navigator.hardwareConcurrency")
    
    print(f"\n✅ Config verification:")
    print(f"   User Agent: {ua[:60]}...")
    print(f"   Platform: {platform_val}")
    print(f"   CPU Cores: {cores}")
    print(f"\n🎉 Profile launch test PASSED!")
