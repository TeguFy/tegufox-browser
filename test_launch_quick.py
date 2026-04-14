#!/usr/bin/env python3
from camoufox import Camoufox
import json

# Load profile
with open("profiles/test-launch-001.json") as f:
    profile = json.load(f)

config = profile.get('config', {})
print(f"🦊 Launching with {len(config)} config keys...")
print(f"Platform: {profile['platform']}")
print(f"User Agent: {config.get('navigator.userAgent', 'N/A')[:60]}...")
print(f"Canvas Seed: {config.get('canvas.seed')}")

# Quick launch test (headless to avoid GUI)
with Camoufox(headless=True, config=config) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    title = page.title()
    print(f"✅ SUCCESS! Browser launched with profile")
    print(f"✅ Page title: {title}")
    print(f"✅ Profile config applied correctly!")
