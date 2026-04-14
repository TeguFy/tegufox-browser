#!/usr/bin/env python3
"""
Performance Benchmark Tests for Tegufox Browser Toolkit

Measures performance metrics for:
- Profile loading time
- Profile validation time
- Session initialization time
- Mouse movement generation time
- Network fingerprint validation time

Author: Tegufox Browser Toolkit
Date: April 14, 2026
Phase: 1 - Week 4 (Integration Testing)
"""

import pytest
import time
import json
import statistics
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from profile_manager import ProfileManager, ValidationLevel


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    @pytest.fixture
    def benchmark_iterations(self):
        """Number of iterations for averaging"""
        return 10

    @pytest.fixture
    def profile_manager(self, tmp_path):
        """Create ProfileManager with temp directory"""
        manager = ProfileManager(profiles_dir=tmp_path / "profiles")
        return manager

    @pytest.fixture
    def sample_profile(self, profile_manager):
        """Create sample profile for testing"""
        profile = profile_manager.create_from_template("chrome-120", "benchmark-test")
        return profile

    def test_benchmark_profile_load(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Profile loading time"""
        times = []

        for _ in range(benchmark_iterations):
            start = time.perf_counter()
            profile = profile_manager.load("benchmark-test")
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)

        print(f"\n📊 Profile Load Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Std Dev: {std_dev:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")

        # Success criteria: < 50ms average
        assert avg_time < 50, f"Profile load too slow: {avg_time:.2f}ms"

    def test_benchmark_validation_basic(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Basic validation time"""
        times = []

        for _ in range(benchmark_iterations):
            start = time.perf_counter()
            result = profile_manager.validate(
                sample_profile, level=ValidationLevel.BASIC
            )
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        print(f"\n📊 Validation (BASIC) Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Std Dev: {std_dev:.2f}ms")

        # Success criteria: < 30ms
        assert avg_time < 30, f"Basic validation too slow: {avg_time:.2f}ms"

    def test_benchmark_validation_standard(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Standard validation time"""
        times = []

        for _ in range(benchmark_iterations):
            start = time.perf_counter()
            result = profile_manager.validate(
                sample_profile, level=ValidationLevel.STANDARD
            )
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)

        print(f"\n📊 Validation (STANDARD) Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")

        # Success criteria: < 100ms
        assert avg_time < 100, f"Standard validation too slow: {avg_time:.2f}ms"

    def test_benchmark_validation_strict(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Strict validation time"""
        times = []

        for _ in range(benchmark_iterations):
            start = time.perf_counter()
            result = profile_manager.validate(
                sample_profile, level=ValidationLevel.STRICT
            )
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)

        print(f"\n📊 Validation (STRICT) Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")

        # Success criteria: < 200ms
        assert avg_time < 200, f"Strict validation too slow: {avg_time:.2f}ms"

    def test_benchmark_profile_save(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Profile save time"""
        times = []

        for i in range(benchmark_iterations):
            profile_name = f"benchmark-save-{i}"
            profile = profile_manager.create_from_template("chrome-120", profile_name)

            start = time.perf_counter()
            profile_manager.save(profile, profile_name)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)

        print(f"\n📊 Profile Save Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")

        # Success criteria: < 100ms
        assert avg_time < 100, f"Profile save too slow: {avg_time:.2f}ms"

    def test_benchmark_profile_clone(
        self, profile_manager, sample_profile, benchmark_iterations
    ):
        """Benchmark: Profile cloning time"""
        times = []

        for i in range(benchmark_iterations):
            start = time.perf_counter()
            cloned = profile_manager.clone("benchmark-test", f"benchmark-clone-{i}")
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = statistics.mean(times)

        print(f"\n📊 Profile Clone Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")

        # Success criteria: < 150ms
        assert avg_time < 150, f"Profile clone too slow: {avg_time:.2f}ms"

    def test_benchmark_template_generation(self, profile_manager, benchmark_iterations):
        """Benchmark: Template generation time"""
        times = []
        templates = ["chrome-120", "firefox-115", "safari-17"]

        for template in templates:
            for i in range(benchmark_iterations // 3):
                start = time.perf_counter()
                profile = profile_manager.create_from_template(
                    template, f"bench-{template}-{i}"
                )
                end = time.perf_counter()
                times.append((end - start) * 1000)

        avg_time = statistics.mean(times)

        print(f"\n📊 Template Generation Benchmark:")
        print(f"  Average: {avg_time:.2f}ms")

        # Success criteria: < 100ms
        assert avg_time < 100, f"Template generation too slow: {avg_time:.2f}ms"

    @pytest.mark.benchmark
    def test_benchmark_summary(self, profile_manager, sample_profile, tmp_path):
        """Generate comprehensive benchmark summary"""
        results = {}

        # Save sample profile first
        profile_manager.save(sample_profile, "benchmark-test")

        # Profile load
        times = []
        for _ in range(50):
            start = time.perf_counter()
            profile_manager.load("benchmark-test")
            times.append((time.perf_counter() - start) * 1000)
        results["profile_load"] = {
            "avg_ms": statistics.mean(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p50_ms": statistics.median(times),
            "p95_ms": statistics.quantiles(times, n=20)[18],  # 95th percentile
        }

        # Validation levels
        for level in [
            ValidationLevel.BASIC,
            ValidationLevel.STANDARD,
            ValidationLevel.STRICT,
        ]:
            times = []
            for _ in range(50):
                start = time.perf_counter()
                profile_manager.validate(sample_profile, level=level)
                times.append((time.perf_counter() - start) * 1000)
            results[f"validation_{level.value}"] = {
                "avg_ms": statistics.mean(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "p50_ms": statistics.median(times),
                "p95_ms": statistics.quantiles(times, n=20)[18],
            }

        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEGUFOX PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 70)

        for operation, metrics in results.items():
            print(f"\n{operation.upper().replace('_', ' ')}:")
            print(f"  Average:  {metrics['avg_ms']:>8.2f}ms")
            print(f"  Median:   {metrics['p50_ms']:>8.2f}ms")
            print(f"  95th %:   {metrics['p95_ms']:>8.2f}ms")
            print(f"  Min:      {metrics['min_ms']:>8.2f}ms")
            print(f"  Max:      {metrics['max_ms']:>8.2f}ms")

        print("\n" + "=" * 70)

        # Save results to file
        results_file = Path(__file__).parent / "benchmark_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Benchmark results saved to: {results_file}")

        # Overall pass criteria
        assert results["profile_load"]["avg_ms"] < 50
        assert results["validation_basic"]["avg_ms"] < 30
        assert results["validation_standard"]["avg_ms"] < 100
        assert results["validation_strict"]["avg_ms"] < 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
