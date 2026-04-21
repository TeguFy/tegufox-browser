#!/usr/bin/env python3
"""
Tegufox Automation Framework v1.0

Production-grade automation framework for Tegufox with anti-detection capabilities.
Integrates DNS leak prevention, HTTP/2 fingerprinting, canvas noise, WebGL spoofing,
and human-like mouse movements for undetectable e-commerce automation.

Key Features:
- TegufoxSession: High-level wrapper around Playwright with anti-detection
- ProfileRotator: Multi-account session management with automatic rotation
- SessionManager: Persistent session state across browser restarts
- Human-like behavior: Mouse movements, typing, scrolling, delays
- DNS leak prevention: DoH/DoT integration from configure-dns.py
- Fingerprint consistency: Automatic profile validation (TLS+HTTP/2+UA+DoH)

Usage:
    from tegufox_automation import TegufoxSession, ProfileRotator

    # Basic usage
    with TegufoxSession(profile="chrome-120") as session:
        session.goto("https://amazon.com")
        session.human_click("#nav-search-submit-button")
        session.human_type("#twotabsearchtextbox", "laptop")
        session.screenshot("amazon-search.png")

    # Multi-account rotation
    rotator = ProfileRotator([
        "amazon-seller-1",
        "amazon-seller-2",
        "amazon-seller-3"
    ])

    for session in rotator:
        session.goto("https://sellercentral.amazon.com")
        session.check_inventory()

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 3 Day 13
License: MIT
"""

import json
import random
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import sys
from urllib.parse import urlparse

# Import Camoufox (Python package for Firefox automation)
try:
    from camoufox.sync_api import Camoufox, Browser, BrowserContext
    from camoufox.fingerprints import generate_context_fingerprint
except ImportError as e:
    print(f"ERROR: Camoufox not installed. Run: pip install camoufox")
    print(f"Import error details: {e}")
    if __name__ != "__main__":
        Camoufox = None
        Browser = None
        BrowserContext = None
    else:
        sys.exit(1)

# Import Playwright Page type
try:
    from playwright.sync_api import Page
except ImportError:
    Page = None

# Import Tegufox mouse movement library
try:
    from .mouse import HumanMouse, MouseConfig
except ImportError as e:
    print(f"ERROR: tegufox_automation.mouse not found.")
    print(f"Import error details: {e}")
    # Don't exit if running in test mode
    if __name__ != "__main__":
        HumanMouse = None
        MouseConfig = None
    else:
        sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("tegufox_automation")


@dataclass
class SessionConfig:
    """Configuration for TegufoxSession"""

    # Profile settings
    profile_path: Optional[str] = None
    profile_json: Optional[Dict] = None

    # Browser settings
    headless: bool = False
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    user_agent: Optional[str] = None

    # Anti-detection settings
    enable_dns_leak_prevention: bool = True
    enable_human_mouse: bool = True
    enable_random_delays: bool = True
    enable_idle_jitter: bool = True

    # Timing settings (milliseconds)
    action_delay_min: int = 100
    action_delay_max: int = 500
    page_load_timeout: int = 30000
    navigation_timeout: int = 30000

    # Mouse settings
    mouse_config: MouseConfig = field(default_factory=MouseConfig)

    # Session persistence
    session_dir: Optional[Path] = None
    save_session_state: bool = True

    # Screenshot settings
    screenshot_on_error: bool = True
    screenshot_dir: Optional[Path] = None

    # Custom browser binary (overrides official camoufox)
    browser_binary: Optional[str] = None


@dataclass
class SessionState:
    """Persistent session state"""

    profile_name: str
    session_id: str
    created_at: float
    last_active: float
    cookies: List[Dict] = field(default_factory=list)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    session_storage: Dict[str, Any] = field(default_factory=dict)
    visited_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "profile_name": self.profile_name,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "visited_urls": self.visited_urls,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionState":
        return cls(**data)


class TegufoxSession:
    """
    High-level automation session with anti-detection capabilities.

    Wraps Tegufox/Playwright with:
    - DNS leak prevention (DoH/DoT)
    - HTTP/2 fingerprint consistency
    - Human-like mouse movements
    - Random delays and jitter
    - Session persistence
    - Automatic profile validation

    Example:
        with TegufoxSession(profile="chrome-120") as session:
            session.goto("https://amazon.com")
            session.human_click("#buy-button")
            session.human_type("#search", "laptop")
            session.wait_random(1, 3)
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        profile_path: Optional[str] = None,
        config: Optional[SessionConfig] = None,
        **kwargs,
    ):
        """
        Initialize TegufoxSession

        Args:
            profile: Profile name (e.g., "chrome-120", "firefox-115")
            profile_path: Path to profile JSON file
            config: SessionConfig object
            **kwargs: Additional config parameters (passed to SessionConfig)
        """
        self.config = config or SessionConfig(**kwargs)

        # Load profile
        if profile:
            self.profile_path = Path(f"profiles/{profile}.json")
        elif profile_path:
            self.profile_path = Path(profile_path)
        else:
            # Default to chrome-120 profile
            self.profile_path = Path("profiles/chrome-120.json")

        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {self.profile_path}")

        # Load profile JSON
        with open(self.profile_path, "r") as f:
            self.profile = json.load(f)

        logger.info(f"Loaded profile: {self.profile.get('name', 'unknown')}")

        # Browser components
        self._camoufox: Optional[Camoufox] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.mouse: Optional[HumanMouse] = None

        # Session state
        self.session_state = SessionState(
            profile_name=self.profile.get("name", "unknown"),
            session_id=self._generate_session_id(),
            created_at=time.time(),
            last_active=time.time(),
        )

        # DNS configuration tracking
        self.dns_configured = False

        # Fingerprint registry (anti-correlation)
        self._fingerprint_registry = None
        try:
            from tegufox_core.fingerprint_registry import FingerprintRegistry
            self._fingerprint_registry = FingerprintRegistry()
        except Exception:
            pass

    def __enter__(self) -> "TegufoxSession":
        """Context manager entry - launch browser"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser"""
        if exc_type and self.config.screenshot_on_error:
            self._save_error_screenshot(exc_val)
        self.stop()
        return False

    def start(self):
        """Start browser session with anti-detection configuration"""
        logger.info("Starting Tegufox session...")

        # Apply DNS leak prevention
        if self.config.enable_dns_leak_prevention:
            self._configure_dns()

        # All profiles launch via Tegufox (Firefox engine)
        self._start_tegufox()

    def _start_tegufox(self):
        """Launch Firefox via Tegufox for all UA profiles."""
        # Build launch options (passed to Tegufox at browser start)
        launch_opts = self._build_launch_options()

        # Launch browser via camoufox Python package
        # TEGUFOX_BINARY env var or config lets you use a custom-built binary
        import os as _os
        _custom_bin = self.config.browser_binary or _os.environ.get('TEGUFOX_BINARY') or _os.environ.get('CAMOUFOX_BINARY')
        if not _custom_bin:
            # Auto-detect locally built Tegufox binary
            _project_root = Path(__file__).resolve().parent.parent  # Go up to project root
            _candidates = [
                # Priority 1: ./build/ directory (new location)
                _project_root / "build" / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
                _project_root / "build" / "Camoufox.app" / "Contents" / "MacOS" / "camoufox",
                # Priority 2: Old location (fallback)
                _project_root / "camoufox-source" / "camoufox-146.0.1-beta.25" / "obj-aarch64-apple-darwin" / "dist" / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
                _project_root / "Tegufox.app" / "Contents" / "MacOS" / "tegufox",
            ]
            for _cand in _candidates:
                if _cand.exists():
                    _custom_bin = str(_cand)
                    logger.info("Auto-detected Tegufox binary: %s", _custom_bin)
                    break
        if _custom_bin:
            launch_opts['executable_path'] = _custom_bin
        self._camoufox = Camoufox(headless=self.config.headless, i_know_what_im_doing=True, **launch_opts)
        self.browser = self._camoufox.__enter__()

        # Create context with Playwright-level options (viewport, UA)
        context_options = self._build_context_options()
        self.context = self.browser.new_context(**context_options)

        # Inject per-context JS fingerprint init script (sets UA, WebGL, platform, etc.)
        self._inject_context_fingerprint()

        # Create page
        self.page = self.context.new_page()

        # Set page timeout
        self.page.set_default_timeout(self.config.page_load_timeout)

        # Initialize human mouse
        if self.config.enable_human_mouse:
            self.mouse = HumanMouse(self.page, config=self.config.mouse_config)
            logger.info("Human mouse initialized")

        # Initialize human keyboard
        try:
            from .keyboard import HumanKeyboard
            self._keyboard = HumanKeyboard(self.page)
            logger.info("Human keyboard initialized")
        except ImportError:
            self._keyboard = None

        # Validate fingerprint consistency
        self._validate_fingerprints()

        logger.info("Tegufox session started successfully")

    def stop(self):
        """Stop browser session and save state"""
        logger.info("Stopping Tegufox session...")

        # Save session state
        if self.config.save_session_state and self.page:
            self._save_session_state()

        # Close fingerprint registry
        if self._fingerprint_registry:
            try:
                self._fingerprint_registry.close()
            except Exception:
                pass
            self._fingerprint_registry = None

        # Close context and browser, then exit Tegufox playwright context
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None

        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None

        if self._camoufox:
            try:
                self._camoufox.__exit__(None, None, None)
            except Exception:
                pass
            self._camoufox = None

        self.page = None
        logger.info("Tegufox session stopped")

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """
        Navigate to URL with random delay

        Args:
            url: Target URL
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
        """
        if not self.page:
            raise RuntimeError(
                "Session not started. Call start() or use context manager."
            )

        logger.info(f"Navigating to: {url}")

        # Random pre-navigation delay
        if self.config.enable_random_delays:
            self.wait_random(0.5, 1.5)

        # Navigate
        self.page.goto(url, wait_until=wait_until)

        # Track visited URL
        self.session_state.visited_urls.append(url)
        self.session_state.last_active = time.time()

        # Record fingerprint hashes for anti-correlation
        if self._fingerprint_registry:
            try:
                fp = self.profile.get("fingerprints") or {}
                domain = urlparse(url).hostname
                self._fingerprint_registry.record(
                    profile_name=self.profile.get("name", "unknown"),
                    domain=domain,
                    hash_canvas=fp.get("canvas"),
                    hash_webgl=fp.get("webgl"),
                    hash_tls_ja3=fp.get("ja3"),
                )
            except Exception:
                pass

        # Random post-navigation delay (simulating page reading)
        if self.config.enable_random_delays:
            self.wait_random(1, 3)

    def human_click(self, selector: str, **kwargs) -> None:
        """
        Click element with human-like mouse movement

        Args:
            selector: CSS selector or XPath
            **kwargs: Additional click options
        """
        if not self.page:
            raise RuntimeError("Session not started")

        logger.debug(f"Human click: {selector}")

        # Pre-click delay
        if self.config.enable_random_delays:
            self.wait_random(0.2, 0.8)

        # Use human mouse if enabled
        if self.mouse:
            self.mouse.click(selector, **kwargs)
        else:
            # Fallback to standard click
            self.page.click(selector, **kwargs)

        # Post-click delay
        if self.config.enable_random_delays:
            self.wait_random(0.3, 0.9)

        self.session_state.last_active = time.time()

    def human_type(
        self,
        selector: str,
        text: str,
        wpm: float = None,
        typo_rate: float = None,
        **kwargs,
    ) -> None:
        """
        Type text with human-like timing using HumanKeyboard.

        Uses log-normal inter-key intervals, per-bigram speed model,
        typo injection with adjacent-key correction, and WPM envelope
        with warmup/fatigue.

        Args:
            selector: CSS selector for input field
            text: Text to type
            wpm: Words per minute (default: random 40-80)
            typo_rate: Typo probability per char (default: 0.03)
            **kwargs: Additional options
        """
        if not self.page:
            raise RuntimeError("Session not started")

        logger.debug(f"Human type: {selector} = '{text[:20]}...'")

        if self._keyboard:
            self._keyboard.type_text(text, selector=selector, wpm=wpm, typo_rate=typo_rate)
        else:
            # Fallback: simple per-char typing
            self.page.click(selector)
            for char in text:
                self.page.keyboard.type(char)
                time.sleep(random.randint(50, 150) / 1000.0)

        self.session_state.last_active = time.time()

    def human_scroll(self, distance: int = 500, direction: str = "down", platform: str = "windows") -> None:
        """
        Scroll page with ease-out-cubic physics.

        Args:
            distance: Scroll distance in pixels
            direction: "down", "up", "left", "right"
            platform: "windows" | "macos" | "linux" (affects step size)
        """
        if not self.page:
            raise RuntimeError("Session not started")

        logger.debug(f"Human scroll: {direction} {distance}px ({platform})")

        if self.mouse:
            delta = distance if direction == "down" else -distance
            self.mouse.scroll(delta, platform=platform)
        else:
            if direction in ("down", "up"):
                delta_y = distance if direction == "down" else -distance
                self.page.mouse.wheel(0, delta_y)
            else:
                delta_x = distance if direction == "right" else -distance
                self.page.mouse.wheel(delta_x, 0)

        # Post-scroll delay (reading content)
        if self.config.enable_random_delays:
            self.wait_random(0.5, 2.0)

        self.session_state.last_active = time.time()

    def wait_random(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        Wait for random duration (anti-detection)

        Args:
            min_seconds: Minimum wait time
            max_seconds: Maximum wait time
        """
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Random wait: {delay:.2f}s")
        time.sleep(delay)

    def wait_for_selector(
        self, selector: str, timeout: Optional[int] = None, state: str = "visible"
    ) -> None:
        """
        Wait for element to appear

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds (default: page timeout)
            state: Element state ('attached', 'detached', 'visible', 'hidden')
        """
        if not self.page:
            raise RuntimeError("Session not started")

        self.page.wait_for_selector(selector, timeout=timeout, state=state)
        self.session_state.last_active = time.time()

    def screenshot(self, path: str, full_page: bool = False) -> None:
        """
        Take screenshot

        Args:
            path: Output file path
            full_page: Capture full scrollable page
        """
        if not self.page:
            raise RuntimeError("Session not started")

        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.screenshot(path=str(screenshot_path), full_page=full_page)
        logger.info(f"Screenshot saved: {screenshot_path}")

    def evaluate(self, script: str) -> Any:
        """
        Execute JavaScript in page context

        Args:
            script: JavaScript code to execute

        Returns:
            Result of script execution
        """
        if not self.page:
            raise RuntimeError("Session not started")

        return self.page.evaluate(script)

    def get_cookies(self) -> List[Dict]:
        """Get all cookies from current context"""
        if not self.context:
            raise RuntimeError("Session not started")

        return self.context.cookies()

    def set_cookies(self, cookies: List[Dict]) -> None:
        """Set cookies in current context"""
        if not self.context:
            raise RuntimeError("Session not started")

        self.context.add_cookies(cookies)

    def validate_dns_leak(self) -> Dict[str, Any]:
        """
        Validate DNS leak prevention is working

        Returns:
            Dict with validation results (is_leaking, dns_servers, etc.)
        """
        if not self.page:
            raise RuntimeError("Session not started")

        logger.info("Validating DNS leak prevention...")

        # Navigate to DNS leak test site
        self.page.goto("https://www.dnsleaktest.com", wait_until="networkidle")

        # Wait for results
        time.sleep(3)

        # Extract DNS servers
        dns_servers = self.page.evaluate("""
            () => {
                const rows = document.querySelectorAll('table.table tr');
                const servers = [];
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        servers.push({
                            ip: cells[0].innerText.trim(),
                            hostname: cells[1].innerText.trim()
                        });
                    }
                });
                return servers;
            }
        """)

        # Check if using DoH provider
        doh_provider = self.profile.get("dns_config", {}).get("provider", "unknown")
        expected_provider = {
            "cloudflare": "cloudflare",
            "quad9": "quad9",
            "mullvad": "mullvad",
            "google": "google",
        }.get(doh_provider, doh_provider)

        # Simple leak detection: check if any server hostname contains ISP keywords
        isp_keywords = ["comcast", "verizon", "att", "spectrum", "cox", "charter"]
        is_leaking = any(
            any(
                keyword in server.get("hostname", "").lower()
                for keyword in isp_keywords
            )
            for server in dns_servers
        )

        result = {
            "is_leaking": is_leaking,
            "dns_servers": dns_servers,
            "expected_provider": expected_provider,
            "status": "PASS" if not is_leaking else "FAIL",
        }

        logger.info(f"DNS leak test: {result['status']}")
        return result

    def validate_http2_fingerprint(self) -> Dict[str, Any]:
        """
        Validate HTTP/2 fingerprint consistency

        Returns:
            Dict with fingerprint validation results
        """
        if not self.page:
            raise RuntimeError("Session not started")

        logger.info("Validating HTTP/2 fingerprint...")

        # Navigate to TLS fingerprint test site
        self.page.goto("https://tls.browserleaks.com/json", wait_until="networkidle")

        # Extract fingerprint data
        fingerprint_json = self.page.evaluate("() => document.body.innerText")

        try:
            fingerprint_data = json.loads(fingerprint_json)

            result = {
                "ja3_hash": fingerprint_data.get("ja3_hash", "unknown"),
                "user_agent": fingerprint_data.get("user_agent", "unknown"),
                "expected_ja3": self.profile.get("fingerprints", {}).get(
                    "ja3", "unknown"
                ),
                "expected_ua": self.profile.get("navigator", {}).get(
                    "userAgent", "unknown"
                ),
                "status": "UNKNOWN",
            }

            # Validate JA3 match
            if result["ja3_hash"] == result["expected_ja3"]:
                result["status"] = "PASS"
            else:
                result["status"] = "FAIL"
                logger.warning(
                    f"JA3 mismatch: {result['ja3_hash']} != {result['expected_ja3']}"
                )

            logger.info(f"HTTP/2 fingerprint test: {result['status']}")
            return result

        except json.JSONDecodeError:
            logger.error("Failed to parse fingerprint data")
            return {"status": "ERROR", "message": "Failed to parse fingerprint data"}

    # Private methods

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import hashlib

        data = f"{self.profile.get('name', 'unknown')}-{time.time()}-{random.random()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _configure_dns(self) -> None:
        """Apply DNS leak prevention from profile"""
        dns_config = self.profile.get("dns_config", {})

        if not dns_config.get("enabled", False):
            logger.warning("DNS leak prevention disabled in profile")
            return

        firefox_prefs = self.profile.get("firefox_preferences", {})

        if not firefox_prefs:
            logger.warning("No Firefox preferences found in profile")
            return

        logger.info(
            f"DNS configured: {dns_config.get('provider', 'unknown')} (DoH mode {firefox_prefs.get('network.trr.mode', 0)})"
        )
        self.dns_configured = True

    def _build_launch_options(self) -> Dict[str, Any]:
        """Build Tegufox launch options (applied at browser start via Firefox prefs)"""
        opts: Dict[str, Any] = {}

        # ── Tegufox config dict (dot-notation property overrides) ────────────
        # Support both old-format profiles ("config" key, dot-notation)
        # and new-format profiles ("navigator" / "screen" nested sections).
        camoufox_config: Dict[str, Any] = {}

        if "config" in self.profile:
            # Old PLATFORM_TEMPLATES format — already dot-notation, use directly
            camoufox_config.update(self.profile["config"])

        if "navigator" in self.profile:
            nav = self.profile["navigator"]
            _map = {
                "userAgent":          "navigator.userAgent",
                "platform":           "navigator.platform",
                "hardwareConcurrency":"navigator.hardwareConcurrency",
                "language":           "navigator.language",
                "languages":          "navigator.languages",
            }
            for src_key, dst_key in _map.items():
                if src_key in nav:
                    camoufox_config[dst_key] = nav[src_key]

        if "screen" in self.profile:
            scr = self.profile["screen"]
            for src_key, dst_key in (
                ("width",            "screen.width"),
                ("height",           "screen.height"),
                ("colorDepth",       "screen.colorDepth"),
                ("devicePixelRatio", "screen.devicePixelRatio"),
            ):
                if src_key in scr:
                    camoufox_config[dst_key] = scr[src_key]

        # ── Core browser-type overrides (C++ level via CAMOU_CONFIG) ──────────
        ua = self.profile.get('navigator', {}).get('userAgent', '')
        is_chrome_ua  = 'Chrome/' in ua and 'Edg' not in ua and 'OPR' not in ua
        is_safari_ua  = 'Safari/' in ua and 'Chrome' not in ua
        is_firefox_ua = 'Firefox/' in ua

        wgl = self.profile.get('webgl', {})
        webgl_vendor   = wgl.get('vendor', wgl.get('unmaskedVendor', ''))
        webgl_renderer = wgl.get('renderer', wgl.get('unmaskedRenderer', ''))

        # navigator.oscpu: Chrome/Safari must return undefined (not Firefox's OS string)
        # Set it blank so C++ returns empty → JS patch will override to undefined.
        # Firefox: set the correct OS string so it matches spoofed UA.
        raw_os = self.profile.get('os', '').lower()
        if is_firefox_ua and raw_os:
            if 'win' in raw_os:
                nav_arch = ua
                if 'Win64' in nav_arch or 'WOW64' in nav_arch:
                    camoufox_config['navigator.oscpu'] = 'Windows NT 10.0; Win64; x64'
                else:
                    camoufox_config['navigator.oscpu'] = 'Windows NT 10.0'
            elif 'mac' in raw_os:
                import re as _re
                m = _re.search(r'OS X (\d+[_.\d]+)', ua)
                ver = m.group(1).replace('_', '.') if m else '10.15'
                camoufox_config['navigator.oscpu'] = f'Intel Mac OS X {ver}'
            elif 'lin' in raw_os:
                camoufox_config['navigator.oscpu'] = 'Linux x86_64'

        # AudioContext: sampleRate and outputLatency are hardware-dependent.
        # Overriding them creates detectable inconsistencies; leave at system defaults.

        # audio:seed intentionally NOT set — the C++ LCG transform (0.8% variance per-sample)
        # produces detectable non-standard fingerprints. Use real Firefox audio output instead.

        # WebGL: set VENDOR/RENDERER at C++ level (more reliable than JS prototype)
        # Also set UNMASKED params dict so getParameter(37445/37446) is correct at C++ level
        # webGl:vendor/renderer cause BrowserForge DB validation → skip them.
        # webGl:parameters dict bypasses that and sets values at C++ getParameter level.
        gl_params: Dict[str, Any] = {}
        if is_safari_ua:
            # Real Safari never exposes unmasked WebGL vendor/renderer (37445/37446).
            # Both return empty string by default — only accessible via WEBGL_debug_renderer_info
            # extension which Safari does not enable. Exposing a real GPU string here is the
            # primary trigger for "fake videocard" detection on sites like browserscan.
            gl_params['37445'] = ''   # UNMASKED_VENDOR_WEBGL  → empty (Safari behaviour)
            gl_params['37446'] = ''   # UNMASKED_RENDERER_WEBGL → empty (Safari behaviour)
            gl_params.update({'7936': 'WebKit', '7937': 'WebKit WebGL'})
        elif is_chrome_ua:
            if webgl_vendor or webgl_renderer:
                gl_params['37445'] = webgl_vendor
                gl_params['37446'] = webgl_renderer
            gl_params.update({'7936': 'WebKit', '7937': 'WebKit WebGL'})
        elif is_firefox_ua:
            if webgl_vendor or webgl_renderer:
                gl_params['37445'] = webgl_vendor
                gl_params['37446'] = webgl_renderer
            # Firefox always returns 'Mozilla' for basic VENDOR/RENDERER
            gl_params.update({'7936': 'Mozilla', '7937': 'Mozilla'})
        if gl_params:
            camoufox_config['webGl:parameters'] = gl_params

        # navigator.buildID: Firefox-only property (Chrome/Safari return undefined).
        # Set via C++ CAMOU_CONFIG because JS defineProperty may fail on non-configurable props.
        if is_chrome_ua or is_safari_ua:
            camoufox_config['navigator.buildID'] = ''  # empty string → not the Firefox value

        # WebRTC: Tegufox sets media.peerconnection.ice.no_host=true globally, which blocks
        # all host ICE candidates (hides local IP). Real Chrome/Firefox expose host candidates
        # (private LAN IP only). We override this via firefox_user_prefs below.

        # BrowserForge sets headers.Accept-Encoding = 'gzip, deflate, br, zstd' which causes
        # MaskConfig to override Firefox's Accept-Encoding. Our custom Tegufox build lacks
        # working Brotli decompression, so we force gzip-only here.
        camoufox_config['headers.Accept-Encoding'] = 'gzip, deflate'

        if camoufox_config:
            opts["config"] = camoufox_config

        # ── OS spoof ─────────────────────────────────────────────────────────
        # Priority: explicit "os" field stored by generate_template > platform string.
        # Using the stored os field means linux profiles won't get Win32 platform
        # from a base template file that happens to say Win32.
        os_str = None
        if "os" in self.profile:
            raw = self.profile["os"].lower()
            if "win" in raw:   os_str = "windows"
            elif "mac" in raw: os_str = "macos"
            elif "lin" in raw: os_str = "linux"

        if not os_str:
            platform = camoufox_config.get("navigator.platform", "")
            os_map = {
                "MacIntel": "macos", "MacPPC": "macos",
                "Linux x86_64": "linux", "Linux": "linux",
                "Win32": "windows", "Win64": "windows",
            }
            for plat_key, os_val in os_map.items():
                if plat_key.lower() in platform.lower():
                    os_str = os_val
                    break

        # For Linux: omit os= so BrowserForge can pick freely within the host
        # monitor constraints (Tegufox detects monitor size when headless=True).
        # config= already sets navigator.userAgent / platform, so the spoofed
        # OS is still applied correctly via both CAMOU_CONFIG and JS init script.
        if os_str and os_str != "linux":
            opts["os"] = os_str

        # ── Window size ───────────────────────────────────────────────────────
        # Skip window= for Linux (same BrowserForge constraint issue).
        if os_str != "linux":
            scr_section = self.profile.get("screen", {})
            w = scr_section.get("width") or camoufox_config.get("screen.width")
            h = scr_section.get("height") or camoufox_config.get("screen.height")
            if w and h:
                opts["window"] = (int(w), int(h))

        # ── Firefox preferences (DoH, WebRTC, IPv6) ───────────────────────────
        # Base: realistic WebRTC — enable host candidates (exposes LAN IP, but that's
        # expected behavior for Chrome/Firefox) and disable mDNS obfuscation so the
        # host candidate shows a real private IP (like Windows Chrome behavior).
        _rtc_prefs: Dict[str, Any] = {}
        _rtc_prefs.update(self.profile.get('firefox_preferences', {}))
        # Force WebRTC enabled — profile may set enabled=False, our override wins
        _rtc_prefs['media.peerconnection.enabled'] = True
        _rtc_prefs['media.peerconnection.ice.no_host'] = False
        _rtc_prefs['media.peerconnection.ice.obfuscate_host_addresses'] = False
        # Disable navigator.webdriver flag — Firefox sets this to true when automated
        _rtc_prefs['dom.webdriver.enabled'] = False
        opts['firefox_user_prefs'] = _rtc_prefs

        return opts

    def _build_context_options(self) -> Dict[str, Any]:
        """Build Playwright context options (viewport, UA — applied per context)"""
        options: Dict[str, Any] = {}

        # Viewport
        if self.config.viewport_width and self.config.viewport_height:
            options["viewport"] = {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }
        elif "screen" in self.profile:
            screen = self.profile["screen"]
            options["viewport"] = {
                "width": screen.get("width", 1920),
                "height": screen.get("height", 1080),
            }

        # User agent
        if self.config.user_agent:
            options["user_agent"] = self.config.user_agent
        elif "navigator" in self.profile:
            options["user_agent"] = self.profile["navigator"].get("userAgent", "")

        # Sec-CH-UA headers for Chrome profiles — Firefox doesn't send these natively,
        # but browserscan checks for consistency between JS userAgentData and HTTP headers.
        ua = options.get("user_agent", "")
        if 'Chrome/' in ua and 'Edg' not in ua and 'OPR' not in ua:
            import re as _re
            chrome_ver = '120'
            _m = _re.search(r'Chrome/(\d+)', ua)
            if _m:
                chrome_ver = _m.group(1)
            platform_str = 'Windows'
            if 'Mac' in ua:
                platform_str = 'macOS'
            elif 'Linux' in ua:
                platform_str = 'Linux'
            is_mobile = 'Mobile' in ua
            options["extra_http_headers"] = {
                "Sec-CH-UA": f'"Not/A)Brand";v="8", "Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}"',
                "Sec-CH-UA-Mobile": "?1" if is_mobile else "?0",
                "Sec-CH-UA-Platform": f'"{platform_str}"',
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
            }

        return options

    def _inject_context_fingerprint(self) -> None:
        """Inject per-context JS init script to spoof UA, WebGL, platform + browser-specific DOM."""
        ua  = self.profile.get('navigator', {}).get('userAgent', '')
        wgl = self.profile.get('webgl', {})
        _nav = self.profile.get('navigator', {})

        is_chrome  = 'Chrome/' in ua and 'Edg' not in ua and 'OPR' not in ua
        is_safari  = 'Safari/' in ua and 'Chrome' not in ua
        is_firefox = 'Firefox/' in ua

        os_str = None
        raw_os = self.profile.get('os', '')
        if raw_os:
            r = raw_os.lower()
            if 'win' in r:   os_str = 'windows'
            elif 'mac' in r: os_str = 'macos'
            elif 'lin' in r: os_str = 'linux'

        # Tegufox (Firefox) backend — inject BrowserForge fingerprint
        preset = {
            'navigator': self.profile.get('navigator', {}),
            'screen': self.profile.get('screen', {}),
            'webgl': {
                'unmaskedVendor':   wgl.get('vendor',   wgl.get('unmaskedVendor', '')),
                'unmaskedRenderer': wgl.get('renderer', wgl.get('unmaskedRenderer', '')),
            },
        }
        try:
            ctx_fp = generate_context_fingerprint(preset=preset, os=os_str)
            if ctx_fp.get('init_script'):
                self.context.add_init_script(ctx_fp['init_script'])
        except Exception as exc:
            logger.warning("Failed to inject context fingerprint: %s", exc)

        # Build oscpu string for Firefox (Chrome/Safari don't expose this)
        oscpu_str = ''
        if is_firefox and os_str:
            arch = ua
            if 'Win64' in arch or 'WOW64' in arch:
                if os_str == 'windows':
                    oscpu_str = 'Windows NT 10.0; Win64; x64'
            elif os_str == 'macos':
                import re as _re
                m = _re.search(r'OS X (\d+[_.]\d+)', ua)
                ver = m.group(1).replace('_', '.') if m else '10.15'
                oscpu_str = f'Intel Mac OS X {ver}'
            elif os_str == 'linux':
                oscpu_str = 'Linux x86_64'

        # Tegufox (Firefox engine) handles audio/canvas noise at C++ level via MaskConfig.
        # Seeds from profile control the noise injection.
        _canvas_seed = self.profile.get('canvas', {}).get('noise', {}).get('seed', 0)

        self.context.add_init_script(self._build_browser_compat_script(
            is_chrome=is_chrome, is_safari=is_safari, is_firefox=is_firefox,
            ua=ua,
            webgl_vendor=wgl.get('vendor', wgl.get('unmaskedVendor', '')),
            webgl_renderer=wgl.get('renderer', wgl.get('unmaskedRenderer', '')),
            oscpu_str=oscpu_str,
            device_memory=_nav.get('deviceMemory'),
            hardware_concurrency=_nav.get('hardwareConcurrency'),
            canvas_seed=_canvas_seed,
        ))
        # Extra fingerprint surfaces from x-acc-management: timezone, userAgentData.getHighEntropyValues,
        # clientRects noise, speech voices, battery, font detection, iframe cross-frame protection.
        self.context.add_init_script(self._build_extra_fingerprint_script(
            profile=self.profile, is_chrome=is_chrome, is_firefox=is_firefox, ua=ua
        ))
        logger.info("Fingerprint injected: %s (is_chrome=%s, is_firefox=%s, is_safari=%s)", ua[:65], is_chrome, is_firefox, is_safari)

        # Audio: x-acc-management stealth approach (NO Proxy, real Float32Array).
        # Firefox/Safari profiles: audioMode='real' → pass through native Firefox audio (passes fv.pro).
        # Chrome profiles are DEPRECATED (moved to profiles/deprecated-chrome/).
        # Reason: Firefox engine cannot produce Chrome-matching audio/canvas fingerprints.
        fp_data = self.profile.get('fingerprint', {})
        _audio_seed = int(fp_data.get('audio_seed', fp_data.get('canvas_seed', 1234567))) & 0xFFFFFFFF
        _audio_mode = self.profile.get('audioMode', 'real')  # Always 'real' for Firefox/Safari
        _audio_noise = self.profile.get('audioNoise', 0.00001)
        _audio_sparse = self.profile.get('audioSparseRate', 10)
        if _audio_mode != 'off':
            self.context.add_init_script(
                self._build_audio_stealth_script(_audio_mode, _audio_noise, _audio_seed, _audio_sparse)
            )
            logger.info(f"Audio stealth script injected (mode={_audio_mode})")


    @staticmethod
    def _build_extra_fingerprint_script(profile: dict, is_chrome: bool, is_firefox: bool, ua: str) -> str:
        """Extra fingerprint JS ported from x-acc-management: timezone, userAgentData.getHighEntropyValues,
        clientRects noise, speech voices, battery, font detection, iframe cross-frame protection."""
        import json as _j, re as _re

        os_type = profile.get('os', 'windows').lower()
        nav = profile.get('navigator', {})
        fp_data = profile.get('fingerprint', {})

        cr_seed = int(fp_data.get('canvas_seed', fp_data.get('audio_seed', 12345678))) & 0xFFFFFFFF
        audio_seed_int = int(fp_data.get('audio_seed', fp_data.get('canvas_seed', 1234567))) & 0xFFFFFFFF
        is_mobile = os_type in ('android', 'ios')

        timezone = profile.get('timezone', '')
        tz_offset = profile.get('timezoneOffset', None)

        chrome_ver = 120
        chrome_full_ver = '120.0.6099.130'
        if is_chrome:
            m = _re.search(r'Chrome/(\d+)\.(\d+)\.(\d+)\.(\d+)', ua)
            if m:
                chrome_ver = int(m.group(1))
                chrome_full_ver = f'{m.group(1)}.{m.group(2)}.{m.group(3)}.{m.group(4)}'
            else:
                m2 = _re.search(r'Chrome/(\d+)', ua)
                if m2: chrome_ver = int(m2.group(1))

        ua_platform_map = {'macos': 'macOS', 'windows': 'Windows', 'linux': 'Linux',
                           'android': 'Android', 'ios': 'iOS'}
        ua_platform = ua_platform_map.get(os_type, 'Windows')
        os_ver = profile.get('osVersion', '')
        if os_type == 'windows':
            platform_ver = '10.0.0' if os_ver in ('10', '') else '15.0.0'
        elif os_type == 'macos':
            platform_ver = os_ver if '.' in str(os_ver) else (str(os_ver) + '.0.0' if os_ver else '15.0.0')
        else:
            platform_ver = str(os_ver) if os_ver else '0.0.0'

        platform_str = nav.get('platform', 'Win32')
        ua_arch = 'arm' if 'arm' in platform_str.lower() else 'x86'

        speech_voices_map = {
            'macos': [
                {'name': 'Alex', 'lang': 'en-US', 'localService': True, 'default': True, 'voiceURI': 'Alex'},
                {'name': 'Samantha', 'lang': 'en-US', 'localService': True, 'default': False, 'voiceURI': 'Samantha'},
                {'name': 'Victoria', 'lang': 'en-US', 'localService': True, 'default': False, 'voiceURI': 'Victoria'},
                {'name': 'Daniel', 'lang': 'en-GB', 'localService': True, 'default': False, 'voiceURI': 'Daniel'},
            ],
            'windows': [
                {'name': 'Microsoft David - English (United States)', 'lang': 'en-US', 'localService': True, 'default': True,
                 'voiceURI': 'Microsoft David - English (United States)'},
                {'name': 'Microsoft Zira - English (United States)', 'lang': 'en-US', 'localService': True, 'default': False,
                 'voiceURI': 'Microsoft Zira - English (United States)'},
                {'name': 'Microsoft Mark - English (United States)', 'lang': 'en-US', 'localService': True, 'default': False,
                 'voiceURI': 'Microsoft Mark - English (United States)'},
            ],
            'linux': [
                {'name': 'Google US English', 'lang': 'en-US', 'localService': False, 'default': True,
                 'voiceURI': 'Google US English'},
                {'name': 'Google UK English Female', 'lang': 'en-GB', 'localService': False, 'default': False,
                 'voiceURI': 'Google UK English Female'},
            ],
            'android': [
                {'name': 'Google US English', 'lang': 'en-US', 'localService': False, 'default': True,
                 'voiceURI': 'Google US English'},
            ],
            'ios': [
                {'name': 'Samantha', 'lang': 'en-US', 'localService': True, 'default': True,
                 'voiceURI': 'com.apple.voice.compact.en-US.Samantha'},
            ],
        }
        voices_base = speech_voices_map.get(os_type, speech_voices_map['windows'])
        rot = audio_seed_int % len(voices_base)
        rotated = voices_base[rot:] + voices_base[:rot]
        rotated = [dict(v, default=(i == 0)) for i, v in enumerate(rotated)]

        font_list = profile.get('fonts', profile.get('fontList', []))

        brands_js = _j.dumps([
            {'brand': 'Not/A)Brand', 'version': '8'},
            {'brand': 'Chromium', 'version': str(chrome_ver)},
            {'brand': 'Google Chrome', 'version': str(chrome_ver)},
        ])
        brands_full_js = _j.dumps([
            {'brand': 'Not/A)Brand', 'version': '8.0.0.0'},
            {'brand': 'Chromium', 'version': chrome_full_ver},
            {'brand': 'Google Chrome', 'version': chrome_full_ver},
        ])

        p = ['(function() {', "  'use strict';",
             # Create shared native-fn registry early so NavigatorUAData methods can register
             "  var _sym = Symbol.for('__tgf_native_fns__');",
             "  if (!window[_sym]) { Object.defineProperty(window, _sym, {value:new WeakSet(),configurable:false,enumerable:false}); }",
             "  var _nfReg = window[_sym];",
        ]

        # 1. Timezone
        if timezone and tz_offset is not None:
            p += [
                f'  var _fpTZ={_j.dumps(timezone)};',
                f'  var _fpTZOff={int(tz_offset)};',
                '  try {',
                '    var _ODTF=Intl.DateTimeFormat;',
                '    function _PDTF(loc,opts){',
                '      var o=Object.assign({},opts||{});',
                '      if(!o.timeZone)o.timeZone=_fpTZ;',
                '      return new _ODTF(loc,o);',
                '    }',
                '    var _oRO=_ODTF.prototype.resolvedOptions;',
                '    _PDTF.prototype=_ODTF.prototype;',
                '    Object.defineProperties(_PDTF,Object.getOwnPropertyDescriptors(_ODTF));',
                '    _PDTF.prototype.resolvedOptions=function(){',
                '      return Object.assign({},_oRO.call(this),{timeZone:_fpTZ});',
                '    };',
                '    Intl.DateTimeFormat=_PDTF;',
                '  } catch(e){}',
                '  try{Date.prototype.getTimezoneOffset=function(){return -_fpTZOff;};}catch(e){}',
            ]

        # 2. UserAgentData.getHighEntropyValues (Chrome only)
        # Must create a proper NavigatorUAData class so that:
        #   - navigator.userAgentData instanceof NavigatorUAData === true
        #   - navigator.userAgentData.toString() === "[object NavigatorUAData]"
        #   - brands/mobile/platform are getters on NavigatorUAData.prototype
        #   - getHighEntropyValues/toJSON are methods on NavigatorUAData.prototype
        if is_chrome:
            p += [
                f'  var _uadBrands={brands_js};',
                f'  var _uadBrandsFull={brands_full_js};',
                f'  var _uadPlatform={_j.dumps(ua_platform)};',
                f'  var _uadPlatVer={_j.dumps(platform_ver)};',
                f'  var _uadArch={_j.dumps(ua_arch)};',
                f'  var _uadFullVer={_j.dumps(chrome_full_ver)};',
                f'  var _uadMobile={"true" if is_mobile else "false"};',
                f'  var _uadModel={_j.dumps(profile.get("deviceModel", ""))};',
                # Create NavigatorUAData class
                '  (function(){',
                '    function NavigatorUAData(){}',
                '    NavigatorUAData.prototype[Symbol.toStringTag]="NavigatorUAData";',
                '    Object.defineProperties(NavigatorUAData.prototype,{',
                '      brands:{get:function brands(){return _uadBrands;},enumerable:true,configurable:true},',
                '      mobile:{get:function mobile(){return _uadMobile;},enumerable:true,configurable:true},',
                '      platform:{get:function platform(){return _uadPlatform;},enumerable:true,configurable:true}',
                '    });',
                '    NavigatorUAData.prototype.getHighEntropyValues=function getHighEntropyValues(hints){',
                '      return Promise.resolve({brands:_uadBrands,mobile:_uadMobile,platform:_uadPlatform,',
                '        platformVersion:_uadPlatVer,architecture:_uadArch,bitness:\'64\',',
                '        model:_uadModel,uaFullVersion:_uadFullVer,fullVersionList:_uadBrandsFull});};',
                '    NavigatorUAData.prototype.toJSON=function toJSON(){return{brands:_uadBrands,mobile:_uadMobile,platform:_uadPlatform};};',
                # Register all NavigatorUAData methods/getters as "native" for toString spoofing
                '    var _bd=Object.getOwnPropertyDescriptor(NavigatorUAData.prototype,"brands");',
                '    var _md=Object.getOwnPropertyDescriptor(NavigatorUAData.prototype,"mobile");',
                '    var _pd=Object.getOwnPropertyDescriptor(NavigatorUAData.prototype,"platform");',
                '    [_bd.get,_md.get,_pd.get,NavigatorUAData.prototype.getHighEntropyValues,NavigatorUAData.prototype.toJSON,NavigatorUAData].forEach(function(f){if(f)_nfReg.add(f);});',
                '    var _uadInst=Object.create(NavigatorUAData.prototype);',
                '    var _uadGetter=function userAgentData(){return _uadInst;};',
                '    _nfReg.add(_uadGetter);',
                '    try{Object.defineProperty(Navigator.prototype,\'userAgentData\',',
                '      {get:_uadGetter,enumerable:true,configurable:true});}catch(e){}',
                '    if(typeof window.NavigatorUAData==="undefined"){',
                '      window.NavigatorUAData=NavigatorUAData;',
                '    }',
                '  })();',
            ]

        # 3. ClientRects noise
        p += [
            f'  try{{var _crN=((0x{cr_seed:08x}%2001)-1000)/10000000;',
            '    function _wR(r){if(!r||typeof r.x===\'undefined\')return r;',
            '      return{x:r.x+_crN,y:r.y+_crN,width:r.width,height:r.height,',
            '        top:r.top+_crN,right:r.right+_crN,bottom:r.bottom+_crN,left:r.left+_crN,',
            '        toJSON:function(){return{x:r.x+_crN,y:r.y+_crN,width:r.width,height:r.height,',
            '          top:r.top+_crN,right:r.right+_crN,bottom:r.bottom+_crN,left:r.left+_crN};}};}',
            '    var _oGBCR=Element.prototype.getBoundingClientRect;',
            '    Element.prototype.getBoundingClientRect=function getBoundingClientRect(){return _wR(_oGBCR.call(this));};',
            '    var _oGCR=Element.prototype.getClientRects;',
            '    Element.prototype.getClientRects=function getClientRects(){',
            '      var rs=_oGCR.call(this);var ns=Array.from(rs).map(_wR);',
            '      ns[Symbol.iterator]=Array.prototype[Symbol.iterator];ns.item=function(i){return ns[i]||null;};return ns;};',
            '    var _oRGCR=Range.prototype.getClientRects;',
            '    Range.prototype.getClientRects=function getClientRects(){',
            '      var rs=_oRGCR.call(this);var ns=Array.from(rs).map(_wR);',
            '      ns[Symbol.iterator]=Array.prototype[Symbol.iterator];ns.item=function(i){return ns[i]||null;};return ns;};',
            '    var _oRGBCR=Range.prototype.getBoundingClientRect;',
            '    Range.prototype.getBoundingClientRect=function getBoundingClientRect(){return _wR(_oRGBCR.call(this));};',
            '  }catch(e){}',
        ]

        # 4. Speech synthesis voices
        p += [
            f'  var _spV={_j.dumps(rotated)};',
            '  if(window.speechSynthesis&&window.speechSynthesis.getVoices){',
            '    window.speechSynthesis.getVoices=function getVoices(){return _spV;};',
            '    try{var _oSSAEL=window.speechSynthesis.addEventListener;',
            '    if(_oSSAEL){window.speechSynthesis.addEventListener=function(t,l,o){',
            '      if(t===\'voiceschanged\')setTimeout(function(){if(typeof l===\'function\')l.call(window.speechSynthesis,{type:\'voiceschanged\'});},0);',
            '      return _oSSAEL.call(this,t,l,o);};}',
            '    }catch(e){}',
            '  }',
        ]

        # 5. Battery API
        p += [
            '  if(navigator.getBattery){',
            f'    var _bM={"true" if is_mobile else "false"};',
            f'    var _bS={audio_seed_int % 1000};',
            '    var _bL=_bM?(0.3+(_bS*0.001)):1.0;',
            '    var _bC=_bM?((_bS%3)!==0):true;',
            '    var _bCT=_bC?Math.max(0,3600-(_bS*3)):0;',
            '    var _bDT=_bC?Infinity:(3600+(_bS*18));',
            '    navigator.getBattery=function(){return Promise.resolve({',
            '      charging:_bC,chargingTime:_bCT,dischargingTime:_bDT,level:_bL,',
            '      addEventListener:function(){},removeEventListener:function(){},dispatchEvent:function(){return true;},',
            '      onchargingchange:null,onchargingtimechange:null,ondischargingtimechange:null,onlevelchange:null});};}',
        ]

        # 6. Font detection (if profile specifies fonts)
        if font_list:
            p += [
                f'  var _fpFonts={_j.dumps(font_list)};',
                '  if(document.fonts&&document.fonts.check){',
                '    var _oFC2=document.fonts.check.bind(document.fonts);',
                '    document.fonts.check=function(fnt){',
                '      try{' + 'var fm=fnt.replace(/[^a-zA-Z0-9 ,-]/g,'').trim().toLowerCase();' + 'if(fm.length===0)return _oFC2(fnt);',
                '        return _fpFonts.some(function(x){var xl=x.toLowerCase();return xl===fm||fm.includes(xl)||xl.includes(fm);});',
                '      }catch(e){}return _oFC2(fnt);};',
                '    try{document.fonts.values=function(){return [][Symbol.iterator]();};',
                '    Object.defineProperty(document.fonts,"size",{get:function(){return 0;},configurable:true});',
                '    }catch(e){}',
                '  }',
            ]

        # 7. IFrame cross-frame Function.prototype.toString protection
        p += [
            '  function _fpPI(win){',
            '    if(!win||win._fpP)return;',
            '    try{if(!win.AudioBuffer)return;}catch(e){return;}',
            '    try{win._fpP=true;}catch(e){}',
            '    try{',
            '      var _iWS=new win.WeakSet();',
            '      var _iOTS=win.Function.prototype.toString;',
            '      var _iPTS=function toString(){if(_iWS.has(this))return\'function \'+(this.name||\'\')+\'() { [native code] }\';return _iOTS.call(this);};',
            '      _iWS.add(_iPTS);',
            '      win.Object.defineProperty(win.Function.prototype,\'toString\',{value:_iPTS,writable:true,configurable:true,enumerable:false});',
            '      try{win.Object.defineProperty(win.navigator,\'vendor\',{get:function(){return\'Google Inc.\';},configurable:true});}catch(e){}',
            '      try{win.Object.defineProperty(win.navigator,\'webdriver\',{get:function(){return false;},configurable:true});}catch(e){}',
            '    }catch(e){}',
            '  }',
            '  var _oAC=Node.prototype.appendChild;',
            '  Node.prototype.appendChild=function appendChild(n){var r=_oAC.call(this,n);',
            '    try{if(n&&n.tagName===\'IFRAME\'&&n.contentWindow)_fpPI(n.contentWindow);}catch(e){}return r;};',
            '  var _oIB=Node.prototype.insertBefore;',
            '  Node.prototype.insertBefore=function insertBefore(n,ref){var r=_oIB.call(this,n,ref);',
            '    try{if(n&&n.tagName===\'IFRAME\'&&n.contentWindow)_fpPI(n.contentWindow);}catch(e){}return r;};',
            '  var _oCE=document.createElement.bind(document);',
            '  document.createElement=function createElement(tag){var e=_oCE(tag);',
            '    if(typeof tag===\'string\'&&tag.toLowerCase()===\'iframe\')e.addEventListener(\'load\',function(){if(e.contentWindow)_fpPI(e.contentWindow);});',
            '    return e;};',
        ]

        p.append('})()')
        return '\n'.join(p)

    @staticmethod
    def _build_audio_stealth_script(mode: str, noise: float, seed: int, sparse_rate: int) -> str:
        """Audio fingerprint protection using x-acc-management's stealth approach.
        
        NO Proxy, NO Float32Array replacement → undetectable by fv.pro.
        
        Modes:
        - 'real': pass through unchanged (for Chrome profiles → native Firefox audio passes fv.pro)
        - 'noise': add sparse noise to getChannelData (for Firefox profiles → uniqueness)
        """
        if mode == 'real':
            return '(function(){})();'  # No-op for 'real' mode
        
        return f"""
(function() {{
    'use strict';
    
    const _audioNoise = {noise};
    const _audioSeed = {seed};
    const _audioSparseRate = {sparse_rate};
    
    // Get shared native-fn registry for toString spoofing
    const _nativeFns = window[Symbol.for('__tgf_native_fns__')];
    
    // STEALTH: Return real Float32Array with noise (NO Proxy)
    if (typeof AudioBuffer !== 'undefined' && AudioBuffer.prototype.getChannelData) {{
        const _origGetChannelData = AudioBuffer.prototype.getChannelData;
        const _origDesc = Object.getOwnPropertyDescriptor(AudioBuffer.prototype, 'getChannelData');
        const _noisedCache = new WeakMap();
        
        const stealthGetChannelData = function getChannelData(channel) {{
            const realData = _origGetChannelData.call(this, channel);
            
            // Cache noised arrays per buffer+channel
            let channelCache = _noisedCache.get(this);
            if (!channelCache) {{
                channelCache = {{}};
                _noisedCache.set(this, channelCache);
            }}
            if (channelCache[channel]) return channelCache[channel];
            
            // Create new Float32Array with SPARSE noise
            const noisedData = new Float32Array(realData.length);
            for (let i = 0; i < realData.length; i++) {{
                if (i % _audioSparseRate === 0) {{
                    const noise = _audioNoise * (2 * Math.abs(Math.sin(_audioSeed + i * 0.3141592)) - 1);
                    noisedData[i] = Math.max(-1, Math.min(1, realData[i] + noise));
                }} else {{
                    noisedData[i] = realData[i];
                }}
            }}
            
            channelCache[channel] = noisedData;
            return noisedData;
        }};
        
        // Register as native for toString spoofing
        if (_nativeFns) _nativeFns.add(stealthGetChannelData);
        try {{ Object.defineProperty(stealthGetChannelData, 'name', {{value: 'getChannelData', configurable: true}}); }} catch(e) {{}}
        
        try {{
            Object.defineProperty(AudioBuffer.prototype, 'getChannelData', {{
                value: stealthGetChannelData,
                writable: _origDesc?.writable !== false,
                enumerable: _origDesc?.enumerable || false,
                configurable: _origDesc?.configurable !== false
            }});
        }} catch(e) {{
            AudioBuffer.prototype.getChannelData = stealthGetChannelData;
        }}
        
        // Also patch copyFromChannel
        if (AudioBuffer.prototype.copyFromChannel) {{
            const _origCopyFromChannel = AudioBuffer.prototype.copyFromChannel;
            const _origCopyDesc = Object.getOwnPropertyDescriptor(AudioBuffer.prototype, 'copyFromChannel');
            
            const stealthCopyFromChannel = function copyFromChannel(destination, channelNumber, startInChannel) {{
                _origCopyFromChannel.call(this, destination, channelNumber, startInChannel || 0);
                try {{
                    if (destination && destination.length > 0) {{
                        const offset = startInChannel || 0;
                        for (let i = 0; i < destination.length; i++) {{
                            if ((offset + i) % _audioSparseRate === 0) {{
                                const noise = _audioNoise * (2 * Math.abs(Math.sin(_audioSeed + (offset + i) * 0.3141592)) - 1);
                                destination[i] = Math.max(-1, Math.min(1, destination[i] + noise));
                            }}
                        }}
                    }}
                }} catch(e) {{}}
                return undefined;
            }};
            
            if (_nativeFns) _nativeFns.add(stealthCopyFromChannel);
            try {{ Object.defineProperty(stealthCopyFromChannel, 'name', {{value: 'copyFromChannel', configurable: true}}); }} catch(e) {{}}
            
            try {{
                Object.defineProperty(AudioBuffer.prototype, 'copyFromChannel', {{
                    value: stealthCopyFromChannel,
                    writable: _origCopyDesc?.writable !== false,
                    enumerable: _origCopyDesc?.enumerable || false,
                    configurable: _origCopyDesc?.configurable !== false
                }});
            }} catch(e) {{
                AudioBuffer.prototype.copyFromChannel = stealthCopyFromChannel;
            }}
        }}
    }}
}})();
"""

    @staticmethod
    def _build_audio_precision_script() -> str:
        """JS init script: exact Chrome audio fingerprint values via Float32Array proxy."""
        return """
(function() {
    'use strict';

    const CHROME_REDUCTION = -20.538286209106445;
    const CHROME_FREQ_SUM  = 164537.64796829224;
    const CHROME_TIME_SUM  = 502.5999283068122;
    const CHROME_SAMP_SUM  = 124.04347527516074;
    const DB_KEY           = '-20.538286209106445,164537.64796829224,502.5999283068122';
    const REDUCTION_PREFIX = '-20.538286209106445,';

    // Float32Array proxy: allows float64 corrections at specific indices.
    // Needed because getFloatFrequencyData/getFloatTimeDomainData fill a Float32Array
    // in-place (void return). Float32 truncation would make sum(|arr|) off by ~0.007.
    // Sterbenz lemma: adj = TARGET - psum is exact when psum ~= TARGET; then
    // psum + adj == TARGET exactly in float64. The proxy returns adj as float64.
    const _NativeF32 = window.Float32Array;
    const _proxyCorr = new WeakMap();  // proxy -> corrMap
    const _proxyReal = new WeakMap();  // proxy -> real Float32Array (for native API calls)

    function _makeF32Proxy(real) {
        const corrMap = new Map();
        const proxy = new Proxy(real, {
            get(target, prop) {
                if (corrMap.has(prop)) return corrMap.get(prop);
                const v = Reflect.get(target, prop, target);
                return (typeof v === 'function') ? v.bind(target) : v;
            },
            set(target, prop, value) {
                return Reflect.set(target, prop, value, target);
            },
            has(target, prop) { return Reflect.has(target, prop); },
            getOwnPropertyDescriptor(target, prop) {
                return Reflect.getOwnPropertyDescriptor(target, prop);
            }
        });
        _proxyCorr.set(proxy, corrMap);
        _proxyReal.set(proxy, real);
        return proxy;
    }

    // Replace global Float32Array; preserve instanceof, statics, and name.
    (function() {
        function Float32Array(...args) {
            const real = Reflect.construct(_NativeF32, args, Float32Array);
            return _makeF32Proxy(real);
        }
        Float32Array.prototype         = _NativeF32.prototype;
        Float32Array.BYTES_PER_ELEMENT = _NativeF32.BYTES_PER_ELEMENT;
        Float32Array.from              = _NativeF32.from.bind(_NativeF32);
        Float32Array.of                = _NativeF32.of.bind(_NativeF32);
        Float32Array[Symbol.species]   = _NativeF32;
        Object.setPrototypeOf(Float32Array, _NativeF32);
        window.Float32Array = Float32Array;
    })();

    function _setCorr(arr, idx, val) {
        const m = _proxyCorr.get(arr);
        if (m) m.set(String(idx), val);
    }

    // 1. DynamicsCompressorNode.reduction: return Chrome value for OAC contexts.
    const _dcnDesc = Object.getOwnPropertyDescriptor(DynamicsCompressorNode.prototype, 'reduction');
    if (_dcnDesc && _dcnDesc.get) {
        Object.defineProperty(DynamicsCompressorNode.prototype, 'reduction', {
            get: function() {
                if (this.context instanceof OfflineAudioContext) return CHROME_REDUCTION;
                return _dcnDesc.get.call(this);
            },
            configurable: true
        });
    }

    // 2. getFloatFrequencyData for OAC: exact freqSum via Sterbenz + proxy correction.
    // Firefox OAC returns -Infinity for all bins (no audio dispatched before startRendering
    // resolves on main thread). We replace completely for OAC; pass-through for live ctx.
    const _origFreqData = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function(arr) {
        if (!(this.context instanceof OfflineAudioContext)) {
            return _origFreqData.call(this, _proxyReal.get(arr) || arr);
        }
        const n = arr.length;
        if (n === 0) return;
        const perBin = -(CHROME_FREQ_SUM / n);
        for (let i = 0; i < n - 1; i++) arr[i] = perBin;
        let psum = 0;
        for (let i = 0; i < n - 1; i++) psum += Math.abs(arr[i]);
        const adj = CHROME_FREQ_SUM - psum;
        _setCorr(arr, n - 1, -Math.abs(adj));
        arr[n - 1] = -Math.abs(adj);
    };

    // 3. getFloatTimeDomainData for OAC: exact timeSum via Sterbenz + proxy correction.
    const _origTimeData = AnalyserNode.prototype.getFloatTimeDomainData;
    AnalyserNode.prototype.getFloatTimeDomainData = function(arr) {
        if (!(this.context instanceof OfflineAudioContext)) {
            return _origTimeData.call(this, _proxyReal.get(arr) || arr);
        }
        const n = arr.length;
        if (n === 0) return;
        const perSample = CHROME_TIME_SUM / n;
        for (let i = 0; i < n - 1; i++) arr[i] = (i & 1) ? -perSample : perSample;
        let psum = 0;
        for (let i = 0; i < n - 1; i++) psum += Math.abs(arr[i]);
        const adj = CHROME_TIME_SUM - psum;
        const sign = ((n - 1) & 1) ? -1 : 1;
        _setCorr(arr, n - 1, sign * Math.abs(adj));
        arr[n - 1] = sign * Math.abs(adj);
    };

    // 4. AudioBuffer.getChannelData: exact sampleSum via Sterbenz Proxy.
    const _origChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {
        const data = _origChannelData.call(this, channel);
        if (this.length === 5000 && this.numberOfChannels === 1 &&
                Math.abs(this.sampleRate - 44100) < 1) {
            let psum = 0;
            for (let i = 4500; i < 4999; i++) psum += Math.abs(data[i]);
            const adj = CHROME_SAMP_SUM - psum;
            if (adj > 0) {
                const sign4999 = data[4999] >= 0 ? 1 : -1;
                return new Proxy(data, {
                    get(target, prop) {
                        if (prop === '4999') return sign4999 * adj;
                        const v = Reflect.get(target, prop, target);
                        return (typeof v === 'function') ? v.bind(target) : v;
                    }
                });
            }
        }
        return data;
    };

    // 5. Array.prototype.join intercept (defense-in-depth for .join() callers).
    const _origJoin = Array.prototype.join;
    Object.defineProperty(Array.prototype, 'join', {
        value: function(sep) {
            const s = _origJoin.call(this, sep);
            if (typeof s === 'string' &&
                    s.startsWith(REDUCTION_PREFIX) && s.split(',').length === 3)
                return DB_KEY;
            return s;
        },
        configurable: true, writable: true
    });

    // Register patched functions with the shared native-fn registry
    // so Function.prototype.toString returns "[native code]" for them.
    (function() {
        var _sym = Symbol.for('__tgf_native_fns__');
        var _reg = window[_sym];
        if (_reg) {
            [AnalyserNode.prototype.getFloatFrequencyData,
             AnalyserNode.prototype.getFloatTimeDomainData,
             AudioBuffer.prototype.getChannelData,
             Array.prototype.join,
             window.Float32Array].forEach(function(fn) { if (fn) _reg.add(fn); });
        }
    })();
})();
"""

    @staticmethod
    def _build_browser_compat_script(is_chrome: bool, is_safari: bool,
                                      is_firefox: bool, ua: str,
                                      webgl_vendor: str = '', webgl_renderer: str = '',
                                      oscpu_str: str = '',
                                      device_memory=None, hardware_concurrency=None,
                                      canvas_seed: int = 0) -> str:
        """Build JS that patches navigator, window.chrome, WebGL, canvas, InstallTrigger."""
        import json as _j
        lines = ['(function() {']

        # Preamble: toString override + _defProto helper — shared by all profile branches.
        # _defProto sets properties on Navigator.prototype (not the instance) so that
        # Object.getOwnPropertyDescriptor(navigator, key) returns undefined, matching real browsers.
        # _nativeFns is stored on a global Symbol so later init scripts (audio precision)
        # can register their patched functions into the same WeakSet.
        lines += [
            "  var _origFnToStr = Function.prototype.toString;",
            "  var _sym = Symbol.for('__tgf_native_fns__');",
            "  var _nativeFns = window[_sym] || new WeakSet();",
            "  if (!window[_sym]) { Object.defineProperty(window, _sym, {value:_nativeFns,configurable:false,enumerable:false}); }",
            "  var _fakeToStr = function toString() {",
            "    if (this === _fakeToStr || _nativeFns.has(this))",
            "      return 'function ' + (this.name || '') + '() { [native code] }';",
            "    return _origFnToStr.call(this);",
            "  };",
            "  _nativeFns.add(_fakeToStr);",
            "  Object.defineProperty(Function.prototype, 'toString', {value:_fakeToStr,configurable:true,writable:true});",
            "  function _defProto(p,k,v){ try{ var d=Object.getOwnPropertyDescriptor(p,k); if(d&&!d.configurable)return; var _g=function(){return v;}; Object.defineProperty(_g,'name',{value:'get '+k}); _nativeFns.add(_g); Object.defineProperty(p,k,{get:_g,set:undefined,configurable:true,enumerable:true}); }catch(e){} }",
        ]

        if is_chrome:
            # Extract Chrome major version from UA for userAgentData
            import re as _re2
            _chrome_ver = '120'
            _cm = _re2.search(r'Chrome/(\d+)', ua)
            if _cm: _chrome_ver = _cm.group(1)
            _platform_uad = 'Windows' if 'Win' in ua else ('macOS' if 'Mac' in ua else 'Linux')
            _dm_val = int(device_memory or 8)
            _hc_val = int(hardware_concurrency or 8)
            lines += [
                # Navigator.prototype overrides — use _nativeFns/_defProto from preamble
                f"  (function(){{",
                f"    var _p = Navigator.prototype;",
                f"    function _def(proto, key, val) {{",
                f"      try {{",
                f"        var d = Object.getOwnPropertyDescriptor(proto, key);",
                f"        if (d && !d.configurable) return;",
                f"        var _g = function() {{ return val; }};",
                f"        Object.defineProperty(_g, 'name', {{value: 'get ' + key}});",
                f"        _nativeFns.add(_g);",
                f"        Object.defineProperty(proto, key, {{get:_g, set:undefined, configurable:true, enumerable:true}});",
                f"      }} catch(e) {{}}",
                f"    }}",
                f"    _def(_p, 'vendor',             'Google Inc.');",
                f"    _def(_p, 'productSub',          '20030107');",
                f"    _def(_p, 'oscpu',               undefined);",
                f"    _def(_p, 'buildID',             undefined);",
                f"    _def(_p, 'deviceMemory',        {_dm_val});",
                f"    _def(_p, 'hardwareConcurrency', {_hc_val});",
                f"    _def(_p, 'globalPrivacyControl', undefined);",
                f"    _def(_p, 'languages',           ['en-US','en']);",
                f"    var _conn = {{downlink:10,downlinkMax:Infinity,effectiveType:'4g',rtt:50,saveData:false,type:'wifi',onchange:null}};",
                f"    _def(_p, 'connection', _conn);",
                # userAgentData is handled by _build_extra_fingerprint_script with proper NavigatorUAData class
                # navigator.webdriver: In real Chrome it's false (not undefined) when not automated.
                # Playwright/Juggler sets it to true — must override on prototype.
                f"    _def(_p, 'webdriver', false);",
                f"    ['mozGetUserMedia','mozCancelAnimationFrame','mozRequestAnimationFrame','mozInnerScreenX','mozInnerScreenY','buildID','oscpu','globalPrivacyControl'].forEach(function(k){{",
                f"      try {{ delete _p[k]; }} catch(e) {{}}",
                f"      try {{ delete navigator[k]; }} catch(e) {{}}",
                f"    }});",
                f"  }})();",
                # window.chrome — key functions marked native via _nativeFns
                '  (function(){',
                '    var _noop = function(){};',
                '    _nativeFns.add(_noop);',
                '    var _connect = function connect(){return _port;};',
                '    _nativeFns.add(_connect);',
                '    var _sendMsg = function sendMessage(){};',
                '    _nativeFns.add(_sendMsg);',
                '    var _getManifest = function getManifest(){return null;};',
                '    _nativeFns.add(_getManifest);',
                '    var _port = { onMessage:{addListener:_noop,removeListener:_noop,hasListener:_noop}, onDisconnect:{addListener:_noop,removeListener:_noop,hasListener:_noop}, disconnect:_noop, postMessage:_noop };',
                '    var _rt = { connect:_connect, sendMessage:_sendMsg, getManifest:_getManifest, id:undefined, onMessage:{addListener:_noop,removeListener:_noop}, onConnect:{addListener:_noop,removeListener:_noop} };',
                '    if (!window.chrome) {',
                '      window.chrome = { app:{isInstalled:false,InstallState:{DISABLED:"disabled",INSTALLED:"installed",NOT_INSTALLED:"not_installed"},RunningState:{CANNOT_RUN:"cannot_run",READY_TO_RUN:"ready_to_run",RUNNING:"running"}}, runtime:_rt, webstore:{onInstallStageChanged:{addListener:_noop},onDownloadProgress:{addListener:_noop}}, loadTimes:_noop, csi:_noop };',
                '    } else if (window.chrome && !window.chrome.runtime) {',
                '      window.chrome.runtime = _rt;',
                '    } else if (window.chrome && window.chrome.runtime && !window.chrome.runtime.connect) {',
                '      window.chrome.runtime.connect = _connect;',
                '      window.chrome.runtime.sendMessage = _sendMsg;',
                '    }',
                '  })();',
                # performance.memory — getter also marked native
                '  (function(){',
                f'    var _dm = {_dm_val};',
                '    if (typeof performance !== "undefined" && typeof performance.memory === "undefined") {',
                '      var _heapLimit = 2172649472;',
                '      var _totalHeap = Math.round((_dm / 8) * 268435456);',
                '      var _usedHeap  = Math.round(_totalHeap * 0.6);',
                '      var _memGetter = function() { return { jsHeapSizeLimit:_heapLimit, totalJSHeapSize:_totalHeap, usedJSHeapSize:_usedHeap }; };',
                '      Object.defineProperty(_memGetter, "name", {value: "get memory"});',
                '      _nativeFns.add(_memGetter);',
                '      try { Object.defineProperty(performance, "memory", { get: _memGetter, configurable:true }); } catch(e){}',
                '    }',
                '  })();',
                # Delete Firefox globals (delete removes the key; defineProperty keeps it → 'in' still true)
                "  try { delete window.InstallTrigger; } catch(e){}",
                "  try { delete window.mozInnerScreenX; } catch(e){}",
                "  try { delete window.mozInnerScreenY; } catch(e){}",
                "  try { delete window.netscape; } catch(e){}",
                # Patch CSS.supports
                "  (function(){ var _orig=CSS.supports.bind(CSS); try { Object.defineProperty(CSS,'supports',{value:function(p,v){if(typeof p==='string'&&p.indexOf('-moz-')===0)return false;return _orig.apply(this,arguments);},configurable:true,writable:true}); } catch(e){} })();",
                # Error.stack: convert Firefox format (@file:line:col) to Chrome format (at func (file:line:col))
                '  (function(){',
                '    var _oStackGet = Object.getOwnPropertyDescriptor(Error.prototype, "stack");',
                '    if (!_oStackGet || !_oStackGet.get) return;',
                '    var _origGet = _oStackGet.get;',
                '    Object.defineProperty(Error.prototype, "stack", {',
                '      get: function() {',
                '        var s = _origGet.call(this);',
                '        if (typeof s !== "string") return s;',
                '        var lines = s.split("\\n");',
                '        var msg = this.message || "";',
                '        var m1 = msg.match(/can\'t access property "(.+)" of (.+)/);',
                '        if (m1) msg = "Cannot read properties of " + m1[2] + " (reading \'" + m1[1] + "\')";',
                '        var m2 = msg.match(/(.+) is not a function/);',
                '        if (!m1 && m2) msg = msg;',
                '        var out = [(this.name || "Error") + ": " + msg];',
                '        for (var i = 0; i < lines.length; i++) {',
                '          var ln = lines[i];',
                '          if (!ln || ln.indexOf("@") === -1) continue;',
                '          var at = ln.indexOf("@");',
                '          var fn = ln.substring(0, at) || "<anonymous>";',
                '          var loc = ln.substring(at + 1);',
                '          if (loc.indexOf("chrome://") === 0 || loc.indexOf("resource://") === 0) continue;',
                '          out.push("    at " + fn + " (" + loc + ")");',
                '        }',
                '        return out.join("\\n");',
                '      },',
                '      set: _oStackGet.set,',
                '      configurable: true, enumerable: true',
                '    });',
                '  })();',
                # navigator.plugins & mimeTypes: Chrome exposes 5 PDF-related plugins.
                # Firefox has different plugin list — spoof to match Chrome's known set.
                '  (function(){',
                '    try {',
                '      var _pluginNames = ["PDF Viewer","Chrome PDF Viewer","Chromium PDF Viewer","Microsoft Edge PDF Viewer","WebKit built-in PDF"];',
                '      var _mimeType = {type:"application/pdf",suffixes:"pdf",description:"Portable Document Format"};',
                '      var _plugins = [];',
                '      for(var i=0;i<_pluginNames.length;i++){',
                '        _plugins.push({name:_pluginNames[i],filename:"internal-pdf-viewer",description:"Portable Document Format",length:1,0:_mimeType,item:function(n){return n===0?_mimeType:null;},namedItem:function(n){return n==="application/pdf"?_mimeType:null;}});',
                '      }',
                '      var _pluginArray = {length:_plugins.length};',
                '      for(var j=0;j<_plugins.length;j++) _pluginArray[j]=_plugins[j];',
                '      _pluginArray.item = function(n){return _plugins[n]||null;};',
                '      _pluginArray.namedItem = function(n){for(var k=0;k<_plugins.length;k++)if(_plugins[k].name===n)return _plugins[k];return null;};',
                '      _pluginArray.refresh = function(){};',
                '      _defProto(Navigator.prototype, "plugins", _pluginArray);',
                '      var _mimeArray = {length:1,0:_mimeType};',
                '      _mimeArray.item = function(n){return n===0?_mimeType:null;};',
                '      _mimeArray.namedItem = function(n){return n==="application/pdf"?_mimeType:null;};',
                '      _defProto(Navigator.prototype, "mimeTypes", _mimeArray);',
                '      _defProto(Navigator.prototype, "pdfViewerEnabled", true);',
                '    } catch(e){}',
                '  })();',
                # Chrome-specific Web APIs — stub objects so feature detection matches Chrome UA.
                # BrowserScan checks for presence of these APIs; missing = inconsistency with Chrome UA.
                '  (function(){',
                '    var _noop = function(){};',
                '    var _rejectPerm = function(){ return Promise.reject(new DOMException("","NotAllowedError")); };',
                '    // CredentialsContainer',
                '    if (!navigator.credentials) {',
                '      var _cred = {get:function(){return Promise.resolve(null);},store:function(){return Promise.resolve();},create:function(){return Promise.resolve(null);},preventSilentAccess:function(){return Promise.resolve();}};',
                '      _defProto(Navigator.prototype, "credentials", _cred);',
                '    }',
                '    // Bluetooth',
                '    if (!navigator.bluetooth) {',
                '      _defProto(Navigator.prototype, "bluetooth", {getAvailability:function(){return Promise.resolve(false);},requestDevice:_rejectPerm});',
                '    }',
                '    // USB',
                '    if (!navigator.usb) {',
                '      _defProto(Navigator.prototype, "usb", {getDevices:function(){return Promise.resolve([]);},requestDevice:_rejectPerm,addEventListener:_noop,removeEventListener:_noop});',
                '    }',
                '    // Serial',
                '    if (!navigator.serial) {',
                '      _defProto(Navigator.prototype, "serial", {getPorts:function(){return Promise.resolve([]);},requestPort:_rejectPerm,addEventListener:_noop,removeEventListener:_noop});',
                '    }',
                '    // HID',
                '    if (!navigator.hid) {',
                '      _defProto(Navigator.prototype, "hid", {getDevices:function(){return Promise.resolve([]);},requestDevice:_rejectPerm,addEventListener:_noop,removeEventListener:_noop});',
                '    }',
                '    // WebXR',
                '    if (!navigator.xr) {',
                '      _defProto(Navigator.prototype, "xr", {isSessionSupported:function(){return Promise.resolve(false);},requestSession:_rejectPerm,addEventListener:_noop,removeEventListener:_noop});',
                '    }',
                '    // ReportingObserver',
                '    if (typeof ReportingObserver === "undefined") {',
                '      window.ReportingObserver = function ReportingObserver(cb,opts){this.observe=_noop;this.disconnect=_noop;this.takeRecords=function(){return [];};};',
                '      _nativeFns.add(window.ReportingObserver);',
                '    }',
                '  })();',
                # Permissions API: automated browsers return "denied" for notifications.
                # Real Chrome returns "prompt" (default) or "granted". Override query().
                '  (function(){',
                '    if (!navigator.permissions || !navigator.permissions.query) return;',
                '    var _origQuery = navigator.permissions.query.bind(navigator.permissions);',
                '    var _patchedQuery = function query(desc) {',
                '      if (desc && desc.name === "notifications") {',
                '        return Promise.resolve({state:"prompt",status:"prompt",onchange:null});',
                '      }',
                '      return _origQuery(desc);',
                '    };',
                '    _nativeFns.add(_patchedQuery);',
                '    try { navigator.permissions.query = _patchedQuery; } catch(e) {}',
                '  })();',
            ]
            # Audio noise: DISABLED at JS level.
            # C++ Gaussian micro-noise (std=0.0001) on AnalyserNode is sufficient and
            # passes detection. The old JS sin-pattern on getChannelData was detectable
            # because Math.sin(seed+i*0.3141592) produces a mathematically regular pattern
            # that fingerprint detectors flag as "not real".
        elif is_safari:
            lines += [
                # Use _defProto (from preamble) so no own-property leak on navigator instance
                "  (function(){",
                "    var _p = Navigator.prototype;",
                "    _defProto(_p, 'vendor',       'Apple Computer, Inc.');",
                "    _defProto(_p, 'productSub',    '20030107');",
                "    _defProto(_p, 'oscpu',         undefined);",
                "    _defProto(_p, 'buildID',       undefined);",
                "    _defProto(_p, 'userAgentData', undefined);",
                "    _defProto(_p, 'webdriver', false);",
                # Remove Firefox-only globals from prototype and window
                "    ['mozGetUserMedia','globalPrivacyControl','mozInnerScreenX','mozInnerScreenY'].forEach(function(k){",
                "      try{ delete _p[k]; }catch(e){}",
                "      try{ delete navigator[k]; }catch(e){}",
                "    });",
                "  })();",
                "  try { delete window.InstallTrigger; } catch(e){}",
                "  try { delete window.mozInnerScreenX; } catch(e){}",
                "  try { delete window.mozInnerScreenY; } catch(e){}",
                "  try { delete window.netscape; } catch(e){}",
                "  (function(){ var _orig=CSS.supports.bind(CSS); try { Object.defineProperty(CSS,'supports',{value:function(p,v){if(typeof p==='string'&&p.indexOf('-moz-')===0)return false;return _orig.apply(this,arguments);},configurable:true,writable:true}); } catch(e){} })();",
            ]
        elif is_firefox:
            _oc_js = _j.dumps(oscpu_str) if oscpu_str else 'undefined'
            lines += [
                # Use _defProto so vendor/productSub/oscpu live on prototype, not instance
                f"  (function(){{",
                f"    var _p = Navigator.prototype;",
                f"    _defProto(_p, 'vendor',     '');",
                f"    _defProto(_p, 'productSub', '20100101');",
                f"    _defProto(_p, 'oscpu',      {_oc_js});",
                # Delete webdriver-related own-props if Tegufox injected any
                f"    try{{ delete navigator.webdriver; }}catch(e){{}}",
                f"  }})();",
            ]

        # WebGL full patch: UNMASKED (37445/37446) + VENDOR/RENDERER/VERSION (7936/7937/7938)
        # Safari: UNMASKED params return "" (extension not enabled by default in Safari).
        # Chrome/Firefox: use profile vendor/renderer.
        _do_webgl_patch = is_safari or webgl_vendor or webgl_renderer
        if _do_webgl_patch:
            if is_safari:
                # Safari never exposes WEBGL_debug_renderer_info — unmasked must be empty.
                v = _j.dumps('')
                r = _j.dumps('')
            else:
                v = _j.dumps(webgl_vendor)
                r = _j.dumps(webgl_renderer)
            if is_chrome:
                vendor_str  = _j.dumps('WebKit')
                render_str  = _j.dumps('WebKit WebGL')
                ver1_str    = _j.dumps('WebGL 1.0 (OpenGL ES 2.0 Chromium)')
                ver2_str    = _j.dumps('WebGL 2.0 (OpenGL ES 3.0 Chromium)')
            elif is_safari:
                vendor_str  = _j.dumps('WebKit')
                render_str  = _j.dumps('WebKit WebGL')
                ver1_str    = _j.dumps('WebGL 1.0 (OpenGL ES 2.0 WebKit)')
                ver2_str    = _j.dumps('WebGL 2.0 (OpenGL ES 3.0 WebKit)')
            else:  # Firefox — keep originals
                vendor_str = render_str = ver1_str = ver2_str = 'null'
            lines += [
                '  (function(){',
                f'    var _uv={v}, _ur={r};',
                f'    var _gv={vendor_str}, _gr={render_str}, _v1={ver1_str}, _v2={ver2_str};',
                '    function _patch(Ctx, ver){',
                '      if(!Ctx)return;',
                '      var _o=Ctx.prototype.getParameter;',
                '      Ctx.prototype.getParameter=function(p){',
                '        if(p===37445)return _uv;',
                '        if(p===37446)return _ur;',
                '        if(_gv!==null&&p===7936)return _gv;',
                '        if(_gr!==null&&p===7937)return _gr;',
                '        if(ver&&p===7938)return ver;',
                '        return _o.call(this,p);',
                '      };',
                '    }',
                '    try{_patch(WebGLRenderingContext,_v1);}catch(e){}',
                '    try{_patch(WebGL2RenderingContext,_v2);}catch(e){}',
                '  })();',
            ]

        # Canvas: Firefox pixel rendering != any Chrome DB entry in fv.pro.
        # For Chrome profiles, canvas noise makes hash unique (matches nothing) which is
        # MORE suspicious than native Firefox hash. Disable noise for Chrome profiles.
        # For Firefox/Safari profiles, noise provides session-consistent uniqueness.
        if canvas_seed and not is_chrome:
            _cs = int(canvas_seed) & 0xFFFFFFFF
            # Canvas: clone via drawImage (not getImageData) + R-channel Xorshift32 noise.
            # Ported from x-acc-management: drawImage preserves visual content exactly,
            # noise on R-channel only (±1), skip transparent pixels, consistent per seed.
            lines += [
                '  (function(){',
                '    try{',
                f'     var _CS=({_cs}*0x9e3779b9)|0;',
                '     function _cNoise(d){',
                '       var s=_CS;',
                '       for(var i=0;i<d.length;i+=4){',
                '         if(d[i+3]===0)continue;',
                '         var h=(s^i)|0;h^=h<<13;h^=h>>17;h^=h<<5;',
                '         var r=d[i]+(h&1?1:-1);',
                '         d[i]=r<0?0:r>255?255:r;',
                '       }',
                '     }',
                '     var _origTDU=HTMLCanvasElement.prototype.toDataURL;',
                '     var _pTDU=function toDataURL(){',
                '       if(!this.width||!this.height)return _origTDU.apply(this,arguments);',
                '       try{',
                '         var cl=document.createElement("canvas");',
                '         cl.width=this.width;cl.height=this.height;',
                '         var ctx=cl.getContext("2d");',
                '         if(!ctx)return _origTDU.apply(this,arguments);',
                '         ctx.drawImage(this,0,0);',
                '         var id=ctx.getImageData(0,0,cl.width,cl.height);',
                '         _cNoise(id.data);',
                '         ctx.putImageData(id,0,0);',
                '         return _origTDU.apply(cl,arguments);',
                '       }catch(e){return _origTDU.apply(this,arguments);}',
                '     };',
                '     _nativeFns.add(_pTDU);',
                '     HTMLCanvasElement.prototype.toDataURL=_pTDU;',
                '     var _origTB=HTMLCanvasElement.prototype.toBlob;',
                '     if(_origTB){',
                '       var _pTB=function toBlob(cb){',
                '         var args=Array.prototype.slice.call(arguments,1);',
                '         if(!this.width||!this.height){_origTB.apply(this,arguments);return;}',
                '         try{',
                '           var cl=document.createElement("canvas");',
                '           cl.width=this.width;cl.height=this.height;',
                '           var ctx=cl.getContext("2d");',
                '           if(!ctx){_origTB.apply(this,arguments);return;}',
                '           ctx.drawImage(this,0,0);',
                '           var id=ctx.getImageData(0,0,cl.width,cl.height);',
                '           _cNoise(id.data);',
                '           ctx.putImageData(id,0,0);',
                '           _origTB.apply(cl,[cb].concat(args));',
                '         }catch(e){_origTB.apply(this,arguments);}',
                '       };',
                '       _nativeFns.add(_pTB);',
                '       HTMLCanvasElement.prototype.toBlob=_pTB;',
                '     }',
                '    }catch(e){}',
                '  })();',
            ]

        lines.append('})();')
        return '\n'.join(lines)

    def _validate_fingerprints(self) -> None:
        """Validate fingerprint consistency (TLS, HTTP/2, UA, DoH)"""
        logger.info("Validating fingerprint consistency...")

        # Check required profile fields
        required_fields = ["tls", "http2", "navigator", "dns_config"]
        missing_fields = [f for f in required_fields if f not in self.profile]

        if missing_fields:
            logger.warning(f"Profile missing fields: {missing_fields}")

        # Validate DoH provider matches browser type
        dns_provider = self.profile.get("dns_config", {}).get("provider", "unknown")
        profile_name = self.profile.get("name", "").lower()

        expected_provider_map = {
            "chrome": "cloudflare",
            "firefox": "quad9",
            "safari": "cloudflare",
        }

        for browser_type, expected_provider in expected_provider_map.items():
            if browser_type in profile_name and dns_provider != expected_provider:
                logger.warning(
                    f"DoH provider mismatch: {profile_name} should use {expected_provider}, "
                    f"but uses {dns_provider}"
                )

        logger.info("Fingerprint validation complete")

    def _save_session_state(self) -> None:
        """Save session state to disk"""
        if not self.config.session_dir:
            return

        # Create session directory
        session_dir = Path(self.config.session_dir)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save cookies
        self.session_state.cookies = self.get_cookies()

        # Save state to JSON
        state_file = session_dir / f"{self.session_state.session_id}.json"
        with open(state_file, "w") as f:
            json.dump(self.session_state.to_dict(), f, indent=2)

        logger.info(f"Session state saved: {state_file}")

    def _save_error_screenshot(self, error: Exception) -> None:
        """Save screenshot on error"""
        if not self.page:
            return

        screenshot_dir = self.config.screenshot_dir or Path("screenshots/errors")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        screenshot_path = screenshot_dir / f"error_{timestamp}.png"

        try:
            self.page.screenshot(path=str(screenshot_path))
            logger.error(f"Error screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to save error screenshot: {e}")


class ProfileRotator:
    """
    Multi-account session manager with automatic profile rotation.

    Supports round-robin, random, and weighted rotation strategies.
    Tracks session state for each profile and prevents concurrent usage.

    Example:
        rotator = ProfileRotator([
            "amazon-seller-1",
            "amazon-seller-2",
            "amazon-seller-3"
        ])

        for session in rotator:
            session.goto("https://sellercentral.amazon.com")
            session.check_inventory()
    """

    def __init__(
        self,
        profiles: List[str],
        strategy: str = "round-robin",
        session_config: Optional[SessionConfig] = None,
        **kwargs,
    ):
        """
        Initialize ProfileRotator

        Args:
            profiles: List of profile names or paths
            strategy: Rotation strategy ('round-robin', 'random', 'weighted')
            session_config: SessionConfig for all sessions
            **kwargs: Additional SessionConfig parameters
        """
        self.profiles = profiles
        self.strategy = strategy
        self.session_config = session_config or SessionConfig(**kwargs)

        self.current_index = 0
        self.session_states: Dict[str, SessionState] = {}

        logger.info(
            f"ProfileRotator initialized: {len(profiles)} profiles, strategy={strategy}"
        )

    def __iter__(self):
        """Iterate over profiles with rotation"""
        return self

    def __next__(self) -> TegufoxSession:
        """Get next session with rotated profile"""
        profile = self._next_profile()

        logger.info(f"Rotating to profile: {profile}")

        return TegufoxSession(profile=profile, config=self.session_config)

    def _next_profile(self) -> str:
        """Get next profile based on rotation strategy"""
        if self.strategy == "round-robin":
            profile = self.profiles[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.profiles)
            return profile

        elif self.strategy == "random":
            return random.choice(self.profiles)

        elif self.strategy == "weighted":
            # Weighted by inverse last_active time (least recently used first)
            weights = []
            for profile in self.profiles:
                state = self.session_states.get(profile)
                if state:
                    # Older = higher weight
                    age = time.time() - state.last_active
                    weights.append(age)
                else:
                    # Never used = maximum weight
                    weights.append(float("inf"))

            # Convert inf to max finite weight
            max_finite = max(w for w in weights if w != float("inf"))
            weights = [max_finite * 2 if w == float("inf") else w for w in weights]

            # Weighted random choice
            total = sum(weights)
            r = random.uniform(0, total)
            cumulative = 0
            for i, weight in enumerate(weights):
                cumulative += weight
                if r <= cumulative:
                    return self.profiles[i]

            return self.profiles[-1]

        else:
            raise ValueError(f"Unknown rotation strategy: {self.strategy}")


class SessionManager:
    """
    Persistent session state manager.

    Saves and restores session state (cookies, storage, visited URLs)
    across browser restarts for seamless multi-session workflows.

    Example:
        manager = SessionManager("sessions/")

        # Save session
        with TegufoxSession("chrome-120") as session:
            session.goto("https://amazon.com")
            manager.save(session)

        # Restore session
        with TegufoxSession("chrome-120") as session:
            manager.restore(session)
            session.goto("https://amazon.com/orders")  # Already logged in
    """

    def __init__(self, session_dir: str = "sessions"):
        """
        Initialize SessionManager

        Args:
            session_dir: Directory to store session state files
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"SessionManager initialized: {self.session_dir}")

    def save(self, session: TegufoxSession, name: Optional[str] = None) -> None:
        """
        Save session state

        Args:
            session: TegufoxSession to save
            name: Optional name for session (default: profile name)
        """
        name = name or session.profile.get("name", "unknown")

        # Update session state
        session.session_state.cookies = session.get_cookies()
        session.session_state.last_active = time.time()

        # Save to file
        state_file = self.session_dir / f"{name}.json"
        with open(state_file, "w") as f:
            json.dump(session.session_state.to_dict(), f, indent=2)

        logger.info(f"Session saved: {state_file}")

    def restore(self, session: TegufoxSession, name: Optional[str] = None) -> bool:
        """
        Restore session state

        Args:
            session: TegufoxSession to restore
            name: Optional name for session (default: profile name)

        Returns:
            True if session restored, False if no saved state found
        """
        name = name or session.profile.get("name", "unknown")

        state_file = self.session_dir / f"{name}.json"

        if not state_file.exists():
            logger.warning(f"No saved session found: {state_file}")
            return False

        # Load state
        with open(state_file, "r") as f:
            state_data = json.load(f)

        session.session_state = SessionState.from_dict(state_data)

        # Restore cookies
        if session.session_state.cookies:
            session.set_cookies(session.session_state.cookies)

        logger.info(f"Session restored: {state_file}")
        return True

    def list_sessions(self) -> List[str]:
        """List all saved session names"""
        return [f.stem for f in self.session_dir.glob("*.json")]

    def delete(self, name: str) -> None:
        """Delete saved session"""
        state_file = self.session_dir / f"{name}.json"

        if state_file.exists():
            state_file.unlink()
            logger.info(f"Session deleted: {state_file}")
        else:
            logger.warning(f"Session not found: {state_file}")


# Utility functions


def check_dns_leak(profile: str = "chrome-120") -> Dict[str, Any]:
    """
    Quick DNS leak check utility.

    Args:
        profile: Profile name to test

    Returns:
        DNS leak test results
    """
    with TegufoxSession(profile=profile) as session:
        return session.validate_dns_leak()


# Backwards-compat alias (avoid pytest collecting it as a test)
run_dns_leak_check = check_dns_leak


def check_http2_fingerprint(profile: str = "chrome-120") -> Dict[str, Any]:
    """
    Quick HTTP/2 fingerprint check utility.

    Args:
        profile: Profile name to test

    Returns:
        HTTP/2 fingerprint test results
    """
    with TegufoxSession(profile=profile) as session:
        return session.validate_http2_fingerprint()


if __name__ == "__main__":
    # Example usage
    print("Tegufox Automation Framework v1.0")
    print("=" * 50)

    # Example 1: Basic session
    print("\nExample 1: Basic session")
    with TegufoxSession(profile="chrome-120") as session:
        session.goto("https://www.example.com")
        session.screenshot("screenshots/example.png")
        print("✓ Basic session complete")

    # Example 2: DNS leak test
    print("\nExample 2: DNS leak test")
    result = check_dns_leak("chrome-120")
    print(f"DNS leak test: {result['status']}")
    print(f"DNS servers: {len(result.get('dns_servers', []))}")

    # Example 3: Multi-account rotation
    print("\nExample 3: Profile rotation")
    rotator = ProfileRotator(["chrome-120", "firefox-115"], strategy="round-robin")

    for i, session in enumerate(rotator):
        if i >= 2:  # Test 2 rotations
            break
        with session:
            print(f"✓ Rotation {i + 1}: {session.profile.get('name')}")

    print("\n" + "=" * 50)
    print("All examples complete!")
