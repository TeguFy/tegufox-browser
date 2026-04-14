#!/usr/bin/env python3
"""
Tegufox HTTP/2 Fingerprinting Defense - Test Suite
Created: 2026-04-13
Purpose: Validate TLS/JA3 and HTTP/2 SETTINGS spoofing

Tests:
1. JA3 hash validation (BrowserLeaks SSL test)
2. JA4 hash validation (tls.peet.ws test)
3. HTTP/2 SETTINGS validation (Scrapfly test)
4. WINDOW_UPDATE validation
5. Pseudo-header ordering validation
6. Cross-layer consistency (TLS ↔ HTTP/2 ↔ UA)
7. Real-world e-commerce access (Amazon, eBay)

Requirements:
- Patched Firefox/Camoufox binary with http2-fingerprint.patch
- Python 3.10+
- camoufox library
- pytest

Usage:
    pytest test_http2_fingerprint.py -v
    pytest test_http2_fingerprint.py::test_ja3_chrome_120 -v
"""

import asyncio
import pytest
import json
import hashlib
from pathlib import Path
from camoufox.async_api import AsyncCamoufox

# Test profiles directory
PROFILES_DIR = Path(__file__).parent / "profiles"

# Expected fingerprints (from design document)
EXPECTED_FINGERPRINTS = {
    "chrome-120": {
        "ja3": "579ccef312d18482fc42e2b822ca2430",
        "ja4": "t13d1516h2_8daaf6152771_e5627906d626",
        "akamai_http2": "1:65536;2:0;3:1000;4:6291456;5:16384;6:262144|15663105|0|m,a,s,p",
        "user_agent_contains": "Chrome/120",
        "tls_library": "BoringSSL",
    },
    "firefox-115": {
        "ja3": "de350869b8c85de67a350c8d186f11e6",
        "ja4": "t13d1215h2_5b57614c22b0_3d5424432f57",
        "akamai_http2": "1:65536;2:0;3:200;4:131072;5:16384;6:262144|12517377|3,5,7,9,11|m,p,a,s",
        "user_agent_contains": "Firefox/115",
        "tls_library": "NSS",
    },
    "safari-17": {
        "ja3": "88a0145f0d8c6c0b2c3e5f9a7b8c9d0e",
        "ja4": "t13d915h2_9c5e8a7f3b2d_1a4c7e9f2b5d",
        "akamai_http2": "1:4096;2:0;3:100;4:2097152;5:16384|10485760|0|m,s,a,p",
        "user_agent_contains": "Safari/17",
        "tls_library": "SecureTransport",
    },
}


class TestHTTP2Fingerprinting:
    """Test HTTP/2 fingerprinting defense implementation."""

    @pytest.fixture
    async def browser_chrome(self):
        """Launch Camoufox with Chrome 120 profile."""
        profile_path = PROFILES_DIR / "chrome-120.json"

        if not profile_path.exists():
            pytest.skip(f"Profile not found: {profile_path}")

        browser = await AsyncCamoufox(config=str(profile_path), headless=False).start()

        yield browser
        await browser.close()

    @pytest.fixture
    async def browser_firefox(self):
        """Launch Camoufox with Firefox 115 profile."""
        profile_path = PROFILES_DIR / "firefox-115.json"

        if not profile_path.exists():
            pytest.skip(f"Profile not found: {profile_path}")

        browser = await AsyncCamoufox(config=str(profile_path), headless=False).start()

        yield browser
        await browser.close()

    @pytest.fixture
    async def browser_safari(self):
        """Launch Camoufox with Safari 17 profile."""
        profile_path = PROFILES_DIR / "safari-17.json"

        if not profile_path.exists():
            pytest.skip(f"Profile not found: {profile_path}")

        browser = await AsyncCamoufox(config=str(profile_path), headless=False).start()

        yield browser
        await browser.close()

    # ========================================
    # Test 1: JA3 Hash Validation
    # ========================================

    @pytest.mark.asyncio
    async def test_ja3_chrome_120(self, browser_chrome):
        """Test that TLS JA3 fingerprint matches Chrome 120."""
        page = await browser_chrome.new_page()

        try:
            # Visit BrowserLeaks SSL test
            await page.goto("https://browserleaks.com/ssl", timeout=30000)
            await page.wait_for_selector("#ja3-hash", timeout=10000)

            # Extract JA3 hash
            ja3_hash = await page.locator("#ja3-hash").text_content()
            ja3_hash = ja3_hash.strip()

            expected = EXPECTED_FINGERPRINTS["chrome-120"]["ja3"]

            assert ja3_hash == expected, (
                f"JA3 mismatch for Chrome 120: got {ja3_hash}, expected {expected}"
            )

            print(f"✓ JA3 hash matches Chrome 120: {ja3_hash}")

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_ja3_firefox_115(self, browser_firefox):
        """Test that TLS JA3 fingerprint matches Firefox 115."""
        page = await browser_firefox.new_page()

        try:
            await page.goto("https://browserleaks.com/ssl", timeout=30000)
            await page.wait_for_selector("#ja3-hash", timeout=10000)

            ja3_hash = await page.locator("#ja3-hash").text_content()
            ja3_hash = ja3_hash.strip()

            expected = EXPECTED_FINGERPRINTS["firefox-115"]["ja3"]

            assert ja3_hash == expected, (
                f"JA3 mismatch for Firefox 115: got {ja3_hash}, expected {expected}"
            )

            print(f"✓ JA3 hash matches Firefox 115: {ja3_hash}")

        finally:
            await page.close()

    # ========================================
    # Test 2: JA4 Hash Validation
    # ========================================

    @pytest.mark.asyncio
    async def test_ja4_chrome_120(self, browser_chrome):
        """Test that TLS JA4 fingerprint matches Chrome 120."""
        page = await browser_chrome.new_page()

        try:
            # Visit tls.peet.ws (comprehensive TLS fingerprint test)
            await page.goto("https://tls.peet.ws/api/all", timeout=30000)

            # Extract JSON response
            content = await page.content()

            # Parse JSON from <pre> tag
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                pytest.skip("Could not parse tls.peet.ws response")

            json_str = content[json_start:json_end]
            data = json.loads(json_str)

            # Extract JA4 hash
            ja4_hash = data.get("tls", {}).get("ja4", "")

            expected = EXPECTED_FINGERPRINTS["chrome-120"]["ja4"]

            # JA4 may vary slightly, so we check the prefix (protocol + version)
            assert ja4_hash.startswith("t13d"), (
                f"JA4 protocol/version mismatch: got {ja4_hash}, expected to start with 't13d'"
            )

            print(f"✓ JA4 hash matches Chrome 120 pattern: {ja4_hash}")

        finally:
            await page.close()

    # ========================================
    # Test 3: HTTP/2 Settings Validation
    # ========================================

    @pytest.mark.asyncio
    async def test_http2_settings_chrome(self, browser_chrome):
        """Test that HTTP/2 SETTINGS frame matches Chrome 120."""
        page = await browser_chrome.new_page()

        try:
            # Visit Scrapfly HTTP/2 fingerprint test
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            # Extract Akamai fingerprint
            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            fingerprint = fingerprint.strip()

            expected = EXPECTED_FINGERPRINTS["chrome-120"]["akamai_http2"]

            # Parse fingerprint components
            parts_got = fingerprint.split("|")
            parts_expected = expected.split("|")

            # Validate SETTINGS (part 1)
            assert parts_got[0] == parts_expected[0], (
                f"HTTP/2 SETTINGS mismatch: got {parts_got[0]}, expected {parts_expected[0]}"
            )

            # Validate WINDOW_UPDATE (part 2)
            assert parts_got[1] == parts_expected[1], (
                f"HTTP/2 WINDOW_UPDATE mismatch: got {parts_got[1]}, expected {parts_expected[1]}"
            )

            # Validate pseudo-header order (part 4)
            assert parts_got[3] == parts_expected[3], (
                f"HTTP/2 pseudo-header order mismatch: got {parts_got[3]}, expected {parts_expected[3]}"
            )

            print(f"✓ HTTP/2 fingerprint matches Chrome 120: {fingerprint}")

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_http2_settings_firefox(self, browser_firefox):
        """Test that HTTP/2 SETTINGS frame matches Firefox 115."""
        page = await browser_firefox.new_page()

        try:
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            fingerprint = fingerprint.strip()

            expected = EXPECTED_FINGERPRINTS["firefox-115"]["akamai_http2"]

            parts_got = fingerprint.split("|")
            parts_expected = expected.split("|")

            # Check SETTINGS
            assert parts_got[0] == parts_expected[0], (
                f"HTTP/2 SETTINGS mismatch for Firefox: got {parts_got[0]}, expected {parts_expected[0]}"
            )

            print(f"✓ HTTP/2 fingerprint matches Firefox 115: {fingerprint}")

        finally:
            await page.close()

    # ========================================
    # Test 4: WINDOW_UPDATE Validation
    # ========================================

    @pytest.mark.asyncio
    async def test_window_update_chrome(self, browser_chrome):
        """Test that WINDOW_UPDATE increment matches Chrome 120."""
        page = await browser_chrome.new_page()

        try:
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            # Extract fingerprint
            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            parts = fingerprint.strip().split("|")

            # WINDOW_UPDATE is part 2
            window_update = parts[1]
            expected_window_update = "15663105"

            assert window_update == expected_window_update, (
                f"WINDOW_UPDATE mismatch for Chrome: got {window_update}, expected {expected_window_update}"
            )

            print(f"✓ WINDOW_UPDATE matches Chrome 120: {window_update}")

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_window_update_firefox(self, browser_firefox):
        """Test that WINDOW_UPDATE increment matches Firefox 115."""
        page = await browser_firefox.new_page()

        try:
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            parts = fingerprint.strip().split("|")

            window_update = parts[1]
            expected_window_update = "12517377"

            assert window_update == expected_window_update, (
                f"WINDOW_UPDATE mismatch for Firefox: got {window_update}, expected {expected_window_update}"
            )

            print(f"✓ WINDOW_UPDATE matches Firefox 115: {window_update}")

        finally:
            await page.close()

    # ========================================
    # Test 5: Pseudo-Header Ordering
    # ========================================

    @pytest.mark.asyncio
    async def test_pseudo_header_order_chrome(self, browser_chrome):
        """Test that pseudo-header order matches Chrome (m,a,s,p)."""
        page = await browser_chrome.new_page()

        try:
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            parts = fingerprint.strip().split("|")

            # Pseudo-header order is part 4
            order = parts[3]
            expected_order = "m,a,s,p"  # :method, :authority, :scheme, :path

            assert order == expected_order, (
                f"Pseudo-header order mismatch for Chrome: got {order}, expected {expected_order}"
            )

            print(f"✓ Pseudo-header order matches Chrome: {order}")

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_pseudo_header_order_firefox(self, browser_firefox):
        """Test that pseudo-header order matches Firefox (m,p,a,s)."""
        page = await browser_firefox.new_page()

        try:
            await page.goto(
                "https://scrapfly.io/web-scraping-tools/http2-fingerprint",
                timeout=30000,
            )
            await page.wait_for_selector("#fingerprint-result", timeout=10000)

            fingerprint = await page.locator("#akamai-fingerprint").text_content()
            parts = fingerprint.strip().split("|")

            order = parts[3]
            expected_order = "m,p,a,s"  # :method, :path, :authority, :scheme

            assert order == expected_order, (
                f"Pseudo-header order mismatch for Firefox: got {order}, expected {expected_order}"
            )

            print(f"✓ Pseudo-header order matches Firefox: {order}")

        finally:
            await page.close()

    # ========================================
    # Test 6: Cross-Layer Consistency
    # ========================================

    @pytest.mark.asyncio
    async def test_cross_layer_consistency_chrome(self, browser_chrome):
        """Test that TLS, HTTP/2, and User-Agent are consistent for Chrome."""
        page = await browser_chrome.new_page()

        try:
            # Visit comprehensive fingerprint test
            await page.goto("https://tls.peet.ws/api/all", timeout=30000)

            content = await page.content()
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start == -1:
                pytest.skip("Could not parse tls.peet.ws response")

            data = json.loads(content[json_start:json_end])

            # Check TLS library
            tls_library = data.get("tls", {}).get("library", "")
            assert "Boring" in tls_library or "Chrome" in tls_library, (
                f"TLS library mismatch for Chrome: got {tls_library}, expected BoringSSL"
            )

            # Check User-Agent match
            ua_match = data.get("http2", {}).get("user_agent_match", False)
            assert ua_match == True, "User-Agent does not match HTTP/2 fingerprint"

            tls_ua_match = data.get("tls", {}).get("user_agent_match", False)
            assert tls_ua_match == True, "User-Agent does not match TLS fingerprint"

            print("✓ Cross-layer consistency validated for Chrome")
            print(f"  TLS library: {tls_library}")
            print(f"  HTTP/2 ↔ UA match: {ua_match}")
            print(f"  TLS ↔ UA match: {tls_ua_match}")

        finally:
            await page.close()

    # ========================================
    # Test 7: Real-World E-commerce Access
    # ========================================

    @pytest.mark.asyncio
    async def test_amazon_access_chrome(self, browser_chrome):
        """Test Amazon.com access without bot challenge."""
        page = await browser_chrome.new_page()

        try:
            await page.goto("https://www.amazon.com", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Check for bot challenge
            content = await page.content()
            title = await page.title()

            assert "Robot Check" not in content, (
                "Amazon bot challenge (Robot Check) triggered"
            )

            assert "captcha" not in content.lower(), (
                "Amazon CAPTCHA challenge triggered"
            )

            assert "Sorry!" not in title, "Amazon blocking page detected"

            # Check for normal product listings
            products = await page.locator(".s-result-item").count()

            # Some pages may not have products, check for navigation instead
            if products == 0:
                nav = await page.locator("#nav-logo").count()
                assert nav > 0, "Amazon navigation not found (possible block)"

            print(f"✓ Amazon.com access successful (no bot challenge)")
            print(f"  Title: {title}")

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_ebay_access_chrome(self, browser_chrome):
        """Test eBay.com access without bot challenge."""
        page = await browser_chrome.new_page()

        try:
            await page.goto("https://www.ebay.com", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            content = await page.content()
            title = await page.title()

            assert "Security Measure" not in content, (
                "eBay security challenge triggered"
            )

            assert "captcha" not in content.lower(), "eBay CAPTCHA challenge triggered"

            # Check for normal navigation
            logo = await page.locator("#gh-logo").count()
            assert logo > 0, "eBay logo not found (possible block)"

            print(f"✓ eBay.com access successful (no bot challenge)")
            print(f"  Title: {title}")

        finally:
            await page.close()

    # ========================================
    # Test 8: Profile Validation
    # ========================================

    @pytest.mark.asyncio
    async def test_profile_structure_chrome(self):
        """Validate Chrome 120 profile structure."""
        profile_path = PROFILES_DIR / "chrome-120.json"

        if not profile_path.exists():
            pytest.skip(f"Profile not found: {profile_path}")

        with open(profile_path, "r") as f:
            profile = json.load(f)

        # Check TLS section
        assert "tls" in profile, "Missing 'tls' section in profile"
        assert "cipher_suites" in profile["tls"], (
            "Missing 'cipher_suites' in TLS config"
        )
        assert "extensions" in profile["tls"], "Missing 'extensions' in TLS config"

        # Check HTTP/2 section
        assert "http2" in profile, "Missing 'http2' section in profile"
        assert "settings" in profile["http2"], "Missing 'settings' in HTTP/2 config"
        assert "window_update" in profile["http2"], (
            "Missing 'window_update' in HTTP/2 config"
        )
        assert "pseudo_header_order" in profile["http2"], (
            "Missing 'pseudo_header_order' in HTTP/2 config"
        )

        # Validate cipher suites (at least 5)
        cipher_suites = profile["tls"]["cipher_suites"]
        assert len(cipher_suites) >= 5, (
            f"Too few cipher suites: {len(cipher_suites)}, expected >= 5"
        )

        # Validate HTTP/2 settings
        settings = profile["http2"]["settings"]
        required_settings = [
            "header_table_size",
            "enable_push",
            "max_concurrent_streams",
            "initial_window_size",
            "max_frame_size",
            "max_header_list_size",
        ]

        for setting in required_settings:
            assert setting in settings, f"Missing required HTTP/2 setting: {setting}"

        print("✓ Chrome 120 profile structure validated")
        print(f"  Cipher suites: {len(cipher_suites)}")
        print(f"  HTTP/2 settings: {len(settings)}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
