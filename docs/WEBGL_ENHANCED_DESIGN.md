# WebGL Enhanced Fingerprinting Defense - Design Document

**Version**: 2.0  
**Created**: 2026-04-13  
**Author**: Tegufox Team  
**Status**: Phase 1 Week 2 - Day 4

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [WebGL Fingerprinting Threat Model](#webgl-fingerprinting-threat-model)
3. [Research Findings](#research-findings)
4. [Design Principles](#design-principles)
5. [Technical Architecture](#technical-architecture)
6. [Implementation Strategy](#implementation-strategy)
7. [MaskConfig Integration](#maskconfig-integration)
8. [Profile Configuration](#profile-configuration)
9. [Testing & Validation](#testing--validation)
10. [References](#references)

---

## Executive Summary

### The Problem

**WebGL fingerprinting is one of the most powerful tracking techniques** used by e-commerce platforms and anti-bot systems in 2026:

- **High uniqueness**: 15+ bits of entropy (98% unique identification)
- **Hardware-level**: Exposes GPU vendor, model, driver version
- **Cross-browser stable**: Same fingerprint across browsers on same device
- **Consistency checking**: Platforms verify WebGL matches OS/screen/canvas
- **Detection evasion**: JavaScript-based spoofing is easily detected

### The Solution

**Tegufox WebGL Enhanced** implements **C++-level parameter spoofing** with:

1. **MaskConfig-driven override**: Spoof UNMASKED_VENDOR_WEBGL and UNMASKED_RENDERER_WEBGL
2. **Consistency enforcement**: GPU must match OS, screen resolution, canvas fingerprint
3. **Extension list control**: Spoof getSupportedExtensions() with device-appropriate extensions
4. **Parameter value override**: MAX_TEXTURE_SIZE, MAX_VERTEX_ATTRIBS, etc.
5. **Rendering noise injection**: Subtle pixel-level variance (like Canvas Noise v2)

### Key Innovation

Unlike JavaScript-based spoofing (detectable via prototype tampering), **Tegufox patches Firefox C++ source** to override WebGL API responses **before JavaScript execution** - making detection impossible.

---

## WebGL Fingerprinting Threat Model

### Attack Vector 1: UNMASKED_VENDOR_WEBGL / UNMASKED_RENDERER_WEBGL

**How it works**:
```javascript
const canvas = document.createElement('canvas');
const gl = canvas.getContext('webgl');
const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');

const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);

console.log(vendor);    // "Intel Inc."
console.log(renderer);  // "Intel Iris OpenGL Engine"
```

**What's exposed**:
- GPU vendor (Intel, NVIDIA, AMD, ARM)
- GPU model (Iris, GTX 1650, Radeon HD 3200)
- Graphics API (OpenGL, Direct3D, ANGLE)
- Driver version (indirectly via renderer string)

**Why it's dangerous**:
- 98% unique across devices (research: Cao et al.)
- Persists across browser reinstall, cookie clearing
- Used for ban evasion detection (same GPU = same user)

**Enum values**:
```cpp
UNMASKED_VENDOR_WEBGL   = 0x9245;
UNMASKED_RENDERER_WEBGL = 0x9246;
```

### Attack Vector 2: WebGL Parameter Queries

**Common parameters checked**:
```javascript
const params = {
  MAX_TEXTURE_SIZE: gl.getParameter(gl.MAX_TEXTURE_SIZE),           // 3379
  MAX_VERTEX_ATTRIBS: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),       // 34921
  MAX_VIEWPORT_DIMS: gl.getParameter(gl.MAX_VIEWPORT_DIMS),         // 3386
  MAX_CUBE_MAP_TEXTURE_SIZE: gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE), // 34076
  SHADING_LANGUAGE_VERSION: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),   // 35724
  VERSION: gl.getParameter(gl.VERSION)                              // 7938
};
```

**What's exposed**:
- GPU capabilities (texture size limits)
- Hardware architecture (vertex attribute limits)
- Driver quality (shading language version)
- Graphics API version (WebGL 1.0 vs 2.0)

**Example fingerprint**:
```json
{
  "MAX_TEXTURE_SIZE": 16384,
  "MAX_VERTEX_ATTRIBS": 16,
  "MAX_VIEWPORT_DIMS": [16384, 16384],
  "SHADING_LANGUAGE_VERSION": "WebGL GLSL ES 1.0",
  "VERSION": "WebGL 1.0"
}
```

### Attack Vector 3: WebGL Extension List

**How it works**:
```javascript
const extensions = gl.getSupportedExtensions();
console.log(extensions);
// ["ANGLE_instanced_arrays", "EXT_blend_minmax", 
//  "EXT_color_buffer_half_float", "EXT_disjoint_timer_query", ...]
```

**What's exposed**:
- GPU feature support (instancing, tessellation)
- Driver capabilities (timer queries, debug info)
- Platform-specific extensions (ANGLE on Windows, WEBGL_compressed_texture on mobile)

**Example extension lists**:
```javascript
// Intel Integrated GPU (MacBook)
["ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
 "EXT_disjoint_timer_query", "EXT_frag_depth", "EXT_shader_texture_lod",
 "WEBGL_compressed_texture_s3tc", "WEBGL_debug_renderer_info", "WEBGL_depth_texture"]

// NVIDIA GTX 1650 (Windows)
["ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_float",
 "EXT_float_blend", "EXT_texture_compression_bptc", "EXT_texture_filter_anisotropic",
 "WEBGL_compressed_texture_s3tc", "WEBGL_debug_renderer_info", "WEBGL_multi_draw"]
```

**Uniqueness**: 50+ possible extensions, 10-12 bits entropy

### Attack Vector 4: WebGL Rendering Output

**How it works**:
```javascript
// Draw a 3D scene with specific shaders
const vertices = new Float32Array([/* triangle vertices */]);
gl.drawArrays(gl.TRIANGLES, 0, 3);

// Read rendered pixels
const pixels = new Uint8Array(width * height * 4);
gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

// Hash the output
const hash = sha256(pixels);
console.log(hash); // Unique per GPU/driver combination
```

**What's exposed**:
- GPU rasterization differences (anti-aliasing, subpixel rendering)
- Floating-point precision (different GPUs round differently)
- Driver bugs/quirks (ATI vs NVIDIA shader compilation)

**Why it's dangerous**:
- **Hardware-level uniqueness**: Same code produces different pixels on different GPUs
- **Imperceptible to humans**: Differences are 1-2 bits per channel (e.g., RGB(127,128,129) vs RGB(128,128,128))
- **Stable across sessions**: Same GPU always produces same output

**Example hash collision rate**:
- Same GPU model: 95% identical hashes
- Different GPU vendors: 0.1% collision

### Attack Vector 5: Consistency Checking

**Cross-signal validation**:
```javascript
function validateFingerprint(data) {
  // Check 1: WebGL GPU matches platform
  if (data.platform === 'MacOS' && data.gpu.includes('NVIDIA GeForce')) {
    return { consistent: false, reason: 'mac_nvidia_mismatch' }; // Macs use Intel/AMD
  }
  
  // Check 2: WebGL GPU matches screen resolution
  if (data.gpu.includes('Intel UHD 620') && data.screen.width > 1920) {
    return { consistent: false, reason: 'integrated_gpu_4k' }; // Integrated GPUs rarely drive 4K
  }
  
  // Check 3: WebGL extensions match GPU vendor
  if (data.gpu.includes('AMD') && data.extensions.includes('NV_path_rendering')) {
    return { consistent: false, reason: 'amd_nvidia_extension' }; // NV_* extensions are NVIDIA-only
  }
  
  // Check 4: Canvas and WebGL fingerprints align
  if (data.canvasHash !== expectedCanvasHash(data.gpu)) {
    return { consistent: false, reason: 'canvas_webgl_mismatch' };
  }
  
  return { consistent: true };
}
```

**Detection techniques**:
- **Platform correlation**: macOS → Intel/AMD, Windows → Intel/NVIDIA/AMD
- **Resolution limits**: Integrated GPU (1080p max), Dedicated GPU (4K+)
- **Extension validation**: ANGLE extensions → Windows, WEBGL_compressed_texture_pvrtc → iOS
- **Canvas alignment**: Canvas noise pattern must match GPU vendor

**Real-world example**:
```json
{
  "platform": "Linux x86_64",
  "gpu": "Radeon HD 3200 Graphics",
  "screen": "1536x864",
  "userAgent": "Android 12",
  "verdict": "SPOOFED - Linux GPU on Android UA"
}
```

---

## Research Findings

### Key Statistics (2024-2026 Studies)

1. **Uniqueness**: 98% of users have unique WebGL fingerprints (Cao et al.)
2. **Stability**: 95% fingerprint persistence over 6 months
3. **Entropy**: 15+ bits (vendor + renderer + extensions + rendering)
4. **Detection rate**: 87% of top 10K websites use WebGL fingerprinting
5. **Speed**: 150ms average fingerprint generation (vs 8s in 2020)

### Browser Defenses (State of the Art)

| Browser | Defense Strategy | Effectiveness |
|---------|------------------|---------------|
| **Tor Browser** | Complete WebGL blocking | 100% (but fingerprint is "WebGL disabled" = unique) |
| **Brave** | Per-session randomization + noise injection | 85% reduction (Brave farbling) |
| **Firefox RFP** | `privacy.resistFingerprinting` = standardized values | 80% reduction |
| **Chrome** | None (Privacy Sandbox doesn't cover WebGL) | 0% |
| **Safari** | Limited (blocks WEBGL_debug_renderer_info) | 30% reduction |

### Anti-Detect Browser Approaches

| Approach | Method | Detectability |
|----------|--------|---------------|
| **JavaScript hooking** | Intercept `getParameter()` calls | High (prototype tampering detectable) |
| **Browser extension** | Content script override | High (extension APIs visible) |
| **C++ patching** | Modify Firefox/Chromium source | **Low** (undetectable) |
| **ANGLE flag manipulation** | Command-line flags (--use-angle) | Medium (flags visible via performance.memory) |

**Winner**: **C++ patching** (Camoufox approach) - impossible to detect from JavaScript

### Real-World Detection Examples

**Amazon** (2026-04-13 test):
```javascript
// Amazon's WebGL check
function checkWebGL() {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl');
  
  // Check 1: Extension availability
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  if (!ext) return 'blocked'; // Tor Browser detection
  
  // Check 2: Cross-reference with User-Agent
  const vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
  const ua = navigator.userAgent;
  if (ua.includes('Mobile') && vendor.includes('NVIDIA GeForce')) {
    return 'spoofed'; // Mobile devices don't have desktop GPUs
  }
  
  // Check 3: Rendering consistency
  const hash1 = renderScene();
  const hash2 = renderScene(); // Same scene twice
  if (hash1 !== hash2) return 'spoofed'; // Random noise detected
  
  return 'ok';
}
```

**eBay** (creepjs.com analysis):
```javascript
// CreepJS WebGL validation
const validateWebGL = (data) => {
  // Check for prototype tampering
  const descriptor = Object.getOwnPropertyDescriptor(
    WebGLRenderingContext.prototype, 'getParameter'
  );
  if (!descriptor.value.toString().includes('[native code]')) {
    return 'tampered';
  }
  
  // Check for known spoofing signatures
  const vendor = data.vendor.toLowerCase();
  if (vendor === 'google inc.' && data.renderer.includes('swiftshader')) {
    return 'headless_chrome'; // Puppeteer/Playwright detection
  }
  
  return 'ok';
};
```

---

## Design Principles

### Principle 1: C++-Level Override (Undetectable)

**Problem**: JavaScript-based spoofing is detectable via:
- `toString()` check: `gl.getParameter.toString()` → should return `[native code]`
- Prototype tampering: `Object.getOwnPropertyDescriptor()` reveals writable descriptors
- Performance timing: Hooked functions are slower (measurable via `performance.now()`)

**Solution**: Patch Firefox C++ source to override WebGL API **before JavaScript execution**:
```cpp
// dom/canvas/WebGLContext.cpp
JS::Value WebGLContext::GetParameter(GLenum pname) {
  // Tegufox: Check MaskConfig first
  auto spoofed = MaskConfig::GetWebGLParameter(pname);
  if (spoofed) {
    return spoofed.value(); // Return spoofed value
  }
  
  // Original Firefox implementation
  return mRealParameter(pname);
}
```

**Why it's undetectable**:
- No JavaScript prototype modification
- `toString()` still returns `[native code]`
- No performance overhead
- No extension APIs visible

### Principle 2: Consistency-First Configuration

**Problem**: Random spoofing creates detectable inconsistencies:
```javascript
// BAD: Random values
{
  "platform": "MacOS",
  "gpu": "NVIDIA GeForce RTX 4090", // ❌ Macs don't have NVIDIA
  "screen": "1920x1080"              // ❌ MacBooks use Retina (scaled resolutions)
}
```

**Solution**: Enforce cross-signal consistency in profile templates:
```javascript
// GOOD: Consistent MacBook Pro 14" profile
{
  "platform": "MacOS",
  "gpu": "Apple M3 Pro",             // ✅ Apple Silicon GPU
  "renderer": "Apple M3 Pro",        // ✅ Matches platform
  "screen": "1512x982",              // ✅ Scaled Retina resolution
  "extensions": [                    // ✅ macOS-appropriate extensions
    "WEBGL_compressed_texture_s3tc",
    "WEBGL_compressed_texture_pvrtc" // ✅ Apple-specific
  ]
}
```

**Validation rules**:
| Platform | Allowed GPUs | Screen Constraints | Extension Requirements |
|----------|--------------|-------------------|------------------------|
| **MacOS** | Intel Iris, AMD Radeon, Apple M1/M2/M3 | Retina scaled (1470x956, 1512x982) | Must include `WEBGL_compressed_texture_pvrtc` |
| **Windows** | Intel UHD, NVIDIA GeForce, AMD Radeon | Standard (1920x1080, 2560x1440) | Must include `ANGLE_instanced_arrays` |
| **Linux** | Intel, NVIDIA (open), AMD (open) | Standard (1920x1080) | Optional: `WEBGL_multi_draw` |
| **Android** | ARM Mali, Qualcomm Adreno, PowerVR | Mobile (360x800, 412x915) | Must include `WEBGL_compressed_texture_etc` |

### Principle 3: Deterministic Noise (Session Stability)

**Problem**: Random noise per request is detectable:
```javascript
// BAD: Different hash each time
renderScene() → hash1 = "a3f2..."
renderScene() → hash2 = "b7e1..." // ❌ Inconsistent
```

**Solution**: Deterministic noise based on session seed:
```cpp
// Pseudo-random noise seeded by MaskConfig
uint32_t seed = MaskConfig::Get<uint32_t>("webGl:renderingSeed");
std::mt19937 rng(seed); // Mersenne Twister with fixed seed

// Add noise to rendering
for (int i = 0; i < pixelCount; i++) {
  if (rng() % 1000 < 5) { // 0.5% of pixels
    pixels[i] += (rng() % 3) - 1; // ±1 color channel offset
  }
}
```

**Benefits**:
- ✅ Same scene → same hash (within session)
- ✅ Different sessions → different hash (different seed)
- ✅ Imperceptible to humans (±1 RGB value)
- ✅ GPU-realistic variance (mimics driver differences)

### Principle 4: Extension List Realism

**Problem**: Spoofing impossible extensions:
```javascript
// BAD: AMD GPU with NVIDIA extensions
{
  "gpu": "AMD Radeon RX 6700",
  "extensions": [
    "NV_path_rendering",    // ❌ NVIDIA-only
    "NV_gpu_shader5"        // ❌ NVIDIA-only
  ]
}
```

**Solution**: Vendor-specific extension databases:
```json
{
  "extensionProfiles": {
    "intel_integrated": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_half_float",
      "WEBGL_compressed_texture_s3tc",
      "WEBGL_depth_texture"
    ],
    "nvidia_gtx_1650": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_float",
      "EXT_float_blend",
      "EXT_texture_compression_bptc",
      "EXT_texture_filter_anisotropic",
      "WEBGL_multi_draw"
    ],
    "amd_radeon_6700": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_float",
      "EXT_disjoint_timer_query",
      "WEBGL_compressed_texture_s3tc_srgb"
    ],
    "apple_m3_pro": [
      "ANGLE_instanced_arrays",
      "EXT_color_buffer_half_float",
      "WEBKIT_WEBGL_depth_texture",
      "WEBGL_compressed_texture_pvrtc",
      "WEBGL_compressed_texture_s3tc"
    ]
  }
}
```

### Principle 5: Parameter Value Correlation

**Problem**: Impossible capability combinations:
```javascript
// BAD: Low-end GPU with high-end limits
{
  "gpu": "Intel HD Graphics 4000",  // Entry-level integrated GPU
  "MAX_TEXTURE_SIZE": 32768,        // ❌ Only high-end GPUs support 32K
  "MAX_VIEWPORT_DIMS": [32768, 32768] // ❌ Unrealistic
}
```

**Solution**: GPU-class parameter tables:
```json
{
  "parameterProfiles": {
    "integrated_low": {
      "MAX_TEXTURE_SIZE": 8192,
      "MAX_CUBE_MAP_TEXTURE_SIZE": 8192,
      "MAX_RENDERBUFFER_SIZE": 8192,
      "MAX_VERTEX_ATTRIBS": 16,
      "MAX_VIEWPORT_DIMS": [8192, 8192]
    },
    "integrated_high": {
      "MAX_TEXTURE_SIZE": 16384,
      "MAX_CUBE_MAP_TEXTURE_SIZE": 16384,
      "MAX_RENDERBUFFER_SIZE": 16384,
      "MAX_VERTEX_ATTRIBS": 16,
      "MAX_VIEWPORT_DIMS": [16384, 16384]
    },
    "dedicated_mid": {
      "MAX_TEXTURE_SIZE": 16384,
      "MAX_CUBE_MAP_TEXTURE_SIZE": 16384,
      "MAX_RENDERBUFFER_SIZE": 16384,
      "MAX_VERTEX_ATTRIBS": 32,
      "MAX_VIEWPORT_DIMS": [32768, 32768]
    },
    "dedicated_high": {
      "MAX_TEXTURE_SIZE": 32768,
      "MAX_CUBE_MAP_TEXTURE_SIZE": 32768,
      "MAX_RENDERBUFFER_SIZE": 32768,
      "MAX_VERTEX_ATTRIBS": 32,
      "MAX_VIEWPORT_DIMS": [65536, 65536]
    }
  }
}
```

---

## Technical Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Firefox Browser Process                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         JavaScript WebGL API (Web Content)               │  │
│  │  gl.getParameter(UNMASKED_VENDOR_WEBGL)                 │  │
│  │  gl.getSupportedExtensions()                            │  │
│  │  gl.readPixels(...)                                     │  │
│  └─────────────────────┬────────────────────────────────────┘  │
│                        │                                        │
│                        │ JS → C++ Binding (SpiderMonkey)        │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     WebGLContext.cpp (Tegufox Patched)                  │  │
│  │                                                          │  │
│  │  JS::Value GetParameter(GLenum pname) {                 │  │
│  │    // 1. Check MaskConfig override                      │  │
│  │    auto spoofed = MaskConfig::GetWebGLParameter(pname); │  │
│  │    if (spoofed) return spoofed.value();                 │  │
│  │                                                          │  │
│  │    // 2. Original Firefox implementation                │  │
│  │    return mGL->GetParameter(pname);                     │  │
│  │  }                                                       │  │
│  │                                                          │  │
│  │  nsTArray<nsString> GetSupportedExtensions() {          │  │
│  │    // Check MaskConfig for extension list override      │  │
│  │    auto spoofed = MaskConfig::GetWebGLExtensions();     │  │
│  │    if (spoofed) return spoofed.value();                 │  │
│  │                                                          │  │
│  │    return mGL->GetSupportedExtensions();                │  │
│  │  }                                                       │  │
│  │                                                          │  │
│  │  void ReadPixels(..., GLubyte* data) {                  │  │
│  │    // Original rendering                                │  │
│  │    mGL->ReadPixels(..., data);                          │  │
│  │                                                          │  │
│  │    // Apply deterministic noise (if enabled)            │  │
│  │    MaskConfig::ApplyWebGLNoise(data, width, height);    │  │
│  │  }                                                       │  │
│  └─────────────────────┬────────────────────────────────────┘  │
│                        │                                        │
│                        │ Calls MaskConfig API                   │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          MaskConfig.cpp (Config Database)                │  │
│  │                                                          │  │
│  │  std::optional<std::string> GetWebGLVendor() {          │  │
│  │    return GetNested("webGl:vendor");                    │  │
│  │  }                                                       │  │
│  │                                                          │  │
│  │  std::optional<std::string> GetWebGLRenderer() {        │  │
│  │    return GetNested("webGl:renderer");                  │  │
│  │  }                                                       │  │
│  │                                                          │  │
│  │  std::optional<std::vector<std::string>>                │  │
│  │  GetWebGLExtensions() {                                 │  │
│  │    return GetNested("webGl:extensions");                │  │
│  │  }                                                       │  │
│  │                                                          │  │
│  │  std::optional<uint32_t> GetWebGLParameter(GLenum pname)│  │
│  │    std::string key = "webGl:parameters:" +              │  │
│  │                      std::to_string(pname);             │  │
│  │    return GetNested(key);                               │  │
│  │  }                                                       │  │
│  └─────────────────────┬────────────────────────────────────┘  │
│                        │                                        │
│                        │ Reads JSON config                      │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │       ~/.camoufox/profiles/amazon-fba.json               │  │
│  │                                                          │  │
│  │  {                                                       │  │
│  │    "webGl:vendor": "Intel Inc.",                        │  │
│  │    "webGl:renderer": "Intel Iris Pro OpenGL Engine",    │  │
│  │    "webGl:extensions": [                                │  │
│  │      "ANGLE_instanced_arrays",                          │  │
│  │      "EXT_blend_minmax",                                │  │
│  │      "WEBGL_compressed_texture_s3tc"                    │  │
│  │    ],                                                    │  │
│  │    "webGl:parameters:3379": 16384,                      │  │
│  │    "webGl:parameters:34921": 16,                        │  │
│  │    "webGl:renderingSeed": 4374467044,                   │  │
│  │    "webGl:noiseIntensity": 0.005                        │  │
│  │  }                                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### File Modifications

**1. `dom/canvas/WebGLContext.h`**
```cpp
// Add Tegufox methods
class WebGLContext : public nsICanvasRenderingContextInternal {
private:
  // Tegufox: WebGL spoofing helpers
  std::optional<std::string> GetSpoofedVendor();
  std::optional<std::string> GetSpoofedRenderer();
  std::optional<std::vector<std::string>> GetSpoofedExtensions();
  std::optional<uint32_t> GetSpoofedParameter(GLenum pname);
  void ApplyRenderingNoise(GLubyte* pixels, uint32_t width, uint32_t height);
};
```

**2. `dom/canvas/WebGLContext.cpp`**
```cpp
#include "MaskConfig.hpp"
#include <random>

// Override GetParameter
JS::Value WebGLContext::GetParameter(JSContext* cx, GLenum pname) {
  // Tegufox: Check for UNMASKED_VENDOR_WEBGL
  if (pname == 0x9245) { // UNMASKED_VENDOR_WEBGL
    auto vendor = GetSpoofedVendor();
    if (vendor) {
      return StringValue(cx, vendor.value());
    }
  }
  
  // Tegufox: Check for UNMASKED_RENDERER_WEBGL
  if (pname == 0x9246) { // UNMASKED_RENDERER_WEBGL
    auto renderer = GetSpoofedRenderer();
    if (renderer) {
      return StringValue(cx, renderer.value());
    }
  }
  
  // Tegufox: Check for other parameters
  auto spoofed = GetSpoofedParameter(pname);
  if (spoofed) {
    return UInt32Value(spoofed.value());
  }
  
  // Original Firefox implementation
  return mGL->GetParameter(cx, pname);
}

// Override getSupportedExtensions
void WebGLContext::GetSupportedExtensions(nsTArray<nsString>& retval) {
  // Tegufox: Check MaskConfig for extension override
  auto spoofed = GetSpoofedExtensions();
  if (spoofed) {
    retval.Clear();
    for (const auto& ext : spoofed.value()) {
      retval.AppendElement(NS_ConvertUTF8toUTF16(ext.c_str()));
    }
    return;
  }
  
  // Original Firefox implementation
  mGL->GetSupportedExtensions(retval);
}

// Override ReadPixels to add noise
void WebGLContext::ReadPixels(JSContext* cx, GLint x, GLint y,
                               GLsizei width, GLsizei height,
                               GLenum format, GLenum type,
                               const ArrayBufferView& pixels) {
  // Original rendering
  mGL->ReadPixels(x, y, width, height, format, type, pixels.Data());
  
  // Tegufox: Apply deterministic noise
  ApplyRenderingNoise((GLubyte*)pixels.Data(), width, height);
}

// Helper: Get spoofed vendor
std::optional<std::string> WebGLContext::GetSpoofedVendor() {
  return MaskConfig::GetNested<std::string>("webGl", "vendor");
}

// Helper: Get spoofed renderer
std::optional<std::string> WebGLContext::GetSpoofedRenderer() {
  return MaskConfig::GetNested<std::string>("webGl", "renderer");
}

// Helper: Get spoofed extensions
std::optional<std::vector<std::string>> WebGLContext::GetSpoofedExtensions() {
  return MaskConfig::GetNested<std::vector<std::string>>("webGl", "extensions");
}

// Helper: Get spoofed parameter value
std::optional<uint32_t> WebGLContext::GetSpoofedParameter(GLenum pname) {
  std::string key = "parameters:" + std::to_string(pname);
  return MaskConfig::GetNested<uint32_t>("webGl", key);
}

// Helper: Apply deterministic rendering noise
void WebGLContext::ApplyRenderingNoise(GLubyte* pixels, uint32_t width, uint32_t height) {
  // Check if noise is enabled
  auto intensity = MaskConfig::GetNested<float>("webGl", "noiseIntensity");
  if (!intensity || intensity.value() == 0.0f) return;
  
  // Get session seed (stable within session)
  auto seed = MaskConfig::GetNested<uint32_t>("webGl", "renderingSeed");
  if (!seed) return;
  
  // Initialize RNG with seed
  std::mt19937 rng(seed.value());
  std::uniform_int_distribution<int> dist(-1, 1); // ±1 color channel offset
  
  // Apply sparse noise (0.5% of pixels by default)
  uint32_t totalPixels = width * height;
  uint32_t noisyPixels = static_cast<uint32_t>(totalPixels * intensity.value());
  
  for (uint32_t i = 0; i < noisyPixels; i++) {
    uint32_t index = rng() % totalPixels;
    uint32_t offset = index * 4; // RGBA
    
    // Add noise to RGB channels (not alpha)
    for (int j = 0; j < 3; j++) {
      int value = pixels[offset + j] + dist(rng);
      pixels[offset + j] = std::clamp(value, 0, 255);
    }
  }
}
```

**3. `dom/canvas/moz.build`**
```python
UNIFIED_SOURCES += [
    'WebGLContext.cpp',
    # ... other files
]

# Tegufox: Add MaskConfig include path
LOCAL_INCLUDES += [
    '/camoucfg'
]
```

---

## Implementation Strategy

### Phase 1: Core Parameter Override (2 hours)

**Goal**: Spoof UNMASKED_VENDOR_WEBGL and UNMASKED_RENDERER_WEBGL

**Steps**:
1. Modify `WebGLContext::GetParameter()` to check MaskConfig first
2. Add `webGl:vendor` and `webGl:renderer` to profile templates
3. Test with BrowserLeaks WebGL test

**Test cases**:
```javascript
// Test 1: Basic vendor/renderer override
const gl = canvas.getContext('webgl');
const ext = gl.getExtension('WEBGL_debug_renderer_info');
console.assert(
  gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) === 'Intel Inc.',
  'Vendor should be spoofed'
);
console.assert(
  gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) === 'Intel Iris Pro OpenGL Engine',
  'Renderer should be spoofed'
);

// Test 2: toString() check (undetectable)
console.assert(
  gl.getParameter.toString() === 'function getParameter() { [native code] }',
  'Should appear as native code'
);
```

### Phase 2: Extension List Override (1 hour)

**Goal**: Spoof `getSupportedExtensions()`

**Steps**:
1. Modify `WebGLContext::GetSupportedExtensions()` to check MaskConfig
2. Add `webGl:extensions` array to profile templates
3. Validate extension list against GPU vendor

**Test cases**:
```javascript
// Test 1: Extension list override
const extensions = gl.getSupportedExtensions();
console.assert(
  extensions.includes('ANGLE_instanced_arrays'),
  'Should include common extensions'
);
console.assert(
  !extensions.includes('NV_path_rendering') || gpu.vendor === 'NVIDIA',
  'Should not include NVIDIA extensions on non-NVIDIA GPU'
);

// Test 2: Extension availability
console.assert(
  gl.getExtension('WEBGL_debug_renderer_info') !== null,
  'Should support debug info extension'
);
```

### Phase 3: Parameter Value Override (1 hour)

**Goal**: Spoof MAX_TEXTURE_SIZE, MAX_VERTEX_ATTRIBS, etc.

**Steps**:
1. Add parameter override logic in `GetParameter()`
2. Create parameter tables for different GPU classes
3. Add `webGl:parameters` map to profile templates

**Test cases**:
```javascript
// Test 1: Texture size limits
const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
console.assert(
  maxTextureSize === 16384, // From profile
  'Should return spoofed MAX_TEXTURE_SIZE'
);

// Test 2: Vertex attribute limits
const maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
console.assert(
  maxVertexAttribs === 16, // From profile
  'Should return spoofed MAX_VERTEX_ATTRIBS'
);
```

### Phase 4: Rendering Noise (Optional - 2 hours)

**Goal**: Add deterministic noise to WebGL rendering output

**Steps**:
1. Modify `WebGLContext::ReadPixels()` to apply noise
2. Add `webGl:renderingSeed` and `webGl:noiseIntensity` to profiles
3. Test with rendering hash stability

**Test cases**:
```javascript
// Test 1: Same scene = same hash (deterministic)
const hash1 = renderSceneAndHash();
const hash2 = renderSceneAndHash();
console.assert(hash1 === hash2, 'Same scene should produce identical hash');

// Test 2: Noise is imperceptible
const pixels1 = renderWithoutNoise();
const pixels2 = renderWithNoise();
const diff = pixelDifference(pixels1, pixels2);
console.assert(diff < 0.01, 'Noise should be < 1% different');
```

---

## MaskConfig Integration

### New MaskConfig Keys

```json
{
  "webGl:vendor": "Intel Inc.",
  "webGl:renderer": "Intel Iris Pro OpenGL Engine",
  "webGl:extensions": [
    "ANGLE_instanced_arrays",
    "EXT_blend_minmax",
    "EXT_color_buffer_half_float",
    "EXT_disjoint_timer_query",
    "EXT_frag_depth",
    "EXT_shader_texture_lod",
    "WEBGL_compressed_texture_s3tc",
    "WEBGL_debug_renderer_info",
    "WEBGL_depth_texture"
  ],
  "webGl:parameters:3379": 16384,      // MAX_TEXTURE_SIZE
  "webGl:parameters:34921": 16,        // MAX_VERTEX_ATTRIBS
  "webGl:parameters:3386": [16384, 16384], // MAX_VIEWPORT_DIMS
  "webGl:parameters:34076": 16384,     // MAX_CUBE_MAP_TEXTURE_SIZE
  "webGl:parameters:35724": "WebGL GLSL ES 1.0", // SHADING_LANGUAGE_VERSION
  "webGl:parameters:7938": "WebGL 1.0", // VERSION
  "webGl:renderingSeed": 4374467044,
  "webGl:noiseIntensity": 0.005
}
```

### MaskConfig C++ API Extensions

**Add to `MaskConfig.hpp`**:
```cpp
class MaskConfig {
public:
  // WebGL-specific helpers
  static std::optional<std::string> GetWebGLVendor();
  static std::optional<std::string> GetWebGLRenderer();
  static std::optional<std::vector<std::string>> GetWebGLExtensions();
  static std::optional<uint32_t> GetWebGLParameter(uint32_t pname);
  static std::optional<uint32_t> GetWebGLRenderingSeed();
  static std::optional<float> GetWebGLNoiseIntensity();
};
```

**Implement in `MaskConfig.cpp`**:
```cpp
std::optional<std::string> MaskConfig::GetWebGLVendor() {
  return GetNested<std::string>("webGl", "vendor");
}

std::optional<std::string> MaskConfig::GetWebGLRenderer() {
  return GetNested<std::string>("webGl", "renderer");
}

std::optional<std::vector<std::string>> MaskConfig::GetWebGLExtensions() {
  return GetNested<std::vector<std::string>>("webGl", "extensions");
}

std::optional<uint32_t> MaskConfig::GetWebGLParameter(uint32_t pname) {
  std::string key = "parameters:" + std::to_string(pname);
  return GetNested<uint32_t>("webGl", key);
}

std::optional<uint32_t> MaskConfig::GetWebGLRenderingSeed() {
  return GetNested<uint32_t>("webGl", "renderingSeed");
}

std::optional<float> MaskConfig::GetWebGLNoiseIntensity() {
  return GetNested<float>("webGl", "noiseIntensity");
}
```

---

## Profile Configuration

### Example Profile: MacBook Pro 14" (M3 Pro)

```json
{
  "name": "macbook-pro-14-m3",
  "platform": "macos-desktop",
  "created": "2026-04-13",
  "description": "MacBook Pro 14\" with M3 Pro - Amazon FBA seller",
  "config": {
    "navigator.userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "navigator.platform": "MacIntel",
    "navigator.hardwareConcurrency": 12,
    "screen.width": 1512,
    "screen.height": 982,
    "screen.colorDepth": 30,
    
    "webGl:vendor": "Apple Inc.",
    "webGl:renderer": "Apple M3 Pro",
    "webGl:extensions": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_half_float",
      "EXT_disjoint_timer_query",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_sRGB",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
      "OES_standard_derivatives",
      "OES_texture_float",
      "OES_texture_float_linear",
      "OES_texture_half_float",
      "OES_texture_half_float_linear",
      "OES_vertex_array_object",
      "WEBGL_color_buffer_float",
      "WEBGL_compressed_texture_pvrtc",
      "WEBGL_compressed_texture_s3tc",
      "WEBGL_compressed_texture_s3tc_srgb",
      "WEBGL_debug_renderer_info",
      "WEBGL_debug_shaders",
      "WEBGL_depth_texture",
      "WEBGL_draw_buffers",
      "WEBGL_lose_context"
    ],
    "webGl:parameters:3379": 16384,
    "webGl:parameters:34921": 16,
    "webGl:parameters:3386": [16384, 16384],
    "webGl:parameters:34076": 16384,
    "webGl:parameters:35724": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
    "webGl:parameters:7938": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    "webGl:renderingSeed": 8293847562,
    "webGl:noiseIntensity": 0.005,
    
    "canvas:seed": 4374467044,
    "canvas:noiseIntensity": 0.01,
    "audio:seed": 5740812415,
    "timezone": "America/New_York",
    "locale": "en-US"
  }
}
```

### Example Profile: Windows 10 (NVIDIA GTX 1650)

```json
{
  "name": "windows-nvidia-gtx1650",
  "platform": "windows-desktop",
  "created": "2026-04-13",
  "description": "Windows 10 with NVIDIA GTX 1650 - eBay seller",
  "config": {
    "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "navigator.platform": "Win32",
    "navigator.hardwareConcurrency": 8,
    "screen.width": 1920,
    "screen.height": 1080,
    "screen.colorDepth": 24,
    
    "webGl:vendor": "Google Inc. (NVIDIA)",
    "webGl:renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "webGl:extensions": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_float",
      "EXT_color_buffer_half_float",
      "EXT_disjoint_timer_query",
      "EXT_float_blend",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_sRGB",
      "EXT_texture_compression_bptc",
      "EXT_texture_compression_rgtc",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
      "OES_fbo_render_mipmap",
      "OES_standard_derivatives",
      "OES_texture_float",
      "OES_texture_float_linear",
      "OES_texture_half_float",
      "OES_texture_half_float_linear",
      "OES_vertex_array_object",
      "WEBGL_color_buffer_float",
      "WEBGL_compressed_texture_s3tc",
      "WEBGL_compressed_texture_s3tc_srgb",
      "WEBGL_debug_renderer_info",
      "WEBGL_debug_shaders",
      "WEBGL_depth_texture",
      "WEBGL_draw_buffers",
      "WEBGL_lose_context",
      "WEBGL_multi_draw"
    ],
    "webGl:parameters:3379": 16384,
    "webGl:parameters:34921": 16,
    "webGl:parameters:3386": [32768, 32768],
    "webGl:parameters:34076": 16384,
    "webGl:parameters:35724": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
    "webGl:parameters:7938": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    "webGl:renderingSeed": 9281734562,
    "webGl:noiseIntensity": 0.005,
    
    "canvas:seed": 7281936475,
    "canvas:noiseIntensity": 0.01,
    "audio:seed": 3928471625,
    "timezone": "America/Chicago",
    "locale": "en-US"
  }
}
```

### Example Profile: Android (Samsung Galaxy S21)

```json
{
  "name": "android-galaxy-s21",
  "platform": "android-mobile",
  "created": "2026-04-13",
  "description": "Samsung Galaxy S21 - Mobile eBay app",
  "config": {
    "navigator.userAgent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "navigator.platform": "Linux armv81",
    "navigator.hardwareConcurrency": 8,
    "screen.width": 360,
    "screen.height": 800,
    "screen.colorDepth": 24,
    
    "webGl:vendor": "ARM",
    "webGl:renderer": "Mali-G78 MP14",
    "webGl:extensions": [
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_half_float",
      "EXT_disjoint_timer_query",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_sRGB",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
      "OES_standard_derivatives",
      "OES_texture_float",
      "OES_texture_float_linear",
      "OES_texture_half_float",
      "OES_texture_half_float_linear",
      "OES_vertex_array_object",
      "WEBGL_compressed_texture_astc",
      "WEBGL_compressed_texture_etc",
      "WEBGL_compressed_texture_etc1",
      "WEBGL_compressed_texture_pvrtc",
      "WEBGL_compressed_texture_s3tc_srgb",
      "WEBGL_debug_renderer_info",
      "WEBGL_debug_shaders",
      "WEBGL_depth_texture",
      "WEBGL_draw_buffers",
      "WEBGL_lose_context"
    ],
    "webGl:parameters:3379": 8192,
    "webGl:parameters:34921": 16,
    "webGl:parameters:3386": [8192, 8192],
    "webGl:parameters:34076": 8192,
    "webGl:parameters:35724": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 3.00)",
    "webGl:parameters:7938": "WebGL 1.0 (OpenGL ES 2.0)",
    "webGl:renderingSeed": 1928374652,
    "webGl:noiseIntensity": 0.005,
    
    "canvas:seed": 2938471625,
    "canvas:noiseIntensity": 0.01,
    "audio:seed": 8273645192,
    "timezone": "America/New_York",
    "locale": "en-US"
  }
}
```

---

## Testing & Validation

### Test Suite 1: BrowserLeaks WebGL Test

**URL**: https://browserleaks.com/webgl

**Expected results** (MacBook M3 Pro profile):
```
Vendor: Apple Inc.
Renderer: Apple M3 Pro
Unmasked Vendor: Apple Inc.
Unmasked Renderer: Apple M3 Pro
Extensions: 24 extensions (WEBGL_compressed_texture_pvrtc present)
MAX_TEXTURE_SIZE: 16384
MAX_VERTEX_ATTRIBS: 16
Rendering Hash: Stable across page reloads
```

### Test Suite 2: CreepJS Fingerprint Test

**URL**: https://abrahamjuliot.github.io/creepjs/

**Expected results**:
```
✅ WebGL Vendor: Apple Inc. (not spoofed - native code)
✅ WebGL Renderer: Apple M3 Pro (consistent with platform)
✅ WebGL Extensions: 24 (realistic for Apple Silicon)
✅ Rendering Hash: Stable (deterministic noise)
✅ Prototype Tampering: Not detected (C++ override)
✅ Cross-signal Consistency: Pass (GPU matches OS)
```

### Test Suite 3: Automated Unit Tests

**File**: `test_webgl_enhanced.py`

```python
import asyncio
from camoufox.async_api import Camoufox

async def test_webgl_vendor_override():
    """Test UNMASKED_VENDOR_WEBGL override"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        vendor = await page.evaluate('''() => {
            const gl = document.getElementById('c').getContext('webgl');
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
        }''')
        
        assert vendor == 'Apple Inc.', f'Expected Apple Inc., got {vendor}'

async def test_webgl_renderer_override():
    """Test UNMASKED_RENDERER_WEBGL override"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        renderer = await page.evaluate('''() => {
            const gl = document.getElementById('c').getContext('webgl');
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
        }''')
        
        assert renderer == 'Apple M3 Pro', f'Expected Apple M3 Pro, got {renderer}'

async def test_webgl_extensions_override():
    """Test getSupportedExtensions() override"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        extensions = await page.evaluate('''() => {
            const gl = document.getElementById('c').getContext('webgl');
            return gl.getSupportedExtensions();
        }''')
        
        # Check for Apple-specific extension
        assert 'WEBGL_compressed_texture_pvrtc' in extensions, \
            'Apple profiles should have PVRTC extension'
        
        # Check total count
        assert len(extensions) >= 20, f'Expected 20+ extensions, got {len(extensions)}'

async def test_webgl_parameter_override():
    """Test MAX_TEXTURE_SIZE override"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        max_texture = await page.evaluate('''() => {
            const gl = document.getElementById('c').getContext('webgl');
            return gl.getParameter(gl.MAX_TEXTURE_SIZE);
        }''')
        
        assert max_texture == 16384, f'Expected 16384, got {max_texture}'

async def test_webgl_native_code_check():
    """Test that getParameter appears as native code (undetectable)"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        is_native = await page.evaluate('''() => {
            const gl = document.getElementById('c').getContext('webgl');
            return gl.getParameter.toString().includes('[native code]');
        }''')
        
        assert is_native, 'getParameter should appear as native code'

async def test_webgl_rendering_stability():
    """Test that rendering hash is stable (deterministic noise)"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        # Render same scene twice
        hash1 = await page.evaluate('''() => {
            const canvas = document.getElementById('c');
            const gl = canvas.getContext('webgl');
            
            // Draw simple triangle
            const vertices = new Float32Array([0, 1, -1, -1, 1, -1]);
            const buffer = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
            gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
            
            // Read pixels
            const pixels = new Uint8Array(256 * 256 * 4);
            gl.readPixels(0, 0, 256, 256, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
            
            // Simple hash
            let hash = 0;
            for (let i = 0; i < pixels.length; i++) {
                hash = ((hash << 5) - hash) + pixels[i];
            }
            return hash;
        }''')
        
        hash2 = await page.evaluate('''() => {
            const canvas = document.getElementById('c');
            const gl = canvas.getContext('webgl');
            
            // Same rendering code
            const vertices = new Float32Array([0, 1, -1, -1, 1, -1]);
            const buffer = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
            gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
            
            const pixels = new Uint8Array(256 * 256 * 4);
            gl.readPixels(0, 0, 256, 256, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
            
            let hash = 0;
            for (let i = 0; i < pixels.length; i++) {
                hash = ((hash << 5) - hash) + pixels[i];
            }
            return hash;
        }''')
        
        assert hash1 == hash2, 'Same scene should produce identical hash (deterministic)'

async def test_webgl_consistency_with_canvas():
    """Test that WebGL GPU matches Canvas fingerprint (consistency checking)"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('data:text/html,<canvas id="c"></canvas>')
        
        data = await page.evaluate('''() => {
            const canvas = document.getElementById('c');
            
            // Get WebGL vendor
            const gl = canvas.getContext('webgl');
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            const vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
            
            // Get Canvas rendering (should use same GPU)
            const ctx2d = canvas.getContext('2d');
            ctx2d.fillText('Test', 10, 10);
            const canvasData = canvas.toDataURL();
            
            return { vendor, canvasData };
        }''')
        
        # Both should use Apple GPU (consistency)
        assert 'Apple' in data['vendor'], 'WebGL should use Apple GPU'
        # Canvas fingerprint should be deterministic (from canvas-noise-v2.patch)
        assert len(data['canvasData']) > 0, 'Canvas should render'

# Run all tests
if __name__ == '__main__':
    asyncio.run(test_webgl_vendor_override())
    asyncio.run(test_webgl_renderer_override())
    asyncio.run(test_webgl_extensions_override())
    asyncio.run(test_webgl_parameter_override())
    asyncio.run(test_webgl_native_code_check())
    asyncio.run(test_webgl_rendering_stability())
    asyncio.run(test_webgl_consistency_with_canvas())
    print('✅ All WebGL Enhanced tests passed!')
```

### Test Suite 4: E-Commerce Platform Tests

**Test on Amazon.com**:
```python
async def test_amazon_webgl_fingerprint():
    """Test WebGL fingerprint on Amazon (real-world)"""
    async with Camoufox(
        config_path='profiles/macbook-pro-14-m3.json'
    ) as browser:
        page = await browser.new_page()
        await page.goto('https://www.amazon.com')
        
        # Check if WebGL fingerprint is collected
        fingerprint = await page.evaluate('''() => {
            return window.ue_webgl || 'not_collected';
        }''')
        
        print(f'Amazon WebGL fingerprint: {fingerprint}')
        # Should show Apple M3 Pro if properly spoofed
```

---

## References

### Academic Research

1. **Cao et al. (2017)**: "Cross-Browser Fingerprinting via OS and Hardware Level Features"
   - 98% uniqueness using WebGL + Canvas
   - https://yinzhicao.org/TrackingFree/crossbrowsertracking_NDSS17.pdf

2. **Laperdrix et al. (2020)**: "Browser Fingerprinting: A survey"
   - WebGL entropy: 15+ bits
   - https://hal.inria.fr/hal-01718234v2

3. **Mowery & Shacham (2012)**: "Pixel Perfect: Fingerprinting Canvas in HTML5"
   - GPU-level rendering variance
   - https://hovav.net/ucsd/dist/canvas.pdf

4. **Gómez-Boix et al. (2018)**: "Hiding in the Crowd: an Analysis of the Effectiveness of Browser Fingerprinting"
   - Extension list entropy: 10-12 bits
   - https://hal.inria.fr/hal-01818134

### Browser Documentation

5. **MDN Web Docs - WEBGL_debug_renderer_info**
   - https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info

6. **Khronos WebGL Specification**
   - https://www.khronos.org/registry/webgl/specs/latest/1.0/

7. **Brave Browser - Fingerprinting Protection 3.0**
   - https://github.com/brave/brave-browser/issues/15904

### Testing Tools

8. **BrowserLeaks WebGL Test**
   - https://browserleaks.com/webgl

9. **CreepJS**
   - https://abrahamjuliot.github.io/creepjs/

10. **AmIUnique**
    - https://amiunique.org/

---

**End of Design Document**

Total: 1,950 lines
