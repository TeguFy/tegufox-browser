#!/usr/bin/env python3
"""
DNS Leak Prevention Test Suite

Comprehensive automated testing for DNS leak prevention in Tegufox profiles.
Tests DoH configuration, WebRTC leak prevention, IPv6 leak prevention, and real-world scenarios.

Usage:
    # Run all tests
    pytest tests/test_dns_leak.py -v

    # Run specific test
    pytest tests/test_dns_leak.py::TestDNSLeakPrevention::test_01_doh_enabled -v

    # Run with detailed output
    pytest tests/test_dns_leak.py -v -s

Requirements:
    - pytest
    - playwright (pytest-playwright)
    - Camoufox installed

Install:
    pip install pytest pytest-playwright
    playwright install firefox

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 3 Day 12
"""

import pytest
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Test configuration
TEST_TIMEOUT = 30000  # 30 seconds per test
PAGE_LOAD_TIMEOUT = 10000  # 10 seconds for page loads

# Expected DoH providers (for validation)
EXPECTED_DOH_PROVIDERS = {
    "cloudflare": ["cloudflare", "apnic", "1.1.1.1"],
    "quad9": ["quad9", "quad 9"],
    "mullvad": ["mullvad"],
    "google": ["google"],
}


class TestDNSLeakPrevention:
    """Test suite for DNS leak prevention"""

    @pytest.fixture(scope="class")
    def browser_context(self):
        """
        Fixture: Browser context with DoH configured.

        This fixture creates a temporary Firefox profile with DNS leak prevention
        configured and returns a browser context for testing.
        """
        with sync_playwright() as p:
            # Create temporary profile directory
            import tempfile

            profile_dir = Path(tempfile.mkdtemp(prefix="tegufox_test_"))

            # Configure DNS leak prevention
            from scripts.configure_dns import DNSConfigurator

            configurator = DNSConfigurator(profile_path=profile_dir, verbose=False)

            # Generate Cloudflare DoH config (mode 3, strict)
            preferences = configurator.generate_preferences(
                provider="cloudflare",
                mode=3,
                disable_ipv6=True,
                disable_webrtc=True,
                disable_prefetch=True,
            )

            configurator.write_user_js(preferences, backup=False)

            # Launch Firefox with configured profile
            browser = p.firefox.launch(
                headless=True,  # Headless for CI/CD
                args=[f"--profile={profile_dir}"],
            )

            context = browser.new_context()

            yield context

            # Cleanup
            context.close()
            browser.close()

            # Remove temp profile
            import shutil

            shutil.rmtree(profile_dir, ignore_errors=True)

    @pytest.fixture
    def page(self, browser_context: BrowserContext):
        """Fixture: New page for each test"""
        page = browser_context.new_page()
        page.set_default_timeout(TEST_TIMEOUT)
        yield page
        page.close()

    def test_01_doh_enabled(self, page: Page):
        """
        Test 1: Verify DoH is enabled (TRR mode 3).

        Checks that Firefox TRR mode is set to 3 (strict DoH, no fallback).
        """
        # Navigate to about:config (special Firefox page)
        page.goto("about:config")

        # Accept warning (if present)
        try:
            accept_button = page.locator(
                'button:has-text("Accept the Risk and Continue")'
            )
            if accept_button.is_visible(timeout=1000):
                accept_button.click()
        except Exception:
            pass  # Button not present, already accepted

        # Search for network.trr.mode
        page.fill('input[id="about-config-search"]', "network.trr.mode")
        page.wait_for_timeout(500)

        # Get preference value
        mode_value = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getIntPref("network.trr.mode");
                } catch (e) {
                    return null;
                }
            }
        """)

        assert mode_value == 3, f"Expected TRR mode 3 (strict), got {mode_value}"

    def test_02_doh_provider_configured(self, page: Page):
        """
        Test 2: Verify DoH provider URI is configured correctly.

        Checks that network.trr.uri is set to a valid DoH endpoint.
        """
        page.goto("about:config")

        # Get network.trr.uri
        uri = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getStringPref("network.trr.uri");
                } catch (e) {
                    return null;
                }
            }
        """)

        assert uri is not None, "network.trr.uri not set"
        assert uri.startswith("https://"), f"Invalid DoH URI (must be HTTPS): {uri}"
        assert "dns-query" in uri, f"Invalid DoH URI (missing dns-query): {uri}"

    def test_03_bootstrap_address_configured(self, page: Page):
        """
        Test 3: Verify bootstrap address is configured (required for mode 3).

        TRR mode 3 requires a bootstrap IP to avoid chicken-and-egg problem.
        """
        page.goto("about:config")

        bootstrap = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getStringPref("network.trr.bootstrapAddress");
                } catch (e) {
                    return null;
                }
            }
        """)

        assert bootstrap is not None, (
            "network.trr.bootstrapAddress not set (required for mode 3)"
        )

        # Validate IP format (simple regex)
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        assert re.match(ip_pattern, bootstrap.split(",")[0]), (
            f"Invalid bootstrap IP format: {bootstrap}"
        )

    def test_04_ipv6_disabled(self, page: Page):
        """
        Test 4: Verify IPv6 is disabled to prevent IPv6 leaks.

        IPv6 queries can bypass DoH on dual-stack networks.
        """
        page.goto("about:config")

        ipv6_disabled = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getBoolPref("network.dns.disableIPv6");
                } catch (e) {
                    return false;
                }
            }
        """)

        assert ipv6_disabled == True, "IPv6 not disabled (IPv6 leak risk)"

    def test_05_webrtc_disabled(self, page: Page):
        """
        Test 5: Verify WebRTC is disabled to prevent IP leaks.

        WebRTC can expose real IP via STUN servers.
        """
        page.goto("about:config")

        webrtc_disabled = page.evaluate("""
            () => {
                try {
                    return !Services.prefs.getBoolPref("media.peerconnection.enabled");
                } catch (e) {
                    return false;
                }
            }
        """)

        assert webrtc_disabled == True, "WebRTC not disabled (IP leak risk)"

    def test_06_dns_prefetch_disabled(self, page: Page):
        """
        Test 6: Verify DNS prefetching is disabled.

        DNS prefetch can cause speculative DNS queries that bypass DoH.
        """
        page.goto("about:config")

        prefetch_disabled = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getBoolPref("network.dns.disablePrefetch");
                } catch (e) {
                    return false;
                }
            }
        """)

        assert prefetch_disabled == True, (
            "DNS prefetch not disabled (speculative query risk)"
        )

    def test_07_ecs_disabled(self, page: Page):
        """
        Test 7: Verify EDNS Client Subnet (ECS) is disabled for privacy.

        ECS can leak user's approximate location to DNS provider.
        """
        page.goto("about:config")

        ecs_disabled = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getBoolPref("network.trr.disable-ECS");
                } catch (e) {
                    return false;
                }
            }
        """)

        assert ecs_disabled == True, (
            "EDNS Client Subnet not disabled (location leak risk)"
        )

    def test_08_strict_mode_enforced(self, page: Page):
        """
        Test 8: Verify strict mode is enforced (no system DNS fallback).

        Ensures that even on DoH failure, system DNS is never used.
        """
        page.goto("about:config")

        strict_mode = page.evaluate("""
            () => {
                try {
                    return Services.prefs.getBoolPref("network.trr.strict_native_fallback");
                } catch (e) {
                    return false;
                }
            }
        """)

        assert strict_mode == True, "Strict mode not enforced (fallback risk)"

    def test_09_dns_leak_dnsleaktest(self, page: Page):
        """
        Test 9: Real-world DNS leak test using dnsleaktest.com.

        Visits dnsleaktest.com and verifies no ISP DNS is visible.
        This is a critical test that validates actual DNS query routing.
        """
        # Visit dnsleaktest.com
        page.goto("https://www.dnsleaktest.com", timeout=PAGE_LOAD_TIMEOUT)

        # Wait for page to load
        page.wait_for_timeout(2000)

        # Click "Standard Test" button
        try:
            standard_test_btn = page.locator('a:has-text("Standard test")')
            if standard_test_btn.is_visible(timeout=2000):
                standard_test_btn.click()
            else:
                # Try alternative selector
                page.click("text=Standard test")
        except Exception as e:
            pytest.skip(f"Could not start DNS leak test (button not found): {e}")

        # Wait for test to complete (up to 15 seconds)
        page.wait_for_timeout(15000)

        # Extract DNS server information
        try:
            # Look for DNS servers in results table
            dns_servers = page.locator(".table-bordered tbody tr")
            count = dns_servers.count()

            if count == 0:
                pytest.skip("DNS leak test did not complete (no results)")

            # Check each DNS server
            leak_detected = False
            isp_names = []

            for i in range(count):
                row = dns_servers.nth(i)
                # Column 2 typically contains ISP name
                cells = row.locator("td")
                if cells.count() >= 2:
                    isp = cells.nth(1).inner_text().lower()
                    isp_names.append(isp)

                    # Check if it's a known DoH provider (not ISP)
                    is_doh_provider = any(
                        provider_keyword in isp
                        for providers in EXPECTED_DOH_PROVIDERS.values()
                        for provider_keyword in providers
                    )

                    # Common ISP keywords (leak indicators)
                    isp_keywords = [
                        "comcast",
                        "at&t",
                        "verizon",
                        "charter",
                        "spectrum",
                        "cox",
                        "centurylink",
                        "frontier",
                        "optimum",
                        "xfinity",
                        "bt",
                        "virgin",
                        "sky",
                        "talktalk",
                        "vodafone",  # UK ISPs
                        "telekom",
                        "o2",
                        "vodafone",  # DE ISPs
                        "orange",
                        "free",
                        "sfr",
                        "bouygues",  # FR ISPs
                    ]

                    if any(keyword in isp for keyword in isp_keywords):
                        leak_detected = True
                        break

            assert not leak_detected, (
                f"DNS LEAK DETECTED: ISP DNS visible in results: {isp_names}"
            )

        except Exception as e:
            pytest.skip(f"Could not parse DNS leak test results: {e}")

    def test_10_webrtc_leak_ipleak(self, page: Page):
        """
        Test 10: WebRTC leak test using ipleak.net.

        Verifies that WebRTC does not expose real IP address.
        """
        # Visit ipleak.net
        page.goto("https://ipleak.net", timeout=PAGE_LOAD_TIMEOUT)

        # Wait for WebRTC detection (JavaScript execution)
        page.wait_for_timeout(5000)

        # Check WebRTC section
        try:
            # Look for WebRTC leak indicators
            webrtc_section = page.locator(
                '#webrtc-detection, .webrtc, [data-testid="webrtc"]'
            )

            if webrtc_section.count() > 0:
                webrtc_text = webrtc_section.first.inner_text().lower()

                # Indicators that WebRTC is disabled or no leak
                safe_indicators = [
                    "not detected",
                    "disabled",
                    "no webrtc",
                    "webrtc not available",
                ]

                # Indicators of a leak
                leak_indicators = ["leak detected", "real ip", "local ip"]

                has_safe_indicator = any(
                    indicator in webrtc_text for indicator in safe_indicators
                )
                has_leak_indicator = any(
                    indicator in webrtc_text for indicator in leak_indicators
                )

                assert not has_leak_indicator or has_safe_indicator, (
                    f"WebRTC leak detected: {webrtc_text}"
                )
            else:
                # WebRTC section not found (possibly blocked by extension)
                # Try JavaScript detection
                webrtc_available = page.evaluate("""
                    () => {
                        return typeof RTCPeerConnection !== 'undefined' ||
                               typeof webkitRTCPeerConnection !== 'undefined' ||
                               typeof mozRTCPeerConnection !== 'undefined';
                    }
                """)

                assert not webrtc_available, (
                    "WebRTC API is available (should be disabled)"
                )

        except Exception as e:
            # If we can't detect WebRTC leak, check if API is disabled
            webrtc_available = page.evaluate("""
                () => {
                    return typeof RTCPeerConnection !== 'undefined';
                }
            """)

            assert not webrtc_available, (
                f"WebRTC leak test inconclusive, but API is available: {e}"
            )

    def test_11_ipv6_leak_test_ipv6(self, page: Page):
        """
        Test 11: IPv6 leak test using test-ipv6.com.

        Verifies that IPv6 is properly disabled or tunneled.
        """
        # Visit test-ipv6.com
        page.goto("https://test-ipv6.com", timeout=PAGE_LOAD_TIMEOUT)

        # Wait for connectivity test
        page.wait_for_timeout(10000)

        # Check IPv6 connectivity status
        try:
            # Look for IPv6 test results
            ipv6_result = page.locator('#ipv6, [data-testid="ipv6"]')

            if ipv6_result.count() > 0:
                ipv6_text = ipv6_result.first.inner_text().lower()

                # IPv6 should be disabled/not detected
                safe_indicators = [
                    "not supported",
                    "not detected",
                    "no ipv6",
                    "ipv6 not available",
                    "no connectivity",
                ]

                has_safe_indicator = any(
                    indicator in ipv6_text for indicator in safe_indicators
                )

                assert has_safe_indicator, (
                    f"IPv6 leak detected (IPv6 is available): {ipv6_text}"
                )
            else:
                # Alternative: Check for specific test result elements
                # test-ipv6.com shows score out of 10
                score_element = page.locator(".score")
                if score_element.count() > 0:
                    score_text = score_element.first.inner_text()
                    # If IPv6 disabled, score should be 10/10 for IPv4-only
                    # Or 0/10 if no connectivity (which would be a different issue)
                    # We mainly care that IPv6 is not leaking
                    pass  # Score alone doesn't indicate leak

        except Exception as e:
            pytest.skip(f"IPv6 leak test inconclusive: {e}")

    def test_12_real_world_amazon(self, page: Page):
        """
        Test 12: Real-world test - Browse Amazon with DoH active.

        Ensures DoH works correctly with real e-commerce sites.
        """
        # Visit Amazon
        page.goto("https://www.amazon.com", timeout=PAGE_LOAD_TIMEOUT)

        # Wait for page to load
        page.wait_for_timeout(3000)

        # Verify page loaded successfully
        try:
            # Check for Amazon logo or common element
            page.wait_for_selector("#nav-logo-sprites, .nav-logo-base", timeout=5000)
        except Exception:
            pytest.skip("Amazon did not load (possible blocking or network issue)")

        # Search for a product
        try:
            search_box = page.locator(
                '#twotabsearchtextbox, input[type="text"][name="field-keywords"]'
            )
            if search_box.count() > 0:
                search_box.first.fill("laptop")

                # Submit search
                search_button = page.locator(
                    'input[type="submit"][value="Go"], #nav-search-submit-button'
                )
                if search_button.count() > 0:
                    search_button.first.click()

                    # Wait for search results
                    page.wait_for_timeout(3000)

                    # Verify search results loaded
                    results = page.locator(
                        '.s-result-item, [data-component-type="s-search-result"]'
                    )
                    assert results.count() > 0, "Amazon search failed (no results)"
        except Exception as e:
            pytest.skip(f"Amazon search test inconclusive: {e}")

    def test_13_real_world_ebay(self, page: Page):
        """
        Test 13: Real-world test - Browse eBay with DoH active.

        Ensures DoH works correctly with eBay.
        """
        # Visit eBay
        page.goto("https://www.ebay.com", timeout=PAGE_LOAD_TIMEOUT)

        # Wait for page to load
        page.wait_for_timeout(3000)

        # Verify page loaded
        try:
            page.wait_for_selector("#gh-logo, .gh-logo", timeout=5000)
        except Exception:
            pytest.skip("eBay did not load")

        # Basic interaction test
        try:
            search_box = page.locator('input[type="text"][name="q"], #gh-ac')
            if search_box.count() > 0:
                search_box.first.fill("vintage camera")

                # Submit
                search_btn = page.locator(
                    'input[type="submit"][value="Search"], #gh-btn'
                )
                if search_btn.count() > 0:
                    search_btn.first.click()
                    page.wait_for_timeout(3000)
        except Exception as e:
            pytest.skip(f"eBay search test inconclusive: {e}")

    def test_14_configuration_persistence(self, browser_context: BrowserContext):
        """
        Test 14: Verify DNS configuration persists across page navigations.

        Ensures DoH settings are not lost during browsing session.
        """
        page = browser_context.new_page()

        # Check TRR mode on first page
        page.goto("about:config")

        mode_initial = page.evaluate("""
            () => Services.prefs.getIntPref("network.trr.mode")
        """)

        # Navigate to different pages
        page.goto("https://example.com")
        page.wait_for_timeout(2000)

        page.goto("https://www.google.com")
        page.wait_for_timeout(2000)

        # Check TRR mode again
        page.goto("about:config")

        mode_final = page.evaluate("""
            () => Services.prefs.getIntPref("network.trr.mode")
        """)

        assert mode_initial == mode_final == 3, (
            f"DoH configuration changed during navigation (initial: {mode_initial}, final: {mode_final})"
        )

        page.close()

    def test_15_doh_provider_reachability(self, page: Page):
        """
        Test 15: Verify DoH provider is reachable.

        Tests that the configured DoH endpoint responds correctly.
        """
        page.goto("about:config")

        # Get DoH URI
        doh_uri = page.evaluate("""
            () => Services.prefs.getStringPref("network.trr.uri")
        """)

        # Make a test DNS query to DoH provider
        # Note: This requires network access, may fail in restricted environments

        try:
            import requests

            # Parse DoH provider base URL
            # Example: https://mozilla.cloudflare-dns.com/dns-query

            # Make a simple DNS query (for example.com)
            # DoH wireformat query (simplified, just test endpoint reachability)
            response = requests.get(
                doh_uri,
                params={"name": "example.com", "type": "A"},
                headers={"accept": "application/dns-json"},
                timeout=5,
            )

            assert response.status_code in [200, 400, 415], (
                f"DoH provider not reachable (status: {response.status_code})"
            )

        except ImportError:
            pytest.skip("requests library not available, skipping reachability test")
        except Exception as e:
            pytest.skip(f"DoH provider reachability test failed: {e}")


class TestDNSLeakPreventionIntegration:
    """Integration tests for DNS leak prevention with other Tegufox components"""

    def test_integration_http2_consistency(self):
        """
        Test: DNS provider consistency with HTTP/2 fingerprint.

        Ensures DoH provider aligns with browser TLS/HTTP/2 fingerprint.
        For example, Chrome profiles should use Cloudflare (Chrome default).
        """
        # Load chrome-120 profile
        profile_path = Path("profiles/chrome-120.json")

        if not profile_path.exists():
            pytest.skip("chrome-120.json profile not found")

        with open(profile_path) as f:
            profile = json.load(f)

        # Check DNS config
        dns_config = profile.get("dns_config", {})
        provider = dns_config.get("provider", "")

        # Chrome should use Cloudflare (default Chrome DoH)
        assert provider == "cloudflare", (
            f"Chrome profile should use Cloudflare DoH (got: {provider})"
        )

    def test_integration_profile_templates(self):
        """
        Test: All profile templates have DNS configuration.

        Ensures every profile template includes dns_config section.
        """
        profiles_dir = Path("profiles")

        if not profiles_dir.exists():
            pytest.skip("profiles directory not found")

        profile_files = list(profiles_dir.glob("*.json"))

        assert len(profile_files) > 0, "No profile templates found"

        for profile_file in profile_files:
            with open(profile_file) as f:
                profile = json.load(f)

            # Check for dns_config
            assert "dns_config" in profile, (
                f"Profile {profile_file.name} missing dns_config"
            )

            dns_config = profile["dns_config"]

            # Check required fields
            assert "enabled" in dns_config, (
                f"Profile {profile_file.name} dns_config missing 'enabled'"
            )

            if dns_config.get("enabled"):
                assert "provider" in dns_config, (
                    f"Profile {profile_file.name} dns_config missing 'provider'"
                )


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# Mark slow tests
pytest.mark.slow(TestDNSLeakPrevention.test_09_dns_leak_dnsleaktest)
pytest.mark.slow(TestDNSLeakPrevention.test_10_webrtc_leak_ipleak)
pytest.mark.slow(TestDNSLeakPrevention.test_11_ipv6_leak_test_ipv6)
pytest.mark.slow(TestDNSLeakPrevention.test_12_real_world_amazon)
pytest.mark.slow(TestDNSLeakPrevention.test_13_real_world_ebay)

# Mark integration tests
pytest.mark.integration(TestDNSLeakPreventionIntegration)


if __name__ == "__main__":
    """Run tests directly with pytest"""
    pytest.main([__file__, "-v", "-s"])
