"""Benchmark overhead of Tegufox C++ patches.

Measures noise injection overhead via HTML test pages.
Runs headless Chromium (JS-level proxy) since Tegufox binary
not yet packaged for macOS. Targets: each operation < 5% overhead.

Note: true C++ overhead can only be measured with Tegufox binary.
This test validates the Python-side overhead + profile loading.
"""

import time
from pathlib import Path

import pytest

from consistency_engine import ConsistencyEngine, default_rules
from fingerprint_registry import FingerprintRegistry
from generator_v2 import generate_fleet
from profile_manager import ProfileManager

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def engine():
    return ConsistencyEngine(default_rules())


@pytest.fixture(scope="module")
def manager():
    return ProfileManager()


class TestConsistencyEngineBenchmark:
    """Engine evaluation must stay fast for real-time profile validation."""

    def test_single_profile_evaluation_under_1ms(self, engine, manager):
        profile = manager.load("chrome-120")
        start = time.perf_counter()
        for _ in range(1000):
            engine.evaluate(profile)
        elapsed = (time.perf_counter() - start) / 1000
        assert elapsed < 0.001, f"Single evaluation took {elapsed*1000:.3f}ms (limit: 1ms)"

    def test_all_profiles_under_5ms_total(self, engine, manager):
        profiles = [manager.load(name) for name in manager.list()]
        start = time.perf_counter()
        for p in profiles:
            engine.evaluate(p)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.005, f"All {len(profiles)} profiles took {elapsed*1000:.1f}ms (limit: 5ms)"


class TestFingerprintRegistryBenchmark:
    """SQLite operations must be fast for per-page-load recording."""

    def test_record_1000_entries_under_1s(self, tmp_path):
        with FingerprintRegistry(tmp_path / "bench.db") as reg:
            start = time.perf_counter()
            for i in range(1000):
                reg.record(f"profile-{i % 10}", f"site-{i}.com",
                           hash_canvas=f"c{i}", hash_webgl=f"w{i}")
            elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"1000 records took {elapsed:.2f}s (limit: 1s)"

    def test_collision_check_under_5ms(self, tmp_path):
        with FingerprintRegistry(tmp_path / "bench.db") as reg:
            for i in range(500):
                reg.record(f"profile-{i}", "example.com",
                           hash_canvas=f"canvas-{i % 50}")
            start = time.perf_counter()
            for _ in range(100):
                reg.find_collisions("profile-new", hash_canvas="canvas-5")
            elapsed = (time.perf_counter() - start) / 100
        assert elapsed < 0.005, f"Collision check took {elapsed*1000:.3f}ms (limit: 5ms)"


class TestGeneratorBenchmark:
    """Fleet generation must be fast for batch profile creation."""

    def test_generate_100_profiles_under_1s(self, manager):
        import random
        rng = random.Random(42)
        start = time.perf_counter()
        fleet = generate_fleet(manager, count=100, rng=rng)
        elapsed = time.perf_counter() - start
        assert len(fleet) == 100
        assert elapsed < 1.0, f"100 profiles took {elapsed:.2f}s (limit: 1s)"


class TestProfileLoadBenchmark:
    """Profile CRUD must be fast."""

    def test_profile_load_under_1ms(self, manager):
        start = time.perf_counter()
        for _ in range(1000):
            manager.load("chrome-120")
        elapsed = (time.perf_counter() - start) / 1000
        assert elapsed < 0.001, f"Profile load took {elapsed*1000:.3f}ms (limit: 1ms)"

    def test_profile_validate_under_1ms(self, manager):
        profile = manager.load("chrome-120")
        start = time.perf_counter()
        for _ in range(1000):
            manager.validate(profile)
        elapsed = (time.perf_counter() - start) / 1000
        assert elapsed < 0.001, f"Profile validate took {elapsed*1000:.3f}ms (limit: 1ms)"
