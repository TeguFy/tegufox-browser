#!/usr/bin/env python3
"""
Test Camoufox with proxy and geoip=False
"""

from camoufox.sync_api import Camoufox
from tegufox_core.proxy_manager import ProxyManager

# Load proxy
pm = ProxyManager()
proxies = pm.list()
if not proxies:
    print("No proxies available")
    exit(1)

proxy_data = pm.load(proxies[0])
print(f"Testing with proxy: {proxy_data['host']}:{proxy_data['port']}")

# Build proxy config
proxy_config = {
    "server": f"http://{proxy_data['host']}:{proxy_data['port']}",
    "username": proxy_data["username"],
    "password": proxy_data["password"],
    "bypass": "localhost,127.0.0.1"
}

print(f"Proxy config: {proxy_config['server']}")
print(f"Bypass: {proxy_config['bypass']}")

try:
    print("\nLaunching Camoufox with proxy and geoip=False...")
    with Camoufox(
        headless=True,
        i_know_what_im_doing=True,
        geoip=False,  # Disable geoip
        proxy=proxy_config
    ) as browser:
        print("✓ Browser launched")
        
        context = browser.new_context()
        print("✓ Context created")
        
        page = context.new_page()
        print("✓ Page created")
        
        print("\nNavigating to httpbin.org/ip...")
        page.goto("https://httpbin.org/ip", timeout=15000)
        print("✓ Navigation successful")
        
        content = page.content()
        print(f"\nPage content:\n{content[:300]}")
        
        print("\n✓ TEST PASSED!")
        
except Exception as e:
    print(f"\n✗ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
