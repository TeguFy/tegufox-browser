#!/usr/bin/env python3
"""
Demo: Test Selected Proxies Feature

This demonstrates the bulk proxy testing functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tegufox_core.proxy_manager import ProxyManager


def main():
    print("\n" + "=" * 60)
    print("DEMO: Test Selected Proxies")
    print("=" * 60 + "\n")
    
    pm = ProxyManager()
    
    # Clean up any existing demo data
    for name in pm.list():
        if name.startswith("demo_bulk_"):
            pm.delete(name)
    
    # Create multiple test proxies
    print("1. Creating test proxies...")
    test_proxies = [
        ("demo_bulk_1", "192.168.1.100", 8080),
        ("demo_bulk_2", "192.168.1.101", 8080),
        ("demo_bulk_3", "192.168.1.102", 8080),
        ("demo_bulk_4", "192.168.1.103", 8080),
        ("demo_bulk_5", "192.168.1.104", 8080),
    ]
    
    for name, host, port in test_proxies:
        pm.create(name, host, port, "user", "pass")
        print(f"   ✓ Created: {name} ({host}:{port})")
    
    # Simulate bulk testing (in GUI, user would select multiple and click "Test")
    print("\n2. Testing selected proxies (simulating bulk test)...")
    print("   Note: These will fail as they're fake proxies")
    
    selected = ["demo_bulk_1", "demo_bulk_2", "demo_bulk_3"]
    print(f"   Selected: {len(selected)} proxies")
    
    results = []
    for name in selected:
        print(f"\n   Testing {name}...")
        result = pm.test_proxy(name, timeout=2)
        results.append((name, result))
        
        if result["success"]:
            print(f"      ✓ Success - IP: {result['ip']}")
        else:
            error_msg = result['error'][:50] if result['error'] else 'Unknown'
            print(f"      ✗ Failed - {error_msg}")
    
    # Show updated statuses
    print("\n3. Updated proxy statuses:")
    for name in test_proxies:
        data = pm.load(name[0])
        status = data['status']
        last_ip = data['last_ip'] or '—'
        status_icon = "✓" if status == "active" else "✗" if status == "failed" else "○"
        print(f"   {status_icon} {name[0]:20} [{status:8}] IP: {last_ip}")
    
    # Clean up
    print("\n4. Cleaning up...")
    for name, _, _ in test_proxies:
        pm.delete(name)
    print("   ✓ Cleaned up")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)
    print("\nIn the GUI:")
    print("  1. Select multiple proxies (checkboxes)")
    print("  2. Click '🔍 Test' button")
    print("  3. All selected proxies will be tested")
    print("  4. Status and IP will be updated for each")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
