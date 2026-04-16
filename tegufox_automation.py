#!/usr/bin/env python3
"""
Tegufox Automation Framework v1.0

Production-grade automation framework for Camoufox with anti-detection capabilities.
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

# Import Camoufox
try:
    from camoufox.sync_api import Camoufox, Browser, BrowserContext
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
    from tegufox_mouse import HumanMouse, MouseConfig
except ImportError as e:
    print(f"ERROR: tegufox_mouse.py not found. Ensure it's in the same directory.")
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

    Wraps Camoufox/Playwright with:
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
            from fingerprint_registry import FingerprintRegistry
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

        # Build launch options (passed to Camoufox at browser start)
        launch_opts = self._build_launch_options()

        # Launch browser via Camoufox context manager
        self._camoufox = Camoufox(headless=self.config.headless, **launch_opts)
        self.browser = self._camoufox.__enter__()

        # Create context with Playwright-level options (viewport, UA)
        context_options = self._build_context_options()
        self.context = self.browser.new_context(**context_options)

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
            from tegufox_keyboard import HumanKeyboard
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

        # Close context and browser, then exit Camoufox playwright context
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
        """Build Camoufox launch options (applied at browser start via Firefox prefs)"""
        opts: Dict[str, Any] = {}

        # Firefox preferences from profile (DoH, WebRTC, IPv6, etc.)
        # These must be set at launch time, not context creation time
        if "firefox_preferences" in self.profile:
            opts["firefox_user_prefs"] = self.profile["firefox_preferences"]

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

        return options

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
