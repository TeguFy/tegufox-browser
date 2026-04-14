# Canvas Noise v2 - Advanced Injection Algorithm Design

**Date**: 2026-04-13  
**Phase**: Phase 1 Week 2 Day 2  
**Status**: Design Document

---

## 📋 Executive Summary

Canvas Noise v2 implements a production-grade canvas fingerprint defense system that:
- **Defeats detection**: Passes CreepJS, BrowserLeaks, Pixelscan noise detection algorithms
- **Maintains consistency**: Per-session, per-origin fingerprints (no random changes on refresh)
- **Preserves functionality**: Visual fidelity maintained for legitimate canvas apps
- **Performance optimized**: <1ms overhead per canvas operation

---

## 🎯 Design Goals

### Primary Goals
1. **Undetectable noise**: Avoid mathematical patterns that CreepJS can identify
2. **Session stability**: Same fingerprint across page refreshes within session
3. **Origin isolation**: Different fingerprints per domain (avoid cross-site tracking)
4. **Visual preservation**: No visible artifacts in canvas applications

### Secondary Goals
5. **Performance**: Minimal CPU overhead (<1ms per operation)
6. **Configurability**: Multiple noise strategies via MaskConfig
7. **GPU correlation**: Noise patterns must match declared GPU vendor/model
8. **E-commerce optimized**: Pass Amazon, eBay, Etsy detection systems

---

## 🔬 Research Findings

### What CreepJS Detects (2026)

**Texture Analysis**:
- Mathematical noise patterns (uniform random, gaussian, perlin)
- Pixel value distributions that don't match real GPU rendering
- Perfect color channel independence (R, G, B modified identically)

**Consistency Checks**:
- Multiple canvas renders produce identical hashes (should vary slightly)
- Noise disappears when canvas rendered multiple times
- Stack trace inspection for overridden `toDataURL()` / `getImageData()`

**Prototype Tampering**:
- Modified native functions produce non-native stack traces
- `toString()` on overridden functions doesn't match native code
- Error messages differ from browser defaults

### What BrowserLeaks Checks

**Rendering Tests**:
- Text rendering with Arial 14px + color mixing
- Emoji rendering (Unicode character pixel differences)
- Gradient support and anti-aliasing behavior
- `toDataURL()` signature MD5 hash

**Expected Behavior**:
- Same browser + OS + GPU = same hash (across sessions)
- Different GPU drivers = different pixel patterns
- Font smoothing variations based on OS settings

### Defense Requirements

Based on research from:
- Brave browser's noise injection (85% uniqueness reduction)
- Firefox FPP mode (canvas noise since v119)
- Anti-detect browser best practices (2026)

**Must Have**:
1. **Per-origin, per-session seeding**: Different seed per domain, stable during session
2. **Sub-pixel noise intensity**: ±1-2 on <0.1% of pixels (imperceptible)
3. **GPU-correlated patterns**: Noise must match expected GPU rendering quirks
4. **Native code preservation**: No JS prototype tampering (C++ level only)

**Must Avoid**:
1. ❌ Random noise on every render (CreepJS detects this immediately)
2. ❌ Uniform distribution (mathematical signature too clean)
3. ❌ Prototype override in JS (stack trace detection)
4. ❌ Affecting visual pixels (breaks legitimate canvas apps)

---

## 🏗️ Algorithm Design

### Strategy 1: GPU-Simulated Rendering Variance (Primary)

**Concept**: Simulate natural GPU rendering inconsistencies that occur in real hardware

**Implementation**:
```cpp
// Seed generation: Per-origin + per-session
uint64_t seed = Hash(origin) XOR Hash(sessionId) XOR MaskConfig::GetUint32("canvas:seed")

// Pixel selection: Sparse, non-uniform distribution
// Target: 0.01% - 0.05% of pixels (imperceptible)
bool ShouldNoisePixel(int x, int y, uint64_t seed) {
    // Use spatial hash to create GPU-like rendering artifacts
    uint64_t hash = SpatialHash(x, y, seed)
    
    // Non-uniform probability based on position
    // Higher near text edges (anti-aliasing variance)
    float edgeDistance = DetectEdgeDistance(x, y)
    float probability = 0.0001 + (edgeDistance < 2.0 ? 0.0004 : 0.0)
    
    return (hash % 100000) < (probability * 100000)
}

// Noise intensity: Sub-pixel variations
int8_t GetNoiseValue(int x, int y, int channel, uint64_t seed) {
    uint64_t hash = Hash(x, y, channel, seed)
    
    // Simulate GPU rounding errors
    // ±1 or ±2 only, never 0 (avoid no-op)
    int8_t values[] = {-2, -1, 1, 2}
    return values[hash % 4]
}

// Channel independence: RGB have correlated but not identical noise
// Simulate real GPU color processing pipeline
void ApplyNoise(uint8_t* pixel, int x, int y, uint64_t seed) {
    uint8_t r = pixel[0], g = pixel[1], b = pixel[2]
    
    if (ShouldNoisePixel(x, y, seed)) {
        // Correlated noise (GPU processes channels together)
        uint64_t channelSeed = Hash(x, y, seed)
        
        pixel[0] = Clamp(r + GetNoiseValue(x, y, 0, channelSeed), 0, 255)
        pixel[1] = Clamp(g + GetNoiseValue(x, y, 1, channelSeed), 0, 255)
        pixel[2] = Clamp(b + GetNoiseValue(x, y, 2, channelSeed), 0, 255)
        // Alpha channel untouched (transparency must be exact)
    }
}
```

**Why This Works**:
- **GPU-realistic**: Mimics actual hardware rendering variations (driver rounding, anti-aliasing)
- **Spatially coherent**: Noise clusters near edges (where real GPU artifacts occur)
- **Deterministic**: Same origin + session = same noise pattern
- **Undetectable**: No mathematical signature, looks like natural GPU behavior

---

### Strategy 2: Temporal Micro-Variance (Secondary)

**Concept**: Add microscopic time-based variations within same session

**Implementation**:
```cpp
// Add tiny timestamp-based component to seed
// Changes every ~100ms, but stays within same fingerprint "bucket"
uint64_t GetTemporalSeed(uint64_t baseSeed) {
    uint64_t timestamp = GetTimestamp() / 100  // 100ms buckets
    return baseSeed ^ (timestamp & 0xFF)        // Only affect lower 8 bits
}

// Result: Canvas hash changes slightly over time, but within expected variance
// Prevents "perfect stability" detection by sophisticated systems
```

**Why This Helps**:
- Real browsers show tiny rendering variations over time
- Defeats "multiple renders = identical hash" detection
- Stays within fingerprint "tolerance zone" (same device, slight variance)

---

### Strategy 3: Operation-Specific Handling

Different canvas operations need different noise approaches:

#### `toDataURL()` - Most Common Fingerprinting Target
```cpp
// Apply noise ONLY when canvas is read via toDataURL()
// Do NOT apply during visual rendering (preserves display quality)
JS::Value CanvasRenderingContext2D::ToDataURL(...) {
    if (MaskConfig::CheckBool("canvas:noise:enable")) {
        uint8_t* imageData = GetImageData()
        uint64_t seed = GenerateSeed(origin, sessionId)
        
        ApplyNoiseToImageData(imageData, width, height, seed)
    }
    
    return GenerateDataURL(imageData)
}
```

#### `getImageData()` - Direct Pixel Access
```cpp
// Apply same noise for consistency with toDataURL()
ImageData CanvasRenderingContext2D::GetImageData(...) {
    ImageData data = ExtractPixels(...)
    
    if (MaskConfig::CheckBool("canvas:noise:enable")) {
        uint64_t seed = GenerateSeed(origin, sessionId)
        ApplyNoiseToImageData(data.pixels, data.width, data.height, seed)
    }
    
    return data
}
```

#### Visual Rendering (drawImage, fillRect, etc.)
```cpp
// NO NOISE during rendering
// Preserves visual quality for:
// - Image editors (Photoshop online, Figma)
// - Games (Canvas-based 2D games)
// - Signature pads (banking, legal documents)
// - QR code generators
```

---

## ⚙️ MaskConfig Parameters

### Configuration Schema

```json
{
  "canvas:seed": 1234567890,           // Base seed (uint32)
  "canvas:noise:enable": true,         // Master switch (bool)
  "canvas:noise:strategy": "gpu",      // "gpu" | "temporal" | "hybrid" (string)
  "canvas:noise:intensity": 0.0001,    // Pixel coverage % (0.01% default)
  "canvas:noise:magnitude": 2,         // Max ±value (1-3 range)
  "canvas:noise:edge-bias": 0.0004,    // Extra noise near edges
  "canvas:noise:temporal": true        // Enable micro-variance over time
}
```

### Parameter Details

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `canvas:seed` | uint32 | 0 - 2^32 | random | Base seed for noise generation |
| `canvas:noise:enable` | bool | - | true | Master enable/disable |
| `canvas:noise:strategy` | string | gpu/temporal/hybrid | "gpu" | Noise algorithm selection |
| `canvas:noise:intensity` | double | 0.00001 - 0.001 | 0.0001 | % of pixels to modify (0.01% = 1 in 10k) |
| `canvas:noise:magnitude` | int32 | 1 - 3 | 2 | Max ±value for pixel changes |
| `canvas:noise:edge-bias` | double | 0 - 0.001 | 0.0004 | Extra probability near edges |
| `canvas:noise:temporal` | bool | - | true | Enable time-based micro-variance |

### Usage Examples

**Maximum stealth (e-commerce, high security)**:
```json
{
  "canvas:seed": 9876543210,
  "canvas:noise:strategy": "hybrid",
  "canvas:noise:intensity": 0.00005,    // Very sparse (0.005%)
  "canvas:noise:magnitude": 1,          // Minimal ±1 changes
  "canvas:noise:temporal": true
}
```

**Balanced (general browsing)**:
```json
{
  "canvas:seed": 1234567890,
  "canvas:noise:strategy": "gpu",
  "canvas:noise:intensity": 0.0001,     // Default 0.01%
  "canvas:noise:magnitude": 2,
  "canvas:noise:temporal": true
}
```

**Aggressive (high anonymity)**:
```json
{
  "canvas:seed": 5555555555,
  "canvas:noise:strategy": "hybrid",
  "canvas:noise:intensity": 0.0005,     // More pixels (0.05%)
  "canvas:noise:magnitude": 3,          // Larger ±3 changes
  "canvas:noise:temporal": false        // Stable fingerprint
}
```

---

## 🧪 Testing Strategy

### Phase 1: Implementation Testing
1. **Unit tests**: Verify noise distribution, intensity, determinism
2. **Visual regression**: Ensure no visible artifacts in canvas apps
3. **Performance**: Benchmark overhead (<1ms requirement)

### Phase 2: Fingerprinting Detection
1. **BrowserLeaks Canvas Test**:
   - Generate canvas signature
   - Verify uniqueness within session
   - Confirm stability across refreshes

2. **CreepJS Full Scan**:
   - Trust score check (target: >80%)
   - Canvas tampering detection (target: 0% detection)
   - Lies/inconsistencies (target: 0 flags)

3. **Pixelscan Analysis**:
   - Consistency check with GPU/OS
   - Noise pattern detection
   - Profile authenticity score

### Phase 3: E-commerce Validation
1. **Amazon**: Product pages, checkout flow
2. **eBay**: Seller dashboard, listing creation
3. **Etsy**: Shop management, order processing

### Success Criteria
- ✅ BrowserLeaks: Stable signature, passes rendering tests
- ✅ CreepJS: 0 "lies", trust score >80%, no tampering detected
- ✅ Pixelscan: Green consistency checks, no red flags
- ✅ E-commerce: No bot detection triggers, normal session flow
- ✅ Performance: <1ms overhead per canvas operation
- ✅ Visual: No artifacts in signature pads, image editors, games

---

## 🔧 Implementation Notes

### File Locations
```
dom/canvas/CanvasRenderingContext2D.cpp  # Main implementation
dom/canvas/CanvasRenderingContext2D.h    # Header declarations
gfx/2d/DataSurfaceHelpers.cpp           # Image data utilities
dom/canvas/moz.build                     # Build configuration
```

### Key Functions to Modify
1. `CanvasRenderingContext2D::ToDataURL()`
2. `CanvasRenderingContext2D::GetImageData()`
3. Add new: `ApplyCanvasNoise(ImageData*, uint64_t seed)`
4. Add new: `GenerateCanvasSeed(nsIPrincipal* origin, sessionId)`

### Dependencies
- `MaskConfig.hpp` - Configuration access
- `nsIPrincipal.h` - Origin/domain detection
- `mozilla/HashFunctions.h` - Cryptographic hashing
- `mozilla/Random.h` - PRNG (DO NOT USE - use deterministic hash instead)

### Critical Requirements
1. **NO JavaScript prototype tampering**: All noise applied in C++ only
2. **Deterministic seeding**: Same origin+session = same noise pattern
3. **Performance**: Use fast hash functions (xxHash, not crypto)
4. **Alpha preservation**: Never modify alpha channel (breaks transparency)
5. **Edge detection**: Simple gradient-based method (avoid expensive algorithms)

---

## 📊 Expected Results

### Fingerprint Entropy Reduction
- **Without noise**: 99%+ unique fingerprints (1 in 1 million)
- **With Noise v2**: 85-90% uniqueness reduction (similar to Brave browser)
- **Effective anonymity**: Fingerprint shared with ~10,000 users

### Detection Resistance
| Detection Method | Without Noise | With Noise v2 |
|------------------|---------------|---------------|
| Canvas hash tracking | ✅ Tracked | ❌ Randomized |
| CreepJS tampering | N/A | ✅ Undetected |
| Texture analysis | N/A | ✅ GPU-realistic |
| Consistency checks | ✅ Passed | ✅ Passed |
| Visual artifacts | ✅ None | ✅ None |

### Performance Impact
- **Noise generation**: ~0.3ms per canvas (baseline: 0ms)
- **Total overhead**: <1% for typical web pages
- **Memory**: +16 bytes per canvas (seed storage)

---

## 🚀 Next Steps

1. **Implement core algorithm** in `CanvasRenderingContext2D.cpp`
2. **Add MaskConfig parameters** to configuration templates
3. **Write unit tests** for noise distribution and determinism
4. **Test with BrowserLeaks** and **CreepJS**
5. **Validate e-commerce sites** (Amazon, eBay, Etsy)
6. **Performance profiling** and optimization
7. **Documentation** and usage guide

---

## 📚 References

### Research Papers
- Acar et al. (2014): "The Web Never Forgets: Persistent Tracking Mechanisms in the Wild"
- Laperdrix et al. (2020): "Browser Fingerprinting: A Survey"
- EFF Panopticlick (2025): "83.6% of browsers have unique Canvas fingerprints"

### Browser Implementations
- **Brave**: Per-site, per-session noise (85% uniqueness reduction)
- **Firefox RFP**: Blank canvas return (100% reduction, breaks sites)
- **Firefox FPP** (v119+): Canvas noise injection (80% reduction)
- **Tor Browser**: Block all canvas readback (100% reduction, high breakage)

### Testing Tools
- **CreepJS** (https://creepjs.vercel.app/): Advanced tampering detection
- **BrowserLeaks** (https://browserleaks.com/canvas): Canvas signature test
- **Pixelscan**: Consistency and authenticity checks

### Detection Research (2026)
- "How to Detect Canvas Noise" (Castle.io, Feb 2025)
- "CreepJS Browser Fingerprint Test" (Undetectable.io, Mar 2026)
- "How Anonymity Checkers Work" (Octobrowser, Apr 2026)

---

**Status**: Ready for implementation  
**Estimated effort**: 6-8 hours  
**Risk**: Low (proven techniques, well-researched)
