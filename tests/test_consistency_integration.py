"""Integration test: run consistency engine across all profiles/*.json.

Full-schema profiles (chrome-120, firefox-115, safari-17) should score >= 0.8
with no error-severity failures. Flat-schema profiles skip most rules.
"""

import json
from pathlib import Path

import pytest

from consistency_engine import ConsistencyEngine, default_rules
from profile_manager import ProfileManager

PROFILES_DIR = Path(__file__).parent.parent / "profiles"
FULL_SCHEMA_PROFILES = {"chrome-120", "firefox-115", "safari-17"}


@pytest.fixture(scope="module")
def engine():
    return ConsistencyEngine(default_rules())


@pytest.fixture(scope="module")
def manager():
    return ProfileManager(str(PROFILES_DIR))


@pytest.fixture(scope="module")
def all_profiles(manager):
    return {name: manager.load(name) for name in manager.list()}


def test_all_profiles_evaluable(engine, all_profiles):
    """Engine must not crash on any profile."""
    for name, profile in all_profiles.items():
        report = engine.evaluate(profile)
        assert isinstance(report.score, float)
        assert 0.0 <= report.score <= 1.0


@pytest.mark.parametrize("name", sorted(FULL_SCHEMA_PROFILES))
def test_full_schema_profiles_pass(engine, manager, name):
    """Full-schema profiles must score >= 0.8 with no error failures."""
    profile = manager.load(name)
    report = engine.evaluate(profile)
    errors = [r for r in report.rule_results if not r.passed and r.severity == "error"]
    assert report.score >= 0.8, f"{name}: score {report.score:.2f}\n{report.summary()}"
    assert not errors, f"{name} has error failures: {[e.rule_name for e in errors]}"


def test_full_schema_profiles_run_most_rules(engine, manager):
    """Full-schema profiles should not skip more than 3 rules."""
    for name in FULL_SCHEMA_PROFILES:
        profile = manager.load(name)
        report = engine.evaluate(profile)
        skipped = sum(1 for r in report.rule_results if r.skipped)
        assert skipped <= 3, f"{name} skipped {skipped}/8 rules"


def test_flat_schema_profiles_skip_gracefully(engine, all_profiles):
    """Flat-schema profiles should not fail any rules (all skip)."""
    for name, profile in all_profiles.items():
        if name in FULL_SCHEMA_PROFILES:
            continue
        report = engine.evaluate(profile)
        errors = [r for r in report.rule_results if not r.passed and not r.skipped]
        assert not errors, f"{name} unexpected failure: {[e.rule_name for e in errors]}"
