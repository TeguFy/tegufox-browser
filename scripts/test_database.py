#!/usr/bin/env python3
"""
Test database operations and verify data integrity
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tegufox_core.database import ProfileDatabase
from tegufox_core.profile_manager import ProfileManager
import json


def test_database_operations():
    """Test all database operations"""
    
    print("=" * 60)
    print("Testing Tegufox Profile Database")
    print("=" * 60)
    
    # Initialize
    db = ProfileDatabase()
    manager = ProfileManager()
    
    print(f"\n✓ Database: {db.db_path}")
    print(f"✓ ProfileManager initialized")
    
    # Test 1: List profiles
    print("\n[Test 1] List all profiles")
    profiles = manager.list()
    print(f"  Found {len(profiles)} profiles:")
    for name in profiles:
        print(f"    - {name}")
    
    # Test 2: Load profile
    print("\n[Test 2] Load profile")
    if profiles:
        test_profile_name = profiles[0]
        profile = manager.load(test_profile_name)
        print(f"  ✓ Loaded: {test_profile_name}")
        print(f"    OS: {profile.get('os')}")
        print(f"    Navigator: {profile.get('navigator', {}).get('userAgent', 'N/A')[:60]}...")
        print(f"    Screen: {profile.get('screen', {}).get('width')}x{profile.get('screen', {}).get('height')}")
        print(f"    WebGL: {profile.get('webgl', {}).get('renderer', 'N/A')[:50]}...")
    
    # Test 3: Search profiles
    print("\n[Test 3] Search profiles")
    search_results = manager.search("firefox")
    print(f"  Search 'firefox': {len(search_results)} results")
    for name in search_results:
        print(f"    - {name}")
    
    # Test 4: Create and save new profile
    print("\n[Test 4] Create and save new profile")
    test_profile = {
        "name": "test-db-profile",
        "description": "Test profile for database",
        "created": "2026-04-21",
        "version": "1.0",
        "os": "linux",
        "browser": "firefox",
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "colorDepth": 24,
            "pixelDepth": 24,
        },
        "navigator": {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
            "platform": "Linux x86_64",
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "maxTouchPoints": 0,
            "vendor": "",
            "language": "en-US",
            "languages": ["en-US", "en"],
        },
        "webgl": {
            "vendor": "NVIDIA Corporation",
            "renderer": "NVIDIA GeForce GTX 1060",
            "extensions": [],
            "parameters": {},
        },
        "canvas": {
            "noise": {
                "seed": 1234567890,
                "intensity": 0.015,
                "magnitude": 1,
                "edge_bias": 1.1,
                "strategy": "hybrid",
                "temporal_variation": 0.0004,
                "sparse_probability": 0.016,
            }
        },
        "dns_config": {
            "enabled": True,
            "provider": "quad9",
            "rationale": "Test DNS config",
            "doh": {
                "uri": "https://dns.quad9.net/dns-query",
                "bootstrap_address": "9.9.9.9",
                "mode": 3,
                "strict_fallback": True,
                "disable_ecs": True,
            },
            "ipv6": {
                "enabled": False,
                "reason": "Test IPv6 disabled",
            },
            "webrtc": {
                "enabled": False,
                "reason": "Test WebRTC disabled",
            },
            "prefetch": {
                "dns_prefetch": False,
                "link_prefetch": False,
                "reason": "Test prefetch disabled",
            },
        },
        "fingerprint": {
            "canvas_seed": 1234567890,
            "audio_seed": 9876543210,
        },
        "fingerprints": {
            "ja3": "",
            "ja4": "",
            "akamai_http2": "",
            "notes": "Test profile",
        },
        "timezone": "America/New_York",
        "timezoneOffset": -300,
        "fonts": ["Arial", "Courier New", "Georgia", "Times New Roman", "Verdana"],
        "firefox_preferences": {
            "network.trr.mode": 3,
            "network.trr.uri": "https://dns.quad9.net/dns-query",
            "media.peerconnection.enabled": False,
        },
    }
    
    manager.save(test_profile)
    print(f"  ✓ Saved: test-db-profile")
    
    # Verify it was saved
    if manager.exists("test-db-profile"):
        print(f"  ✓ Verified: profile exists in database")
        loaded = manager.load("test-db-profile")
        print(f"  ✓ Loaded back successfully")
        
        # Verify data integrity
        assert loaded["name"] == test_profile["name"]
        assert loaded["os"] == test_profile["os"]
        assert loaded["screen"]["width"] == test_profile["screen"]["width"]
        assert loaded["navigator"]["userAgent"] == test_profile["navigator"]["userAgent"]
        assert loaded["webgl"]["renderer"] == test_profile["webgl"]["renderer"]
        assert loaded["timezone"] == test_profile["timezone"]
        assert len(loaded["fonts"]) == len(test_profile["fonts"])
        print(f"  ✓ Data integrity verified")
    
    # Test 5: Delete profile
    print("\n[Test 5] Delete profile")
    if manager.delete("test-db-profile"):
        print(f"  ✓ Deleted: test-db-profile")
        if not manager.exists("test-db-profile"):
            print(f"  ✓ Verified: profile removed from database")
    
    # Test 6: Profile validation
    print("\n[Test 6] Profile validation")
    if profiles:
        from tegufox_core.profile_manager import ValidationLevel
        profile = manager.load(profiles[0])
        result = manager.validate(profile, ValidationLevel.STANDARD)
        print(f"  Profile: {profiles[0]}")
        print(f"  Valid: {result.valid}")
        print(f"  Score: {result.score:.2f}")
        if result.errors:
            print(f"  Errors: {result.errors}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")
    
    # Summary
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
    print(f"\nDatabase statistics:")
    stats = manager.get_stats()
    print(f"  Total profiles: {stats['total_profiles']}")
    print(f"  Browser counts: {stats['browser_counts']}")
    print(f"  Validation: {stats['validation']}")


if __name__ == "__main__":
    test_database_operations()
