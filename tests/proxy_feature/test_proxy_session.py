#!/usr/bin/env python3
"""
Test script for proxy assignment in TegufoxSession

Usage:
    python3 test_proxy_session.py [proxy_name]
"""

import sys
from tegufox_core.proxy_manager import ProxyManager, format_proxy_url
from tegufox_automation import TegufoxSession, SessionConfig

def test_proxy_session(proxy_name=None):
    """Test launching a session with proxy"""
    
    # List available proxies
    pm = ProxyManager()
    proxies = pm.list()
    
    print(f"Available proxies: {len(proxies)}")
    for p in proxies[:5]:
        data = pm.load(p)
        status = data.get('status', 'unknown')
        print(f"  - {p}: {data['host']}:{data['port']} [{status}]")
    
    if not proxy_name:
        if not proxies:
            print("\nNo proxies available. Please add proxies first.")
            return
        # Use first active proxy
        for p in proxies:
            data = pm.load(p)
            if data.get('status') == 'active':
                proxy_name = p
                break
        if not proxy_name:
            proxy_name = proxies[0]
    
    print(f"\nTesting with proxy: {proxy_name}")
    
    # Load proxy data
    proxy_data = pm.load(proxy_name)
    if not proxy_data:
        print(f"Error: Proxy '{proxy_name}' not found")
        return
    
    print(f"Proxy details: {proxy_data['host']}:{proxy_data['port']}")
    print(f"Status: {proxy_data.get('status', 'unknown')}")
    
    # Test proxy first
    print("\nTesting proxy connection...")
    result = pm.test_proxy(proxy_name, timeout=10)
    if result["success"]:
        print(f"✓ Proxy is working! External IP: {result['ip']}")
    else:
        print(f"✗ Proxy test failed: {result.get('error', 'Unknown error')}")
        print("Continuing anyway...")
    
    # Build proxy config
    # IMPORTANT: Playwright expects server WITHOUT credentials in the URL
    protocol = proxy_data.get('protocol', 'http')
    host = proxy_data['host']
    port = proxy_data['port']
    
    proxy_config = {
        "server": f"{protocol}://{host}:{port}"
    }
    if proxy_data.get("username") and proxy_data.get("password"):
        proxy_config["username"] = proxy_data["username"]
        proxy_config["password"] = proxy_data["password"]
    
    print(f"\nProxy config: {proxy_config}")
    
    # Create session with proxy
    print("\nLaunching browser session with proxy...")
    
    # Use a simple profile dict instead of database profile
    simple_profile = {
        "name": "test-chrome",
        "os": "macos",
        "navigator": {
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "MacIntel",
            "hardwareConcurrency": 8,
            "language": "en-US",
            "languages": ["en-US", "en"]
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "colorDepth": 24,
            "devicePixelRatio": 2
        }
    }
    
    config = SessionConfig(
        headless=False,
        viewport_width=800,
        viewport_height=600,
        proxy=proxy_config
    )
    
    try:
        with TegufoxSession(profile=simple_profile, config=config) as session:
            print("✓ Session started successfully")
            
            # Navigate to IP check site
            print("\nNavigating to IP check site...")
            session.goto("https://api.ipify.org?format=json")
            session.wait(2)
            
            # Get page content
            content = session.page.content()
            print(f"Page content: {content[:200]}")
            
            print("\n✓ Test completed successfully!")
            print("Press Enter to close browser...")
            input()
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    proxy_name = sys.argv[1] if len(sys.argv) > 1 else None
    test_proxy_session(proxy_name)
