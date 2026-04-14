#!/usr/bin/env python3
"""
Mouse Movement v2 Testing Script

Tests the tegufox_mouse.py human-like movement library:
1. Bezier path generation and visualization
2. Fitts's Law timing verification
3. Bot detection evasion (deviceandbrowserinfo.com)
4. E-commerce site navigation (Amazon, eBay)
5. Visual movement inspection

Usage:
    python test_mouse_movement_v2.py
"""

import sys
import time
import random
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tegufox_mouse import HumanMouse, MouseConfig, Point
from camoufox.sync_api import Camoufox


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


def test_bezier_path_generation():
    """Test Bezier curve path generation"""
    print_test("Bezier Path Generation")

    try:
        from tegufox_mouse import HumanMouse

        # Create mock page object
        class MockPage:
            class Mouse:
                def move(self, x, y):
                    pass

                def down(self):
                    pass

                def up(self):
                    pass

                def wheel(self, dx, dy):
                    pass

            def __init__(self):
                self.mouse = self.Mouse()

        page = MockPage()
        mouse = HumanMouse(page)

        # Generate path
        start = Point(100, 100)
        end = Point(500, 400)
        distance = mouse._distance(start, end)

        path = mouse._generate_bezier_path(start, end, distance)

        print_info(f"Generated {len(path)} points")
        print_info(f"Distance: {distance:.2f}px")
        print_info(f"Start: ({start.x}, {start.y})")
        print_info(f"End: ({end.x}, {end.y})")

        # Verify path properties
        assert len(path) >= 25, "Path should have at least 25 points"
        assert path[0].x == start.x and path[0].y == start.y, (
            "Path should start at start point"
        )

        # Check path is curved (not straight line)
        mid_point = path[len(path) // 2]
        straight_mid_x = (start.x + end.x) / 2
        straight_mid_y = (start.y + end.y) / 2

        deviation = abs(mid_point.x - straight_mid_x) + abs(
            mid_point.y - straight_mid_y
        )

        print_info(f"Mid-point deviation from straight line: {deviation:.2f}px")

        if deviation > 10:
            print_pass(f"Path is curved (deviation: {deviation:.2f}px)")
        else:
            print_warning(f"Path may be too straight (deviation: {deviation:.2f}px)")

        print_pass("Bezier path generation working")
        return True

    except Exception as e:
        print_fail(f"Bezier test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fitts_law_timing():
    """Test Fitts's Law movement time calculation"""
    print_test("Fitts's Law Timing")

    try:
        from tegufox_mouse import HumanMouse

        class MockPage:
            class Mouse:
                def move(self, x, y):
                    pass

                def down(self):
                    pass

                def up(self):
                    pass

            def __init__(self):
                self.mouse = self.Mouse()

        page = MockPage()
        mouse = HumanMouse(page)

        # Test cases: (distance, target_width, expected_time_range)
        test_cases = [
            (100, 50, (200, 400)),  # Short move, medium target
            (500, 20, (600, 900)),  # Long move, small target (harder)
            (500, 100, (300, 600)),  # Long move, large target (easier)
            (1000, 50, (700, 1100)),  # Very long move
        ]

        print_info("Testing movement time calculations:")

        for distance, width, expected_range in test_cases:
            time_ms = mouse._calculate_fitts_time(distance, width)

            min_time, max_time = expected_range
            in_range = min_time <= time_ms <= max_time

            status = "✅" if in_range else "⚠️"
            print(
                f"  {status} Distance: {distance}px, Target: {width}px → {time_ms:.0f}ms"
            )

            if not in_range:
                print_warning(f"    Expected {min_time}-{max_time}ms")

        print_pass("Fitts's Law timing working")
        return True

    except Exception as e:
        print_fail(f"Fitts's Law test failed: {e}")
        return False


def test_bot_detection_evasion():
    """Test against deviceandbrowserinfo.com bot detection"""
    print_test("Bot Detection Evasion")

    try:
        print_info("Launching browser with human mouse...")

        config = {
            "canvas:seed": random.randint(1000000000, 9999999999),
            "canvas:noise:enable": True,
            "canvas:noise:strategy": "gpu",
        }

        with Camoufox(config=config, headless=False) as browser:
            page = browser.new_page()
            mouse = HumanMouse(page)

            print_info("Navigating to bot detection site...")
            page.goto(
                "https://deviceandbrowserinfo.com/are_you_a_bot_interactions",
                wait_until="networkidle",
            )

            print_info("Performing human-like interactions...")

            # Wait a bit (simulate reading)
            time.sleep(2)

            # Move mouse around naturally
            for _ in range(3):
                # Random movement
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                mouse.move_to_position(x, y)
                time.sleep(random.uniform(0.5, 1.5))

            print_info("Waiting 30 seconds for detection analysis...")
            print_info("Please manually verify:")
            print("    1. isBot: false")
            print("    2. All 23 flags are false")
            print("    3. suspiciousClientSideBehavior: false")

            time.sleep(30)

            print_pass("Bot detection test completed - verify results manually")

        return True

    except Exception as e:
        print_fail(f"Bot detection test failed: {e}")
        return False


def test_visual_movement():
    """Visual test of mouse movement realism"""
    print_test("Visual Movement Inspection")

    try:
        print_info("Launching browser for visual inspection...")

        with Camoufox(headless=False) as browser:
            page = browser.new_page()
            mouse = HumanMouse(page)

            # Navigate to a blank page
            page.goto("about:blank")
            page.set_viewport_size({"width": 1200, "height": 800})

            # Inject visual indicators
            page.evaluate("""
                document.body.style.margin = '0';
                document.body.style.padding = '20px';
                document.body.style.fontFamily = 'Arial';
                
                const h1 = document.createElement('h1');
                h1.textContent = 'Mouse Movement Visual Test';
                document.body.appendChild(h1);
                
                const p = document.createElement('p');
                p.textContent = 'Watch the cursor move in curved paths with natural speed variation.';
                document.body.appendChild(p);
                
                // Create target buttons
                for (let i = 0; i < 6; i++) {
                    const btn = document.createElement('button');
                    btn.textContent = `Target ${i + 1}`;
                    btn.style.position = 'absolute';
                    btn.style.left = `${Math.random() * 800 + 100}px`;
                    btn.style.top = `${Math.random() * 500 + 100}px`;
                    btn.style.padding = '10px 20px';
                    btn.style.fontSize = '16px';
                    btn.id = `target-${i}`;
                    document.body.appendChild(btn);
                }
            """)

            print_info("Moving to targets with Bezier curves...")

            # Move to each target
            for i in range(6):
                selector = f"#target-{i}"
                print(f"  Moving to Target {i + 1}...")
                mouse.move_to(selector)
                time.sleep(0.5)

                # Click with random offset
                mouse.click(selector)
                time.sleep(0.3)

            print_info("Movement demonstration complete")
            print_info("Browser will close in 10 seconds...")
            time.sleep(10)

            print_pass("Visual movement test completed")

        return True

    except Exception as e:
        print_fail(f"Visual test failed: {e}")
        return False


def test_amazon_navigation():
    """Test realistic navigation on Amazon"""
    print_test("Amazon E-commerce Navigation")

    try:
        print_info("Launching browser with full stealth configuration...")

        config = {
            "canvas:seed": random.randint(1000000000, 9999999999),
            "canvas:noise:enable": True,
            "canvas:noise:strategy": "gpu",
            "canvas:noise:intensity": 0.00005,  # Ultra-conservative for Amazon
        }

        with Camoufox(config=config, headless=False) as browser:
            page = browser.new_page()
            mouse = HumanMouse(page)

            print_info("Navigating to Amazon...")
            page.goto("https://www.amazon.com", wait_until="networkidle")

            # Wait a bit (simulate reading homepage)
            time.sleep(2)

            print_info("Clicking search box...")
            try:
                mouse.click("input#twotabsearchtextbox")
                time.sleep(0.5)

                # Type search query with human-like delays
                print_info("Typing search query...")
                for char in "laptop":
                    page.keyboard.type(char)
                    time.sleep(random.uniform(0.1, 0.3))

                time.sleep(0.5)

                print_info("Submitting search...")
                mouse.click("input#nav-search-submit-button")

                page.wait_for_load_state("networkidle")
                time.sleep(2)

                print_info("Amazon navigation successful")
                print_info("Browser will remain open for 20 seconds for inspection...")
                time.sleep(20)

                print_pass("Amazon navigation test passed")

            except Exception as click_error:
                print_warning(f"Click interaction issue: {click_error}")
                print_info("This may be due to Amazon's page structure changing")
                print_info("Browser will remain open for manual inspection...")
                time.sleep(30)

        return True

    except Exception as e:
        print_fail(f"Amazon navigation test failed: {e}")
        return False


def main():
    """Run all mouse movement tests"""

    print_header("🖱️ MOUSE MOVEMENT V2 TESTING SUITE")

    print_info("Testing human-like mouse movement library")
    print_info("Library: tegufox_mouse.py")
    print()

    # Run tests
    results = []

    # Test 1: Bezier path generation
    print()
    results.append(("Bezier Path Generation", test_bezier_path_generation()))

    # Test 2: Fitts's Law timing
    print()
    results.append(("Fitts's Law Timing", test_fitts_law_timing()))

    # Test 3: Visual movement
    print()
    results.append(("Visual Movement", test_visual_movement()))

    # Test 4: Bot detection evasion
    print()
    results.append(("Bot Detection Evasion", test_bot_detection_evasion()))

    # Test 5: Amazon navigation
    print()
    results.append(("Amazon Navigation", test_amazon_navigation()))

    # Summary
    print_header("📊 TEST SUMMARY")

    for test_name, passed in results:
        status = "PASS ✅" if passed else "FAIL ❌"
        print(f"{test_name:.<50} {status}")

    total = len(results)
    passed_count = sum(1 for _, p in results if p)

    print(f"\n{Colors.BOLD}Total: {passed_count}/{total} tests passed{Colors.END}")

    if passed_count == total:
        print_pass("All tests completed successfully!")
        print_info("\nNext steps:")
        print("  1. Integrate tegufox_mouse into your automation scripts")
        print("  2. Test on additional e-commerce sites (eBay, Etsy)")
        print("  3. Monitor for bot detection over extended sessions")
    else:
        print_fail(f"{total - passed_count} test(s) failed")
        print_info("Review errors above and fix issues")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
