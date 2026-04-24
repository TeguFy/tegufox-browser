#!/usr/bin/env python3
"""
Complete proxy integration test

Tests:
1. Proxy loading from ProxyManager
2. Proxy config format
3. Camoufox launch with proxy
4. Browser navigation through proxy
5. IP verification
"""

from tegufox_core.proxy_manager import ProxyManager
from camoufox.sync_api import Camoufox

def test_complete_proxy_flow():
    print("=" * 60)
    print("COMPLETE PROXY INTEGRATION TEST")
    print("=" * 60)
    
    # Step 1: Load proxy from ProxyManager
    print("\n[1/5] Loading proxy from ProxyManager...")
    pm = ProxyManager()
    proxies = pm.list()
    
    if not proxies:
        print("✗ No proxies available")
        return False
    
    # Find first active proxy
    proxy_name = None
    for p in proxies:
        data = pm.load(p)
        if data.get('status') == 'active':
            proxy_name = p
            break
    
    if not proxy_name:
        proxy_name = proxies[0]
    
    proxy_data = pm.load(proxy_name)
    print(f"✓ Loaded proxy: {proxy_name}")
    print(f"  Host: {proxy_data['host']}:{proxy_data['port']}")
    print(f"  Status: {proxy_data.get('status', 'unknown')}")
    
    # Step 2: Build proxy config
    print("\n[2/5] Building proxy config...")
    proxy_config = {
        "server": f"http://{proxy_data['host']}:{proxy_data['port']}",
        "username": proxy_data["username"],
        "password": proxy_data["password"],
        "bypass": "localhost,127.0.0.1"
    }
    print(f"✓ Proxy config built")
    print(f"  Server: {proxy_config['server']}")
    print(f"  Bypass: {proxy_config['bypass']}")
    print(f"  Auth: {'Yes' if proxy_config.get('username') else 'No'}")
    
    # Step 3: Launch Camoufox with proxy
    print("\n[3/5] Launching Camoufox with proxy...")
    try:
        with Camoufox(
            headless=True,
            i_know_what_im_doing=True,
            geoip=False,  # Critical: disable geoip validation
            proxy=proxy_config
        ) as browser:
            print("✓ Browser launched successfully")
            
            # Step 4: Navigate through proxy
            print("\n[4/5] Creating context and page...")
            context = browser.new_context()
            page = context.new_page()
            print("✓ Context and page created")
            
            print("\nNavigating to httpbin.org/ip...")
            page.goto("https://httpbin.org/ip", timeout=15000)
            print("✓ Navigation successful")
            
            # Step 5: Verify IP
            print("\n[5/5] Verifying external IP...")
            content = page.content()
            
            # Extract IP from response
            import re
            ip_match = re.search(r'"origin":\s*"([^"]+)"', content)
            if ip_match:
                external_ip = ip_match.group(1)
                print(f"✓ External IP: {external_ip}")
                
                # Check if it's different from local IP
                import socket
                local_ip = socket.gethostbyname(socket.gethostname())
                if external_ip != local_ip:
                    print(f"✓ IP is different from local IP ({local_ip})")
                    print("\n" + "=" * 60)
                    print("✅ ALL TESTS PASSED!")
                    print("=" * 60)
                    return True
                else:
                    print(f"⚠️  External IP matches local IP - proxy may not be working")
            else:
                print("✗ Could not extract IP from response")
                print(f"Response: {content[:200]}")
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False

if __name__ == "__main__":
    success = test_complete_proxy_flow()
    exit(0 if success else 1)
