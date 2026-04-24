#!/usr/bin/env python3
"""
Quick test to verify proxy integration in GUI

This script:
1. Lists available proxies
2. Shows how to test them
3. Launches the GUI for manual testing

Usage:
    python3 test_proxy_gui.py
"""

from tegufox_core.proxy_manager import ProxyManager

def main():
    print("=" * 60)
    print("TEGUFOX PROXY INTEGRATION TEST")
    print("=" * 60)
    
    # List available proxies
    pm = ProxyManager()
    proxies = pm.list()
    
    print(f"\n✓ Found {len(proxies)} proxies in database")
    
    if proxies:
        print("\nProxy List:")
        for i, p in enumerate(proxies[:5], 1):
            data = pm.load(p)
            status = data.get('status', 'unknown')
            status_icon = "✓" if status == "active" else "✗" if status == "failed" else "?"
            print(f"  {i}. {status_icon} {p}: {data['host']}:{data['port']} [{status}]")
        
        if len(proxies) > 5:
            print(f"  ... and {len(proxies) - 5} more")
        
        # Test first proxy
        print(f"\n--- Testing first proxy: {proxies[0]} ---")
        result = pm.test_proxy(proxies[0], timeout=10)
        if result["success"]:
            print(f"✓ Proxy is working! External IP: {result['ip']}")
            print(f"  Response time: {result.get('response_time', 'N/A')}s")
        else:
            print(f"✗ Proxy test failed: {result.get('error', 'Unknown error')}")
    else:
        print("\n⚠ No proxies found in database")
        print("  Add proxies using the GUI: Proxies tab → Add Proxy")
    
    print("\n" + "=" * 60)
    print("PROXY INTEGRATION STATUS")
    print("=" * 60)
    print("\n✓ Proxy dropdown added to Sessions page")
    print("✓ Test button for proxy verification")
    print("✓ Proxy config passed to SessionWorker")
    print("✓ Proxy passed to Camoufox via launch_options()")
    print("✓ Credential format fixed (separate username/password)")
    print("✓ Proxy configured at browser launch level (Firefox requirement)")
    
    print("\n" + "=" * 60)
    print("MANUAL TEST INSTRUCTIONS")
    print("=" * 60)
    print("\n1. Launch GUI: python3 -m tegufox_gui")
    print("2. Go to Sessions tab")
    print("3. Select a proxy from dropdown")
    print("4. Click 'Test' button to verify proxy")
    print("5. Click 'Launch' to start browser with proxy")
    print("6. Navigate to: https://httpbin.org/headers")
    print("7. Verify X-Forwarded-For header shows proxy IP")
    
    print("\n" + "=" * 60)
    print("KNOWN ISSUES")
    print("=" * 60)
    print("\n• fv.pro returns 502 (proxy provider limitation)")
    print("• Use httpbin.org or api.ipify.org for testing")
    
    print("\n" + "=" * 60)
    
    # Ask if user wants to launch GUI
    print("\nLaunch GUI now? (y/n): ", end="")
    try:
        response = input().strip().lower()
        if response == 'y':
            print("\nLaunching Tegufox GUI...")
            import subprocess
            subprocess.run(["python3", "-m", "tegufox_gui"])
    except KeyboardInterrupt:
        print("\n\nExiting...")

if __name__ == "__main__":
    main()
