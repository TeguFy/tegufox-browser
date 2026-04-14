#!/usr/bin/env python3
from camoufox import Camoufox
import json

# Create simple profile without WebGL (let Camoufox auto-generate)
simple_config = {
    'navigator.userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/135.0',
    'navigator.platform': 'Win32',
    'navigator.hardwareConcurrency': 8,
    'screen.width': 1920,
    'screen.height': 1080,
    'canvas:seed': 123456789,
}

print(f"🦊 Testing simple profile config...")
print(f"Config keys: {len(simple_config)}\n")

with Camoufox(headless=True, config=simple_config, i_know_what_im_doing=True) as browser:
    page = browser.new_page()
    page.goto("https://example.com")
    
    print(f"✅ SUCCESS! Browser launched")
    print(f"✅ Page loaded: {page.title()}")
    
    # Check config
    ua = page.evaluate("navigator.userAgent")
    platform_val = page.evaluate("navigator.platform")
    cores = page.evaluate("navigator.hardwareConcurrency")
    
    print(f"\n✅ Config applied:")
    print(f"   Platform: {platform_val}")
    print(f"   CPU Cores: {cores}")
    print(f"\n🎉 Simple profile test PASSED!")
