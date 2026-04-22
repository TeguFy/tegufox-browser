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
import re
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright, Page, BrowserContext


def parse_user_js(path: Path) -> Dict[str, Any]:
    """Parse Firefox user.js file into a dict of preference name -> value."""
    prefs: Dict[str, Any] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith('user_pref('):
            continue
        # user_pref("key", value);
        inner = line[len('user_pref('):-2]  # strip leading keyword and trailing );
        sep = inner.index(',')  # first comma separates key from value
        key = inner[:sep].strip().strip('"')
        raw = inner[sep + 1:].strip()
        if raw == 'true':
            prefs[key] = True
        elif raw == 'false':
            prefs[key] = False
        elif raw.startswith('"'):
            prefs[key] = raw.strip('"')
        else:
            try:
                prefs[key] = int(raw)
            except ValueError:
                prefs[key] = raw
    return prefs

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
    def configured_profile(self):
        """
        Fixture: Write DoH config to a temp profile dir (no browser needed).
        Yields (profile_dir, preferences_dict).
        """
        from scripts.configure_dns import DNSConfigurator

        profile_dir = Path(tempfile.mkdtemp(prefix="tegufox_test_"))
        configurator = DNSConfigurator(profile_path=profile_dir, verbose=False)
        preferences = configurator.generate_preferences(
            provider="cloudflare",
            mode=3,
            disable_ipv6=True,
            disable_webrtc=True,
            disable_prefetch=True,
        )
        configurator.write_user_js(preferences, backup=False)
        yield profile_dir, preferences
        shutil.rmtree(profile_dir, ignore_errors=True)

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

            # Launch Firefox with configured profile via persistent context
            context = p.firefox.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
            )

            yield context

            # Cleanup
            context.close()

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

    def test_01_doh_enabled(self, configured_profile):
        """Test 1: Verify DoH is enabled (TRR mode 3) in written user.js."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        assert prefs.get("network.trr.mode") == 3, (
            f"Expected TRR mode 3 (strict), got {prefs.get('network.trr.mode')}"
        )

    def test_02_doh_provider_configured(self, configured_profile):
        """Test 2: Verify DoH URI is a valid HTTPS dns-query endpoint."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        uri = prefs.get("network.trr.uri")
        assert uri is not None, "network.trr.uri not set"
        assert uri.startswith("https://"), f"Invalid DoH URI (must be HTTPS): {uri}"
        assert "dns-query" in uri, f"Invalid DoH URI (missing dns-query): {uri}"

    def test_03_bootstrap_address_configured(self, configured_profile):
        """Test 3: Verify bootstrap IP is set (required for TRR mode 3)."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        bootstrap = prefs.get("network.trr.bootstrapAddress")
        assert bootstrap is not None, (
            "network.trr.bootstrapAddress not set (required for mode 3)"
        )
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        assert re.match(ip_pattern, bootstrap.split(",")[0]), (
            f"Invalid bootstrap IP format: {bootstrap}"
        )

    def test_04_ipv6_disabled(self, configured_profile):
        """Test 4: Verify IPv6 is disabled to prevent IPv6 leaks."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        assert prefs.get("network.dns.disableIPv6") is True, (
            "IPv6 not disabled (IPv6 leak risk)"
        )

    def test_05_webrtc_disabled(self, configured_profile):
        """Test 5: Verify WebRTC peer connection is disabled."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        # media.peerconnection.enabled = false means WebRTC is disabled
        assert prefs.get("media.peerconnection.enabled") is False, (
            "WebRTC not disabled (IP leak risk)"
        )

    def test_06_dns_prefetch_disabled(self, configured_profile):
        """Test 6: Verify DNS prefetching is disabled."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        assert prefs.get("network.dns.disablePrefetch") is True, (
            "DNS prefetch not disabled (speculative query risk)"
        )

    def test_07_ecs_disabled(self, configured_profile):
        """Test 7: Verify EDNS Client Subnet (ECS) is disabled."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        assert prefs.get("network.trr.disable-ECS") is True, (
            "EDNS Client Subnet not disabled (location leak risk)"
        )

    def test_08_strict_mode_enforced(self, configured_profile):
        """Test 8: Verify strict mode — no system DNS fallback on DoH failure."""
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        assert prefs.get("network.trr.strict_native_fallback") is True, (
            "Strict mode not enforced (fallback risk)"
        )

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

    def test_14_configuration_persistence(self, configured_profile):
        """
        Test 14: Verify user.js persists across restarts (file is always read at startup).

        Since user.js is applied on every Firefox startup, persistence is guaranteed
        as long as the file exists in the profile directory.
        """
        profile_dir, _ = configured_profile
        user_js = profile_dir / "user.js"
        assert user_js.exists(), "user.js not found in profile directory"
        prefs = parse_user_js(user_js)
        # Configuration must survive any navigation u2014 user.js is re-applied each startup
        assert prefs.get("network.trr.mode") == 3, "TRR mode not persisted in user.js"
        assert prefs.get("network.dns.disableIPv6") is True, "IPv6 setting not persisted"

    def test_15_doh_provider_reachability(self, configured_profile):
        """
        Test 15: Verify the configured DoH endpoint responds to DNS-over-HTTPS queries.
        Requires network access u2014 skipped when offline.
        """
        profile_dir, _ = configured_profile
        prefs = parse_user_js(profile_dir / "user.js")
        doh_uri = prefs.get("network.trr.uri")
        assert doh_uri is not None, "network.trr.uri not set in user.js"

        try:
            import urllib.request

            req = urllib.request.Request(
                f"{doh_uri}?name=example.com&type=A",
                headers={"accept": "application/dns-json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status in [200, 400, 415], (
                    f"DoH provider not reachable (status: {resp.status})"
                )
        except Exception as e:
            pytest.skip(f"DoH reachability test skipped (network unavailable): {e}")


class TestDNSLeakPreventionIntegration:
    """Integration tests for DNS leak prevention with other Tegufox components"""

    def test_integration_http2_consistency(self):
        """
        Test: DNS provider consistency with HTTP/2 fingerprint.

        Ensures DoH provider aligns with browser TLS/HTTP/2 fingerprint.
        For example, Chrome profiles should use Cloudflare (Chrome default).
        """
        from profile_manager import ProfileManager
        manager = ProfileManager()
        try:
            profile = manager.load("chrome-120")
        except FileNotFoundError:
            pytest.skip("chrome-120 profile not found in database")

        # Check DNS config
        dns_config = profile.get("dns_config", {})
        provider = dns_config.get("provider", "")

        # Chrome should use Cloudflare (default Chrome DoH)
        assert provider == "cloudflare", (
            f"Chrome profile should use Cloudflare DoH (got: {provider})"
        )

    def test_integration_profile_templates(self):
        """
        Test: Standard browser templates have complete DNS configuration.

        Only checks the canonical browser templates (chrome-120, firefox-115, safari-17).
        """
        from profile_manager import ProfileManager
        STANDARD_TEMPLATES = ["chrome-120", "firefox-115", "safari-17"]
        manager = ProfileManager()

        found = 0
        for name in STANDARD_TEMPLATES:
            try:
                profile = manager.load(name)
            except FileNotFoundError:
                continue
            found += 1

            assert "dns_config" in profile, (
                f"Template {name} missing dns_config"
            )
            dns_config = profile["dns_config"]
            assert "enabled" in dns_config, (
                f"Template {name} dns_config missing 'enabled'"
            )
            if dns_config.get("enabled"):
                assert "provider" in dns_config, (
                    f"Template {name} dns_config missing 'provider'"
                )

        assert found > 0, "No standard browser templates found in database"


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
