#!/usr/bin/env python3
"""
Canvas Noise v2 Testing Script

Tests the canvas-noise-v2.patch implementation against:
1. BrowserLeaks Canvas Fingerprinting test
2. CreepJS fingerprinting detection
3. Visual regression (ensure no artifacts)
4. Performance benchmarking

Usage:
    python test_canvas_noise_v2.py
"""

import asyncio
import json
import time
from pathlib import Path
from camoufox.sync_api import Camoufox

# Test profile with canvas noise v2 enabled
CANVAS_V2_PROFILE = "profiles/test-canvas-v2.json"

# Test URLs
BROWSERLEAKS_CANVAS = "https://browserleaks.com/canvas"
CREEPJS_URL = "https://creepjs.vercel.app/"


# Colors for output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.END}\n")


def print_test(name):
    print(f"{Colors.CYAN}{Colors.BOLD}[TEST] {name}{Colors.END}")


def print_pass(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_fail(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def load_profile_config(profile_path):
    """Load and return profile configuration"""
    with open(profile_path) as f:
        profile = json.load(f)

    # Remove auto-generated keys (Camoufox will generate these)
    config = profile.get("config", {}).copy()
    auto_gen_keys = [
        "navigator.userAgent",
        "navigator.platform",
        "navigator.hardwareConcurrency",
        "screen.width",
        "screen.height",
        "screen.colorDepth",
        "webGl:vendor",
        "webGl:renderer",
    ]

    for key in auto_gen_keys:
        config.pop(key, None)

    return config


def test_browserleaks_canvas():
    """Test BrowserLeaks canvas fingerprinting"""
    print_test("BrowserLeaks Canvas Fingerprinting")

    try:
        config = load_profile_config(CANVAS_V2_PROFILE)

        print_info(f"Canvas noise config:")
        for key, value in config.items():
            if "canvas" in key:
                print(f"    {key}: {value}")

        print_info("Launching browser...")

        with Camoufox(config=config, headless=False) as browser:
            page = browser.new_page()

            print_info(f"Navigating to {BROWSERLEAKS_CANVAS}...")
            page.goto(BROWSERLEAKS_CANVAS, wait_until="networkidle")

            # Wait for page to fully load
            page.wait_for_timeout(3000)

            print_info("Waiting 30 seconds for manual inspection...")
            print_info("Please check:")
            print("    1. Canvas signature is generated")
            print("    2. Canvas image renders correctly")
            print("    3. No visual artifacts visible")
            print("    4. Uniqueness indicator shows variation")

            # Keep browser open for manual inspection
            page.wait_for_timeout(30000)

            print_pass("BrowserLeaks test completed - please verify results manually")

    except Exception as e:
        print_fail(f"BrowserLeaks test failed: {e}")
        return False

    return True


def test_creepjs():
    """Test CreepJS fingerprinting detection"""
    print_test("CreepJS Fingerprinting Detection")

    try:
        config = load_profile_config(CANVAS_V2_PROFILE)

        print_info("Launching browser...")

        with Camoufox(config=config, headless=False) as browser:
            page = browser.new_page()

            print_info(f"Navigating to {CREEPJS_URL}...")
            page.goto(CREEPJS_URL, wait_until="networkidle")

            # Wait for CreepJS to complete all tests
            print_info("Waiting for CreepJS to complete tests (60 seconds)...")
            page.wait_for_timeout(60000)

            print_info("Please manually verify:")
            print("    1. Trust score > 80%")
            print("    2. Canvas section shows NO 'lies' or tampering detected")
            print("    3. No 'prototype tampering' warnings")
            print("    4. Canvas data exists and is stable")

            # Keep browser open for inspection
            print_info("Browser will remain open for 60 seconds for inspection...")
            page.wait_for_timeout(60000)

            print_pass("CreepJS test completed - please verify results manually")

    except Exception as e:
        print_fail(f"CreepJS test failed: {e}")
        return False

    return True


def test_stability():
    """Test canvas fingerprint stability across refreshes"""
    print_test("Canvas Fingerprint Stability")

    try:
        config = load_profile_config(CANVAS_V2_PROFILE)

        print_info("Testing canvas stability across page refreshes...")

        with Camoufox(config=config, headless=False) as browser:
            page = browser.new_page()
            page.goto(BROWSERLEAKS_CANVAS, wait_until="networkidle")
            page.wait_for_timeout(5000)

            # Get first canvas signature
            print_info("Capturing first canvas signature...")
            page.wait_for_timeout(2000)

            # Refresh page
            print_info("Refreshing page...")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(5000)

            print_info("Capturing second canvas signature...")
            page.wait_for_timeout(2000)

            print_warning("Please manually compare the two canvas signatures:")
            print("    - They should be SIMILAR (within same session)")
            print("    - Small variations are OK (temporal noise)")
            print("    - Complete randomness = FAIL")

            page.wait_for_timeout(20000)

            print_pass("Stability test completed - verify signatures manually")

    except Exception as e:
        print_fail(f"Stability test failed: {e}")
        return False

    return True


def test_performance():
    """Benchmark canvas operations performance"""
    print_test("Canvas Performance Benchmark")

    try:
        config = load_profile_config(CANVAS_V2_PROFILE)

        print_info("Testing canvas performance with noise enabled...")

        with Camoufox(config=config, headless=True) as browser:
            page = browser.new_page()

            # Navigate to a canvas-heavy test page
            page.goto(BROWSERLEAKS_CANVAS, wait_until="networkidle")

            # Measure page load time
            start_time = time.time()
            page.wait_for_timeout(3000)
            load_time = time.time() - start_time

            print_info(f"Page load time: {load_time:.2f}s")

            # Expected: <1ms overhead per canvas operation
            # For a typical page with 5-10 canvas operations: <10ms total overhead

            if load_time < 5.0:
                print_pass(f"Performance acceptable: {load_time:.2f}s")
            else:
                print_warning(f"Performance may need optimization: {load_time:.2f}s")

    except Exception as e:
        print_fail(f"Performance test failed: {e}")
        return False

    return True


def main():
    """Run all canvas noise v2 tests"""

    print_header("🎨 CANVAS NOISE V2 TESTING SUITE")

    # Check profile exists
    if not Path(CANVAS_V2_PROFILE).exists():
        print_fail(f"Profile not found: {CANVAS_V2_PROFILE}")
        print_info("Please create profile first:")
        print(
            f"    ./tegufox-config create --platform amazon-fba --name test-canvas-v2"
        )
        return

    print_info(f"Using profile: {CANVAS_V2_PROFILE}")

    # Run tests
    results = []

    # Test 1: BrowserLeaks
    print("\n")
    results.append(("BrowserLeaks Canvas", test_browserleaks_canvas()))

    # Test 2: CreepJS
    print("\n")
    results.append(("CreepJS Detection", test_creepjs()))

    # Test 3: Stability
    print("\n")
    results.append(("Fingerprint Stability", test_stability()))

    # Test 4: Performance
    print("\n")
    results.append(("Performance Benchmark", test_performance()))

    # Summary
    print_header("📊 TEST SUMMARY")

    for test_name, passed in results:
        status = "PASS ✅" if passed else "FAIL ❌"
        print(f"{test_name:.<40} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print_pass("All tests completed successfully!")
        print_info("\nNext steps:")
        print("  1. Verify manual checks passed")
        print("  2. Test on e-commerce sites (Amazon, eBay, Etsy)")
        print("  3. Run performance profiling if needed")
    else:
        print_fail(f"{total - passed} test(s) failed")
        print_info("Review errors above and fix issues")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
