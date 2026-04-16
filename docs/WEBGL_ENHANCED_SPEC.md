# WebGL Enhanced Patch - Technical Specification

**Tegufox Browser Toolkit**  
**Phase 2 - Week 1 Days 5-7**  
**Patch ID**: webgl-enhanced-gpu-consistency  
**Priority**: HIGH  
**Status**: 🔨 IN PROGRESS

---

## Executive Summary

WebGL Enhanced patch adds **GPU profile consistency validation** on top of Camoufox's existing WebGL spoofing, ensuring that vendor, renderer, extensions, and capabilities all match a coherent GPU profile.

**Key Enhancement**: While Camoufox allows setting arbitrary vendor/renderer values, Tegufox ensures these values are **consistent and believable** by validating against real GPU profiles.

---

## Problem Statement

### Current Camoufox Implementation

Camoufox allows spoofing:
- ✅ `UNMASKED_VENDOR_WEBGL` (e.g., "Google Inc.")
- ✅ `UNMASKED_RENDERER_WEBGL` (e.g., "ANGLE (NVIDIA GeForce RTX 3080)")

**Issue**: No validation of consistency. User can set:
```json
{
  "webGl:vendor": "Intel Inc.",
  "webGl:renderer": "ANGLE (NVIDIA GeForce RTX 3080)"
}
```
This is **DETECTABLE** because Intel vendor with NVIDIA renderer is impossible.

### Detection Vectors

Websites can detect inconsistency by checking:

1. **Vendor-Renderer Mismatch**
   ```javascript
   const vendor = gl.getParameter(gl.getExtension('WEBGL_debug_renderer_info').UNMASKED_VENDOR_WEBGL);
   const renderer = gl.getParameter(gl.getExtension('WEBGL_debug_renderer_info').UNMASKED_RENDERER_WEBGL);
   
   // Detection: Intel vendor with NVIDIA renderer
   if (vendor.includes("Intel") && renderer.includes("NVIDIA")) {
     alert("FAKE BROWSER DETECTED!");
   }
   ```

2. **Extension List Mismatch**
   ```javascript
   const extensions = gl.getSupportedExtensions();
   
   // NVIDIA GPUs always support "WEBGL_compressed_texture_s3tc"
   // Intel HD Graphics doesn't
   if (renderer.includes("NVIDIA") && !extensions.includes("WEBGL_compressed_texture_s3tc")) {
     alert("INCONSISTENT GPU!");
   }
   ```

3. **Capability Mismatch**
   ```javascript
   const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
   
   // RTX 3080 supports 32768
   // Intel HD Graphics 620 only supports 16384
   if (renderer.includes("RTX 3080") && maxTextureSize < 16384) {
     alert("CAPABILITY MISMATCH!");
   }
   ```

---

## Solution Design

### Architecture

```
Tegufox GPU Consistency Layer
    ↓
Camoufox WebGL Spoofing (MaskConfig)
    ↓
Firefox WebGL Implementation
    ↓
GPU Driver
```

### GPU Profile Database

Create a database of **real GPU profiles** with consistent values:

```cpp
// TegufoxGPUProfiles.h
struct GPUProfile {
  std::string vendor;
  std::string renderer;
  std::vector<std::string> extensions;
  uint32_t maxTextureSize;
  uint32_t maxCubeMapTextureSize;
  uint32_t maxRenderBufferSize;
  uint32_t maxVertexAttribs;
  // ... other capabilities
};

static const std::vector<GPUProfile> KNOWN_GPU_PROFILES = {
  // NVIDIA RTX 3080
  {
    .vendor = "Google Inc. (NVIDIA)",
    .renderer = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.9649)",
    .extensions = {
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_half_float",
      "EXT_disjoint_timer_query",
      "EXT_float_blend",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_texture_compression_rgtc",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
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
    },
    .maxTextureSize = 32768,
    .maxCubeMapTextureSize = 32768,
    .maxRenderBufferSize = 32768,
    .maxVertexAttribs = 16
  },
  
  // Intel HD Graphics 620
  {
    .vendor = "Google Inc. (Intel)",
    .renderer = "ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.100.8681)",
    .extensions = {
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_half_float",
      "EXT_float_blend",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
      "OES_standard_derivatives",
      "OES_texture_float",
      "OES_texture_float_linear",
      "OES_texture_half_float",
      "OES_texture_half_float_linear",
      "OES_vertex_array_object",
      "WEBGL_color_buffer_float",
      "WEBGL_compressed_texture_s3tc",
      "WEBGL_debug_renderer_info",
      "WEBGL_debug_shaders",
      "WEBGL_depth_texture",
      "WEBGL_draw_buffers",
      "WEBGL_lose_context"
    },
    .maxTextureSize = 16384,
    .maxCubeMapTextureSize = 16384,
    .maxRenderBufferSize = 16384,
    .maxVertexAttribs = 16
  },
  
  // AMD Radeon RX 6800
  {
    .vendor = "Google Inc. (AMD)",
    .renderer = "ANGLE (AMD, AMD Radeon RX 6800 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.13025.1000)",
    .extensions = {
      "ANGLE_instanced_arrays",
      "EXT_blend_minmax",
      "EXT_color_buffer_float",
      "EXT_color_buffer_half_float",
      "EXT_disjoint_timer_query",
      "EXT_float_blend",
      "EXT_frag_depth",
      "EXT_shader_texture_lod",
      "EXT_texture_compression_rgtc",
      "EXT_texture_filter_anisotropic",
      "OES_element_index_uint",
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
    },
    .maxTextureSize = 32768,
    .maxCubeMapTextureSize = 32768,
    .maxRenderBufferSize = 32768,
    .maxVertexAttribs = 16
  }
};
```

---

## Implementation Plan

### Phase 1: Create GPU Profile Database

**New File**: `dom/canvas/TegufoxGPUProfiles.h`

```cpp
#ifndef DOM_CANVAS_TEGUFOX_GPU_PROFILES_H_
#define DOM_CANVAS_TEGUFOX_GPU_PROFILES_H_

#include <string>
#include <vector>
#include <cstdint>

namespace mozilla {
namespace dom {

struct TegufoxGPUProfile {
  std::string vendor;
  std::string renderer;
  std::vector<std::string> extensions;
  uint32_t maxTextureSize;
  uint32_t maxCubeMapTextureSize;
  uint32_t maxRenderBufferSize;
  uint32_t maxVertexAttribs;
  uint32_t maxTextureImageUnits;
  uint32_t maxVertexTextureImageUnits;
  uint32_t maxCombinedTextureImageUnits;
  uint32_t maxFragmentUniformVectors;
  uint32_t maxVertexUniformVectors;
  uint32_t maxVaryingVectors;
  
  // Validation helper
  bool IsConsistentWith(const std::string& vendorQuery, const std::string& rendererQuery) const;
};

class TegufoxGPUProfiles {
 public:
  // Find profile by vendor/renderer
  static const TegufoxGPUProfile* FindProfile(const std::string& vendor, const std::string& renderer);
  
  // Get random profile
  static const TegufoxGPUProfile& GetRandomProfile();
  
  // Validate vendor-renderer consistency
  static bool ValidateConsistency(const std::string& vendor, const std::string& renderer);
  
 private:
  static const std::vector<TegufoxGPUProfile>& GetProfiles();
};

}  // namespace dom
}  // namespace mozilla

#endif  // DOM_CANVAS_TEGUFOX_GPU_PROFILES_H_
```

**New File**: `dom/canvas/TegufoxGPUProfiles.cpp`

Implementation with real GPU profiles (NVIDIA, AMD, Intel).

---

### Phase 2: Enhance ClientWebGLContext

**Modify**: `dom/canvas/ClientWebGLContext.cpp`

Add consistency validation in `getParameter()`:

```cpp
// Around line 2600-2640
case dom::WEBGL_debug_renderer_info_Binding::UNMASKED_RENDERER_WEBGL: {
  nsAutoString stored;
  if (WebGLParamsManager::GetRenderer(GetUserContextId(), stored)) {
    // TEGUFOX ENHANCEMENT: Validate consistency
    nsAutoString vendorStored;
    if (WebGLParamsManager::GetVendor(GetUserContextId(), vendorStored)) {
      std::string vendor = NS_ConvertUTF16toUTF8(vendorStored).get();
      std::string renderer = NS_ConvertUTF16toUTF8(stored).get();
      
      if (!TegufoxGPUProfiles::ValidateConsistency(vendor, renderer)) {
        // Log warning but don't break (user misconfiguration)
        printf_stderr("TEGUFOX WARNING: Inconsistent GPU profile detected!\n");
        printf_stderr("  Vendor: %s\n", vendor.c_str());
        printf_stderr("  Renderer: %s\n", renderer.c_str());
      }
    }
    
    ret = Some(NS_ConvertUTF16toUTF8(stored));
    break;
  }
}
```

---

### Phase 3: Extension List Filtering

**Modify**: `dom/canvas/ClientWebGLContext.cpp`

Add extension filtering in `GetSupportedExtensions()`:

```cpp
void ClientWebGLContext::GetSupportedExtensions(
    dom::Nullable<nsTArray<nsString>>& retval) const {
  
  // ... existing code ...
  
  // TEGUFOX ENHANCEMENT: Filter extensions based on GPU profile
  nsAutoString vendorStored, rendererStored;
  if (WebGLParamsManager::GetVendor(GetUserContextId(), vendorStored) &&
      WebGLParamsManager::GetRenderer(GetUserContextId(), rendererStored)) {
    
    std::string vendor = NS_ConvertUTF16toUTF8(vendorStored).get();
    std::string renderer = NS_ConvertUTF16toUTF8(rendererStored).get();
    
    const TegufoxGPUProfile* profile = TegufoxGPUProfiles::FindProfile(vendor, renderer);
    if (profile) {
      // Filter extensions to only include those in profile
      nsTArray<nsString> filtered;
      for (const auto& ext : supportedExts) {
        std::string extName = NS_ConvertUTF16toUTF8(ext).get();
        auto it = std::find(profile->extensions.begin(), profile->extensions.end(), extName);
        if (it != profile->extensions.end()) {
          filtered.AppendElement(ext);
        }
      }
      retval.SetValue(std::move(filtered));
      return;
    }
  }
  
  // ... fallback to original code ...
}
```

---

## Testing Strategy

### Test 1: Vendor-Renderer Consistency

```html
<!DOCTYPE html>
<html>
<head><title>Tegufox WebGL Consistency Test</title></head>
<body>
<canvas id="canvas" width="400" height="400"></canvas>
<script>
const canvas = document.getElementById('canvas');
const gl = canvas.getContext('webgl');

const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);

console.log('Vendor:', vendor);
console.log('Renderer:', renderer);

// Test consistency
if (vendor.includes('NVIDIA') && !renderer.includes('NVIDIA')) {
  console.error('INCONSISTENT: NVIDIA vendor with non-NVIDIA renderer!');
} else if (vendor.includes('Intel') && renderer.includes('NVIDIA')) {
  console.error('INCONSISTENT: Intel vendor with NVIDIA renderer!');
} else if (vendor.includes('AMD') && renderer.includes('NVIDIA')) {
  console.error('INCONSISTENT: AMD vendor with NVIDIA renderer!');
} else {
  console.log('✅ CONSISTENT GPU profile');
}
</script>
</body>
</html>
```

### Test 2: Extension List Consistency

```javascript
const extensions = gl.getSupportedExtensions();
console.log('Extensions:', extensions);

// NVIDIA RTX 3080 should have "WEBGL_compressed_texture_s3tc"
if (renderer.includes('RTX 3080') && !extensions.includes('WEBGL_compressed_texture_s3tc')) {
  console.error('MISSING EXTENSION for RTX 3080!');
}

// Intel HD Graphics should NOT have "WEBGL_multi_draw"
if (renderer.includes('Intel HD') && extensions.includes('WEBGL_multi_draw')) {
  console.error('IMPOSSIBLE EXTENSION for Intel HD!');
}
```

### Test 3: Capability Consistency

```javascript
const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
console.log('Max Texture Size:', maxTextureSize);

// RTX 3080 should support 32768
if (renderer.includes('RTX 3080') && maxTextureSize < 32768) {
  console.error('CAPABILITY MISMATCH: RTX 3080 should support 32768!');
}
```

---

## Performance Impact

- **Overhead**: ~0.05ms for profile lookup (first call only, cached afterwards)
- **Memory**: ~50KB for GPU profile database
- **Extension filtering**: O(n*m) where n = extensions, m = profile extensions (typically < 100)

---

## Deliverables

1. ✅ `dom/canvas/TegufoxGPUProfiles.h` - GPU profile database header
2. ✅ `dom/canvas/TegufoxGPUProfiles.cpp` - GPU profile database implementation
3. ✅ `dom/canvas/ClientWebGLContext.cpp` - Enhanced with consistency validation
4. ✅ `patches/tegufox/webgl-enhanced.patch` - Final patch file
5. ✅ `test_webgl_consistency.html` - Test suite
6. ✅ `docs/WEBGL_ENHANCED_SPEC.md` - This document

---

## Next Steps

After WebGL Enhanced completion:

1. **Audio Context Patch** (Week 2) - AudioContext fingerprinting protection
2. **Font Metrics v2 Patch** (Week 2) - Font enumeration and measureText protection
3. **Integration Testing** (Week 3) - All patches working together

---

**Status**: Specification Complete, Ready for Implementation  
**Estimated Implementation Time**: 8-10 hours

---

**End of WebGL Enhanced Specification**
