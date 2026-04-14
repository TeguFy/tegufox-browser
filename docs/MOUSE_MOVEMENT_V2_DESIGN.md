# Mouse Movement v2 - Design Document

**Date**: 2026-04-13  
**Phase**: Phase 1 Week 2 Day 3  
**Status**: Design Phase

---

## 📋 Executive Summary

Mouse Movement v2 implements human-like cursor behavior to defeat behavioral bot detection systems that analyze:
- **Movement patterns**: Straight lines vs curved Bezier paths
- **Velocity profiles**: Constant speed vs natural acceleration/deceleration
- **Click timing**: Instant clicks vs realistic delays
- **Idle behavior**: Static cursor vs natural micro-movements (jitter)
- **Coordinate variance**: Perfect center clicks vs randomized positions

**Goal**: Pass DataDome, PerimeterX, and e-commerce behavioral analysis

---

## 🎯 Problem Statement

### What Behavioral Detection Systems Track

**Modern anti-bot systems** (DataDome, PerimeterX, Cloudflare) run JavaScript that records:

```javascript
// Every mouse event on the page
document.addEventListener('mousemove', (e) => {
    track({
        x: e.clientX,
        y: e.clientY,
        timestamp: Date.now(),
        velocity: calculateVelocity(),
        acceleration: calculateAcceleration()
    });
});
```

**Bot Signatures Detected**:
1. ❌ **Straight-line teleportation**: `mousemove` directly from (0,0) to button
2. ❌ **Constant velocity**: Every movement same speed
3. ❌ **Perfect targeting**: Always click exact center of elements
4. ❌ **Instant clicks**: 0ms delay between page load and click
5. ❌ **No idle movement**: Cursor completely static between actions
6. ❌ **Zero jitter**: No micro-corrections or tremor
7. ❌ **Machine-gun timing**: Consistent intervals (exactly 1000ms between actions)

### Research Findings (2026)

**Libraries Studied**:
- **ghost-cursor** (Puppeteer): Bezier curves + Fitts's Law (62K+ weekly downloads)
- **HumanCursor** (Selenium): Natural motion with variable speed
- **cloakbrowser-human**: Full behavioral layer (mouse + keyboard + scroll)
- **shy-mouse-playwright**: Fatigue simulation + polling rate variation
- **pydoll**: Physics-based scrolling with momentum/friction

**Key Techniques**:
1. **Bezier Curves**: Cubic Bezier with asymmetric control points (more curvature early)
2. **Fitts's Law**: `MT = a + b × log₂(D/W + 1)` (movement time based on distance/width)
3. **Minimum-Jerk Velocity**: Bell-shaped speed profile (slow → fast → slow)
4. **Physiological Tremor**: Gaussian noise ~1px, scaled inversely with velocity
5. **Overshoot & Correction**: 70% chance of overshooting by 3-12%, then correcting
6. **Idle Jitter**: 15-20px micro-movements during "reading" phases

---

## 🏗️ Algorithm Design

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│  1. BEZIER PATH GENERATION                                  │
│     - Cubic Bezier curves with randomized control points    │
│     - Asymmetric curvature (more early, less late)          │
│     - Step count: distance / 8 (minimum 25 steps)           │
│                                                              │
│  2. FITTS'S LAW TIMING                                      │
│     - MT = a + b × log₂(D/W + 1)                            │
│     - a = 50ms (base time), b = 150ms (scaling factor)      │
│     - Larger/farther targets = longer movement time         │
│                                                              │
│  3. MINIMUM-JERK VELOCITY PROFILE                           │
│     - Bell curve: v(t) = sin(π × t) for t ∈ [0, 1]         │
│     - Slow start (0-20%): acceleration phase                │
│     - Fast middle (20-80%): cruise phase                    │
│     - Slow end (80-100%): deceleration phase                │
│                                                              │
│  4. PHYSIOLOGICAL TREMOR                                    │
│     - Gaussian noise: N(0, σ) where σ ≈ 1px                 │
│     - Scaled inversely with velocity (more tremor when slow)│
│     - Applied perpendicular to movement direction           │
│                                                              │
│  5. OVERSHOOT & CORRECTION                                  │
│     - 70% chance for fast movements (>500px)                │
│     - Overshoot: 3-12px beyond target                       │
│     - Correction: Bezier curve back to target (50-150ms)    │
│                                                              │
│  6. IDLE JITTER (Background Thread)                         │
│     - Small random movements (5-20px) every 1-3 seconds     │
│     - Simulates reading/scanning behavior                   │
│     - Stops during precise actions                          │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Strategy

**Native C++ Implementation** (Firefox browser modification):
- Hook: `EventStateManager::GenerateMouseEnterExit()` and `MouseEvent` dispatching
- Intercept: Playwright/Selenium mouse commands at browser level
- Apply: Bezier path + velocity profile + tremor before firing DOM events
- Timing: Use Firefox's event loop for realistic delays

**Why C++ vs JavaScript**:
- ✅ No JS prototype tampering (undetectable)
- ✅ Works with all automation frameworks (Playwright, Selenium, etc.)
- ✅ Consistent across all pages (can't be blocked by websites)
- ✅ Performance: Native code, no JS overhead

---

## 📐 Mathematical Foundations

### 1. Cubic Bezier Curves

**Formula**:
```
B(t) = (1-t)³·P₀ + 3(1-t)²t·P₁ + 3(1-t)t²·P₂ + t³·P₃
where t ∈ [0, 1]
```

**Control Points**:
```cpp
P0 = startPosition  // (x0, y0)
P3 = endPosition    // (x3, y3)

// P1: First control point (early curvature)
double deviation1 = Random(0.2, 0.5) * distance  // 20-50% of distance
double angle1 = atan2(y3-y0, x3-x0) + Random(-π/4, π/4)  // ±45° variance
P1.x = x0 + cos(angle1) * deviation1
P1.y = y0 + sin(angle1) * deviation1

// P2: Second control point (late curvature)  
double deviation2 = Random(0.1, 0.3) * distance  // 10-30% of distance
double angle2 = atan2(y3-y0, x3-x0) + Random(-π/6, π/6)  // ±30° variance
P2.x = x3 - cos(angle2) * deviation2
P2.y = y3 - sin(angle2) * deviation2
```

**Asymmetric curvature**: P1 has larger deviation (more curve early in path)

### 2. Fitts's Law

**Movement Time Calculation**:
```cpp
double CalculateMovementTime(double distance, double targetWidth) {
    const double a = 50.0;    // Base time (ms)
    const double b = 150.0;   // Scaling factor (ms)
    
    // Index of Difficulty
    double ID = log2((distance / targetWidth) + 1.0);
    
    // Movement Time
    double MT = a + b * ID;
    
    // Add randomness (±15%)
    double variance = MT * Random(-0.15, 0.15);
    
    return MT + variance;
}
```

**Example**:
- Small button (20px) at 500px: `MT = 50 + 150 × log₂(26) ≈ 750ms`
- Large button (100px) at 500px: `MT = 50 + 150 × log₂(6) ≈ 435ms`
- Short move (100px) to 50px: `MT = 50 + 150 × log₂(3) ≈ 287ms`

### 3. Minimum-Jerk Velocity Profile

**Bell Curve Velocity**:
```cpp
double GetVelocity(double t) {
    // t ∈ [0, 1], normalized time along path
    // Returns velocity multiplier
    
    // Sine-based bell curve
    double v = sin(M_PI * t);
    
    // Add slight randomness
    v += Random(-0.05, 0.05);
    
    return max(0.1, v);  // Minimum 10% velocity
}
```

**Velocity Profile**:
```
1.0 |     ╱‾‾‾╲
    |    ╱     ╲
0.5 |   ╱       ╲
    |  ╱         ╲
0.0 |─╯───────────╲─
    0   0.25  0.5  0.75  1.0 (t)
```

### 4. Physiological Tremor

**Gaussian Noise Application**:
```cpp
struct Point ApplyTremor(Point p, double velocity) {
    // Tremor magnitude inversely proportional to velocity
    // Fast movements = less tremor (hand is stable during quick motions)
    // Slow movements = more tremor (micro-corrections)
    
    double sigma = 1.0 / (velocity + 0.1);  // Base tremor ~1px
    
    // Gaussian noise
    double tremorX = GaussianRandom(0, sigma);
    double tremorY = GaussianRandom(0, sigma);
    
    return {p.x + tremorX, p.y + tremorY};
}
```

### 5. Overshoot & Correction

**Overshoot Logic**:
```cpp
bool ShouldOvershoot(double distance, double velocity) {
    if (distance < 200) return false;  // Short movements don't overshoot
    if (velocity < 0.7) return false;  // Slow movements don't overshoot
    
    return Random(0, 1) < 0.7;  // 70% chance for fast long movements
}

Point CalculateOvershoot(Point target, Point direction) {
    double overshootDistance = Random(3, 12);  // 3-12px beyond target
    
    return {
        target.x + direction.x * overshootDistance,
        target.y + direction.y * overshootDistance
    };
}
```

**Correction Path**:
- Generate new Bezier curve from overshoot point back to target
- Duration: 50-150ms (quick correction)
- Same velocity profile (bell curve)

### 6. Idle Jitter

**Background Movement**:
```cpp
void IdleJitter() {
    while (!stopJitter) {
        Sleep(Random(1000, 3000));  // Wait 1-3 seconds
        
        Point current = GetCursorPosition();
        
        // Small random offset (5-20px)
        double offsetX = Random(-20, 20);
        double offsetY = Random(-20, 20);
        
        Point target = {current.x + offsetX, current.y + offsetY};
        
        // Move with minimal Bezier curve (subtle)
        MoveMouse(current, target, {.steps = 10, .duration = 200});
    }
}
```

---

## ⚙️ MaskConfig Parameters

### Configuration Schema

```json
{
  "mouse:humanize": true,
  "mouse:movement:strategy": "bezier",
  "mouse:movement:min-steps": 25,
  "mouse:movement:steps-divisor": 8,
  "mouse:movement:wobble-max": 1.5,
  "mouse:movement:overshoot-chance": 0.70,
  "mouse:movement:overshoot-distance": [3, 12],
  "mouse:click:offset-max": 10,
  "mouse:click:delay-min": 50,
  "mouse:click:delay-max": 200,
  "mouse:idle:enabled": true,
  "mouse:idle:interval": [1000, 3000],
  "mouse:idle:distance": [5, 20],
  "mouse:fitts:enabled": true,
  "mouse:fitts:a": 50,
  "mouse:fitts:b": 150,
  "mouse:tremor:enabled": true,
  "mouse:tremor:sigma": 1.0
}
```

### Parameter Reference

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `mouse:humanize` | bool | true | - | Master enable/disable switch |
| `mouse:movement:strategy` | string | "bezier" | bezier/linear | Path algorithm |
| `mouse:movement:min-steps` | int32 | 25 | 10 - 100 | Minimum movement steps |
| `mouse:movement:steps-divisor` | int32 | 8 | 5 - 20 | Steps = distance / divisor |
| `mouse:movement:wobble-max` | double | 1.5 | 0 - 5 | Perpendicular wobble amplitude (px) |
| `mouse:movement:overshoot-chance` | double | 0.70 | 0 - 1 | Probability of overshoot |
| `mouse:movement:overshoot-distance` | array | [3, 12] | [1, 20] | Overshoot distance range (px) |
| `mouse:click:offset-max` | int32 | 10 | 0 - 50 | Max click offset from element center (px) |
| `mouse:click:delay-min` | int32 | 50 | 0 - 500 | Min delay before click (ms) |
| `mouse:click:delay-max` | int32 | 200 | 50 - 1000 | Max delay before click (ms) |
| `mouse:idle:enabled` | bool | true | - | Enable background jitter |
| `mouse:idle:interval` | array | [1000, 3000] | [500, 5000] | Jitter interval range (ms) |
| `mouse:idle:distance` | array | [5, 20] | [1, 50] | Jitter distance range (px) |
| `mouse:fitts:enabled` | bool | true | - | Use Fitts's Law for timing |
| `mouse:fitts:a` | double | 50 | 30 - 100 | Base movement time (ms) |
| `mouse:fitts:b` | double | 150 | 100 - 300 | Scaling factor (ms) |
| `mouse:tremor:enabled` | bool | true | - | Add physiological tremor |
| `mouse:tremor:sigma` | double | 1.0 | 0.5 - 3.0 | Tremor magnitude (px) |

---

## 🧪 Testing Strategy

### Detection Benchmarks

**deviceandbrowserinfo.com/are_you_a_bot_interactions**:
- Target: `isBot: false`, all 23 flags `false`
- Check: `suspiciousClientSideBehavior: false`

**Metrics Comparison**:

| Metric | Human | Straight Line | With Bezier |
|--------|-------|---------------|-------------|
| Mouse events | 204 | 546 | 115 |
| Avg velocity variance | High | None | High |
| Path straightness | 0.6-0.8 | 1.0 | 0.6-0.8 |
| Click offset std dev | 8-12px | 0px | 8-12px |

### E-commerce Testing

**Amazon** (aggressive behavioral analysis):
- Product page navigation
- Add to cart clicks
- Checkout form interaction
- Expected: No bot detection triggers

**eBay** (moderate tracking):
- Seller dashboard navigation
- Listing creation clicks
- Image uploads (drag/drop)
- Expected: Normal session flow

**Etsy** (moderate tracking):
- Shop management clicks
- Order processing
- Search interactions
- Expected: No anomalies

---

## 🚀 Implementation Plan

### Phase 1: Core Bezier Movement (2 hours)

**Files to modify**:
- `widget/EventStateManager.cpp` - Mouse event generation
- `dom/events/EventTarget.cpp` - Event dispatching
- `widget/InputData.h` - Mouse input structures

**Functions to implement**:
1. `GenerateBezierPath(start, end, config)`
2. `CalculateFittsTime(distance, width)`
3. `ApplyVelocityProfile(path, totalTime)`
4. `ApplyTremor(point, velocity)`
5. `ProcessMouseMove(fromX, fromY, toX, toY)`

### Phase 2: Click Randomization (1 hour)

**Click coordinate variance**:
- Get element bounding box
- Generate random offset within bounds
- Apply Gaussian distribution (center bias)

**Click timing**:
- Random delay before click (50-200ms)
- Mouse down duration (50-150ms)
- Ensure `mousedown` → `mouseup` → `click` event sequence

### Phase 3: Idle Jitter (1 hour)

**Background thread**:
- Launch separate thread on browser start
- Sleep for random interval (1-3s)
- Small movement (5-20px) when no user action
- Stop during automation commands

### Phase 4: Testing & Tuning (4 hours)

**Automated tests**:
- Unit tests for Bezier calculation
- Velocity profile verification
- Fitts's Law accuracy

**Manual tests**:
- deviceandbrowserinfo.com bot detection
- E-commerce site navigation
- Visual inspection of movement realism

---

## 📊 Expected Results

### Movement Quality

**Path Realism**:
- Bezier curves: ✅ Natural curvature
- Straight lines: ❌ Obvious bot behavior

**Velocity Variation**:
- Bell curve: ✅ Realistic acceleration/deceleration
- Constant speed: ❌ Machine-like movement

**Click Targeting**:
- Random offset: ✅ Human-like imprecision
- Perfect center: ❌ Robotic precision

### Detection Evasion

| System | Detection Vector | Without Humanization | With Mouse v2 |
|--------|------------------|---------------------|---------------|
| DataDome | Mouse path analysis | ❌ Straight lines | ✅ Bezier curves |
| PerimeterX | Velocity profiling | ❌ Constant speed | ✅ Bell curve |
| Cloudflare | Click timing | ❌ Instant (0ms) | ✅ Random (50-200ms) |
| Amazon | Idle behavior | ❌ Static cursor | ✅ Jitter enabled |
| E-commerce | Click variance | ❌ Perfect center | ✅ Randomized ±10px |

### Performance Impact

**Overhead**:
- Bezier calculation: ~0.5ms per movement
- Event generation: ~2ms per 100px movement
- Idle jitter: Background thread (negligible CPU)
- **Total**: <1% performance impact

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Bezier path generation working
- ✅ Fitts's Law timing implemented
- ✅ Velocity profile applied correctly
- ✅ Tremor/wobble added
- ✅ Overshoot & correction functional
- ✅ Idle jitter running in background
- ✅ Click randomization active

### Quality Requirements
- ✅ deviceandbrowserinfo: `isBot: false`
- ✅ Visual inspection: Movement looks natural
- ✅ E-commerce sites: No bot detection
- ✅ Performance: <1% overhead

### Configuration Requirements
- ✅ All 16 MaskConfig parameters working
- ✅ Templates updated with mouse humanization
- ✅ Validation passing
- ✅ Documentation complete

---

## 📚 References

### Libraries Studied
- **ghost-cursor**: https://github.com/Xetera/ghost-cursor (Puppeteer)
- **HumanCursor**: https://github.com/Shahrukh-Iqbal/HumanCursor (Selenium)
- **cloakbrowser-human**: https://github.com/evelaa123/cloakbrowser-human (Playwright)
- **shy-mouse-playwright**: https://github.com/AB6162/shy-mouse-playwright
- **bezier-mouse-js**: https://github.com/ChrisdeWolf/bezier-mouse-js
- **pydoll**: https://github.com/autoscrape-labs/pydoll

### Research Papers
- Fitts, P. M. (1954): "The information capacity of the human motor system"
- Flash, T. & Hogan, N. (1985): "The coordination of arm movements: minimum jerk"
- Lakha, A. & Glasauer, S. (2022): "Physiological tremor in cursor control"

### Detection Systems
- **DataDome**: AI behavioral analysis (mouse movement patterns)
- **PerimeterX**: Velocity profiling and timing analysis
- **Cloudflare**: JavaScript challenges + mouse tracking
- **deviceandbrowserinfo.com**: 23-point bot interaction test

---

## 💡 Key Insights

### What Makes Movement "Human"

**Not just curves**:
- ✅ Asymmetric Bezier (more curve early, less late)
- ✅ Velocity variation (bell curve, not constant)
- ✅ Tremor during slow movements
- ✅ Occasional overshoot & correction
- ✅ Random click offsets
- ✅ Idle micro-movements

**Common mistakes**:
- ❌ Perfectly symmetric curves (too artificial)
- ❌ Too many steps (200+ points = laggy)
- ❌ No velocity profile (looks robotic)
- ❌ No tremor (too smooth)
- ❌ Always clicking exact center

### Performance vs Realism Trade-offs

**Bezier steps**:
- Too few (<20): Choppy movement, obvious bot
- Too many (>100): Performance hit, excessive events
- **Optimal**: distance / 8, minimum 25 steps

**Idle jitter frequency**:
- Too frequent (<500ms): Distracting, uses CPU
- Too rare (>5s): Cursor seems dead
- **Optimal**: 1-3 second intervals

---

**Status**: Design complete, ready for implementation  
**Estimated effort**: 8 hours (Core: 2h, Click: 1h, Idle: 1h, Testing: 4h)  
**Risk**: Medium (Firefox event system complex, but well-documented)
