# Phase 2 - Detailed Plan: Core C++ Engine Patches

**Tegufox Browser Toolkit**  
**Phase**: 2 of 5  
**Created**: 2026-04-14  
**Duration**: 4-6 weeks  
**Focus**: Deep C++ level browser fingerprint evasion

---

## Executive Summary

Phase 2 represents the **most critical milestone** in Tegufox development — implementing C++ engine-level patches that provide true browser fingerprint evasion at the Gecko core level.

Unlike Phase 1's Python automation layer, Phase 2 patches **cannot be detected** because they modify browser behavior before any JavaScript executes.

**Key Differentiator**: While tools like Puppeteer/Playwright inject JavaScript after page load, Tegufox patches are **compiled into the browser binary** itself.

---

## Objectives

| # | Objective | Priority | Est. Time |
|---|-----------|----------|-----------|
| 1 | Canvas v2 Patch (per-domain seed) | CRITICAL | 12h |
| 2 | WebGL Enhanced Patch (GPU consistency) | HIGH | 10h |
| 3 | Audio Context Patch (timing noise) | HIGH | 8h |
| 4 | Font Metrics v2 Patch (measureText offset) | MEDIUM | 8h |
| 5 | TLS JA3/JA4 Tuning (cipher suites) | HIGH | 12h |
| 6 | HTTP/2 Settings Patch (frame order) | MEDIUM | 10h |
| 7 | Navigator v2 Patch (hardware info) | MEDIUM | 8h |
| 8 | WebRTC ICE Manager v2 (C++ level) | HIGH | 14h |

**Total Estimated Time**: 82 hours (~2-3 weeks)

---

## Phase 2 Milestones

### Milestone 1: Build Environment Setup (Week 1, Days 1-3)

**Goal**: Establish C++ development workflow for Firefox patches

#### Tasks

1. **Install Firefox Build Dependencies** (Day 1)
   ```bash
   # macOS
   brew install mercurial rust llvm cmake ninja
   
   # Linux
   sudo apt install mercurial rustc clang cmake ninja-build
   ```

2. **Clone Firefox Source** (Day 1-2)
   ```bash
   hg clone https://hg.mozilla.org/mozilla-central/
   cd mozilla-central
   ./mach bootstrap
   ```
   **Note**: ~3GB download, 2-4 hour first build

3. **Configure Build** (Day 2)
   ```javascript
   // mozconfig
   ac_add_options --enable-application=browser
   ac_add_options --enable-debug
   ac_add_options --disable-optimize
   mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-tegufox-debug
   ```

4. **First Build Test** (Day 2-3)
   ```bash
   ./mach build
   ./mach run
   ```

5. **Create Patch Testing Framework** (Day 3)
   - Automated patch application script
   - Regression test suite
   - Fingerprint validation tests

**Success Criteria**:
- ✅ Firefox builds successfully
- ✅ Custom binary launches without errors
- ✅ Patch can be applied and reverted cleanly

---

### Milestone 2: Canvas v2 Patch (Week 1, Days 4-5)

**Goal**: Implement per-domain canvas fingerprint randomization

#### Background

**Current Problem**: Canvas fingerprinting generates same hash across all domains  
**Tegufox Solution**: Per-domain seed + noise injection at C++ level

#### Implementation Plan

**File to Patch**: `dom/canvas/CanvasRenderingContext2D.cpp`

**Method to Intercept**: `GetImageData()`, `ToDataURL()`

**Patch Strategy**:
```cpp
// Pseudo-code
uint64_t GenerateDomainSeed(const nsACString& domain) {
    // Hash domain + session ID + timestamp
    return XXH64(domain.Data(), domain.Length(), g_session_seed);
}

void ApplyCanvasNoise(ImageData* data, uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::normal_distribution<double> noise(0.0, 0.5);
    
    for (size_t i = 0; i < data->Length(); i++) {
        // Add subtle noise to RGBA values
        data->At(i) += static_cast<uint8_t>(noise(rng));
    }
}
```

**MaskConfig Integration**:
```json
{
  "canvas:perDomainSeed": true,
  "canvas:noiseIntensity": 0.5,
  "canvas:antiCorrelation": true
}
```

#### Test Plan

1. **Hash Uniqueness Test**:
   - Load same page 10 times
   - Verify canvas hash changes each time
   - Verify hash is stable within same page load

2. **Domain Isolation Test**:
   - canvas hash on domain-a.com
   - canvas hash on domain-b.com
   - Verify hashes are different

3. **BrowserLeaks Validation**:
   - https://browserleaks.com/canvas
   - Verify "Unique" status (not "Consistent")

**Deliverables**:
- `patches/canvas-v2-domain-seed.patch`
- `tests/test_canvas_v2_domain.py`
- `docs/CANVAS_V2_DESIGN.md`

---

### Milestone 3: WebGL Enhanced Patch (Week 2, Days 6-7)

**Goal**: GPU vendor/renderer consistency matrix

#### Background

**Detection Vector**: `getParameter(UNMASKED_VENDOR_WEBGL)` reveals real GPU  
**Tegufox Solution**: Consistent GPU spoofing across all WebGL APIs

#### GPU Consistency Matrix

| Profile | Vendor | Renderer | Extensions |
|---------|--------|----------|------------|
| chrome-120-nvidia | NVIDIA Corporation | GeForce RTX 3080 | WEBGL_lose_context, EXT_texture_filter_anisotropic |
| chrome-120-amd | ATI Technologies Inc. | AMD Radeon RX 6800 XT | WEBGL_compressed_texture_s3tc, ANGLE_instanced_arrays |
| firefox-115-intel | Intel Inc. | Intel(R) UHD Graphics 630 | WEBGL_debug_renderer_info, OES_standard_derivatives |

#### Implementation Plan

**File to Patch**: `dom/canvas/WebGLContext.cpp`

**Methods to Intercept**:
- `GetParameter(UNMASKED_VENDOR_WEBGL)`
- `GetParameter(UNMASKED_RENDERER_WEBGL)`
- `GetSupportedExtensions()`

**Patch Strategy**:
```cpp
// Load GPU profile from MaskConfig
struct GPUProfile {
    std::string vendor;
    std::string renderer;
    std::vector<std::string> extensions;
};

GPUProfile LoadGPUProfile(MaskConfig* config) {
    return {
        config->GetString("webgl:vendor"),
        config->GetString("webgl:renderer"),
        config->GetStringArray("webgl:extensions")
    };
}

// Override GetParameter
JSValueRef WebGLContext::GetParameter(uint32_t pname) {
    if (pname == UNMASKED_VENDOR_WEBGL) {
        return JS_NewStringCopyZ(ctx, m_gpuProfile.vendor.c_str());
    }
    if (pname == UNMASKED_RENDERER_WEBGL) {
        return JS_NewStringCopyZ(ctx, m_gpuProfile.renderer.c_str());
    }
    // ... original code
}
```

**Test Plan**:
- Verify vendor/renderer match profile
- Verify extension list matches GPU type
- Test on https://browserleaks.com/webgl

**Deliverables**:
- `patches/webgl-enhanced-gpu-consistency.patch`
- `tests/test_webgl_consistency.py`
- `docs/WEBGL_GPU_MATRIX.md`

---

### Milestone 4: TLS JA3/JA4 Tuning (Week 2, Days 8-10)

**Goal**: Match TLS fingerprint to target browser

#### Background

**Detection Vector**: TLS Client Hello fingerprinting (JA3/JA3S)  
**Tegufox Solution**: NSS library patches for cipher suite order

#### TLS Fingerprint Targets

| Browser | JA3 Hash | Cipher Suites | Extensions |
|---------|----------|---------------|------------|
| Chrome 120 | 579ccef312d18482 | TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384 | server_name, renegotiation_info |
| Firefox 115 | de350869b8c85de6 | TLS_CHACHA20_POLY1305_SHA256, TLS_AES_128_GCM_SHA256 | extended_master_secret, session_ticket |
| Safari 17 | 66818e4f5f48d10b | TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384 | ec_point_formats, supported_groups |

#### Implementation Plan

**File to Patch**: `security/nss/lib/ssl/ssl3con.c`

**Function to Intercept**: `ssl3_SendClientHello()`

**Patch Strategy**:
```c
// Load cipher suite order from MaskConfig
static const SSL3CipherSuite tegufox_cipher_order[] = {
    TLS_AES_128_GCM_SHA256,
    TLS_AES_256_GCM_SHA384,
    TLS_CHACHA20_POLY1305_SHA256,
    // ... from config
};

// Override cipher suite order
SECStatus ssl3_SendClientHello(sslSocket *ss) {
    if (ss->opt.tegufox_enabled) {
        ss->ssl3.hs.cipherSuites = tegufox_cipher_order;
        ss->ssl3.hs.cipherSuiteCount = sizeof(tegufox_cipher_order) / sizeof(SSL3CipherSuite);
    }
    // ... original code
}
```

**Test Plan**:
- Capture TLS handshake with Wireshark
- Verify JA3 hash matches target browser
- Test on https://browserleaks.com/ssl

**Deliverables**:
- `patches/tls-ja3-cipher-order.patch`
- `tests/test_tls_ja3.py`
- `docs/TLS_FINGERPRINT_GUIDE.md`

---

### Milestone 5: WebRTC ICE Manager v2 (Week 3, Days 11-14)

**Goal**: C++ level IP address replacement in ICE candidates

#### Background

**Detection Vector**: WebRTC leaks real IP despite VPN/proxy  
**Tegufox Solution**: Intercept at `PeerConnectionImpl.cpp` level

#### Implementation Plan

**File to Patch**: `media/webrtc/signaling/src/peerconnection/PeerConnectionImpl.cpp`

**Method to Intercept**: `OnIceCandidate()`

**Patch Strategy**:
```cpp
void PeerConnectionImpl::OnIceCandidate(const IceCandidate& candidate) {
    // Replace real IP with profile IP
    std::string masked_candidate = candidate.candidate;
    
    // Extract real IP
    std::regex ip_regex(R"((\d{1,3}\.){3}\d{1,3})");
    
    // Replace with profile IP from MaskConfig
    std::string profile_ip = GetMaskConfig()->GetString("webrtc:publicIp");
    masked_candidate = std::regex_replace(masked_candidate, ip_regex, profile_ip);
    
    // Call original handler with masked candidate
    Original_OnIceCandidate(IceCandidate(masked_candidate));
}
```

**MaskConfig Integration**:
```json
{
  "webrtc:publicIp": "203.0.113.42",
  "webrtc:localIp": "192.168.1.100",
  "webrtc:forceDefaultAddressOnly": true,
  "webrtc:blockSTUN": true
}
```

**Test Plan**:
- Test on https://browserleaks.com/ip
- Test on https://ipleak.net/
- Verify no real IP leaks

**Deliverables**:
- `patches/webrtc-ice-manager-v2.patch`
- `tests/test_webrtc_leak.py`
- `docs/WEBRTC_ICE_DESIGN.md`

---

## Patch Development Workflow

### 1. Design Phase
- Research Firefox source code
- Identify interception points
- Document patch strategy
- Create test plan

### 2. Implementation Phase
```bash
# Create patch branch
cd mozilla-central
hg branch tegufox-canvas-v2

# Make changes
vim dom/canvas/CanvasRenderingContext2D.cpp

# Generate patch
hg diff > ../tegufox-browser/patches/canvas-v2.patch

# Test build
./mach build
./mach run
```

### 3. Testing Phase
```bash
# Run automated tests
cd ../tegufox-browser
source venv/bin/activate
pytest tests/test_canvas_v2.py -v

# Manual validation
python test_browserleaks.py --canvas
```

### 4. Integration Phase
```bash
# Update MaskConfig
vim profiles/chrome-120.json

# Test with automation framework
python test_automation_with_patch.py
```

---

## Success Criteria

Phase 2 is successful if:

| Criterion | Target | Validation |
|-----------|--------|------------|
| Canvas hash entropy | Variable across domains | BrowserLeaks test |
| WebGL consistency | 100% match to GPU profile | Manual verification |
| TLS JA3 match | ≥ 95% match to target browser | Wireshark capture |
| WebRTC IP leak | 0% | IPLeak.net test |
| Build time | < 4 hours | Time measurement |
| Patch conflicts | 0 | Automated checks |
| Performance overhead | < 5% | Benchmark suite |
| Test pass rate | ≥ 95% | pytest results |

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Firefox build fails | Medium | High | Pre-test on known-good commit |
| Patch breaks browser | High | Critical | Extensive testing before merge |
| Performance degradation | Medium | Medium | Profile critical paths |
| Update breaks patches | High | High | Monitor Firefox releases |
| Complex C++ debugging | High | Medium | Use LLDB, extensive logging |

---

## Resources & Tools

### Development Tools
- **IDE**: VS Code with C++ extension
- **Debugger**: LLDB (macOS) / GDB (Linux)
- **Build**: Mozilla mach build system
- **VCS**: Mercurial (hg)
- **Profiling**: Firefox Profiler

### Testing Tools
- **BrowserLeaks**: Canvas, WebGL, TLS fingerprinting
- **IPLeak.net**: WebRTC leak detection
- **Wireshark**: TLS handshake analysis
- **pytest**: Automated test suite

### Reference Documentation
- **MDN**: Web APIs reference
- **Mozilla Source Docs**: https://searchfox.org/
- **NSS Docs**: https://developer.mozilla.org/docs/Mozilla/Projects/NSS

---

## Timeline

| Week | Days | Milestone | Deliverables |
|------|------|-----------|--------------|
| Week 1 | 1-3 | Build environment | Firefox builds, patch workflow |
| Week 1 | 4-5 | Canvas v2 | Patch + tests + docs |
| Week 2 | 6-7 | WebGL Enhanced | Patch + GPU matrix |
| Week 2 | 8-10 | TLS JA3/JA4 | NSS patches + validation |
| Week 3 | 11-14 | WebRTC ICE v2 | C++ interception + tests |
| Week 3 | 15 | Integration testing | All patches working together |

**Total Duration**: 3 weeks (15 days)  
**Buffer**: +3 days for unexpected issues

---

## Deliverables Summary

**C++ Patches** (8 patches):
1. canvas-v2-domain-seed.patch
2. webgl-enhanced-gpu-consistency.patch
3. audio-context-timing-noise.patch
4. font-metrics-v2-offset.patch
5. tls-ja3-cipher-order.patch
6. http2-settings-frame-order.patch
7. navigator-v2-hardware-info.patch
8. webrtc-ice-manager-v2.patch

**Test Files** (~2,000 lines):
- test_canvas_v2_domain.py
- test_webgl_consistency.py
- test_tls_ja3.py
- test_webrtc_leak.py
- test_integration_all_patches.py

**Documentation** (~3,000 lines):
- CANVAS_V2_DESIGN.md
- WEBGL_GPU_MATRIX.md
- TLS_FINGERPRINT_GUIDE.md
- WEBRTC_ICE_DESIGN.md
- PHASE2_CPP_PATCH_WORKFLOW.md

---

## Next Steps After Phase 2

**Phase 3: Fingerprint Consistency Engine**
- Cross-layer validation
- Profile scoring system
- Anti-correlation engine

**Phase 4: Behavioral Layer**
- Advanced mouse movements
- Keyboard behavioral patterns
- Bot detection bypass validation

**Phase 5: Ecosystem & API**
- REST API
- Plugin system
- npm package

---

**Status**: Phase 2 Planning Complete  
**Ready to Start**: April 15, 2026  
**Estimated Completion**: May 6, 2026

---

**End of Phase 2 Plan**
