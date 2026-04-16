"""Statistical validation of behavioral modules.

Verifies that mouse, keyboard, and scroll outputs match
expected human-like distributions rather than bot signatures.
"""

import math
import random
import statistics
from unittest.mock import MagicMock

import pytest

from tegufox_mouse import HumanMouse, MouseConfig, Point
from tegufox_keyboard import HumanKeyboard, KeyboardConfig, _BIGRAM_SPEED


# ---------------------------------------------------------------------------
# Mouse statistical tests
# ---------------------------------------------------------------------------


class TestMouseDistributions:
    @pytest.fixture
    def mouse(self):
        page = MagicMock()
        return HumanMouse(page, MouseConfig(tremor_enabled=False))

    def test_bezier_path_length_proportional_to_distance(self, mouse):
        """Longer distance should produce more path points."""
        short_path = mouse._generate_bezier_path(Point(0, 0), Point(50, 0), 50)
        long_path = mouse._generate_bezier_path(Point(0, 0), Point(500, 0), 500)
        assert len(long_path) > len(short_path)

    def test_fitts_law_timing_increases_with_distance(self, mouse):
        """Fitts's Law: longer distance = longer movement time."""
        t_short = mouse._calculate_fitts_time(100, 50)
        t_long = mouse._calculate_fitts_time(800, 50)
        assert t_long > t_short

    def test_fitts_law_timing_increases_with_smaller_target(self, mouse):
        """Fitts's Law: smaller target = longer movement time."""
        t_big = mouse._calculate_fitts_time(400, 100)
        t_small = mouse._calculate_fitts_time(400, 10)
        assert t_small > t_big

    def test_velocity_profile_is_bell_shaped(self, mouse):
        """Velocity should peak mid-movement and be low at endpoints."""
        samples = [mouse._get_velocity_multiplier(t / 100) for t in range(101)]
        # Start and end should be slower than middle
        start_avg = statistics.mean(samples[:10])
        mid_avg = statistics.mean(samples[40:60])
        end_avg = statistics.mean(samples[90:])
        assert mid_avg > start_avg
        assert mid_avg > end_avg

    def test_overshoot_only_on_long_movements(self, mouse):
        """Short movements (< 200px) should never overshoot."""
        results = [mouse._should_overshoot(50) for _ in range(100)]
        assert not any(results)

    def test_tremor_adds_gaussian_noise(self):
        """Tremor should shift points by small Gaussian amounts."""
        page = MagicMock()
        mouse = HumanMouse(page, MouseConfig(tremor_enabled=True, tremor_sigma=1.0))
        original = Point(100, 100)
        offsets = []
        for _ in range(1000):
            p = mouse._apply_tremor(original)
            offsets.append(math.sqrt((p.x - 100) ** 2 + (p.y - 100) ** 2))
        # Mean offset should be close to sigma * sqrt(2/pi) for half-normal
        mean_offset = statistics.mean(offsets)
        assert 0.5 < mean_offset < 2.5, f"Mean tremor offset {mean_offset:.2f} outside expected range"


# ---------------------------------------------------------------------------
# Keyboard statistical tests
# ---------------------------------------------------------------------------


class TestKeyboardDistributions:
    @pytest.fixture
    def keyboard(self):
        page = MagicMock()
        return HumanKeyboard(page, KeyboardConfig(typo_rate=0), rng=random.Random(42))

    def test_inter_key_intervals_are_lognormal(self, keyboard):
        """Delays should follow log-normal distribution (positive skew)."""
        delays = []
        for _ in range(500):
            d = keyboard._calculate_delay("a", "t", base_ms=100)
            delays.append(d)
        # Log-normal: mean > median (positive skew)
        mean_d = statistics.mean(delays)
        median_d = statistics.median(delays)
        assert mean_d > median_d, "Delays should be positively skewed (log-normal)"

    def test_common_bigrams_faster_than_rare(self, keyboard):
        """'th' should produce shorter delays than 'qz'."""
        fast_delays = [keyboard._calculate_delay("h", "t", 100) for _ in range(200)]
        slow_delays = [keyboard._calculate_delay("z", "q", 100) for _ in range(200)]
        assert statistics.mean(fast_delays) < statistics.mean(slow_delays)

    def test_wpm_range_produces_expected_speed(self, keyboard):
        """At 60 WPM, avg delay should be ~200ms per char (60000 / 60 / 5)."""
        base_ms = 60_000 / (60 * 5)  # 200ms
        delays = [keyboard._calculate_delay("a", "b", base_ms) for _ in range(500)]
        mean_d = statistics.mean(delays)
        # Should be in range [100, 400] ms (log-normal spread around 200)
        assert 80 < mean_d < 500, f"Mean delay {mean_d:.0f}ms outside expected range for 60 WPM"

    def test_punctuation_adds_pause(self, keyboard):
        """Period/comma should add extra delay vs regular letters."""
        letter_delays = [keyboard._calculate_delay("a", "b", 100) for _ in range(200)]
        period_delays = [keyboard._calculate_delay(".", "a", 100) for _ in range(200)]
        assert statistics.mean(period_delays) > statistics.mean(letter_delays) * 1.3

    def test_warmup_slower_than_cruise(self, keyboard):
        """First few chars should be slower than cruise."""
        keyboard._chars_typed = 0
        warmup_delays = [keyboard._calculate_delay("a", "b", 100) for _ in range(5)]
        keyboard._chars_typed = 30
        cruise_delays = [keyboard._calculate_delay("a", "b", 100) for _ in range(5)]
        assert statistics.mean(warmup_delays) > statistics.mean(cruise_delays)

    def test_typo_generation_produces_adjacent_keys(self):
        """Most typos should be adjacent keys on QWERTY."""
        kb = HumanKeyboard(MagicMock(), KeyboardConfig(typo_adjacent_bias=1.0), rng=random.Random(42))
        typos = [kb._generate_typo("f") for _ in range(100)]
        from tegufox_keyboard import _ADJACENT_KEYS
        adjacent = set(_ADJACENT_KEYS.get("f", ""))
        adjacent_count = sum(1 for t in typos if t in adjacent)
        assert adjacent_count == 100  # 100% adjacent bias

    def test_bigram_table_has_expected_entries(self):
        """Bigram table should cover common English bigrams."""
        common = ["th", "he", "in", "er", "an", "re", "on"]
        for bg in common:
            assert bg in _BIGRAM_SPEED, f"Missing common bigram: {bg}"
            assert _BIGRAM_SPEED[bg] < 1.0, f"Common bigram {bg} should be < 1.0"


# ---------------------------------------------------------------------------
# Scroll tests
# ---------------------------------------------------------------------------


class TestScrollBehavior:
    def test_scroll_calls_wheel_multiple_times(self):
        """Large scroll should produce multiple wheel events (not one giant jump)."""
        page = MagicMock()
        mouse = HumanMouse(page, MouseConfig())
        mouse.scroll(500, platform="windows")
        calls = page.mouse.wheel.call_args_list
        assert len(calls) > 3, f"Expected multiple scroll events, got {len(calls)}"

    def test_scroll_total_matches_requested(self):
        """Sum of all scroll ticks should equal requested delta."""
        page = MagicMock()
        mouse = HumanMouse(page, MouseConfig())
        mouse.scroll(400, platform="macos")
        total = sum(args[0][1] for args in page.mouse.wheel.call_args_list)
        assert abs(total - 400) <= 10, f"Total scrolled {total}, expected ~400"

    def test_scroll_down_positive_up_negative(self):
        """Positive delta = scroll down, negative = scroll up."""
        page = MagicMock()
        mouse = HumanMouse(page, MouseConfig())
        mouse.scroll(-300, platform="linux")
        ticks = [args[0][1] for args in page.mouse.wheel.call_args_list]
        assert all(t < 0 for t in ticks), "All ticks should be negative for scroll up"
