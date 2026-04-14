#!/usr/bin/env python3
"""
Test Camoufox on e-commerce platforms
Phase 0 - Week 2: E-commerce detection tests
Automated mode: checks for bot detection indicators
"""

from camoufox import Camoufox
import time
import json


def test_ecommerce(automated=True):
    """Test Camoufox on e-commerce platforms for bot detection

    Args:
        automated: If True, runs automated checks and saves results
                  If False, waits for manual inspection
    """

    print("🦊 Testing Camoufox on E-commerce Platforms...\n")
    print(f"Mode: {'Automated' if automated else 'Manual Inspection'}\n")

    platforms = [
        {
            "name": "eBay",
            "url": "https://www.ebay.com",
            "desc": "Test eBay bot detection and account access",
        },
        {
            "name": "Amazon",
            "url": "https://www.amazon.com",
            "desc": "Test Amazon anti-bot measures",
        },
        {
            "name": "Etsy",
            "url": "https://www.etsy.com",
            "desc": "Test Etsy verification requirements",
        },
    ]

    results = []

    try:
        for platform in platforms:
            print(f"\n{'=' * 60}")
            print(f"🛒 Platform: {platform['name']}")
            print(f"📝 {platform['desc']}")
            print(f"🌐 URL: {platform['url']}")
            print(f"{'=' * 60}\n")

            with Camoufox(headless=False) as browser:
                print(f"✅ Browser launched for {platform['name']}")

                page = browser.new_page()

                # Navigate
                print(f"Loading {platform['name']}...")
                page.goto(platform["url"], wait_until="networkidle")

                # Wait for page to fully load
                page.wait_for_timeout(5000)

                # Check for common bot detection indicators
                content = page.content().lower()

                print("\n🔍 Checking for detection indicators...")

                indicators = {
                    "CAPTCHA": "captcha" in content,
                    "Verification": "verify" in content or "verification" in content,
                    "Blocked": "blocked" in content or "access denied" in content,
                    "Robot Check": "robot" in content or "bot" in content,
                }

                detected = False
                for indicator, found in indicators.items():
                    status = "❌ DETECTED" if found else "✅ Not found"
                    print(f"   {indicator}: {status}")
                    if found:
                        detected = True

                # Result summary
                if detected:
                    result = "⚠️ DETECTION TRIGGERED"
                    print(f"\n{result}")
                else:
                    result = "✅ NO DETECTION"
                    print(f"\n{result}")

                results.append(
                    {
                        "platform": platform["name"],
                        "result": result,
                        "indicators": indicators,
                        "url": platform["url"],
                        "pageTitle": page.title(),
                    }
                )

                if not automated:
                    # Manual inspection mode
                    print("\n📊 Please manually inspect:")
                    print("   - Is there a CAPTCHA?")
                    print("   - Can you browse normally?")
                    print("   - Any suspicious behavior?")
                    print("   - Try clicking around, searching, etc.\n")
                    input(f"Press Enter when done testing {platform['name']}...")
                else:
                    # Brief pause to observe
                    page.wait_for_timeout(2000)

        # Summary
        print(f"\n\n{'=' * 60}")
        print("📊 E-COMMERCE TEST SUMMARY")
        print(f"{'=' * 60}\n")

        for r in results:
            print(f"{r['platform']}: {r['result']}")

        print(f"\n{'=' * 60}")

        if automated:
            # Save results
            results_file = "baseline-ecommerce-results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"📊 Results saved to: {results_file}")
        else:
            print("📝 Document these results in:")
            print("   docs/phase0-ecommerce-results.md")

        print(f"{'=' * 60}\n")

        return results

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        raise


if __name__ == "__main__":
    import sys

    manual_mode = "--manual" in sys.argv
    test_ecommerce(automated=not manual_mode)
