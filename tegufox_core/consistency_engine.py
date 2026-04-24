"""
Tegufox Consistency Engine

Cross-layer fingerprint validation for browser profiles. Each rule evaluates a
single dimension of consistency (UA vs platform, UA vs TLS cipher order,
screen vs DPR, etc.) with an independent weight. The engine aggregates them
into a weighted score in [0, 1] plus a per-rule breakdown for debugging.

Design contract:
- Rules are side-effect free and return a RuleResult with the weight they
  contributed. Missing profile fields cause the rule to skip (weight
  redistributes to others) rather than fail.
- Rule weights declared at class level must sum to 1.0 across the default rule
  set; `ConsistencyEngine.evaluate()` renormalises if a rule skips.
- Anti-correlation lives in a separate FingerprintRegistry (SQLite); the
  engine only queries it when one is passed in.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Set

Severity = Literal["error", "warning"]


@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    weight: float
    message: str
    severity: Severity = "warning"
    skipped: bool = False
    details: dict = field(default_factory=dict)


@dataclass
class ConsistencyReport:
    score: float
    passed: bool
    rule_results: List[RuleResult]
    collisions: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Score: {self.score:.3f}  Passed: {self.passed}"]
        for r in self.rule_results:
            tag = "SKIP" if r.skipped else ("PASS" if r.passed else r.severity.upper())
            lines.append(f"  [{tag}] {r.rule_name} (w={r.weight:.2f}): {r.message}")
        if self.collisions:
            lines.append(f"  Collisions: {', '.join(self.collisions)}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "rules": [
                {
                    "name": r.rule_name,
                    "passed": r.passed,
                    "weight": r.weight,
                    "message": r.message,
                    "severity": r.severity,
                    "skipped": r.skipped,
                    "details": r.details,
                }
                for r in self.rule_results
            ],
            "collisions": self.collisions,
        }


class Rule(ABC):
    name: str = "rule"
    weight: float = 0.0
    severity: Severity = "warning"

    @abstractmethod
    def evaluate(self, profile: dict) -> RuleResult: ...

    def _skip(self, message: str) -> RuleResult:
        return RuleResult(
            rule_name=self.name,
            passed=True,
            weight=self.weight,
            message=message,
            severity=self.severity,
            skipped=True,
        )


# ---------------------------------------------------------------------------
# Rule 1: Platform / User-Agent coherence
# ---------------------------------------------------------------------------


class PlatformUARule(Rule):
    name = "platform_ua"
    weight = 0.20
    severity = "error"

    _PLATFORM_BY_UA_MARKER = [
        ("Windows NT", {"Win32"}),
        ("Macintosh", {"MacIntel"}),
        ("Linux", {"Linux x86_64", "Linux armv8l", "Linux armv7l", "Linux i686"}),
        ("Android", {"Linux armv8l", "Linux armv7l"}),
        ("iPhone", {"iPhone"}),
        ("iPad", {"MacIntel", "iPad"}),
    ]

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        ua = nav.get("userAgent", "")
        platform = nav.get("platform", "")

        if not ua or not platform:
            return self._skip("navigator.userAgent or platform missing")

        for marker, expected in self._PLATFORM_BY_UA_MARKER:
            if marker in ua:
                if platform in expected:
                    return RuleResult(
                        self.name, True, self.weight,
                        f"UA '{marker}' matches platform '{platform}'",
                        self.severity,
                    )
                return RuleResult(
                    self.name, False, self.weight,
                    f"UA mentions '{marker}' but platform='{platform}' (expected one of {sorted(expected)})",
                    self.severity,
                    details={"ua_marker": marker, "platform": platform, "expected": sorted(expected)},
                )

        return RuleResult(
            self.name, False, self.weight,
            f"UA has no recognised platform marker: {ua[:80]}",
            self.severity,
        )


# ---------------------------------------------------------------------------
# Rule 2: navigator.language  ↔ expected locales
# ---------------------------------------------------------------------------


class LanguageLocaleRule(Rule):
    name = "language_locale"
    weight = 0.15
    severity = "warning"

    _LANG_TO_REGIONS = {
        "en-US": {"US"},
        "en-GB": {"GB"},
        "en-CA": {"CA"},
        "en-AU": {"AU"},
        "fr-FR": {"FR"},
        "fr-CA": {"CA"},
        "de-DE": {"DE"},
        "de-AT": {"AT"},
        "es-ES": {"ES"},
        "es-MX": {"MX"},
        "pt-BR": {"BR"},
        "pt-PT": {"PT"},
        "ja-JP": {"JP"},
        "zh-CN": {"CN"},
        "zh-TW": {"TW"},
        "ko-KR": {"KR"},
        "vi-VN": {"VN"},
        "ru-RU": {"RU"},
    }

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        primary = nav.get("language")
        languages = nav.get("languages") or []

        if not primary:
            return self._skip("navigator.language missing")

        if languages and languages[0] != primary:
            return RuleResult(
                self.name, False, self.weight,
                f"navigator.language='{primary}' but languages[0]='{languages[0]}'",
                self.severity,
            )

        if primary not in self._LANG_TO_REGIONS:
            return RuleResult(
                self.name, False, self.weight,
                f"language '{primary}' not in common locale set (could be a typo)",
                self.severity,
            )

        for secondary in languages[1:]:
            if "-" not in secondary and secondary != primary.split("-")[0]:
                return RuleResult(
                    self.name, False, self.weight,
                    f"secondary language '{secondary}' doesn't share root with '{primary}'",
                    self.severity,
                )

        return RuleResult(
            self.name, True, self.weight,
            f"language '{primary}' and secondaries coherent",
            self.severity,
        )


# ---------------------------------------------------------------------------
# Rule 3: Screen / DPR / viewport coherence
# ---------------------------------------------------------------------------


class ScreenDPRViewportRule(Rule):
    name = "screen_dpr_viewport"
    weight = 0.15
    severity = "warning"

    _COMMON_RATIOS = [
        (16, 9),
        (16, 10),
        (3, 2),
        (4, 3),
        (21, 9),
        (1470, 956),   # 13" MacBook Air/Pro logical
        (1512, 982),   # 14" MacBook Pro logical
        (1728, 1117),  # 16" MacBook Pro logical
    ]
    _RATIO_TOLERANCE = 0.02

    def evaluate(self, profile: dict) -> RuleResult:
        screen = profile.get("screen") or {}
        width = screen.get("width")
        height = screen.get("height")

        if not width or not height:
            return self._skip("screen.width or screen.height missing")

        actual_ratio = width / height
        ratio_ok = any(
            abs(actual_ratio - (w / h)) / (w / h) <= self._RATIO_TOLERANCE
            for w, h in self._COMMON_RATIOS
        )
        if not ratio_ok:
            return RuleResult(
                self.name, False, self.weight,
                f"{width}x{height} aspect {actual_ratio:.3f} doesn't match common ratios",
                self.severity,
                details={"ratio": actual_ratio},
            )

        avail_height = screen.get("availHeight")
        if avail_height is not None:
            taskbar = height - avail_height
            if taskbar < 0 or taskbar > 120:
                return RuleResult(
                    self.name, False, self.weight,
                    f"availHeight {avail_height} implausible (taskbar={taskbar}px, expect 0-120)",
                    self.severity,
                )

        dpr = screen.get("devicePixelRatio", 1.0)
        if dpr not in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
            return RuleResult(
                self.name, False, self.weight,
                f"devicePixelRatio={dpr} is not a standard value",
                self.severity,
            )

        return RuleResult(
            self.name, True, self.weight,
            f"{width}x{height} @ DPR {dpr} coherent",
            self.severity,
        )


# ---------------------------------------------------------------------------
# Rule 4: UA  ↔ TLS cipher suite order
# ---------------------------------------------------------------------------


class TLSCipherOrderRule(Rule):
    """Validate the first few cipher suites match the target browser's stack.

    Chrome (BoringSSL): TLS13 AES128-GCM, TLS13 AES256-GCM, TLS13 CHACHA20.
    Firefox (NSS): TLS13 AES128-GCM, TLS13 CHACHA20, TLS13 AES256-GCM.
    Safari (SecureTransport): TLS13 AES256-GCM first.
    """

    name = "tls_cipher_order"
    weight = 0.20
    severity = "error"

    _EXPECTED_PREFIX = {
        "chrome": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
        ],
        "firefox": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_256_GCM_SHA384",
        ],
        "safari": [
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256",
        ],
    }

    @staticmethod
    def _detect_browser(ua: str) -> Optional[str]:
        if "Chrome/" in ua and "Edg/" not in ua and "OPR/" not in ua:
            return "chrome"
        if "Firefox/" in ua:
            return "firefox"
        if "Safari/" in ua and "Chrome/" not in ua:
            return "safari"
        return None

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        tls = profile.get("tls") or {}
        suites = tls.get("cipher_suites") or []
        ua = nav.get("userAgent", "")

        if not ua or not suites:
            return self._skip("navigator.userAgent or tls.cipher_suites missing")

        browser = self._detect_browser(ua)
        if browser is None:
            return self._skip("could not infer browser family from UA")

        expected = self._EXPECTED_PREFIX[browser]
        actual_prefix = suites[: len(expected)]

        if actual_prefix == expected:
            return RuleResult(
                self.name, True, self.weight,
                f"TLS cipher prefix matches {browser} signature",
                self.severity,
            )
        return RuleResult(
            self.name, False, self.weight,
            f"{browser} TLS prefix mismatch: expected {expected}, got {actual_prefix}",
            self.severity,
            details={"browser": browser, "expected": expected, "actual": actual_prefix},
        )


# ---------------------------------------------------------------------------
# Rule 5: GPU vendor / WebGL renderer  (user hot-spot)
# ---------------------------------------------------------------------------


class GPUWebGLRule(Rule):
    """Cross-check navigator.platform against webgl.renderer fingerprints.

    The heuristic here depends on which bot checks you target: permissive
    keyword match trades false positives for coverage; strict regex trades
    false negatives for confidence. The user fills in the patterns because
    the right balance depends on the target site dataset.
    """

    name = "gpu_webgl"
    weight = 0.20
    severity = "error"

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        webgl = profile.get("webgl") or {}
        platform = nav.get("platform", "")
        ua = nav.get("userAgent", "")
        renderer = webgl.get("renderer", "")
        vendor = webgl.get("vendor", "")

        if not platform or not renderer:
            return self._skip("navigator.platform or webgl.renderer missing")

        patterns = {
            "Win32": [
                re.compile(r"ANGLE \(.+Direct3D11.+ps_5_0"),
                re.compile(r"ANGLE \(.+Vulkan"),
                re.compile(r"Mozilla -- GeForce"),
                re.compile(r"(?:NVIDIA\s+)?GeForce\s+(?:GTX|RTX)\s+\d"),
                re.compile(r"NVIDIA\s+Quadro"),
                re.compile(r"Intel\(R\) (?:Iris|UHD|HD|Arc)(?:\(TM\))?(?:\(R\))?(?:\s+[\w\d]+)*\s+Graphics"),
                re.compile(r"AMD Radeon (?:RX|R\d|Pro|Vega|HD)\s+[\w\d]+"),
            ],
            "MacIntel": [
                re.compile(r"ANGLE \(Apple, ANGLE Metal Renderer: Apple M[1-9] ?(Pro|Max|Ultra)?"),
                re.compile(r"ANGLE \(Apple, Apple M[1-9] ?(Pro|Max|Ultra)?"),
                re.compile(r"Apple M[1-9] ?(Pro|Max|Ultra)? ?GPU"),
                re.compile(r"Apple GPU"),
                re.compile(r"Apple M[1-9]"),
                re.compile(r"AMD Radeon (Pro )?[A-Z0-9]+"),
                re.compile(r"ATI Technologies Inc\., AMD Radeon"),
                re.compile(r"Intel\(R\) (?:Iris|UHD|HD)(?:\(TM\))?(?:\s+(?:Plus|Pro))?(?:\s+\w+)? ?Graphics"),
                re.compile(r"Intel\(R\) .+OpenGL Engine"),
            ],
            "Linux x86_64": [
                re.compile(r"Mesa"),
                re.compile(r"llvmpipe"),
                re.compile(r"GeForce .+/PCIe/SSE2"),
                re.compile(r"Radeon .+ \(.+, LLVM"),
                re.compile(r"AMD Radeon .+ \(NAVI\d+"),
            ],
        }

        candidates = patterns.get(platform, [])
        if not candidates:
            return self._skip(f"no GPU patterns defined for platform '{platform}'")

        for pat in candidates:
            if pat.search(renderer):
                return RuleResult(
                    self.name, True, self.weight,
                    f"renderer matches {platform} pattern /{pat.pattern}/",
                    self.severity,
                )

        return RuleResult(
            self.name, False, self.weight,
            f"renderer '{renderer[:80]}' doesn't match any {platform} pattern",
            self.severity,
            details={"platform": platform, "renderer": renderer, "vendor": vendor},
        )


# ---------------------------------------------------------------------------
# Rule 6: OS  ↔ font list  (user hot-spot)
# ---------------------------------------------------------------------------


# TODO USER: Fill in required fonts per OS.
# Context: OS-bundled fonts that a real browser on that OS must report.
# Keep the set small (3-5 per OS) — too many creates false negatives when
# the user opts out of default fonts.
#   - "windows": Segoe UI, Calibri, Arial, Tahoma
#   - "macos":   SF Pro Text / Helvetica Neue / Menlo / Monaco
#   - "linux":   DejaVu Sans / Liberation Sans / Ubuntu (at least one)
OS_REQUIRED_FONTS: dict = {
    "windows": {"Segoe UI", "Arial", "Tahoma"},
    "macos":   {"Helvetica Neue", "Menlo", "Monaco"},
    "linux":   {"DejaVu Sans", "Liberation Sans"},
}


class OSFontListRule(Rule):
    name = "os_fonts"
    weight = 0.10
    severity = "warning"

    _PLATFORM_TO_OS = {
        "Win32": "windows",
        "MacIntel": "macos",
        "Linux x86_64": "linux",
        "Linux armv8l": "linux",
        "Linux armv7l": "linux",
        "Linux i686": "linux",
    }

    def evaluate(self, profile: dict) -> RuleResult:
        fonts = profile.get("fonts")
        platform = (profile.get("navigator") or {}).get("platform", "")

        if fonts is None:
            return self._skip("profile.fonts not provided")
        if not OS_REQUIRED_FONTS:
            return self._skip("OS_REQUIRED_FONTS is empty (user must fill in)")

        os_key = self._PLATFORM_TO_OS.get(platform)
        if os_key is None:
            return self._skip(f"platform '{platform}' not mapped to an OS")

        required: Set[str] = OS_REQUIRED_FONTS.get(os_key, set())
        if not required:
            return self._skip(f"no required fonts defined for os '{os_key}'")

        provided = set(fonts)
        missing = required - provided
        if missing:
            return RuleResult(
                self.name, False, self.weight,
                f"{os_key} missing required fonts: {sorted(missing)}",
                self.severity,
                details={"missing": sorted(missing), "os": os_key},
            )

        return RuleResult(
            self.name, True, self.weight,
            f"{os_key} fonts include all required entries",
            self.severity,
        )


# ---------------------------------------------------------------------------
# Rule 7: HTTP/2 pseudo-header order u2194 UA browser family
# ---------------------------------------------------------------------------


class HTTP2PseudoHeaderRule(Rule):
    name = "http2_pseudo_header"
    weight = 0.10
    severity = "error"

    _EXPECTED_ORDER = {
        "chrome": ["method", "authority", "scheme", "path"],
        "firefox": ["method", "path", "authority", "scheme"],
        "safari": ["method", "scheme", "authority", "path"],
    }

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        http2 = profile.get("http2") or {}
        ua = nav.get("userAgent", "")
        order = http2.get("pseudo_header_order") or []

        if not ua or not order:
            return self._skip("navigator.userAgent or http2.pseudo_header_order missing")

        browser = TLSCipherOrderRule._detect_browser(ua)
        if browser is None:
            return self._skip("could not infer browser family from UA")

        expected = self._EXPECTED_ORDER.get(browser)
        if expected is None:
            return self._skip(f"no pseudo-header order defined for '{browser}'")

        if order == expected:
            return RuleResult(
                self.name, True, self.weight,
                f"HTTP/2 pseudo-header order matches {browser}",
                self.severity,
            )
        return RuleResult(
            self.name, False, self.weight,
            f"{browser} HTTP/2 pseudo-header order mismatch: expected {expected}, got {order}",
            self.severity,
            details={"browser": browser, "expected": expected, "actual": order},
        )


# ---------------------------------------------------------------------------
# Rule 8: navigator.language u2194 timezone coherence
# ---------------------------------------------------------------------------


class LocaleTimezoneRule(Rule):
    """Check that navigator.language region aligns with the profile's timezone.

    If the profile has no timezone field, the rule skips gracefully.
    """

    name = "locale_timezone"
    weight = 0.05
    severity = "warning"

    _LANG_REGION_TO_TIMEZONES = {
        "US": {"America/New_York", "America/Chicago", "America/Denver",
               "America/Los_Angeles", "America/Phoenix", "America/Anchorage",
               "Pacific/Honolulu"},
        "GB": {"Europe/London"},
        "CA": {"America/Toronto", "America/Vancouver", "America/Edmonton"},
        "AU": {"Australia/Sydney", "Australia/Melbourne", "Australia/Perth"},
        "FR": {"Europe/Paris"},
        "DE": {"Europe/Berlin"},
        "AT": {"Europe/Vienna"},
        "ES": {"Europe/Madrid"},
        "MX": {"America/Mexico_City"},
        "BR": {"America/Sao_Paulo"},
        "PT": {"Europe/Lisbon"},
        "JP": {"Asia/Tokyo"},
        "CN": {"Asia/Shanghai"},
        "TW": {"Asia/Taipei"},
        "KR": {"Asia/Seoul"},
        "VN": {"Asia/Ho_Chi_Minh"},
        "RU": {"Europe/Moscow"},
    }

    def evaluate(self, profile: dict) -> RuleResult:
        nav = profile.get("navigator") or {}
        lang = nav.get("language", "")
        tz = profile.get("timezone") or profile.get("intl", {}).get("timezone", "")

        if not lang:
            return self._skip("navigator.language missing")
        if not tz:
            return self._skip("profile.timezone missing")

        parts = lang.split("-")
        if len(parts) < 2:
            return self._skip(f"language '{lang}' has no region subtag")

        region = parts[-1].upper()
        expected_tzs = self._LANG_REGION_TO_TIMEZONES.get(region)

        if expected_tzs is None:
            return RuleResult(
                self.name, True, self.weight,
                f"region '{region}' not in known set, skipping tz check",
                self.severity,
                skipped=True,
            )

        if tz in expected_tzs:
            return RuleResult(
                self.name, True, self.weight,
                f"timezone '{tz}' consistent with language region '{region}'",
                self.severity,
            )

        return RuleResult(
            self.name, False, self.weight,
            f"timezone '{tz}' inconsistent with language region '{region}' "
            f"(expected one of {sorted(expected_tzs)})",
            self.severity,
            details={"timezone": tz, "region": region, "expected": sorted(expected_tzs)},
        )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ConsistencyEngine:
    def __init__(self, rules: List[Rule], registry=None):
        self.rules = rules
        self.registry = registry

    def evaluate(self, profile: dict) -> ConsistencyReport:
        results: List[RuleResult] = []
        for rule in self.rules:
            try:
                results.append(rule.evaluate(profile))
            except NotImplementedError as e:
                results.append(RuleResult(
                    rule_name=rule.name,
                    passed=True,
                    weight=rule.weight,
                    message=f"not implemented yet: {e}",
                    severity=rule.severity,
                    skipped=True,
                ))

        active = [r for r in results if not r.skipped]
        total_weight = sum(r.weight for r in active)
        if total_weight > 0:
            score = sum(r.weight for r in active if r.passed) / total_weight
        else:
            score = 1.0

        passed = all(r.passed or r.skipped or r.severity != "error" for r in results)

        collisions: List[str] = []
        if self.registry is not None:
            collisions = self.registry.find_collisions_for_profile(profile)

        return ConsistencyReport(
            score=score,
            passed=passed and not collisions,
            rule_results=results,
            collisions=collisions,
        )


def default_rules() -> List[Rule]:
    return [
        PlatformUARule(),
        LanguageLocaleRule(),
        ScreenDPRViewportRule(),
        TLSCipherOrderRule(),
        GPUWebGLRule(),
        OSFontListRule(),
        HTTP2PseudoHeaderRule(),
        LocaleTimezoneRule(),
    ]
