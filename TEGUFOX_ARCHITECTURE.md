# Tegufox Architecture: Building ON TOP of Camoufox

**Author**: Tegufox Team  
**Date**: April 14, 2026  
**Status**: Phase 2 Architecture Definition

---

## Overview

Tegufox là một **deep browser fingerprint engine** được xây dựng ON TOP của Camoufox (Firefox Gecko fork). Strategy: **Fork & Extend** - kế thừa 32+ patches của Camoufox và thêm 8 Tegufox-specific patches.

## Directory Structure

```
tegufox-browser/                    # Main project repo
├── tegufox_automation.py           # Python automation framework (Phase 1 ✅)
├── profile_manager.py              # Profile management (Phase 1 ✅)
├── patches/                        # Tegufox patches
│   ├── tegufox/                    # Tegufox-specific patches (Phase 2)
│   │   ├── canvas-v2.patch
│   │   ├── webgl-enhanced.patch
│   │   ├── tls-ja3.patch
│   │   └── ...
│   └── applied/                    # Applied patch tracking
├── camoufox-source/                # Forked Camoufox source (to be created)
│   ├── patches/                    # Original 32 Camoufox patches
│   │   ├── audio-context-spoofing.patch
│   │   ├── webgl-spoofing.patch
│   │   └── ...
│   ├── Makefile
│   ├── scripts/
│   └── camoufox-<version>/         # Built Firefox source with patches
└── scripts/
    ├── phase2-setup.sh             # Setup Camoufox fork
    ├── tegufox-build.sh            # Build Tegufox binary
    └── tegufox-apply-patches.sh    # Apply Tegufox patches
```

## Strategy: Fork & Extend

### Why Fork Camoufox?

1. **Inherit 32+ battle-tested patches**: Audio, WebGL, fonts, geolocation, timezone, etc.
2. **Production-ready base**: Camoufox đã pass fingerprint tests
3. **Faster development**: Focus on Tegufox-specific features
4. **All-in-one repository**: Single source of truth

### Workflow

```
1. Fork Camoufox
   └─> Copy /Users/lugon/dev/2026-3/camoufox-source 
       to tegufox-browser/camoufox-source/

2. Download Firefox Source
   └─> Camoufox Makefile downloads Firefox tarball
       Extracts to: camoufox-source/camoufox-<version>-<release>/

3. Apply Camoufox Patches (32 patches)
   └─> make dir
       Applies: audio-context-spoofing.patch, webgl-spoofing.patch, etc.

4. Apply Tegufox Patches (8 NEW patches)
   └─> ./scripts/tegufox-apply-patches.sh
       Applies: canvas-v2.patch, webgl-enhanced.patch, tls-ja3.patch, etc.

5. Build Tegufox Binary
   └─> make build
       Output: camoufox-source/camoufox-<version>/obj-*/dist/bin/tegufox-bin
```

---

## Phase 2 Development Plan

### Priority 1 Patches (3 weeks)

| Patch | File to Patch | Effort | Status |
|-------|--------------|--------|--------|
| **Canvas v2** | `dom/canvas/CanvasRenderingContext2D.cpp` | 12h | 📋 Planned |
| **WebGL Enhanced** | `dom/canvas/WebGLContext.cpp` | 10h | 📋 Planned |
| **Audio Context** | `dom/media/webaudio/AudioContext.cpp` | 8h | 📋 Planned |
| **TLS JA3/JA4** | `netwerk/socket/nsSocketTransport2.cpp` | 12h | 📋 Planned |
| **WebRTC ICE v2** | `media/mtransport/ipc/PStunAddrsRequest.ipdl` | 14h | 📋 Planned |

### Patch Structure Example

**Tegufox Canvas v2 Patch** (`patches/tegufox/canvas-v2.patch`):

```diff
diff --git a/dom/canvas/CanvasRenderingContext2D.cpp b/dom/canvas/CanvasRenderingContext2D.cpp
index 1234567890..abcdef1234 100644
--- a/dom/canvas/CanvasRenderingContext2D.cpp
+++ b/dom/canvas/CanvasRenderingContext2D.cpp
@@ -45,6 +45,7 @@
 #include "mozilla/dom/ImageData.h"
 #include "mozilla/StaticPrefs_privacy.h"
+#include "TegufoxCanvasNoise.h"

 // Tegufox Canvas v2: Per-domain seed generation
+TegufoxCanvasNoise::InjectNoise(imageData, domain);
```

---

## Build System Integration

### Camoufox Makefile Targets

Tegufox sử dụng Camoufox Makefile với custom targets:

```bash
# Setup Camoufox source
make setup              # Extract Firefox + init git repo

# Apply Camoufox patches
make dir                # Apply 32 Camoufox patches

# Apply Tegufox patches (NEW)
make tegufox-patches    # Apply 8 Tegufox patches

# Build
make build              # Build with all patches

# Run
make run                # Launch Tegufox browser
```

### New Tegufox Makefile Additions

Add to `camoufox-source/Makefile`:

```makefile
# Tegufox-specific targets
tegufox-patches:
	python3 ../scripts/tegufox-apply-patches.py $(version) $(release)

tegufox-build: dir tegufox-patches
	./mach build

tegufox-run: tegufox-build
	CAMOU_CONFIG='{"tegufox": true}' ./mach run
```

---

## Patch Development Workflow

### Step 1: Setup Development Environment

```bash
cd /Users/lugon/dev/2026-3/tegufox-browser
./scripts/phase2-setup.sh
# This will:
# 1. Copy Camoufox source to camoufox-source/
# 2. Download Firefox source
# 3. Apply Camoufox patches
# 4. Setup build environment
```

### Step 2: Create a Tegufox Patch

```bash
# Enter Camoufox source
cd camoufox-source/camoufox-<version>-<release>

# Make a checkpoint
make checkpoint

# Edit C++ files
vim dom/canvas/CanvasRenderingContext2D.cpp

# Generate patch
git diff > ../../patches/tegufox/canvas-v2.patch

# Test patch
cd ../..
./scripts/tegufox-apply-patches.sh patches/tegufox/canvas-v2.patch
```

### Step 3: Build and Test

```bash
cd camoufox-source
make build                  # 1-2 hours first build

# Test run
make run

# Run automated tests
cd ../tests
pytest test_canvas_v2.py
```

---

## Canvas v2 Patch Specification

**Goal**: Per-domain deterministic canvas noise injection

**Files to modify**:
1. `dom/canvas/CanvasRenderingContext2D.cpp` - Inject noise in GetImageData()
2. `dom/canvas/TegufoxCanvasNoise.h` (NEW) - Noise generator class
3. `dom/canvas/TegufoxCanvasNoise.cpp` (NEW) - Implementation
4. `dom/canvas/moz.build` - Add to build system

**Algorithm**:
```cpp
// TegufoxCanvasNoise.cpp
uint64_t TegufoxCanvasNoise::GenerateDomainSeed(const nsAString& domain) {
    // XXH64 hash of domain
    return XXH64(domain.c_str(), domain.length(), 0);
}

void TegufoxCanvasNoise::InjectNoise(ImageData* imageData, uint64_t seed) {
    // Gaussian noise with domain seed
    std::mt19937_64 rng(seed);
    std::normal_distribution<float> dist(0.0, 2.0);
    
    for (uint32_t i = 0; i < imageData->Length(); i += 4) {
        float noise = dist(rng);
        imageData->Data()[i] = Clamp(imageData->Data()[i] + noise, 0, 255);
        // RGB channels only, preserve Alpha
    }
}
```

**Testing**:
- Same domain → Same canvas fingerprint
- Different domain → Different canvas fingerprint
- Performance: < 5% overhead on GetImageData()

---

## WebGL Enhanced Patch Specification

**Goal**: GPU consistency matrix + vendor/renderer per-domain spoofing

**Extends Camoufox's existing**: `patches/webgl-spoofing.patch`

**New features**:
1. **GPU Consistency Matrix**: Ensure WebGL parameters match spoofed GPU
2. **Per-domain WebGL vendor/renderer**: Different per domain, consistent within domain
3. **WebGL2 Support**: Extend to WebGL2 contexts

**Files to modify**:
1. `dom/canvas/WebGLContext.cpp` - Add GPU consistency checks
2. `dom/canvas/TegufoxWebGLMatrix.h` (NEW) - GPU parameter matrix
3. `dom/canvas/TegufoxWebGLMatrix.cpp` (NEW) - Validation logic

---

## TLS JA3/JA4 Patch Specification

**Goal**: Randomize TLS cipher suite order per session

**Files to modify**:
1. `security/manager/ssl/nsNSSIOLayer.cpp` - TLS handshake
2. `security/nss/lib/ssl/ssl3con.c` - Cipher suite ordering

**Challenge**: NSS library integration

---

## MaskConfig Integration

Camoufox sử dụng **MaskConfig** system để inject config từ Python → C++:

```cpp
// Camoufox pattern
#include "MaskConfig.hpp"

uint32_t AudioContext::MaxChannelCount() const {
  if (auto value = MaskConfig::GetUint32("AudioContext:maxChannelCount"))
    return value.value();
  // fallback
}
```

**Tegufox extends this**:

```cpp
// Tegufox pattern
#include "TegufoxConfig.hpp"

uint64_t CanvasRenderingContext2D::GetDomainSeed() {
  if (auto seed = TegufoxConfig::GetUint64("Canvas:domainSeed"))
    return seed.value();
  // fallback: generate from document.domain
}
```

---

## Configuration Schema

**Tegufox Profile JSON** (extends Camoufox MaskConfig):

```json
{
  "camoufox": {
    "AudioContext": {
      "sampleRate": 48000,
      "maxChannelCount": 6
    }
  },
  "tegufox": {
    "Canvas": {
      "domainSeed": "auto",
      "noiseStdDev": 2.0
    },
    "WebGL": {
      "gpuModel": "NVIDIA GeForce RTX 3080",
      "consistencyMatrix": true
    },
    "TLS": {
      "ja3RandomizeOrder": true
    }
  }
}
```

---

## Success Metrics

### Phase 2 Goals

| Metric | Target | Test Method |
|--------|--------|-------------|
| Canvas uniqueness | < 1% collision | BrowserLeaks.com |
| WebGL consistency | 100% parameter match | GPU-benchmark |
| TLS JA3 entropy | > 1000 variants | TLS fingerprint test |
| Build time (first) | < 2 hours | macOS ARM64 |
| Build time (incremental) | < 10 minutes | Single file change |
| Performance overhead | < 5% | Benchmark suite |

---

## Risk Mitigation

### Challenge 1: Camoufox Updates

**Problem**: Camoufox releases new versions, our fork becomes outdated

**Solution**: 
- Tag current Camoufox version: `camoufox-v0.5.0-base`
- Quarterly sync: Merge Camoufox updates, resolve conflicts
- Automated tests catch breaking changes

### Challenge 2: Firefox API Changes

**Problem**: Firefox Gecko API changes break patches

**Solution**:
- Pin Firefox version in Camoufox (currently 133.x)
- Test patches against Firefox ESR (long-term support)
- Gradual migration when Firefox updates

### Challenge 3: Build Complexity

**Problem**: Compiling Firefox takes 1-2 hours

**Solution**:
- Use ccache for faster rebuilds
- Incremental builds: `./mach build faster`
- CI/CD with pre-built artifacts

---

## Development Timeline

### Week 1 (April 14-20, 2026)
- ✅ Day 1: Fork Camoufox, setup build environment
- 🔄 Day 2-3: Canvas v2 patch implementation
- ⏳ Day 4-5: Canvas v2 testing & validation

### Week 2 (April 21-27, 2026)
- ⏳ Day 1-2: WebGL Enhanced patch
- ⏳ Day 3: Audio Context patch
- ⏳ Day 4-5: Integration testing

### Week 3 (April 28 - May 4, 2026)
- ⏳ Day 1-2: TLS JA3/JA4 patch
- ⏳ Day 3-4: WebRTC ICE v2 patch
- ⏳ Day 5: Full system testing

---

## Resources

### Camoufox Documentation
- GitHub: https://github.com/daijro/camoufox
- Docs: https://camoufox.com
- Patches: `/Users/lugon/dev/2026-3/camoufox-source/patches/`

### Firefox Development
- Gecko Source: https://searchfox.org
- Build Docs: https://firefox-source-docs.mozilla.org
- API Reference: https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide

### Tegufox Specs
- `PHASE2_PLAN.md` - 3-week roadmap
- `CANVAS_V2_SPEC.md` - Canvas patch technical spec
- `ROADMAP.md` - Overall project timeline

---

**Next Steps**: Run `./scripts/phase2-setup.sh` to fork Camoufox and begin Phase 2 development.
