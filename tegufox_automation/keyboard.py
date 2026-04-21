"""
Tegufox Keyboard v1 u2014 Human-Like Typing Behavior

Produces realistic keystroke timing that passes behavioral analysis:
- Inter-keystroke intervals follow a log-normal distribution (human motor model)
- Per-bigram timing: common bigrams (th, er, in) are faster than rare ones (qz, xj)
- Typo injection + correction: configurable error rate with realistic backspaceu2192retype
- WPM envelope: 40-80 WPM with natural variance (warmup u2192 cruise u2192 fatigue)
- Modifier keys (shift, caps) have distinct timing profiles

Usage:
    from tegufox_keyboard import HumanKeyboard
    keyboard = HumanKeyboard(page)
    keyboard.type_text("Hello world")
    keyboard.type_text("Search query", wpm=55)
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Bigram timing model
# ---------------------------------------------------------------------------

# Relative speed multipliers for common English bigrams.
# 1.0 = average, < 1.0 = faster (well-practiced), > 1.0 = slower (awkward reach).
_BIGRAM_SPEED: dict[str, float] = {
    # Fast bigrams (same hand, rolling motion)
    "th": 0.70, "he": 0.72, "in": 0.74, "er": 0.73, "an": 0.75,
    "re": 0.76, "on": 0.78, "en": 0.77, "at": 0.79, "es": 0.80,
    "or": 0.81, "ti": 0.82, "te": 0.78, "is": 0.83, "it": 0.80,
    "al": 0.84, "ar": 0.82, "st": 0.79, "nd": 0.80, "to": 0.81,
    # Medium bigrams
    "se": 0.90, "ha": 0.88, "ou": 0.92, "io": 0.93, "le": 0.89,
    "ve": 0.91, "co": 0.90, "me": 0.88, "de": 0.90, "hi": 0.92,
    "ri": 0.91, "ro": 0.93, "ic": 0.94, "ne": 0.89, "ea": 0.87,
    "ra": 0.90, "ce": 0.92, "li": 0.88, "ch": 0.85, "ll": 0.86,
    # Slow bigrams (awkward finger transitions)
    "qu": 1.25, "xi": 1.20, "zz": 1.30, "qw": 1.35, "xc": 1.22,
    "zx": 1.40, "jk": 1.28, "vb": 1.32, "mn": 1.15, "bf": 1.25,
}

# Nearby keys for typo generation (QWERTY layout)
_ADJACENT_KEYS: dict[str, str] = {
    "a": "sqwz", "b": "vghn", "c": "xdfv", "d": "sfecr", "e": "wrsdf",
    "f": "dgrtcv", "g": "fhtyb", "h": "gjyun", "i": "ujko", "j": "hkuim",
    "k": "jloi", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}


@dataclass
class KeyboardConfig:
    """Configuration for human-like typing."""

    # WPM (words per minute) u2014 target range
    wpm_min: float = 40.0
    wpm_max: float = 80.0

    # Log-normal distribution parameters for inter-key interval.
    # mu and sigma are derived from WPM at runtime; these are base modifiers.
    timing_sigma: float = 0.35  # Variance of log-normal (higher = more spread)

    # Typo simulation
    typo_rate: float = 0.03        # Probability of typo per character
    typo_adjacent_bias: float = 0.80  # Prob typo is adjacent key (vs random)
    correction_delay_ms: float = 250  # Pause before noticing typo
    backspace_interval_ms: float = 60  # Speed of backspace keys

    # Shift key timing
    shift_hold_before_ms: Tuple[float, float] = (30, 80)
    shift_release_after_ms: Tuple[float, float] = (20, 60)

    # Pause behavior
    word_pause_ms: Tuple[float, float] = (80, 200)   # Pause after space
    comma_pause_ms: Tuple[float, float] = (100, 300)  # Pause after comma
    period_pause_ms: Tuple[float, float] = (150, 400)  # Pause after period

    # Warmup/fatigue envelope
    warmup_chars: int = 5           # Characters before reaching cruise speed
    warmup_multiplier: float = 1.4  # Slower during warmup
    fatigue_onset_chars: int = 80   # Characters before fatigue kicks in
    fatigue_multiplier: float = 1.15  # Slower when fatigued


class HumanKeyboard:
    """Human-like typing controller for Playwright pages."""

    def __init__(self, page, config: Optional[KeyboardConfig] = None, rng: Optional[random.Random] = None):
        self.page = page
        self.config = config or KeyboardConfig()
        self._rng = rng or random.Random()
        self._chars_typed = 0

    def type_text(
        self,
        text: str,
        selector: Optional[str] = None,
        wpm: Optional[float] = None,
        typo_rate: Optional[float] = None,
    ) -> None:
        """Type text with human-like timing.

        Args:
            text: String to type.
            selector: Optional CSS selector to focus before typing.
            wpm: Override WPM (default: random in config range).
            typo_rate: Override typo rate.
        """
        if selector:
            self.page.click(selector)
            time.sleep(self._rng.uniform(0.1, 0.3))

        wpm = wpm or self._rng.uniform(self.config.wpm_min, self.config.wpm_max)
        typo_rate = typo_rate if typo_rate is not None else self.config.typo_rate

        # Average ms per character at target WPM (1 word u2248 5 chars)
        base_interval_ms = 60_000 / (wpm * 5)

        prev_char = ""
        i = 0
        while i < len(text):
            char = text[i]

            # Typo injection
            if typo_rate > 0 and char.isalpha() and self._rng.random() < typo_rate:
                typo_char = self._generate_typo(char)
                self._press_key(typo_char, base_interval_ms, prev_char)
                time.sleep(self.config.correction_delay_ms / 1000)
                self.page.keyboard.press("Backspace")
                time.sleep(self.config.backspace_interval_ms / 1000)

            # Type actual character
            delay = self._calculate_delay(char, prev_char, base_interval_ms)
            self._press_key(char, delay, prev_char)

            prev_char = char
            self._chars_typed += 1
            i += 1

    def press_key(self, key: str) -> None:
        """Press a single key with realistic timing."""
        self.page.keyboard.press(key)
        time.sleep(self._rng.uniform(0.05, 0.15))

    # -------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------

    def _press_key(self, char: str, delay_ms: float, prev_char: str) -> None:
        """Press a character key with shift handling."""
        needs_shift = char.isupper() or char in '!@#$%^&*()_+{}|:"<>?~'

        if needs_shift:
            self.page.keyboard.down("Shift")
            time.sleep(self._rng.uniform(*self.config.shift_hold_before_ms) / 1000)

        self.page.keyboard.press(char)

        if needs_shift:
            time.sleep(self._rng.uniform(*self.config.shift_release_after_ms) / 1000)
            self.page.keyboard.up("Shift")

        time.sleep(delay_ms / 1000)

    def _calculate_delay(self, char: str, prev_char: str, base_ms: float) -> float:
        """Calculate inter-key delay with all modifiers applied."""
        # 1. Log-normal base
        mu = math.log(base_ms) - 0.5 * self.config.timing_sigma ** 2
        delay = self._rng.lognormvariate(mu, self.config.timing_sigma)

        # 2. Bigram modifier
        bigram = (prev_char + char).lower()
        bigram_mult = _BIGRAM_SPEED.get(bigram, 1.0)
        delay *= bigram_mult

        # 3. Punctuation pauses
        if char == " ":
            delay += self._rng.uniform(*self.config.word_pause_ms)
        elif char == ",":
            delay += self._rng.uniform(*self.config.comma_pause_ms)
        elif char in ".!?":
            delay += self._rng.uniform(*self.config.period_pause_ms)

        # 4. Warmup / fatigue envelope
        if self._chars_typed < self.config.warmup_chars:
            t = self._chars_typed / self.config.warmup_chars
            mult = self.config.warmup_multiplier - (self.config.warmup_multiplier - 1.0) * t
            delay *= mult
        elif self._chars_typed > self.config.fatigue_onset_chars:
            excess = self._chars_typed - self.config.fatigue_onset_chars
            mult = 1.0 + (self.config.fatigue_multiplier - 1.0) * min(1.0, excess / 100)
            delay *= mult

        return max(20, delay)  # Floor: 20ms

    def _generate_typo(self, char: str) -> str:
        """Generate a plausible typo for a character."""
        lower = char.lower()
        if self._rng.random() < self.config.typo_adjacent_bias:
            adj = _ADJACENT_KEYS.get(lower, "")
            if adj:
                typo = self._rng.choice(adj)
                return typo.upper() if char.isupper() else typo
        # Random letter fallback
        typo = chr(self._rng.randint(ord('a'), ord('z')))
        return typo.upper() if char.isupper() else typo
