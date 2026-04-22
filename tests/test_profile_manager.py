#!/usr/bin/env python3
"""
Profile Manager Test Suite

Comprehensive tests for profile_manager.py covering:
- CRUD operations (create, read, update, delete)
- Profile validation (basic, standard, strict)
- Template generation
- Bulk operations (clone, merge, import, export)
- Search and filtering
- Statistics

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 3 Day 14
"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from profile_manager import (
    ProfileManager,
    ValidationLevel,
    ValidationResult,
    BROWSER_TEMPLATES,
)


# Fixtures


@pytest.fixture
def temp_profiles_dir():
    """Temporary profiles directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_profiles_dir):
    """ProfileManager instance with isolated temp database"""
    return ProfileManager(db_path=str(temp_profiles_dir / "test.db"))


@pytest.fixture
def sample_profile():
    """Sample profile for testing"""
    return {
        "name": "test-profile",
        "description": "Test profile",
        "created": "2026-04-14",
        "version": "1.0",
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "colorDepth": 24,
            "pixelDepth": 24,
        },
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "vendor": "Google Inc.",
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "language": "en-US",
            "languages": ["en-US", "en"],
        },
    }


# Test 1: ProfileManager Initialization


def test_manager_initialization(temp_profiles_dir):
    """Test ProfileManager initialization"""
    manager = ProfileManager(db_path=str(temp_profiles_dir / "init.db"))

    assert manager.db is not None

    print("✓ Test 1 passed: ProfileManager initialization")


# Test 2: Create Profile


def test_create_profile(manager):
    """Test creating new profile"""
    profile = manager.create(name="test-create", description="Test creation")

    assert profile["name"] == "test-create"
    assert profile["description"] == "Test creation"
    assert "navigator" in profile
    assert "screen" in profile

    print("✓ Test 2 passed: Create profile")


# Test 3: Save and Load Profile


def test_save_load_profile(manager, sample_profile):
    """Test saving and loading profile"""
    # Save
    saved_path = manager.save(sample_profile, "test-save")
    assert saved_path.exists()

    # Load - DB may add default fields, check key fields only
    loaded = manager.load("test-save")
    assert loaded["name"] == sample_profile["name"]
    nav_orig = sample_profile["navigator"]
    nav_loaded = loaded["navigator"]
    for key in nav_orig:
        assert nav_loaded[key] == nav_orig[key], f"navigator.{key} mismatch"

    print("✓ Test 3 passed: Save and load profile")


# Test 4: Delete Profile


def test_delete_profile(manager, sample_profile):
    """Test deleting profile"""
    # Create and save
    manager.save(sample_profile, "test-delete")
    assert manager.exists("test-delete")

    # Delete
    deleted = manager.delete("test-delete")
    assert deleted is True
    assert not manager.exists("test-delete")

    # Delete non-existent
    deleted = manager.delete("nonexistent")
    assert deleted is False

    print("✓ Test 4 passed: Delete profile")


# Test 5: List Profiles


def test_list_profiles(manager, sample_profile):
    """Test listing profiles"""
    # Create multiple profiles
    for i in range(3):
        profile = sample_profile.copy()
        profile["name"] = f"test-list-{i}"
        manager.save(profile, f"test-list-{i}")

    # List all
    profiles = manager.list()
    assert len(profiles) == 3
    assert "test-list-0" in profiles
    assert "test-list-1" in profiles
    assert "test-list-2" in profiles

    # List with pattern
    chrome_profiles = manager.list("test-list-*")
    assert len(chrome_profiles) == 3

    print("✓ Test 5 passed: List profiles")


# Test 6: Profile Exists


def test_exists(manager, sample_profile):
    """Test checking if profile exists"""
    assert not manager.exists("test-exists")

    manager.save(sample_profile, "test-exists")
    assert manager.exists("test-exists")

    print("✓ Test 6 passed: Profile exists check")


# Test 7: Create from Template


def test_create_from_template(manager):
    """Test creating profile from template"""
    # Create from chrome-120 template
    profile = manager.create_from_template(template="chrome-120", name="test-chrome")

    assert profile["name"] == "test-chrome"
    assert "navigator" in profile

    # Test invalid template
    with pytest.raises(ValueError):
        manager.create_from_template("invalid-template", "test")

    print("✓ Test 7 passed: Create from template")


# Test 8: Basic Validation


def test_validation_basic(manager):
    """Test basic profile validation"""
    # Valid profile
    profile = {
        "name": "test-valid",
        "navigator": {
            "userAgent": "Mozilla/5.0...",
            "platform": "Win32",
        },
    }

    result = manager.validate(profile, ValidationLevel.BASIC)
    assert result.valid is True
    assert result.score >= 0.8

    # Missing required field
    invalid_profile = {"name": "test-invalid"}
    result = manager.validate(invalid_profile, ValidationLevel.BASIC)
    assert result.valid is False
    assert len(result.errors) > 0

    print("✓ Test 8 passed: Basic validation")


# Test 9: Standard Validation


def test_validation_standard(manager):
    """Test standard profile validation"""
    profile = {
        "name": "chrome-test",
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "vendor": "Google Inc.",
        },
        "dns_config": {
            "enabled": True,
            "provider": "cloudflare",
            "doh": {
                "uri": "https://mozilla.cloudflare-dns.com/dns-query",
                "mode": 3,
            },
        },
    }

    result = manager.validate(profile, ValidationLevel.STANDARD)
    assert result.level == ValidationLevel.STANDARD
    assert result.score >= 0.7

    print("✓ Test 9 passed: Standard validation")


# Test 10: Strict Validation


def test_validation_strict(manager):
    """Test strict profile validation"""
    profile = {
        "name": "chrome-strict",
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "vendor": "Google Inc.",
        },
        "http2": {"pseudo_header_order": ["method", "authority", "scheme", "path"]},
        "dns_config": {
            "enabled": True,
            "provider": "cloudflare",
        },
    }

    result = manager.validate(profile, ValidationLevel.STRICT)
    assert result.level == ValidationLevel.STRICT

    # Test DoH provider mismatch (Firefox with Cloudflare)
    firefox_profile = profile.copy()
    firefox_profile["name"] = "firefox-strict"
    firefox_profile["navigator"]["userAgent"] = "Mozilla/5.0 Firefox/115.0"
    firefox_profile["navigator"]["vendor"] = ""

    result = manager.validate(firefox_profile, ValidationLevel.STRICT)
    assert len(result.warnings) > 0  # Should warn about DoH provider

    print("✓ Test 10 passed: Strict validation")


# Test 11: Clone Profile


def test_clone_profile(manager, sample_profile):
    """Test cloning profile"""
    # Save original
    manager.save(sample_profile, "test-original")

    # Clone
    cloned = manager.clone("test-original", "test-cloned")

    assert cloned["name"] == "test-cloned"
    for key in sample_profile["navigator"]:
        assert cloned["navigator"][key] == sample_profile["navigator"][key]

    # Clone with overrides
    cloned_custom = manager.clone(
        "test-original", "test-cloned-custom", description="Custom description"
    )

    assert cloned_custom["description"] == "Custom description"

    print("✓ Test 11 passed: Clone profile")


# Test 12: Merge Profiles


def test_merge_profiles(manager):
    """Test merging profiles"""
    # Create base profile
    base = {
        "name": "base",
        "navigator": {
            "userAgent": "Base UA",
            "platform": "Win32",
        },
        "screen": {
            "width": 1920,
            "height": 1080,
        },
    }
    manager.save(base, "test-base")

    # Create overlay profile (full navigator required for DB)
    overlay = {
        "name": "overlay",
        "navigator": {
            "userAgent": "Base UA",
            "platform": "MacIntel",  # Override platform
        },
        "screen": {
            "width": 1920,
            "height": 1080,
        },
        "dns_config": {  # New section
            "enabled": True,
        },
    }
    manager.save(overlay, "test-overlay")

    # Merge
    merged = manager.merge("test-base", "test-overlay", "test-merged")

    assert merged["name"] == "test-merged"
    assert merged["navigator"]["userAgent"] == "Base UA"  # Shared between both
    assert merged["navigator"]["platform"] == "MacIntel"  # From overlay
    assert "dns_config" in merged  # New from overlay
    assert merged["screen"]["width"] == 1920  # From base

    print("✓ Test 12 passed: Merge profiles")


# Test 13: Export Bulk


def test_export_bulk(manager, sample_profile, temp_profiles_dir):
    """Test bulk export raises NotImplementedError (DB-only workflow)"""
    with pytest.raises(NotImplementedError):
        manager.export_bulk(["export-0"], str(temp_profiles_dir / "exported.txt"))

    print("✓ Test 13 passed: Export bulk raises NotImplementedError")


# Test 14: Import Bulk


def test_import_bulk(manager, temp_profiles_dir):
    """Test bulk import raises NotImplementedError (DB-only workflow)"""
    with pytest.raises(NotImplementedError):
        manager.import_bulk(str(temp_profiles_dir / "import.txt"))

    print("✓ Test 14 passed: Import bulk raises NotImplementedError")


# Test 15: Generate Template


def test_generate_template(manager):
    """Test template generation"""
    profile = manager.generate_template(
        browser="chrome-120",
        os="windows",
        screen_width=2560,
        screen_height=1440,
        doh_provider="cloudflare",
    )

    assert "navigator" in profile
    assert profile["screen"]["width"] == 2560
    assert profile["screen"]["height"] == 1440
    assert profile["dns_config"]["provider"] == "cloudflare"

    # Test invalid browser
    with pytest.raises(ValueError):
        manager.generate_template("invalid-browser", "windows")

    print("✓ Test 15 passed: Generate template")


# Test 16: Search Profiles


def test_search_profiles(manager, sample_profile):
    """Test profile search"""
    # Create profiles
    for i in range(3):
        profile = sample_profile.copy()
        profile["name"] = f"chrome-{i}"
        profile["description"] = "Chrome browser profile"
        manager.save(profile, f"chrome-{i}")

    for i in range(2):
        profile = sample_profile.copy()
        profile["name"] = f"firefox-{i}"
        profile["description"] = "Firefox browser profile"
        manager.save(profile, f"firefox-{i}")

    # Search by name
    results = manager.search("chrome")
    assert len(results) >= 3

    # Search by description
    results = manager.search("Firefox")
    assert len(results) >= 2

    print("✓ Test 16 passed: Search profiles")


# Test 17: Filter by Browser


def test_filter_by_browser(manager, sample_profile):
    """Test filtering by browser"""
    # Create profiles
    for browser in ["chrome", "firefox", "safari"]:
        for i in range(2):
            profile = sample_profile.copy()
            profile["name"] = f"{browser}-{i}"
            manager.save(profile, f"{browser}-{i}")

    # Filter
    chrome_profiles = manager.filter_by_browser("chrome")
    assert len(chrome_profiles) >= 2

    print("✓ Test 17 passed: Filter by browser")


# Test 18: Get Statistics


def test_get_statistics(manager, sample_profile):
    """Test getting profile statistics"""
    # Create profiles
    for i in range(5):
        profile = sample_profile.copy()
        profile["name"] = f"stats-{i}"
        manager.save(profile, f"stats-{i}")

    stats = manager.get_stats()

    assert "total_profiles" in stats
    assert stats["total_profiles"] >= 5
    assert "browser_counts" in stats
    assert "validation" in stats

    print("✓ Test 18 passed: Get statistics")


# Test 19: Validation Result


def test_validation_result():
    """Test ValidationResult dataclass"""
    result = ValidationResult(
        valid=True,
        level=ValidationLevel.STANDARD,
        errors=[],
        warnings=["Test warning"],
        score=0.95,
    )

    assert result.valid is True
    assert result.score == 0.95
    assert len(result.warnings) == 1

    # Test to_dict
    result_dict = result.to_dict()
    assert result_dict["valid"] is True
    assert result_dict["level"] == "standard"
    assert result_dict["score"] == 0.95

    print("✓ Test 19 passed: ValidationResult")


# Test 20: DoH Provider Validation


def test_doh_provider_validation(manager):
    """Test DoH provider alignment validation"""
    # Chrome with Cloudflare (correct)
    chrome_profile = {
        "name": "chrome-doh-test",
        "navigator": {
            "userAgent": "Mozilla/5.0 Chrome/120.0.0.0",
            "vendor": "Google Inc.",
        },
        "dns_config": {
            "enabled": True,
            "provider": "cloudflare",
        },
    }

    result = manager.validate(chrome_profile, ValidationLevel.STANDARD)
    assert len([w for w in result.warnings if "DoH provider" in w]) == 0

    # Firefox with Cloudflare (should warn)
    firefox_profile = {
        "name": "firefox-doh-test",
        "navigator": {
            "userAgent": "Mozilla/5.0 Firefox/115.0",
            "vendor": "",
        },
        "dns_config": {
            "enabled": True,
            "provider": "cloudflare",  # Should be quad9
        },
    }

    result = manager.validate(firefox_profile, ValidationLevel.STANDARD)
    assert len([w for w in result.warnings if "DoH provider" in w]) > 0

    print("✓ Test 20 passed: DoH provider validation")


# Test runner

if __name__ == "__main__":
    print("Profile Manager Test Suite")
    print("=" * 60)
    print()

    # Run pytest
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
        ]
    )
