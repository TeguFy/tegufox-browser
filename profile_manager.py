#!/usr/bin/env python3
"""
Tegufox Profile Manager Library

Core library for managing Tegufox browser profiles with validation,
template generation, and bulk operations.

Features:
- Profile CRUD operations (create, read, update, delete)
- Validation system (TLS+HTTP/2+DNS consistency checks)
- Template generator (browser fingerprint presets)
- Bulk operations (import/export, clone, merge)
- Integration with configure-dns.py
- Profile search and filtering

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 3 Day 14
License: MIT
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import copy

# Profile templates and validation data
BROWSER_TEMPLATES = {
    "chrome-120": {
        "name": "Chrome 120 on Windows 11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "vendor": "Google Inc.",
        "platform": "Win32",
        "doh_provider": "cloudflare",
        "ja3": "579ccef312d18482fc42e2b822ca2430",
        "pseudo_header_order": ["method", "authority", "scheme", "path"],
    },
    "firefox-115": {
        "name": "Firefox 115 ESR on Windows 11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "vendor": "",
        "platform": "Win32",
        "doh_provider": "quad9",
        "ja3": "de350869b8c85de67a350c8d186f11e6",
        "pseudo_header_order": ["method", "path", "authority", "scheme"],
    },
    "safari-17": {
        "name": "Safari 17 on macOS Sonoma",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "vendor": "Apple Computer, Inc.",
        "platform": "MacIntel",
        "doh_provider": "cloudflare",
        "ja3": "66818e4f5f48d10b27e4892c00347c3f",
        "pseudo_header_order": ["method", "scheme", "authority", "path"],
    },
}

DOH_PROVIDERS = {
    "cloudflare": {
        "uri": "https://mozilla.cloudflare-dns.com/dns-query",
        "bootstrap": "1.1.1.1",
    },
    "quad9": {
        "uri": "https://dns.quad9.net/dns-query",
        "bootstrap": "9.9.9.9",
    },
    "mullvad": {
        "uri": "https://adblock.dns.mullvad.net/dns-query",
        "bootstrap": "194.242.2.2",
    },
}


class ValidationLevel(Enum):
    """Profile validation levels"""

    BASIC = "basic"  # Basic structure validation
    STANDARD = "standard"  # + fingerprint consistency
    STRICT = "strict"  # + cross-layer validation


@dataclass
class ValidationResult:
    """Profile validation result"""

    valid: bool
    level: ValidationLevel
    errors: List[str]
    warnings: List[str]
    score: float  # 0.0 - 1.0

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "level": self.level.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
        }


class ProfileManager:
    """
    Manages Tegufox browser profiles with validation and templates.

    Example:
        manager = ProfileManager("profiles/")

        # Create profile from template
        profile = manager.create_from_template("chrome-120", "my-profile")

        # Validate profile
        result = manager.validate(profile)

        # Save profile
        manager.save(profile, "my-profile")
    """

    def __init__(self, profiles_dir: str = "profiles"):
        """
        Initialize ProfileManager

        Args:
            profiles_dir: Directory containing profile JSON files
        """
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    # CRUD Operations

    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create new profile from scratch

        Args:
            name: Profile name
            **kwargs: Profile properties

        Returns:
            New profile dict
        """
        profile = {
            "name": name,
            "description": kwargs.get("description", f"Custom profile: {name}"),
            "created": time.strftime("%Y-%m-%d"),
            "version": "1.0",
            "screen": kwargs.get(
                "screen",
                {
                    "width": 1920,
                    "height": 1080,
                    "availWidth": 1920,
                    "availHeight": 1040,
                    "colorDepth": 24,
                    "pixelDepth": 24,
                },
            ),
            "navigator": kwargs.get(
                "navigator",
                {
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "platform": "Win32",
                    "hardwareConcurrency": 8,
                    "deviceMemory": 8,
                    "maxTouchPoints": 0,
                    "vendor": "",
                    "language": "en-US",
                    "languages": ["en-US", "en"],
                },
            ),
        }

        # Add optional sections
        if "tls" in kwargs:
            profile["tls"] = kwargs["tls"]
        if "http2" in kwargs:
            profile["http2"] = kwargs["http2"]
        if "webgl" in kwargs:
            profile["webgl"] = kwargs["webgl"]
        if "canvas" in kwargs:
            profile["canvas"] = kwargs["canvas"]
        if "dns_config" in kwargs:
            profile["dns_config"] = kwargs["dns_config"]
        if "firefox_preferences" in kwargs:
            profile["firefox_preferences"] = kwargs["firefox_preferences"]

        return profile

    def create_from_template(
        self, template: str, name: str, **overrides
    ) -> Dict[str, Any]:
        """
        Create profile from browser template

        Args:
            template: Template name ("chrome-120", "firefox-115", "safari-17")
            name: Profile name
            **overrides: Override template values

        Returns:
            New profile dict
        """
        if template not in BROWSER_TEMPLATES:
            raise ValueError(
                f"Unknown template: {template}. Available: {list(BROWSER_TEMPLATES.keys())}"
            )

        template_data = BROWSER_TEMPLATES[template]

        # Load full template from existing profile if available
        template_file = self.profiles_dir / f"{template}.json"
        if template_file.exists():
            with open(template_file, "r") as f:
                base_profile = json.load(f)
        else:
            # Create minimal profile from template data
            base_profile = {
                "name": name,
                "description": template_data["name"],
                "created": time.strftime("%Y-%m-%d"),
                "version": "1.0",
                "navigator": {
                    "userAgent": template_data["user_agent"],
                    "vendor": template_data["vendor"],
                    "platform": template_data["platform"],
                },
            }

        # Clone and update name
        profile = copy.deepcopy(base_profile)
        profile["name"] = name

        # Apply overrides
        for key, value in overrides.items():
            if (
                isinstance(value, dict)
                and key in profile
                and isinstance(profile[key], dict)
            ):
                profile[key].update(value)
            else:
                profile[key] = value

        return profile

    def load(self, name: str) -> Dict[str, Any]:
        """
        Load profile from file

        Args:
            name: Profile name (without .json extension)

        Returns:
            Profile dict
        """
        profile_file = self.profiles_dir / f"{name}.json"

        if not profile_file.exists():
            raise FileNotFoundError(f"Profile not found: {profile_file}")

        with open(profile_file, "r") as f:
            return json.load(f)

    def save(self, profile: Dict[str, Any], name: Optional[str] = None) -> Path:
        """
        Save profile to file

        Args:
            profile: Profile dict
            name: Optional profile name (default: use profile["name"])

        Returns:
            Path to saved file
        """
        name = name or profile.get("name", "unnamed")
        profile_file = self.profiles_dir / f"{name}.json"

        with open(profile_file, "w") as f:
            json.dump(profile, f, indent=2)

        return profile_file

    def delete(self, name: str) -> bool:
        """
        Delete profile

        Args:
            name: Profile name

        Returns:
            True if deleted, False if not found
        """
        profile_file = self.profiles_dir / f"{name}.json"

        if profile_file.exists():
            profile_file.unlink()
            return True
        return False

    def list(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all profiles

        Args:
            pattern: Optional glob pattern (e.g., "chrome-*")

        Returns:
            List of profile names
        """
        if pattern:
            files = self.profiles_dir.glob(f"{pattern}.json")
        else:
            files = self.profiles_dir.glob("*.json")

        return sorted([f.stem for f in files])

    def exists(self, name: str) -> bool:
        """Check if profile exists"""
        return (self.profiles_dir / f"{name}.json").exists()

    # Validation

    def validate(
        self, profile: Dict[str, Any], level: ValidationLevel = ValidationLevel.STANDARD
    ) -> ValidationResult:
        """
        Validate profile structure and consistency

        Args:
            profile: Profile dict to validate
            level: Validation level

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        score = 1.0

        # BASIC: Required fields
        required_fields = ["name", "navigator"]
        for field in required_fields:
            if field not in profile:
                errors.append(f"Missing required field: {field}")
                score -= 0.2

        # Check navigator fields
        if "navigator" in profile:
            nav = profile["navigator"]
            if "userAgent" not in nav:
                errors.append("Missing navigator.userAgent")
                score -= 0.1
            if "platform" not in nav:
                warnings.append("Missing navigator.platform")
                score -= 0.05

        if level in (ValidationLevel.STANDARD, ValidationLevel.STRICT):
            # Check TLS + HTTP/2 consistency
            if "tls" in profile and "http2" in profile:
                tls = profile["tls"]
                http2 = profile["http2"]

                # Check ALPN includes h2
                alpn = tls.get("extensions", {}).get("alpn", [])
                if "h2" not in alpn:
                    warnings.append("TLS ALPN missing 'h2' for HTTP/2")
                    score -= 0.05

            # Check DNS configuration
            if "dns_config" in profile:
                dns = profile["dns_config"]
                if dns.get("enabled") and "doh" not in dns:
                    errors.append("DNS config enabled but missing DoH settings")
                    score -= 0.1

                # Check DoH provider alignment
                provider = dns.get("provider", "")
                profile_name = profile.get("name", "").lower()

                expected_provider = None
                if "chrome" in profile_name:
                    expected_provider = "cloudflare"
                elif "firefox" in profile_name:
                    expected_provider = "quad9"
                elif "safari" in profile_name:
                    expected_provider = "cloudflare"

                if expected_provider and provider != expected_provider:
                    warnings.append(
                        f"DoH provider mismatch: {profile_name} should use {expected_provider}, "
                        f"but uses {provider}"
                    )
                    score -= 0.05

            # Check fingerprint hashes present
            if "fingerprints" in profile:
                fp = profile["fingerprints"]
                if "ja3" not in fp:
                    warnings.append("Missing JA3 fingerprint hash")
                    score -= 0.05

        if level == ValidationLevel.STRICT:
            # Cross-layer validation

            # Check HTTP/2 pseudo-header order matches browser
            if "http2" in profile:
                http2 = profile["http2"]
                pseudo_order = http2.get("pseudo_header_order", [])
                profile_name = profile.get("name", "").lower()

                expected_order = None
                if "chrome" in profile_name:
                    expected_order = ["method", "authority", "scheme", "path"]
                elif "firefox" in profile_name:
                    expected_order = ["method", "path", "authority", "scheme"]
                elif "safari" in profile_name:
                    expected_order = ["method", "scheme", "authority", "path"]

                if expected_order and pseudo_order != expected_order:
                    errors.append(
                        f"HTTP/2 pseudo-header order mismatch: expected {expected_order}, "
                        f"got {pseudo_order}"
                    )
                    score -= 0.1

            # Check User-Agent consistency
            if "navigator" in profile:
                ua = profile["navigator"].get("userAgent", "")
                vendor = profile["navigator"].get("vendor", "")

                if "Chrome" in ua and vendor != "Google Inc.":
                    errors.append(f"User-Agent claims Chrome but vendor is '{vendor}'")
                    score -= 0.1

                if "Firefox" in ua and vendor != "":
                    errors.append(
                        f"User-Agent claims Firefox but vendor is '{vendor}' (should be empty)"
                    )
                    score -= 0.1

                if "Safari" in ua and "Apple" not in vendor:
                    errors.append(f"User-Agent claims Safari but vendor is '{vendor}'")
                    score -= 0.1

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        return ValidationResult(
            valid=len(errors) == 0,
            level=level,
            errors=errors,
            warnings=warnings,
            score=score,
        )

    # Bulk Operations

    def clone(self, source: str, destination: str, **overrides) -> Dict[str, Any]:
        """
        Clone existing profile with optional overrides

        Args:
            source: Source profile name
            destination: Destination profile name
            **overrides: Override values

        Returns:
            Cloned profile dict
        """
        profile = self.load(source)
        profile = copy.deepcopy(profile)

        # Update name
        profile["name"] = destination

        # Update creation date
        profile["created"] = time.strftime("%Y-%m-%d")

        # Apply overrides
        for key, value in overrides.items():
            if (
                isinstance(value, dict)
                and key in profile
                and isinstance(profile[key], dict)
            ):
                profile[key].update(value)
            else:
                profile[key] = value

        return profile

    def merge(self, base: str, overlay: str, name: str) -> Dict[str, Any]:
        """
        Merge two profiles (overlay overwrites base)

        Args:
            base: Base profile name
            overlay: Overlay profile name
            name: Merged profile name

        Returns:
            Merged profile dict
        """
        base_profile = self.load(base)
        overlay_profile = self.load(overlay)

        # Deep merge
        merged = copy.deepcopy(base_profile)

        def deep_merge(base_dict: Dict, overlay_dict: Dict):
            """Recursively merge overlay into base"""
            for key, value in overlay_dict.items():
                if (
                    key in base_dict
                    and isinstance(base_dict[key], dict)
                    and isinstance(value, dict)
                ):
                    deep_merge(base_dict[key], value)
                else:
                    base_dict[key] = value

        deep_merge(merged, overlay_profile)

        # Update name
        merged["name"] = name
        merged["created"] = time.strftime("%Y-%m-%d")

        return merged

    def export_bulk(self, names: List[str], output_file: str) -> None:
        """
        Export multiple profiles to single JSON file

        Args:
            names: List of profile names
            output_file: Output file path
        """
        profiles = {}
        for name in names:
            try:
                profiles[name] = self.load(name)
            except FileNotFoundError:
                print(f"Warning: Profile not found: {name}")

        with open(output_file, "w") as f:
            json.dump(profiles, f, indent=2)

    def import_bulk(self, input_file: str, overwrite: bool = False) -> List[str]:
        """
        Import multiple profiles from single JSON file

        Args:
            input_file: Input file path
            overwrite: Overwrite existing profiles

        Returns:
            List of imported profile names
        """
        with open(input_file, "r") as f:
            profiles = json.load(f)

        imported = []
        for name, profile in profiles.items():
            if not overwrite and self.exists(name):
                print(f"Skipping existing profile: {name}")
                continue

            self.save(profile, name)
            imported.append(name)

        return imported

    # Template Generation

    def generate_template(
        self,
        browser: str,
        os: str,
        screen_width: int = 1920,
        screen_height: int = 1080,
        doh_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate profile template for specific browser/OS

        Args:
            browser: Browser type ("chrome-120", "firefox-115", "safari-17")
            os: Operating system ("windows", "macos", "linux")
            screen_width: Screen width
            screen_height: Screen height
            doh_provider: DoH provider (auto-detected if None)

        Returns:
            Generated profile dict
        """
        if browser not in BROWSER_TEMPLATES:
            raise ValueError(f"Unknown browser: {browser}")

        template = BROWSER_TEMPLATES[browser]

        # Auto-detect DoH provider
        if doh_provider is None:
            doh_provider = template["doh_provider"]

        if doh_provider not in DOH_PROVIDERS:
            raise ValueError(f"Unknown DoH provider: {doh_provider}")

        doh_config = DOH_PROVIDERS[doh_provider]

        # Generate profile name
        profile_name = f"{browser}-{os}-{int(time.time())}"

        # Create profile from template
        profile = self.create_from_template(browser, profile_name)

        # Ensure screen section exists
        if "screen" not in profile:
            profile["screen"] = {}

        # Update screen dimensions
        profile["screen"]["width"] = screen_width
        profile["screen"]["height"] = screen_height
        profile["screen"]["availWidth"] = screen_width
        profile["screen"]["availHeight"] = screen_height - 40  # Task bar

        # Update DoH config
        if "dns_config" not in profile:
            profile["dns_config"] = {}

        profile["dns_config"].update(
            {
                "enabled": True,
                "provider": doh_provider,
                "doh": {
                    "uri": doh_config["uri"],
                    "bootstrap_address": doh_config["bootstrap"],
                    "mode": 3,
                    "strict_fallback": True,
                    "disable_ecs": True,
                },
            }
        )

        return profile

    # Search and Filter

    def search(self, query: str) -> List[str]:
        """
        Search profiles by name, description, or browser type

        Args:
            query: Search query

        Returns:
            List of matching profile names
        """
        matches = []
        query_lower = query.lower()

        for name in self.list():
            try:
                profile = self.load(name)

                # Search in name
                if query_lower in name.lower():
                    matches.append(name)
                    continue

                # Search in description
                if (
                    "description" in profile
                    and query_lower in profile["description"].lower()
                ):
                    matches.append(name)
                    continue

                # Search in user agent
                if "navigator" in profile:
                    ua = profile["navigator"].get("userAgent", "")
                    if query_lower in ua.lower():
                        matches.append(name)
                        continue

            except Exception:
                continue

        return matches

    def filter_by_browser(self, browser: str) -> List[str]:
        """
        Filter profiles by browser type

        Args:
            browser: Browser type ("chrome", "firefox", "safari")

        Returns:
            List of matching profile names
        """
        return self.search(browser)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get profile statistics

        Returns:
            Stats dict
        """
        all_profiles = self.list()

        browser_counts = {
            "chrome": 0,
            "firefox": 0,
            "safari": 0,
            "other": 0,
        }

        validation_stats = {
            "valid": 0,
            "invalid": 0,
            "avg_score": 0.0,
        }

        total_score = 0.0

        for name in all_profiles:
            try:
                profile = self.load(name)

                # Count by browser
                name_lower = name.lower()
                if "chrome" in name_lower:
                    browser_counts["chrome"] += 1
                elif "firefox" in name_lower:
                    browser_counts["firefox"] += 1
                elif "safari" in name_lower:
                    browser_counts["safari"] += 1
                else:
                    browser_counts["other"] += 1

                # Validate
                result = self.validate(profile, ValidationLevel.STANDARD)
                if result.valid:
                    validation_stats["valid"] += 1
                else:
                    validation_stats["invalid"] += 1

                total_score += result.score

            except Exception:
                validation_stats["invalid"] += 1

        if all_profiles:
            validation_stats["avg_score"] = total_score / len(all_profiles)

        return {
            "total_profiles": len(all_profiles),
            "browser_counts": browser_counts,
            "validation": validation_stats,
        }


# Utility functions


def validate_profile_file(
    profile_path: str, level: str = "standard"
) -> ValidationResult:
    """
    Validate profile file

    Args:
        profile_path: Path to profile JSON file
        level: Validation level ("basic", "standard", "strict")

    Returns:
        ValidationResult
    """
    manager = ProfileManager()

    with open(profile_path, "r") as f:
        profile = json.load(f)

    validation_level = ValidationLevel(level)
    return manager.validate(profile, validation_level)


if __name__ == "__main__":
    # Example usage
    print("Tegufox Profile Manager Library")
    print("=" * 60)

    manager = ProfileManager("profiles/")

    # List profiles
    print("\nAvailable profiles:")
    for name in manager.list():
        print(f"  - {name}")

    # Get stats
    print("\nProfile statistics:")
    stats = manager.get_stats()
    print(f"  Total profiles: {stats['total_profiles']}")
    print(f"  Browser counts: {stats['browser_counts']}")
    print(f"  Validation: {stats['validation']}")

    # Validate a profile
    if manager.exists("chrome-120"):
        print("\nValidating chrome-120 profile:")
        profile = manager.load("chrome-120")
        result = manager.validate(profile, ValidationLevel.STRICT)
        print(f"  Valid: {result.valid}")
        print(f"  Score: {result.score:.2f}")
        if result.errors:
            print(f"  Errors: {result.errors}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")
