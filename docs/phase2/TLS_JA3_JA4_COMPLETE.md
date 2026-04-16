# TLS JA3/JA4 Enhanced Patch - COMPLETE

**Tegufox Browser Toolkit**  
**Phase 2 - Patch 4/8**  
**Status**: COMPLETE  
**Completion Date**: 2026-04-15  
**Build Time**: 22 seconds (incremental)  
**Patch Lines**: 352 lines  
**Build Result**: Zero errors, zero warnings (in NSS layer)

---

## Executive Summary

The **TLS JA3/JA4 Enhanced** patch adds **domain-based cipher suite order randomization** ON TOP of Camoufox's existing TLS protections (extension permutation + GREASE). This creates unique-per-domain TLS fingerprints that prevent cross-site JA3/JA4 correlation while remaining deterministic per domain.

### Key Achievement

**BUILDS ON TOP** of Camoufox's existing TLS protections:
- Camoufox: Extension permutation via Fisher-Yates shuffle (`ssl3ext.c:1139-1181`)
- Camoufox: GREASE cipher suite value injection (`ssl3con.c:5352-5361`)
- Tegufox: Domain-based cipher suite ORDER randomization (NEW)
- Combined: Different JA3/JA4 fingerprint per domain, deterministic within domain

---

## What Was Implemented

### Files Created

1. **`security/nss/lib/ssl/TegufoxTLSNoise.h`** (73 lines)
   - Pure C header with `extern "C"` for C++ compatibility
   - `TegufoxTLS_GenerateDomainSeed()` - XXH64 hash of hostname
   - `TegufoxTLS_ShuffleCipherOrder()` - Fisher-Yates shuffle with PCG RNG
   - `TegufoxTLS_ExtractHostname()` - URL parser for hostname extraction

2. **`security/nss/lib/ssl/TegufoxTLSNoise.c`** (194 lines)
   - XXH64 hash implementation (same algorithm as Canvas v2 and Audio patches)
   - PCG-XSH-RR random number generator (better statistical properties than LCG)
   - Fisher-Yates shuffle for cipher suite indices
   - URL hostname extraction with protocol/port/path stripping

### Files Modified

3. **`security/nss/lib/ssl/ssl3con.c`** (2 changes)
   - Added `#include "TegufoxTLSNoise.h"` at line 39
   - Modified `ssl3_AppendCipherSuites()` function: Added domain-based cipher shuffle
     using `shuffledIndices[]` array before the cipher loop

4. **`security/nss/lib/ssl/ssl.gyp`** (1 change)
   - Added `'TegufoxTLSNoise.c'` to sources list (line 56)

5. **`security/nss/lib/ssl/manifest.mn`** (1 change)
   - Added `TegufoxTLSNoise.c \` to CSRCS list (line 67)

---

## Architecture

### Data Flow

```
TLS Handshake (ClientHello construction)
    |
    v
ssl3_AppendCipherSuites(ss, ...)
    |
    +-- Extract hostname from ss->url
    |       TegufoxTLS_ExtractHostname("https://example.com/page", ...)
    |       -> "example.com"
    |
    +-- Generate domain seed
    |       TegufoxTLS_GenerateDomainSeed("example.com", 11)
    |       -> XXH64 hash -> 0x7A3B2C1D4E5F6078 (deterministic)
    |
    +-- Shuffle cipher indices
    |       TegufoxTLS_ShuffleCipherOrder([0,1,2,...N], N, seed)
    |       -> Fisher-Yates with PCG RNG
    |       -> [14,3,7,0,...] (deterministic per domain)
    |
    +-- Append cipher suites in shuffled order
            for j in 0..N: use cipherSuites[shuffledIndices[j]]
```

### Consistency with Other Patches

All Tegufox patches use the same seeding strategy:
- **Canvas v2**: `XXH64(domain)` -> pixel noise seed
- **Audio v2**: `XXH64(domain)` -> frequency/time domain noise seed
- **TLS JA3/JA4**: `XXH64(domain)` -> cipher order seed
- Same domain = same fingerprint across sessions (deterministic)
- Different domains = different fingerprints (anti-correlation)

### NSS Layer Specifics

- NSS operates BEFORE HTTP/DOM layer - no `Document` object available
- Hostname comes from `ss->url` field on `sslSocket` struct
- NSS is pure C (not C++) - all TLS files are `.c` not `.cpp`
- NSS uses gyp build system (`ssl.gyp`) + `manifest.mn` for source listing
- Build system: changes to `ssl.gyp` trigger backend regeneration automatically

---

## Technical Details

### Cipher Suite Shuffle Algorithm

```c
// Fisher-Yates shuffle (same algorithm Camoufox uses for extensions)
for (unsigned int i = count - 1; i > 0; i--) {
    uint32_t rand = PCG_Random(&rngState);
    unsigned int j = rand % (i + 1);
    // Swap indices[i] and indices[j]
    unsigned int temp = indices[i];
    indices[i] = indices[j];
    indices[j] = temp;
}
```

### Hostname Extraction

Handles various URL formats:
- `https://example.com/path` -> `example.com`
- `http://sub.example.com:8080/path?q=1` -> `sub.example.com`
- `example.com` -> `example.com`
- Converts to lowercase for consistency

### Safety Features

- If `ss->url` is NULL or empty, falls back to sequential (original) cipher order
- If hostname extraction fails, uses original order
- If seed is 0 (edge case), shuffle is skipped
- `useTegufoxShuffle` flag ensures conditional-only usage
- No memory allocation (stack-based `shuffledIndices[]` array)
- No external dependencies (self-contained XXH64 + PCG implementations)

---

## Impact on JA3/JA4 Fingerprinting

### Before (Camoufox baseline)
- Cipher suites always in same order: `[TLS_AES_128_GCM, TLS_AES_256_GCM, ...]`
- Same JA3 hash for ALL domains
- Extension order randomized (Camoufox)
- GREASE values injected (Camoufox)

### After (Tegufox enhancement)
- Cipher suites in domain-specific order: `[TLS_CHACHA20, TLS_AES_128, ...]` for site A, `[TLS_AES_256, TLS_AES_128, ...]` for site B
- Different JA3 hash per domain
- Same JA3 hash when revisiting same domain (deterministic)
- Extension order still randomized (Camoufox, preserved)
- GREASE values still injected (Camoufox, preserved)

---

## Patch File

**Location**: `patches/tegufox/tls-ja3-ja4-enhanced.patch` (352 lines)

Includes:
- Modified: `ssl3con.c` (include + cipher shuffle logic)
- Modified: `ssl.gyp` (source listing)
- Modified: `manifest.mn` (source listing)
- New: `TegufoxTLSNoise.h` (73 lines)
- New: `TegufoxTLSNoise.c` (194 lines)

---

## Verification

### Build Verification
```bash
cd camoufox-source && make build
# Result: "Your build was successful!" in 22 seconds
# Zero compilation errors in NSS layer
```

### Runtime Verification
```bash
make run  # Navigate to https://tls.browserleaks.com/tls
# Compare JA3 hash with standard Firefox
# Navigate to different domains, compare JA3 hashes
```

### Expected Behavior
1. JA3 hash should differ from vanilla Firefox/Camoufox
2. JA3 hash should differ between domains (e.g., browserleaks.com vs google.com)
3. JA3 hash should be consistent for same domain across page reloads
4. TLS connections should work normally (no handshake failures)
