#!/usr/bin/env python3
"""
Test GUI integration - verify profile creation and management works
"""

import json
from pathlib import Path
import sys

# Add current directory to path to import from tegufox_gui
sys.path.insert(0, str(Path(__file__).parent))

from tegufox_gui import create_profile_data, PLATFORM_TEMPLATES


def test_profile_creation():
    """Test creating profiles programmatically"""
    print("🧪 Testing Profile Creation\n")

    # Test 1: Create single eBay profile
    print("Test 1: Create eBay seller profile...")
    try:
        profile_file, profile_data = create_profile_data("ebay-seller", "test-ebay-001")
        print(f"✅ Created: {profile_file}")
        print(f"   Platform: {profile_data['platform']}")
        print(f"   Config keys: {len(profile_data['config'])}")
        print(f"   Canvas seed: {profile_data['config'].get('canvas:seed')}")
        print()
    except Exception as e:
        print(f"❌ Failed: {e}\n")
        return False

    # Test 2: Create Amazon profile
    print("Test 2: Create Amazon FBA profile...")
    try:
        profile_file, profile_data = create_profile_data(
            "amazon-fba", "test-amazon-001"
        )
        print(f"✅ Created: {profile_file}")
        print(f"   Platform: {profile_data['platform']}")
        print(
            f"   User Agent: {profile_data['config'].get('navigator:userAgent')[:50]}..."
        )
        print()
    except Exception as e:
        print(f"❌ Failed: {e}\n")
        return False

    # Test 3: List all profiles
    print("Test 3: List all created profiles...")
    profiles_dir = Path("profiles")
    if profiles_dir.exists():
        profiles = list(profiles_dir.glob("*.json"))
        print(f"✅ Found {len(profiles)} profiles:")
        for p in profiles:
            with open(p) as f:
                data = json.load(f)
                print(f"   • {p.name} - {data.get('platform')}")
        print()

    # Test 4: Verify profile structure
    print("Test 4: Validate profile structure...")
    test_file = profiles_dir / "test-ebay-001.json"
    if test_file.exists():
        with open(test_file) as f:
            data = json.load(f)

        required_fields = ["name", "platform", "created", "config", "metadata"]
        missing = [f for f in required_fields if f not in data]

        if not missing:
            print(f"✅ All required fields present")
            print(f"   Version: {data['metadata'].get('tegufox_version')}")
        else:
            print(f"❌ Missing fields: {missing}")
            return False

    print("\n✅ All tests passed!")
    return True


def cleanup_test_profiles():
    """Clean up test profiles"""
    print("\n🧹 Cleaning up test profiles...")
    profiles_dir = Path("profiles")
    if profiles_dir.exists():
        for profile in profiles_dir.glob("test-*.json"):
            profile.unlink()
            print(f"   Deleted: {profile.name}")


if __name__ == "__main__":
    success = test_profile_creation()

    # Ask if user wants to clean up
    response = input("\nDelete test profiles? (y/n): ")
    if response.lower() == "y":
        cleanup_test_profiles()

    sys.exit(0 if success else 1)
