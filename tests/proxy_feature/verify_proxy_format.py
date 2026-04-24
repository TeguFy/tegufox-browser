#!/usr/bin/env python3
"""
Verify proxy configuration is correct

This script checks that the proxy format matches Playwright's expectations.
"""

from tegufox_core.proxy_manager import ProxyManager

def verify_proxy_format():
    """Verify proxy configuration format"""
    pm = ProxyManager()
    proxies = pm.list()
    
    if not proxies:
        print("❌ No proxies found. Please add proxies first.")
        return False
    
    print(f"✓ Found {len(proxies)} proxies\n")
    
    # Check first active proxy
    for proxy_name in proxies:
        proxy_data = pm.load(proxy_name)
        if proxy_data.get('status') == 'active':
            print(f"Checking proxy: {proxy_name}")
            print(f"  Host: {proxy_data['host']}")
            print(f"  Port: {proxy_data['port']}")
            print(f"  Status: {proxy_data['status']}")
            print()
            
            # Build config
            protocol = proxy_data.get('protocol', 'http')
            host = proxy_data['host']
            port = proxy_data['port']
            
            proxy_config = {
                "server": f"{protocol}://{host}:{port}",
                "username": proxy_data.get("username"),
                "password": proxy_data.get("password"),
            }
            
            print("✓ Correct Playwright format:")
            print(f"  {proxy_config}")
            print()
            
            # Verify format
            if '@' in proxy_config['server']:
                print("❌ ERROR: Credentials should NOT be in server URL!")
                print("   Fix: Remove credentials from server field")
                return False
            
            if proxy_config['username'] and proxy_config['password']:
                print("✓ Authentication configured correctly")
            else:
                print("⚠ No authentication (proxy may not require it)")
            
            print()
            print("✓ Proxy format is correct!")
            return True
    
    print("⚠ No active proxies found. Test proxies first.")
    return False

if __name__ == "__main__":
    verify_proxy_format()
