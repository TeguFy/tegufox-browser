#!/usr/bin/env python3
"""
Test Camoufox fingerprinting capabilities
Phase 0 - Week 2: Fingerprint tests
Automated mode: captures fingerprint data programmatically
"""

from camoufox import Camoufox
import time
import json


def test_fingerprint(automated=True):
    """Test Camoufox fingerprinting on various detection sites

    Args:
        automated: If True, captures data and closes automatically
                  If False, waits for manual inspection
    """

    print("🦊 Testing Camoufox Fingerprinting...\n")
    print(f"Mode: {'Automated' if automated else 'Manual Inspection'}\n")

    results = {}

    tests = [
        {
            "name": "CreepJS",
            "url": "https://abrahamjuliot.github.io/creepjs/",
            "wait": 15000,
            "desc": "Check trust score (should be >70%)",
            "capture_script": """() => {
                // Try to capture CreepJS results
                const trustScore = document.querySelector('.ellipsis-all');
                const fingerprint = document.querySelector('#fingerprint-data');
                return {
                    trustScore: trustScore ? trustScore.textContent : 'Not found',
                    hasFingerprint: !!fingerprint,
                    pageTitle: document.title
                };
            }""",
        },
        {
            "name": "BrowserLeaks - Canvas",
            "url": "https://browserleaks.com/canvas",
            "wait": 5000,
            "desc": "Check canvas fingerprint uniqueness",
            "capture_script": """() => {
                return {
                    pageTitle: document.title,
                    canvasSupported: !!document.querySelector('canvas'),
                    pageLoaded: document.readyState
                };
            }""",
        },
        {
            "name": "Navigator Properties",
            "url": "https://browserleaks.com/javascript",
            "wait": 5000,
            "desc": "Check navigator.webdriver and other properties",
            "capture_script": """() => {
                return {
                    webdriver: navigator.webdriver,
                    platform: navigator.platform,
                    userAgent: navigator.userAgent,
                    languages: navigator.languages,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory || 'undefined',
                    pageTitle: document.title
                };
            }""",
        },
    ]

    try:
        # Run without geoip for now (requires extra installation)
        with Camoufox(headless=False) as browser:
            print("✅ Browser launched")

            for test in tests:
                print(f"\n{'=' * 60}")
                print(f"🧪 Test: {test['name']}")
                print(f"📝 Description: {test['desc']}")
                print(f"🌐 URL: {test['url']}")
                print(f"{'=' * 60}\n")

                page = browser.new_page()

                # Navigate
                print(f"Loading {test['name']}...")
                page.goto(test["url"])

                # Wait for content to load
                page.wait_for_timeout(test["wait"])
                print(
                    f"✅ Page loaded, waiting {test['wait'] / 1000}s for analysis...\n"
                )

                if automated and "capture_script" in test:
                    # Automated: capture data via JavaScript
                    try:
                        data = page.evaluate(test["capture_script"])
                        results[test["name"]] = data
                        print(f"📊 Captured data:")
                        print(json.dumps(data, indent=2))
                    except Exception as e:
                        print(f"⚠️  Could not capture data: {e}")
                        results[test["name"]] = {"error": str(e)}

                    # Brief pause to see the page
                    page.wait_for_timeout(3000)
                else:
                    # Manual inspection mode
                    print("📊 Please inspect the results manually:")
                    print("   - Check if any bot detection is triggered")
                    print("   - Note any anomalies or warnings")
                    print("   - Record the results\n")
                    input(f"Press Enter when done inspecting {test['name']}...")

                page.close()

            print(f"\n{'=' * 60}")
            print("✅ All fingerprint tests completed!")

            if automated:
                # Save results
                results_file = "baseline-fingerprint-results.json"
                with open(results_file, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"📊 Results saved to: {results_file}")
            else:
                print("📝 Please document your findings in:")
                print("   docs/phase0-fingerprint-results.md")

            print(f"{'=' * 60}\n")

            return results

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        raise


if __name__ == "__main__":
    import sys

    manual_mode = "--manual" in sys.argv
    test_fingerprint(automated=not manual_mode)
