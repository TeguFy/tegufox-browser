#!/usr/bin/env python3
"""
Test Camoufox basic functionality
Phase 0 - Week 1: First test
"""

from camoufox import Camoufox
import time


def test_basic_launch():
    """Test if Camoufox can launch successfully"""
    print("🦊 Testing Camoufox basic launch...")

    try:
        with Camoufox(headless=False) as browser:
            print("✅ Browser launched successfully!")

            # Create new page
            page = browser.new_page()
            print("✅ New page created!")

            # Navigate to a simple page
            page.goto("https://example.com")
            print("✅ Navigated to example.com")

            # Get page title
            title = page.title()
            print(f"📄 Page title: {title}")

            # Wait a bit
            time.sleep(2)

            print("\n✅ Basic test PASSED!")

            # Wait 3 seconds then close
            time.sleep(3)

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        raise


if __name__ == "__main__":
    test_basic_launch()
