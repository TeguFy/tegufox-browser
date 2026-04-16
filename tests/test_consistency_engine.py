"""Unit tests for the consistency engine."""

from __future__ import annotations

import pytest

from consistency_engine import (
    ConsistencyEngine,
    GPUWebGLRule,
    HTTP2PseudoHeaderRule,
    LanguageLocaleRule,
    LocaleTimezoneRule,
    OSFontListRule,
    PlatformUARule,
    ScreenDPRViewportRule,
    TLSCipherOrderRule,
    default_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chrome_windows_full_profile():
    """Chrome Windows with http2 + timezone for full rule coverage."""
    return {
        "name": "chrome-120-win-full",
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "language": "en-US",
            "languages": ["en-US", "en"],
            "vendor": "Google Inc.",
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availHeight": 1040,
            "devicePixelRatio": 1.0,
        },
        "tls": {
            "cipher_suites": [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
            ],
        },
        "webgl": {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        },
        "http2": {
            "pseudo_header_order": ["method", "authority", "scheme", "path"],
        },
        "timezone": "America/New_York",
    }


@pytest.fixture
def chrome_windows_profile():
    return {
        "name": "chrome-120-win",
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "language": "en-US",
            "languages": ["en-US", "en"],
            "vendor": "Google Inc.",
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availHeight": 1040,
            "devicePixelRatio": 1.0,
        },
        "tls": {
            "cipher_suites": [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            ],
        },
        "webgl": {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        },
    }


# ---------------------------------------------------------------------------
# PlatformUARule
# ---------------------------------------------------------------------------


class TestPlatformUARule:
    def test_chrome_windows_passes(self, chrome_windows_profile):
        result = PlatformUARule().evaluate(chrome_windows_profile)
        assert result.passed
        assert result.rule_name == "platform_ua"

    def test_chrome_windows_mac_platform_fails(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["platform"] = "MacIntel"
        result = PlatformUARule().evaluate(chrome_windows_profile)
        assert not result.passed
        assert "MacIntel" in result.message

    def test_missing_fields_skip(self):
        result = PlatformUARule().evaluate({"navigator": {}})
        assert result.skipped


# ---------------------------------------------------------------------------
# LanguageLocaleRule
# ---------------------------------------------------------------------------


class TestLanguageLocaleRule:
    def test_en_us_passes(self, chrome_windows_profile):
        result = LanguageLocaleRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_mismatched_languages_array_fails(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["languages"] = ["vi-VN", "en-US"]
        result = LanguageLocaleRule().evaluate(chrome_windows_profile)
        assert not result.passed
        assert "languages[0]" in result.message


# ---------------------------------------------------------------------------
# ScreenDPRViewportRule
# ---------------------------------------------------------------------------


class TestScreenDPRViewportRule:
    def test_1920x1080_passes(self, chrome_windows_profile):
        result = ScreenDPRViewportRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_weird_ratio_fails(self, chrome_windows_profile):
        chrome_windows_profile["screen"]["width"] = 1000
        chrome_windows_profile["screen"]["height"] = 700
        result = ScreenDPRViewportRule().evaluate(chrome_windows_profile)
        assert not result.passed

    def test_implausible_taskbar_fails(self, chrome_windows_profile):
        chrome_windows_profile["screen"]["availHeight"] = 500  # 580px taskbar
        result = ScreenDPRViewportRule().evaluate(chrome_windows_profile)
        assert not result.passed
        assert "taskbar" in result.message

    def test_unusual_dpr_fails(self, chrome_windows_profile):
        chrome_windows_profile["screen"]["devicePixelRatio"] = 1.42
        result = ScreenDPRViewportRule().evaluate(chrome_windows_profile)
        assert not result.passed


# ---------------------------------------------------------------------------
# TLSCipherOrderRule
# ---------------------------------------------------------------------------


class TestTLSCipherOrderRule:
    def test_chrome_prefix_passes(self, chrome_windows_profile):
        result = TLSCipherOrderRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_firefox_ua_with_chrome_order_fails(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["userAgent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        )
        result = TLSCipherOrderRule().evaluate(chrome_windows_profile)
        assert not result.passed
        assert "firefox" in result.message.lower()

    def test_firefox_prefix_firefox_ua_passes(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["userAgent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        )
        chrome_windows_profile["tls"]["cipher_suites"] = [
            "TLS_AES_128_GCM_SHA256",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_256_GCM_SHA384",
        ]
        result = TLSCipherOrderRule().evaluate(chrome_windows_profile)
        assert result.passed


# ---------------------------------------------------------------------------
# GPUWebGLRule (user hot-spot)
# ---------------------------------------------------------------------------


class TestGPUWebGLRule:
    def test_angle_d3d11_passes_on_windows(self, chrome_windows_profile):
        result = GPUWebGLRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_mac_renderer_on_windows_fails(self, chrome_windows_profile):
        chrome_windows_profile["webgl"]["renderer"] = "Apple M2 GPU"
        result = GPUWebGLRule().evaluate(chrome_windows_profile)
        assert not result.passed

    def test_apple_m_chip_passes_on_mac(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["platform"] = "MacIntel"
        chrome_windows_profile["navigator"]["userAgent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )
        chrome_windows_profile["webgl"]["renderer"] = "Apple M3 Pro GPU"
        result = GPUWebGLRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_skips_when_webgl_missing(self):
        result = GPUWebGLRule().evaluate(
            {"navigator": {"platform": "Win32"}, "webgl": {}}
        )
        assert result.skipped


# ---------------------------------------------------------------------------
# OSFontListRule (user hot-spot)
# ---------------------------------------------------------------------------


class TestOSFontListRule:
    def test_skips_when_fonts_missing(self, chrome_windows_profile):
        result = OSFontListRule().evaluate(chrome_windows_profile)
        assert result.skipped

    def test_windows_fonts_passes(self, chrome_windows_profile):
        chrome_windows_profile["fonts"] = ["Segoe UI", "Arial", "Tahoma", "Calibri"]
        result = OSFontListRule().evaluate(chrome_windows_profile)
        assert result.passed

    def test_windows_missing_segoe_fails(self, chrome_windows_profile):
        chrome_windows_profile["fonts"] = ["Arial", "Tahoma"]
        result = OSFontListRule().evaluate(chrome_windows_profile)
        assert not result.passed
        assert "Segoe UI" in result.message


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# HTTP2PseudoHeaderRule
# ---------------------------------------------------------------------------


class TestHTTP2PseudoHeaderRule:
    def test_chrome_order_passes(self, chrome_windows_full_profile):
        result = HTTP2PseudoHeaderRule().evaluate(chrome_windows_full_profile)
        assert result.passed

    def test_firefox_order_with_chrome_ua_fails(self, chrome_windows_full_profile):
        chrome_windows_full_profile["http2"]["pseudo_header_order"] = [
            "method", "path", "authority", "scheme"
        ]
        result = HTTP2PseudoHeaderRule().evaluate(chrome_windows_full_profile)
        assert not result.passed
        assert "mismatch" in result.message

    def test_skips_without_http2(self, chrome_windows_profile):
        result = HTTP2PseudoHeaderRule().evaluate(chrome_windows_profile)
        assert result.skipped


# ---------------------------------------------------------------------------
# LocaleTimezoneRule
# ---------------------------------------------------------------------------


class TestLocaleTimezoneRule:
    def test_en_us_new_york_passes(self, chrome_windows_full_profile):
        result = LocaleTimezoneRule().evaluate(chrome_windows_full_profile)
        assert result.passed

    def test_en_us_tokyo_fails(self, chrome_windows_full_profile):
        chrome_windows_full_profile["timezone"] = "Asia/Tokyo"
        result = LocaleTimezoneRule().evaluate(chrome_windows_full_profile)
        assert not result.passed
        assert "Asia/Tokyo" in result.message

    def test_skips_without_timezone(self, chrome_windows_profile):
        result = LocaleTimezoneRule().evaluate(chrome_windows_profile)
        assert result.skipped

    def test_ja_jp_tokyo_passes(self, chrome_windows_full_profile):
        chrome_windows_full_profile["navigator"]["language"] = "ja-JP"
        chrome_windows_full_profile["timezone"] = "Asia/Tokyo"
        result = LocaleTimezoneRule().evaluate(chrome_windows_full_profile)
        assert result.passed


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


class TestConsistencyEngine:
    def test_engine_with_4_implemented_rules(self, chrome_windows_profile):
        rules = [
            PlatformUARule(),
            LanguageLocaleRule(),
            ScreenDPRViewportRule(),
            TLSCipherOrderRule(),
        ]
        engine = ConsistencyEngine(rules)
        report = engine.evaluate(chrome_windows_profile)
        assert report.passed
        assert report.score == pytest.approx(1.0)
        assert len(report.rule_results) == 4

    def test_engine_skipped_rules_renormalise(self):
        """Profile with only navigator → most rules skip, score still meaningful."""
        thin_profile = {
            "name": "thin",
            "navigator": {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120",
                "platform": "Win32",
                "language": "en-US",
            },
        }
        engine = ConsistencyEngine(
            [PlatformUARule(), LanguageLocaleRule(), ScreenDPRViewportRule()]
        )
        report = engine.evaluate(thin_profile)
        assert report.score == pytest.approx(1.0)
        skipped = [r for r in report.rule_results if r.skipped]
        assert len(skipped) == 1  # screen skip

    def test_engine_mixed_pass_fail(self, chrome_windows_profile):
        chrome_windows_profile["navigator"]["platform"] = "MacIntel"  # fails UA rule
        engine = ConsistencyEngine([
            PlatformUARule(),
            LanguageLocaleRule(),
            ScreenDPRViewportRule(),
            TLSCipherOrderRule(),
        ])
        report = engine.evaluate(chrome_windows_profile)
        assert not report.passed
        # 3 pass out of 4, but platform rule is error-severity → report.passed=False
        assert 0.5 < report.score < 1.0

    def test_default_rules_includes_all_eight(self):
        rules = default_rules()
        assert len(rules) == 8
        names = {r.name for r in rules}
        assert names == {
            "platform_ua",
            "language_locale",
            "screen_dpr_viewport",
            "tls_cipher_order",
            "gpu_webgl",
            "os_fonts",
            "http2_pseudo_header",
            "locale_timezone",
        }
