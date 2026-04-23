#!/usr/bin/env python3
"""
Test script for Proxy Management feature
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tegufox_core.proxy_manager import ProxyManager, parse_proxy_line


def test_parsing():
    """Test proxy string parsing"""
    print("=" * 60)
    print("TEST 1: Proxy String Parsing")
    print("=" * 60)
    
    test_cases = [
        ("192.168.1.1:8080:user:pass", True),
        ("user:pass@192.168.1.2:8080", True),
        ("192.168.1.3:8080", True),
        ("10.0.0.1:3128:admin:secret123", True),
        ("invalid", False),
        ("192.168.1.1", False),
    ]
    
    passed = 0
    for line, should_pass in test_cases:
        result = parse_proxy_line(line)
        success = (result is not None) == should_pass
        status = "✓" if success else "✗"
        print(f"{status} {line:40} -> {result}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(test_cases)}\n")
    return passed == len(test_cases)


def test_crud():
    """Test CRUD operations"""
    print("=" * 60)
    print("TEST 2: CRUD Operations")
    print("=" * 60)
    
    pm = ProxyManager()
    
    # Clean up any existing test data
    for name in pm.list():
        if name.startswith("test_"):
            pm.delete(name)
    
    # Create
    print("\n1. CREATE")
    proxy = pm.create("test_proxy1", "192.168.1.100", 8080, "user1", "pass1")
    print(f"   Created: {proxy['name']} - {proxy['host']}:{proxy['port']}")
    
    # Read
    print("\n2. READ")
    loaded = pm.load("test_proxy1")
    print(f"   Loaded: {loaded['name']} - {loaded['username']}")
    
    # Update
    print("\n3. UPDATE")
    updated = pm.update("test_proxy1", host="192.168.1.200", port=9090)
    print(f"   Updated: {updated['host']}:{updated['port']}")
    
    # List
    print("\n4. LIST")
    all_proxies = pm.list()
    print(f"   Total proxies: {len(all_proxies)}")
    
    # Delete
    print("\n5. DELETE")
    pm.delete("test_proxy1")
    remaining = pm.list()
    print(f"   Remaining: {len(remaining)}")
    
    print("\n✓ CRUD operations completed\n")
    return True


def test_bulk_import():
    """Test bulk import"""
    print("=" * 60)
    print("TEST 3: Bulk Import")
    print("=" * 60)
    
    pm = ProxyManager()
    
    # Clean up
    for name in pm.list():
        if name.startswith("proxy_"):
            pm.delete(name)
    
    bulk_data = [
        "10.0.0.1:3128:admin:secret",
        "user:pass@10.0.0.2:8888",
        "10.0.0.3:8080",
        "invalid_line",
    ]
    
    print(f"\nImporting {len(bulk_data)} lines...")
    success_count, errors = pm.bulk_import(bulk_data)
    
    print(f"   Success: {success_count}")
    print(f"   Errors: {len(errors)}")
    if errors:
        for err in errors:
            print(f"      - {err}")
    
    # Verify
    all_proxies = pm.list()
    print(f"\n   Total proxies in DB: {len(all_proxies)}")
    
    # Clean up
    for name in all_proxies:
        if name.startswith("proxy_"):
            pm.delete(name)
    
    print("\n✓ Bulk import completed\n")
    return success_count == 3 and len(errors) == 1


def test_multiple_delete():
    """Test multiple delete"""
    print("=" * 60)
    print("TEST 4: Multiple Delete")
    print("=" * 60)
    
    pm = ProxyManager()
    
    # Create test proxies
    print("\nCreating test proxies...")
    for i in range(5):
        pm.create(f"test_del_{i}", f"10.0.0.{i}", 8080 + i)
    
    print(f"   Created: {len([p for p in pm.list() if p.startswith('test_del_')])} proxies")
    
    # Delete multiple
    to_delete = ["test_del_0", "test_del_2", "test_del_4"]
    print(f"\nDeleting {len(to_delete)} proxies...")
    success_count, errors = pm.delete_multiple(to_delete)
    
    print(f"   Deleted: {success_count}")
    print(f"   Errors: {len(errors)}")
    
    # Verify
    remaining = [p for p in pm.list() if p.startswith("test_del_")]
    print(f"   Remaining: {len(remaining)} - {remaining}")
    
    # Clean up
    for name in remaining:
        pm.delete(name)
    
    print("\n✓ Multiple delete completed\n")
    return success_count == 3 and len(remaining) == 2


def test_search():
    """Test search functionality"""
    print("=" * 60)
    print("TEST 5: Search")
    print("=" * 60)
    
    pm = ProxyManager()
    
    # Create test data
    print("\nCreating test proxies...")
    pm.create("search_test_1", "192.168.1.100", 8080)
    pm.create("search_test_2", "10.0.0.50", 3128)
    pm.create("other_proxy", "172.16.0.1", 8888)
    
    # Search by name
    print("\n1. Search by name 'search':")
    results = pm.search("search")
    print(f"   Found: {len(results)} proxies")
    for r in results:
        print(f"      - {r['name']}")
    
    # Search by IP
    print("\n2. Search by IP '192.168':")
    results = pm.search("192.168")
    print(f"   Found: {len(results)} proxies")
    for r in results:
        print(f"      - {r['name']} ({r['host']})")
    
    # Clean up
    for name in ["search_test_1", "search_test_2", "other_proxy"]:
        pm.delete(name)
    
    print("\n✓ Search completed\n")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TEGUFOX PROXY MANAGER - TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("Parsing", test_parsing()))
        results.append(("CRUD", test_crud()))
        results.append(("Bulk Import", test_bulk_import()))
        results.append(("Multiple Delete", test_multiple_delete()))
        results.append(("Search", test_search()))
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {name}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed!")
        return True
    else:
        print("\n⚠️  Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
