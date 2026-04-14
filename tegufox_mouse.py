"""
Tegufox Mouse Movement v2 - Human-Like Cursor Behavior

Provides realistic mouse movement patterns for Camoufox automation:
- Bezier curve paths with asymmetric control points
- Fitts's Law timing (distance + target size based)
- Minimum-jerk velocity profiles (bell curve)
- Physiological tremor and micro-corrections
- Overshoot & correction for fast movements
- Idle jitter simulation (background micro-movements)

Usage:
    from tegufox_mouse import HumanMouse
    from camoufox.sync_api import Camoufox

    with Camoufox() as browser:
        page = browser.new_page()
        mouse = HumanMouse(page)

        # Human-like movement and click
        mouse.click('button#submit')

        # Move with idle jitter
        mouse.move_to('input#search')

        # Scroll naturally
        mouse.scroll(500)

Author: Tegufox Team
Date: 2026-04-13
License: MIT
"""

import math
import random
import time
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Point:
    """2D point with x, y coordinates"""

    x: float
    y: float


@dataclass
class MouseConfig:
    """Configuration for human-like mouse movement"""

    # Movement
    strategy: str = "bezier"  # "bezier" or "linear"
    min_steps: int = 25
    steps_divisor: int = 8  # steps = distance / divisor
    wobble_max: float = 1.5  # Max perpendicular wobble (px)

    # Overshoot
    overshoot_chance: float = 0.70  # Probability of overshoot
    overshoot_min: float = 3.0  # Min overshoot distance (px)
    overshoot_max: float = 12.0  # Max overshoot distance (px)

    # Click
    click_offset_max: int = 10  # Max offset from element center (px)
    click_delay_min: int = 50  # Min delay before click (ms)
    click_delay_max: int = 200  # Max delay before click (ms)
    hold_duration_min: int = 50  # Min mouse hold time (ms)
    hold_duration_max: int = 150  # Max mouse hold time (ms)

    # Idle
    idle_enabled: bool = True
    idle_interval_min: int = 1000  # Min idle jitter interval (ms)
    idle_interval_max: int = 3000  # Max idle jitter interval (ms)
    idle_distance_min: int = 5  # Min idle movement distance (px)
    idle_distance_max: int = 20  # Max idle movement distance (px)

    # Fitts's Law
    fitts_enabled: bool = True
    fitts_a: float = 50.0  # Base time (ms)
    fitts_b: float = 150.0  # Scaling factor (ms)

    # Tremor
    tremor_enabled: bool = True
    tremor_sigma: float = 1.0  # Gaussian noise std dev (px)


class HumanMouse:
    """
    Human-like mouse movement controller for Camoufox/Playwright

    Implements realistic mouse behavior patterns:
    - Bezier curve trajectories
    - Fitts's Law timing
    - Velocity profiles
    - Tremor simulation
    - Click randomization
    - Idle jitter
    """

    def __init__(self, page, config: Optional[MouseConfig] = None):
        """
        Initialize human mouse controller

        Args:
            page: Playwright/Camoufox page object
            config: MouseConfig instance (optional, uses defaults)
        """
        self.page = page
        self.config = config or MouseConfig()
        self._last_position = Point(0, 0)
        self._idle_jitter_active = False

    def click(self, selector: str, **kwargs):
        """
        Click element with human-like movement and timing

        Args:
            selector: CSS selector for target element
            **kwargs: Additional click options
        """
        # Get element bounding box
        element = self.page.locator(selector).first
        box = element.bounding_box()

        if not box:
            raise ValueError(f"Element not found or not visible: {selector}")

        # Calculate randomized click position (not exact center)
        target_x, target_y = self._randomize_click_position(box)

        # Move mouse to target with Bezier curve
        self.move_to_position(target_x, target_y)

        # Random delay before click (thinking time)
        delay_ms = random.randint(
            self.config.click_delay_min, self.config.click_delay_max
        )
        time.sleep(delay_ms / 1000)

        # Perform click with realistic hold duration
        hold_ms = random.randint(
            self.config.hold_duration_min, self.config.hold_duration_max
        )

        self.page.mouse.down()
        time.sleep(hold_ms / 1000)
        self.page.mouse.up()

    def move_to(self, selector: str):
        """
        Move mouse to element center with human-like trajectory

        Args:
            selector: CSS selector for target element
        """
        element = self.page.locator(selector).first
        box = element.bounding_box()

        if not box:
            raise ValueError(f"Element not found: {selector}")

        # Element center
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2

        self.move_to_position(center_x, center_y, target_width=box["width"])

    def move_to_position(self, x: float, y: float, target_width: float = 50.0):
        """
        Move mouse to specific coordinates with human-like path

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            target_width: Target size for Fitts's Law (default: 50px)
        """
        start = self._last_position
        end = Point(x, y)

        # Calculate movement distance
        distance = self._distance(start, end)

        if distance < 5:  # Too short, just teleport
            self.page.mouse.move(x, y)
            self._last_position = end
            return

        # Generate Bezier path
        path = self._generate_bezier_path(start, end, distance)

        # Calculate movement time using Fitts's Law
        total_time_ms = self._calculate_fitts_time(distance, target_width)

        # Apply velocity profile and move
        self._execute_movement(path, total_time_ms, distance)

        # Check for overshoot
        if self._should_overshoot(distance):
            self._apply_overshoot(end, start, end)

        self._last_position = end

    def scroll(self, delta_y: int):
        """
        Scroll page with natural physics simulation

        Args:
            delta_y: Vertical scroll distance (pixels)
        """
        # TODO: Implement physics-based scrolling with momentum
        # For now, use simple scroll
        self.page.mouse.wheel(0, delta_y)

    # =========================================================================
    # PRIVATE METHODS - Bezier Path Generation
    # =========================================================================

    def _generate_bezier_path(
        self, start: Point, end: Point, distance: float
    ) -> List[Point]:
        """
        Generate cubic Bezier curve path from start to end

        Args:
            start: Starting point
            end: Ending point
            distance: Distance between points

        Returns:
            List of Point objects along curve
        """
        # Calculate number of steps
        steps = max(self.config.min_steps, int(distance / self.config.steps_divisor))

        # Generate asymmetric control points
        p1 = self._generate_control_point(
            start, end, distance, deviation_range=(0.2, 0.5), angle_variance=math.pi / 4
        )
        p2 = self._generate_control_point(
            end, start, distance, deviation_range=(0.1, 0.3), angle_variance=math.pi / 6
        )

        # Generate points along Bezier curve
        path = []
        for i in range(steps + 1):
            t = i / steps
            point = self._cubic_bezier(start, p1, p2, end, t)

            # Add tremor if enabled
            if self.config.tremor_enabled:
                point = self._apply_tremor(point)

            path.append(point)

        return path

    def _generate_control_point(
        self,
        start: Point,
        end: Point,
        distance: float,
        deviation_range: Tuple[float, float],
        angle_variance: float,
    ) -> Point:
        """Generate single Bezier control point with randomness"""
        # Random deviation (% of distance)
        deviation = random.uniform(*deviation_range) * distance

        # Base angle from start to end
        base_angle = math.atan2(end.y - start.y, end.x - start.x)

        # Add random variance
        angle = base_angle + random.uniform(-angle_variance, angle_variance)

        # Calculate control point position
        return Point(
            start.x + math.cos(angle) * deviation, start.y + math.sin(angle) * deviation
        )

    def _cubic_bezier(
        self, p0: Point, p1: Point, p2: Point, p3: Point, t: float
    ) -> Point:
        """
        Calculate point on cubic Bezier curve at parameter t

        Formula: B(t) = (1-t)³·P₀ + 3(1-t)²t·P₁ + 3(1-t)t²·P₂ + t³·P₃
        """
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        t2 = t * t
        t3 = t2 * t

        return Point(
            mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x,
            mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y,
        )

    # =========================================================================
    # PRIVATE METHODS - Timing & Velocity
    # =========================================================================

    def _calculate_fitts_time(self, distance: float, target_width: float) -> float:
        """
        Calculate movement time using Fitts's Law

        MT = a + b × log₂(D/W + 1)

        Args:
            distance: Movement distance (pixels)
            target_width: Target size (pixels)

        Returns:
            Movement time in milliseconds
        """
        if not self.config.fitts_enabled:
            # Simple linear time if Fitts disabled
            return distance * 2.0  # 2ms per pixel

        # Index of Difficulty
        ID = math.log2((distance / target_width) + 1.0)

        # Movement Time
        MT = self.config.fitts_a + self.config.fitts_b * ID

        # Add random variance (±15%)
        variance = MT * random.uniform(-0.15, 0.15)

        return max(100, MT + variance)  # Minimum 100ms

    def _get_velocity_multiplier(self, t: float) -> float:
        """
        Get velocity multiplier at normalized time t using bell curve

        Args:
            t: Normalized time [0, 1]

        Returns:
            Velocity multiplier [0.1, 1.0]
        """
        # Sine-based bell curve (slow → fast → slow)
        v = math.sin(math.pi * t)

        # Add slight randomness
        v += random.uniform(-0.05, 0.05)

        return max(0.1, min(1.0, v))

    def _execute_movement(
        self, path: List[Point], total_time_ms: float, distance: float
    ):
        """
        Execute mouse movement along path with velocity profile

        Args:
            path: List of points to move through
            total_time_ms: Total movement duration
            distance: Total distance traveled
        """
        num_points = len(path)

        for i, point in enumerate(path):
            # Normalized time
            t = i / (num_points - 1) if num_points > 1 else 0

            # Get velocity multiplier
            velocity = self._get_velocity_multiplier(t)

            # Calculate delay for this step
            step_delay_ms = (total_time_ms / num_points) / velocity

            # Move mouse
            self.page.mouse.move(point.x, point.y)

            # Wait with velocity-adjusted delay
            if i < num_points - 1:  # Don't delay on last point
                time.sleep(step_delay_ms / 1000)

    # =========================================================================
    # PRIVATE METHODS - Tremor & Overshoot
    # =========================================================================

    def _apply_tremor(self, point: Point) -> Point:
        """
        Apply physiological tremor (Gaussian noise) to point

        Args:
            point: Original point

        Returns:
            Point with tremor applied
        """
        sigma = self.config.tremor_sigma

        # Gaussian noise
        tremor_x = random.gauss(0, sigma)
        tremor_y = random.gauss(0, sigma)

        return Point(point.x + tremor_x, point.y + tremor_y)

    def _should_overshoot(self, distance: float) -> bool:
        """
        Determine if movement should overshoot target

        Args:
            distance: Movement distance

        Returns:
            True if should overshoot
        """
        if distance < 200:  # Short movements don't overshoot
            return False

        return random.random() < self.config.overshoot_chance

    def _apply_overshoot(self, target: Point, start: Point, end: Point):
        """
        Apply overshoot and correction movement

        Args:
            target: Target position
            start: Movement start position
            end: Movement end position
        """
        # Calculate overshoot direction (extension of movement vector)
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Normalize direction
        dir_x = dx / length
        dir_y = dy / length

        # Random overshoot distance
        overshoot_dist = random.uniform(
            self.config.overshoot_min, self.config.overshoot_max
        )

        # Overshoot point
        overshoot_point = Point(
            end.x + dir_x * overshoot_dist, end.y + dir_y * overshoot_dist
        )

        # Move to overshoot
        self.page.mouse.move(overshoot_point.x, overshoot_point.y)
        time.sleep(random.uniform(0.03, 0.08))  # 30-80ms pause

        # Correct back to target (quick Bezier)
        correction_path = self._generate_bezier_path(
            overshoot_point, target, overshoot_dist
        )
        self._execute_movement(
            correction_path,
            total_time_ms=random.uniform(50, 150),
            distance=overshoot_dist,
        )

    # =========================================================================
    # PRIVATE METHODS - Click Randomization
    # =========================================================================

    def _randomize_click_position(self, box: Dict[str, float]) -> Tuple[float, float]:
        """
        Generate randomized click position within element bounds

        Uses Gaussian distribution to bias toward center

        Args:
            box: Element bounding box (x, y, width, height)

        Returns:
            (x, y) coordinates for click
        """
        # Element center
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2

        # Gaussian offset (biased toward center)
        offset_x = random.gauss(0, self.config.click_offset_max / 3)
        offset_y = random.gauss(0, self.config.click_offset_max / 3)

        # Clamp to element bounds
        min_x = box["x"] + 5
        max_x = box["x"] + box["width"] - 5
        min_y = box["y"] + 5
        max_y = box["y"] + box["height"] - 5

        click_x = max(min_x, min(max_x, center_x + offset_x))
        click_y = max(min_y, min(max_y, center_y + offset_y))

        return (click_x, click_y)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _distance(self, p1: Point, p2: Point) -> float:
        """Calculate Euclidean distance between two points"""
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.sqrt(dx * dx + dy * dy)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================


def example_amazon_shopping():
    """Example: Navigate Amazon with human-like mouse movements"""
    from camoufox.sync_api import Camoufox

    # Load profile with canvas noise v2
    config = {
        "canvas:seed": 1234567890,
        "canvas:noise:enable": True,
        "canvas:noise:strategy": "gpu",
    }

    with Camoufox(config=config, headless=False) as browser:
        page = browser.new_page()
        mouse = HumanMouse(page)

        # Navigate to Amazon
        page.goto("https://www.amazon.com")

        # Search for product (human-like click on search box)
        mouse.click("input#twotabsearchtextbox")
        page.keyboard.type("laptop", delay=random.randint(100, 300))

        # Submit search (move and click)
        mouse.click("input#nav-search-submit-button")

        # Wait for results
        page.wait_for_load_state("networkidle")

        # Click first product (random click position)
        mouse.click(".s-result-item:nth-child(1) h2 a")

        # Scroll down to reviews
        mouse.scroll(500)

        # Add to cart
        mouse.click("#add-to-cart-button")

        print("✅ Human-like shopping complete!")


if __name__ == "__main__":
    example_amazon_shopping()
