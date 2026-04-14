#!/usr/bin/env python3
"""
Test browser launch with profile configuration
"""

from camoufox import Camoufox
import json
from pathlib import Path
import time


def test_profile_launch():
    """Test launching browser with a profile"""
    print("🦊 Testing Camoufox launch with profile config\n")

    # Load a test profile
    profile_file = Path("profiles/xxx.json")
    if not profile_file.exists():
        print(f"❌ Profile not found: {profile_file}")
        print("Please create a profile first using the GUI or CLI")
        return False

    with open(profile_file) as f:
        profile_data = json.load(f)

    config = profile_data.get("config", {})
    platform = profile_data.get("platform", "unknown")

    print(f"Profile: {profile_data['name']}")
    print(f"Platform: {platform}")
    print(f"Config keys: {len(config)}")
    print(f"\nConfig preview:")
    for key, value in list(config.items())[:5]:
        print(f"  • {key}: {value}")
    print(f"  ... and {len(config) - 5} more\n")

    try:
        print("🚀 Launching browser with config...\n")

        with Camoufox(headless=False, config=config) as browser:
            print("✅ Browser launched successfully!")

            # Create new page
            page = browser.new_page()
            print("✅ New page created")

            # Navigate to bot detection test
            print("🌐 Navigating to bot detection test...")
            page.goto("https://www.browserscan.net/bot-detection")
            print("✅ Page loaded")

            print("\n✅ Test PASSED!")
            print("Check the browser window for bot detection results")
            print("Press Enter to close browser...")
            input()

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    test_profile_launch()
