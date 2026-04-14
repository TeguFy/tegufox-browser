#!/usr/bin/env python3
"""
Configure DNS Leak Prevention for Tegufox Profiles

Applies DoH/DoT settings to Firefox/Camoufox profiles via preferences.
Supports multiple DoH providers (Cloudflare, Quad9, Mullvad, Google, NextDNS).

Usage:
    # Apply DNS config from profile JSON
    python scripts/configure-dns.py --profile profiles/chrome-120.json

    # Apply custom DoH provider
    python scripts/configure-dns.py --provider cloudflare --mode 3

    # Validate DNS configuration
    python scripts/configure-dns.py --validate

    # Test DNS leak prevention
    python scripts/configure-dns.py --test

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 3 Day 12
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import time

# DoH Provider Configuration
DOH_PROVIDERS = {
    "cloudflare": {
        "name": "Cloudflare",
        "uri": "https://mozilla.cloudflare-dns.com/dns-query",
        "bootstrap": "1.1.1.1",
        "bootstrap_ipv6": "2606:4700:4700::1111",
        "description": "Cloudflare DoH (fastest, 330+ PoPs, 99.99% uptime)",
        "privacy": "Good (24h log purge, GDPR compliant)",
        "jurisdiction": "USA (5 Eyes)",
        "speed": "12ms avg globally",
    },
    "cloudflare-no-log": {
        "name": "Cloudflare (No Logging)",
        "uri": "https://1.1.1.2/dns-query",
        "bootstrap": "1.1.1.2",
        "bootstrap_ipv6": "2606:4700:4700::1112",
        "description": "Cloudflare with malware blocking, no logging option",
        "privacy": "Good (same as cloudflare)",
        "jurisdiction": "USA (5 Eyes)",
        "speed": "12ms avg globally",
    },
    "quad9": {
        "name": "Quad9",
        "uri": "https://dns.quad9.net/dns-query",
        "bootstrap": "9.9.9.9",
        "bootstrap_ipv6": "2620:fe::fe",
        "description": "Quad9 (privacy-focused, Swiss jurisdiction, malware blocking)",
        "privacy": "Excellent (zero logging, non-profit, GDPR compliant)",
        "jurisdiction": "Switzerland (NOT in 5/9/14 Eyes)",
        "speed": "18ms avg globally",
    },
    "mullvad": {
        "name": "Mullvad DNS",
        "uri": "https://adblock.dns.mullvad.net/dns-query",
        "bootstrap": "194.242.2.2",
        "bootstrap_ipv6": "2a07:e340::2",
        "description": "Mullvad (extreme privacy, ad/tracker blocking)",
        "privacy": "Excellent (zero logging, Swedish jurisdiction)",
        "jurisdiction": "Sweden (strong privacy laws)",
        "speed": "35ms avg globally (smaller network)",
    },
    "mullvad-no-filter": {
        "name": "Mullvad DNS (No Filtering)",
        "uri": "https://dns.mullvad.net/dns-query",
        "bootstrap": "194.242.2.3",
        "bootstrap_ipv6": "2a07:e340::3",
        "description": "Mullvad without ad blocking",
        "privacy": "Excellent (zero logging)",
        "jurisdiction": "Sweden",
        "speed": "35ms avg globally",
    },
    "google": {
        "name": "Google Public DNS",
        "uri": "https://dns.google/dns-query",
        "bootstrap": "8.8.8.8",
        "bootstrap_ipv6": "2001:4860:4860::8888",
        "description": "Google Public DNS (reliable, but privacy concerns)",
        "privacy": "Poor (24-48h logging, permanent aggregation)",
        "jurisdiction": "USA (5 Eyes, Google data collection)",
        "speed": "15ms avg globally",
    },
}

# Browser-specific DoH provider mapping (for profile auto-detection)
BROWSER_DOH_MAPPING = {
    "chrome": "cloudflare",
    "firefox": "quad9",
    "safari": "cloudflare",
}

# TRR Mode explanations
TRR_MODES = {
    0: "Off (use system DNS, NO PROTECTION)",
    1: "Race mode (DoH + system DNS parallel, use fastest)",
    2: "Preferred (DoH first, fallback to system DNS)",
    3: "Strict (DoH ONLY, no fallback) ⭐ RECOMMENDED",
    5: "Off by choice (explicit disable)",
}


class DNSConfigurator:
    """Manage DNS configuration for Firefox/Camoufox profiles"""

    def __init__(self, profile_path: Optional[Path] = None, verbose: bool = True):
        """
        Initialize DNS configurator.

        Args:
            profile_path: Path to Firefox profile directory (optional)
            verbose: Print detailed output
        """
        self.profile_path = profile_path
        self.verbose = verbose

        if profile_path:
            self.prefs_path = profile_path / "prefs.js"
            self.user_js_path = profile_path / "user.js"

    def log(self, message: str, level: str = "INFO"):
        """Print log message if verbose"""
        if self.verbose:
            prefix = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅",
                "WARNING": "⚠️ ",
                "ERROR": "❌",
                "DEBUG": "🔍",
            }.get(level, "")
            print(f"{prefix} {message}")

    def get_doh_config(self, provider: str) -> Dict[str, Any]:
        """
        Get DoH configuration for provider.

        Args:
            provider: Provider name (cloudflare, quad9, mullvad, google)

        Returns:
            Provider configuration dict
        """
        if provider not in DOH_PROVIDERS:
            available = ", ".join(DOH_PROVIDERS.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return DOH_PROVIDERS[provider]

    def generate_preferences(
        self,
        provider: str = "cloudflare",
        mode: int = 3,
        disable_ipv6: bool = True,
        disable_webrtc: bool = True,
        disable_prefetch: bool = True,
        custom_uri: Optional[str] = None,
        custom_bootstrap: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate Firefox preferences for DNS leak prevention.

        Args:
            provider: DoH provider name
            mode: TRR mode (0-5, default: 3 = strict)
            disable_ipv6: Disable IPv6 to prevent leaks
            disable_webrtc: Disable WebRTC to prevent IP leaks
            disable_prefetch: Disable DNS prefetching
            custom_uri: Custom DoH URI (overrides provider)
            custom_bootstrap: Custom bootstrap IP (overrides provider)

        Returns:
            Dict of Firefox preferences
        """
        # Get provider config
        config = self.get_doh_config(provider)

        # Use custom values if provided
        doh_uri = custom_uri or config["uri"]
        bootstrap_ip = custom_bootstrap or config["bootstrap"]

        preferences = {}

        # Core TRR Settings
        preferences["network.trr.mode"] = mode
        preferences["network.trr.uri"] = doh_uri

        if mode == 3:
            # Mode 3 (strict) requires bootstrap address
            preferences["network.trr.bootstrapAddress"] = bootstrap_ip
            preferences["network.trr.strict_native_fallback"] = True

        # TRR Behavior
        preferences["network.trr.max_fails"] = 5
        preferences["network.trr.request_timeout_ms"] = 3000
        preferences["network.trr.request_timeout_mode_trronly_ms"] = 5000
        preferences["network.trr.early-AAAA"] = True
        preferences["network.trr.wait-for-A-and-AAAA"] = True

        # Privacy Settings
        preferences["network.trr.disable-ECS"] = True  # Disable EDNS Client Subnet
        preferences["network.trr.split_horizon_mitigations"] = True

        # Validation
        preferences["network.trr.confirmationNS"] = "example.com"
        preferences["network.trr.mode-cname-check"] = True

        # Exclusions (empty by default)
        preferences["network.trr.excluded-domains"] = ""
        preferences["network.trr.builtin-excluded-domains"] = "localhost,local"

        # IPv6 Settings
        if disable_ipv6:
            preferences["network.dns.disableIPv6"] = True
            preferences["network.dns.disablePrefetchFromHTTPS"] = True
        else:
            preferences["network.dns.disableIPv6"] = False
            # If IPv6 enabled, add IPv6 bootstrap
            if "bootstrap_ipv6" in config:
                preferences["network.trr.bootstrapAddress"] = (
                    f"{bootstrap_ip},{config['bootstrap_ipv6']}"
                )

        # DNS Prefetching
        if disable_prefetch:
            preferences["network.dns.disablePrefetch"] = True
            preferences["network.prefetch-next"] = False
            preferences["network.http.speculative-parallel-limit"] = 0

        # WebRTC Settings
        if disable_webrtc:
            # Complete WebRTC disable (nuclear option)
            preferences["media.peerconnection.enabled"] = False
            preferences["media.navigator.enabled"] = False
            preferences["media.getusermedia.screensharing.enabled"] = False
        else:
            # Partial WebRTC (mDNS obfuscation)
            preferences["media.peerconnection.enabled"] = True
            preferences["media.peerconnection.ice.default_address_only"] = True
            preferences["media.peerconnection.ice.no_host"] = True
            preferences["media.peerconnection.ice.obfuscate_host_addresses"] = True
            preferences["media.peerconnection.ice.proxy_only_if_behind_proxy"] = True

        # Additional Privacy
        preferences["network.dns.blockDotOnion"] = True  # Block .onion (Tor safety)

        return preferences

    def write_user_js(self, preferences: Dict[str, Any], backup: bool = True):
        """
        Write preferences to user.js file.

        user.js is preferred over prefs.js because:
        - Applied on every Firefox startup
        - User can't accidentally change via about:config
        - Clean separation from browser-generated prefs

        Args:
            preferences: Dict of preference name -> value
            backup: Create backup of existing user.js
        """
        if not self.profile_path:
            raise ValueError("Profile path not set")

        # Backup existing user.js
        if backup and self.user_js_path.exists():
            backup_path = self.user_js_path.with_suffix(".js.backup")
            self.log(f"Backing up existing user.js to {backup_path.name}")
            self.user_js_path.rename(backup_path)

        # Generate user.js content
        lines = [
            "// Tegufox Browser Toolkit - DNS Leak Prevention",
            "// Auto-generated by configure-dns.py",
            f"// Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "// DO NOT EDIT MANUALLY - Changes will be overwritten",
            "",
            "// ========================================",
            "// DNS LEAK PREVENTION CONFIGURATION",
            "// ========================================",
            "",
        ]

        # Group preferences by category
        trr_prefs = []
        dns_prefs = []
        webrtc_prefs = []
        other_prefs = []

        for key, value in sorted(preferences.items()):
            # Format value
            if isinstance(value, bool):
                js_value = "true" if value else "false"
            elif isinstance(value, str):
                js_value = f'"{value}"'
            elif isinstance(value, int):
                js_value = str(value)
            else:
                js_value = json.dumps(value)

            pref_line = f'user_pref("{key}", {js_value});'

            # Categorize
            if key.startswith("network.trr"):
                trr_prefs.append(pref_line)
            elif key.startswith("network.dns"):
                dns_prefs.append(pref_line)
            elif key.startswith("media."):
                webrtc_prefs.append(pref_line)
            else:
                other_prefs.append(pref_line)

        # Write categorized preferences
        if trr_prefs:
            lines.append("// --- TRR (Trusted Recursive Resolver) Settings ---")
            lines.extend(trr_prefs)
            lines.append("")

        if dns_prefs:
            lines.append("// --- DNS Settings ---")
            lines.extend(dns_prefs)
            lines.append("")

        if webrtc_prefs:
            lines.append("// --- WebRTC Leak Prevention ---")
            lines.extend(webrtc_prefs)
            lines.append("")

        if other_prefs:
            lines.append("// --- Other Privacy Settings ---")
            lines.extend(other_prefs)
            lines.append("")

        # Write to file
        content = "\n".join(lines)
        self.user_js_path.write_text(content)

        self.log(
            f"✅ Wrote {len(preferences)} preferences to {self.user_js_path}", "SUCCESS"
        )

    def apply_from_profile_json(self, profile_json_path: Path):
        """
        Apply DNS config from Tegufox profile JSON.

        Args:
            profile_json_path: Path to profile JSON file
        """
        self.log(f"Loading profile: {profile_json_path}")

        with open(profile_json_path) as f:
            profile = json.load(f)

        # Extract DNS config
        dns_config = profile.get("dns_config", {})

        if not dns_config.get("enabled", True):
            self.log("⚠️  DNS config disabled in profile, skipping", "WARNING")
            return

        # Get provider
        provider = dns_config.get("provider", "cloudflare")

        # Get DoH settings
        doh = dns_config.get("doh", {})
        mode = doh.get("mode", 3)
        custom_uri = doh.get("uri")
        custom_bootstrap = doh.get("bootstrap_address")

        # Get feature flags
        disable_ipv6 = not dns_config.get("ipv6", {}).get("enabled", False)
        disable_webrtc = not dns_config.get("webrtc", {}).get("enabled", False)
        disable_prefetch = not dns_config.get("prefetch", {}).get("dns_prefetch", True)

        self.log(f"Provider: {provider} (TRR mode {mode})")
        self.log(f"IPv6: {'Disabled' if disable_ipv6 else 'Enabled'}")
        self.log(
            f"WebRTC: {'Disabled' if disable_webrtc else 'Enabled (mDNS obfuscation)'}"
        )

        # Generate preferences
        preferences = self.generate_preferences(
            provider=provider,
            mode=mode,
            disable_ipv6=disable_ipv6,
            disable_webrtc=disable_webrtc,
            disable_prefetch=disable_prefetch,
            custom_uri=custom_uri,
            custom_bootstrap=custom_bootstrap,
        )

        # Write to user.js
        if self.profile_path:
            self.write_user_js(preferences)
        else:
            # Print preferences (no profile path)
            self.log("\nGenerated Preferences:")
            for key, value in sorted(preferences.items()):
                print(f"  {key} = {value}")

    def validate_config(self) -> Dict[str, Any]:
        """
        Validate DNS configuration in Firefox profile.

        Returns:
            Dict with validation results
        """
        if not self.profile_path:
            raise ValueError("Profile path not set, cannot validate")

        if not self.user_js_path.exists() and not self.prefs_path.exists():
            return {
                "status": "error",
                "message": "No preferences file found (user.js or prefs.js)",
            }

        # Read preferences from user.js (preferred) or prefs.js
        prefs_file = (
            self.user_js_path if self.user_js_path.exists() else self.prefs_path
        )

        self.log(f"Reading preferences from {prefs_file.name}")

        # Parse preferences (simple regex-based parsing)
        import re

        content = prefs_file.read_text()
        pref_pattern = r'user_pref\("([^"]+)",\s*(.+?)\);'

        prefs = {}
        for match in re.finditer(pref_pattern, content):
            key = match.group(1)
            value_str = match.group(2)

            # Parse value
            if value_str == "true":
                value = True
            elif value_str == "false":
                value = False
            elif value_str.startswith('"') and value_str.endswith('"'):
                value = value_str[1:-1]  # String
            else:
                try:
                    value = int(value_str)
                except ValueError:
                    value = value_str

            prefs[key] = value

        # Validate critical settings
        validation = {
            "status": "valid",
            "provider": "unknown",
            "mode": prefs.get("network.trr.mode", 0),
            "issues": [],
            "warnings": [],
        }

        # Check TRR mode
        mode = prefs.get("network.trr.mode", 0)
        if mode == 0:
            validation["issues"].append(
                "TRR disabled (mode 0) - NO DNS LEAK PROTECTION"
            )
        elif mode == 1 or mode == 2:
            validation["warnings"].append(
                f"TRR mode {mode} - fallback to system DNS possible"
            )
        elif mode == 3:
            validation["provider"] = "strict"
            # Mode 3 requires bootstrap address
            if "network.trr.bootstrapAddress" not in prefs:
                validation["issues"].append(
                    "TRR mode 3 requires network.trr.bootstrapAddress"
                )

        # Detect provider from URI
        uri = prefs.get("network.trr.uri", "")
        if "cloudflare" in uri:
            validation["provider"] = "cloudflare"
        elif "quad9" in uri:
            validation["provider"] = "quad9"
        elif "mullvad" in uri:
            validation["provider"] = "mullvad"
        elif "google" in uri:
            validation["provider"] = "google"

        # Check IPv6
        if not prefs.get("network.dns.disableIPv6", False):
            validation["warnings"].append("IPv6 enabled - potential IPv6 leak")

        # Check WebRTC
        if prefs.get("media.peerconnection.enabled", True):
            validation["warnings"].append("WebRTC enabled - potential IP leak")

        # Overall status
        if validation["issues"]:
            validation["status"] = "invalid"
        elif validation["warnings"]:
            validation["status"] = "warnings"

        return validation

    def print_validation_report(self, validation: Dict[str, Any]):
        """Print validation report"""
        status = validation["status"]

        if status == "valid":
            self.log("✅ DNS configuration is VALID", "SUCCESS")
        elif status == "warnings":
            self.log("⚠️  DNS configuration has warnings", "WARNING")
        else:
            self.log("❌ DNS configuration is INVALID", "ERROR")

        print(f"\n📊 Validation Report:")
        print(f"  Status: {status.upper()}")
        print(
            f"  TRR Mode: {validation['mode']} ({TRR_MODES.get(validation['mode'], 'Unknown')})"
        )
        print(f"  Provider: {validation['provider']}")

        if validation["issues"]:
            print(f"\n❌ Issues ({len(validation['issues'])}):")
            for issue in validation["issues"]:
                print(f"  - {issue}")

        if validation["warnings"]:
            print(f"\n⚠️  Warnings ({len(validation['warnings'])}):")
            for warning in validation["warnings"]:
                print(f"  - {warning}")

    def test_dns_leak(self) -> Dict[str, Any]:
        """
        Test for DNS leaks (basic validation without browser).

        For full testing, use test_dns_leak.py with Playwright.

        Returns:
            Dict with test results
        """
        self.log("🧪 Testing DNS leak prevention...")

        results = {"status": "unknown", "tests": {}}

        # Test 1: Validate user.js exists and has DoH config
        if not self.profile_path:
            results["status"] = "error"
            results["message"] = "No profile path set"
            return results

        validation = self.validate_config()
        results["tests"]["config_validation"] = validation

        if validation["status"] == "invalid":
            results["status"] = "failed"
            results["message"] = "Invalid DNS configuration"
            return results

        # Test 2: Check for system DNS queries (requires tcpdump, advanced)
        self.log(
            "⚠️  Full DNS leak testing requires browser. Use test_dns_leak.py", "WARNING"
        )
        self.log("   Recommended tests:")
        self.log("   1. Visit https://www.dnsleaktest.com")
        self.log("   2. Visit https://ipleak.net (WebRTC test)")
        self.log("   3. Visit https://test-ipv6.com (IPv6 test)")

        results["status"] = "partial"
        results["message"] = "Config validated, manual testing recommended"

        return results


def list_providers():
    """Print list of available DoH providers"""
    print("\n📋 Available DoH Providers:\n")

    for key, provider in DOH_PROVIDERS.items():
        print(f"  {key}")
        print(f"    Name: {provider['name']}")
        print(f"    URI: {provider['uri']}")
        print(f"    Bootstrap: {provider['bootstrap']}")
        print(f"    Privacy: {provider['privacy']}")
        print(f"    Jurisdiction: {provider['jurisdiction']}")
        print(f"    Speed: {provider['speed']}")
        print(f"    Description: {provider['description']}")
        print()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Configure DNS leak prevention for Tegufox profiles",
        epilog="""
Examples:
  # Apply DNS config from profile JSON
  python configure-dns.py --profile profiles/chrome-120.json
  
  # Apply Cloudflare DoH in strict mode (mode 3)
  python configure-dns.py --provider cloudflare --mode 3 --profile-dir ~/.camoufox
  
  # Validate existing configuration
  python configure-dns.py --validate --profile-dir ~/.camoufox
  
  # List available providers
  python configure-dns.py --list-providers
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--profile", type=Path, help="Path to Tegufox profile JSON file"
    )

    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Path to Firefox/Camoufox profile directory (for direct config)",
    )

    parser.add_argument(
        "--provider", choices=list(DOH_PROVIDERS.keys()), help="DoH provider name"
    )

    parser.add_argument(
        "--mode",
        type=int,
        choices=[0, 1, 2, 3, 5],
        default=3,
        help="TRR mode (0=off, 1=race, 2=preferred, 3=strict, 5=explicit-off). Default: 3",
    )

    parser.add_argument(
        "--custom-uri", type=str, help="Custom DoH URI (overrides provider)"
    )

    parser.add_argument(
        "--custom-bootstrap",
        type=str,
        help="Custom bootstrap IP address (overrides provider)",
    )

    parser.add_argument(
        "--enable-ipv6",
        action="store_true",
        help="Enable IPv6 (default: disabled to prevent leaks)",
    )

    parser.add_argument(
        "--enable-webrtc",
        action="store_true",
        help="Enable WebRTC with mDNS obfuscation (default: disabled)",
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate existing DNS configuration"
    )

    parser.add_argument(
        "--test", action="store_true", help="Test for DNS leaks (basic validation)"
    )

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available DoH providers and exit",
    )

    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    # List providers and exit
    if args.list_providers:
        list_providers()
        return 0

    # Initialize configurator
    configurator = DNSConfigurator(
        profile_path=args.profile_dir, verbose=not args.quiet
    )

    # Validate mode
    if args.validate:
        if not args.profile_dir:
            print("❌ Error: --profile-dir required for validation")
            return 1

        validation = configurator.validate_config()
        configurator.print_validation_report(validation)
        return 0 if validation["status"] != "invalid" else 1

    # Test mode
    if args.test:
        if not args.profile_dir:
            print("❌ Error: --profile-dir required for testing")
            return 1

        results = configurator.test_dns_leak()
        print(f"\n🧪 Test Results: {results['status'].upper()}")
        print(f"   {results['message']}")
        return 0

    # Apply from profile JSON
    if args.profile:
        if not args.profile.exists():
            print(f"❌ Error: Profile not found: {args.profile}")
            return 1

        configurator.apply_from_profile_json(args.profile)

        # If profile_dir provided, write to that directory
        if args.profile_dir:
            configurator.profile_path = args.profile_dir
            configurator.user_js_path = args.profile_dir / "user.js"

            # Re-apply to profile directory
            configurator.apply_from_profile_json(args.profile)

        return 0

    # Apply from CLI arguments
    if args.provider:
        if not args.profile_dir:
            print("❌ Error: --profile-dir required when using --provider")
            return 1

        # Generate preferences
        preferences = configurator.generate_preferences(
            provider=args.provider,
            mode=args.mode,
            disable_ipv6=not args.enable_ipv6,
            disable_webrtc=not args.enable_webrtc,
            disable_prefetch=True,
            custom_uri=args.custom_uri,
            custom_bootstrap=args.custom_bootstrap,
        )

        # Write to user.js
        configurator.write_user_js(preferences)

        print(f"\n✅ Successfully configured {args.provider} DoH (mode {args.mode})")
        print(f"   Profile: {args.profile_dir}")
        print(f"\n   Next steps:")
        print(f"   1. Restart Firefox/Camoufox")
        print(f"   2. Visit https://www.dnsleaktest.com to verify")
        print(f"   3. Visit https://ipleak.net to check WebRTC")

        return 0

    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
