#!/usr/bin/env python3
"""
Demo script for Proxy Management feature

This script demonstrates:
1. Creating proxies
2. Bulk importing proxies
3. Testing proxies (will fail without real proxies)
4. Searching and filtering
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tegufox_core.proxy_manager import ProxyManager


def main():
    print("\n" + "=" * 60)
    print("TEGUFOX PROXY MANAGER - DEMO")
    print("=" * 60 + "\n")
    
    pm = ProxyManager()
    
    # Clean up any existing demo data
    for name in pm.list():
        if name.startswith("demo_"):
            pm.delete(name)
    
    # 1. Create single proxy
    print("1. Creating single proxy...")
    proxy = pm.create(
        name="demo_proxy_1",
        host="192.168.1.100",
        port=8080,
        username="admin",
        password="secret123",
        protocol="http",
        notes="Demo proxy for testing"
    )
    print(f"   ✓ Created: {proxy['name']}")
    print(f"     Host: {proxy['host']}:{proxy['port']}")
    print(f"     User: {proxy['username']}")
    
    # 2. Bulk import
    print("\n2. Bulk importing proxies...")
    bulk_data = [
        "10.0.0.1:3128:user1:pass1",
        "user2:pass2@10.0.0.2:8888",
        "10.0.0.3:8080",
        "172.16.0.1:9090:admin:admin123",
    ]
    
    print(f"   Importing {len(bulk_data)} proxies...")
    success_count, errors = pm.bulk_import(bulk_data)
    print(f"   ✓ Imported: {success_count} proxies")
    if errors:
        print(f"   ✗ Errors: {len(errors)}")
        for err in errors:
            print(f"      - {err}")
    
    # 3. List all proxies
    print("\n3. Listing all proxies...")
    all_proxies = pm.list()
    print(f"   Total: {len(all_proxies)} proxies")
    for name in all_proxies:
        data = pm.load(name)
        print(f"   - {name:20} {data['host']:15}:{data['port']:5} {data['username'] or '(no auth)':15} [{data['status']}]")
    
    # 4. Search
    print("\n4. Searching proxies...")
    results = pm.search("10.0.0")
    print(f"   Search '10.0.0': {len(results)} results")
    for r in results:
        print(f"   - {r['name']} ({r['host']})")
    
    # 5. Update proxy
    print("\n5. Updating proxy...")
    updated = pm.update("demo_proxy_1", status="active", notes="Updated demo proxy")
    print(f"   ✓ Updated: {updated['name']}")
    print(f"     Status: {updated['status']}")
    print(f"     Notes: {updated['notes']}")
    
    # 6. Test proxy (will fail without real proxy)
    print("\n6. Testing proxy (expected to fail)...")
    print("   Note: This will fail because we're using fake proxy addresses")
    result = pm.test_proxy("demo_proxy_1", timeout=3)
    print(f"   Result: {'✓ Success' if result['success'] else '✗ Failed'}")
    if result['success']:
        print(f"   IP: {result['ip']}")
        print(f"   Response time: {result['response_time']}s")
    else:
        error_msg = result['error'][:80] if result['error'] else 'Unknown'
        print(f"   Error: {error_msg}")
    
    # 7. Delete multiple
    print("\n7. Deleting proxies...")
    to_delete = [name for name in pm.list() if name.startswith("proxy_")]
    if to_delete:
        success_count, errors = pm.delete_multiple(to_delete)
        print(f"   ✓ Deleted: {success_count} proxies")
    
    # Clean up demo data
    print("\n8. Cleaning up demo data...")
    for name in pm.list():
        if name.startswith("demo_"):
            pm.delete(name)
    print("   ✓ Cleaned up")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)
    print("\nTo use the GUI:")
    print("  python tegufox-gui")
    print("\nThen click on 'Proxies' in the sidebar to:")
    print("  • Import proxies (single or bulk)")
    print("  • Edit proxy settings")
    print("  • Test proxies (fetch IP)")
    print("  • Delete proxies (single or multiple)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
