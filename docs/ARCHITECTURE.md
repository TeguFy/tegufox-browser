# Tegufox — Architecture Design

## Overview

Tegufox là một **deep browser fingerprint engine** xây dựng trên Camoufox (Firefox Gecko). Mục tiêu là giả lập môi trường trình duyệt ở tất cả các tầng — từ giao thức mạng cấp thấp cho đến hành vi sinh trắc học — để không một hệ thống anti-fraud nào có thể phân biệt với người dùng thật.

**Principle**: Build ON TOP of Camoufox. Không replace, cẩng thêm C++ patches và automation layer.

---

## Fingerprint Layers

Mỗi tầng là một vector ma anti-fraud sử dụng để phân loại browser. Tegufox phủ tất cả 7 tầng:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 7: Behavioral Fingerprint                      │
│  • Mouse movement patterns (Fitts' Law + tremor)      │
│  • Typing rhythm (inter-keystroke distribution)       │
│  • Scroll momentum & pauses                          │
│  • Form interaction timing                           │
├─────────────────────────────────────────────────────────┤
│  Layer 6: Hardware Fingerprint                        │
│  • WebGL: vendor, renderer, extensions, precision      │
│  • Canvas: per-domain noise, hash variation           │
│  • Audio Context: timing & frequency noise            │
│  • Fonts: metrics offset, enumeration consistency     │
│  • Battery API: realistic values                     │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Browser Environment Fingerprint             │
│  • navigator.* properties (hardwareConcurrency, etc.) │
│  • Screen / viewport / window dimensions              │
│  • navigator.webdriver removal (C++ level)            │
│  • Headless mode masking                             │
│  • window.chrome presence/absence per UA              │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Network Protocol Fingerprint                │
│  • TLS: cipher suite order, JA3/JA4 hash             │
│  • TLS: Client Hello extensions list                 │
│  • HTTP/2: SETTINGS frame parameters                 │
│  • HTTP/2: pseudo-header order (:method/:path/etc.)  │
│  • ALPN negotiation order                           │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Network Fingerprint                         │
│  • WebRTC: ICE candidate IP replacement               │
│  • WebRTC: STUN leak prevention                      │
│  • DNS: DoH/DoT routing per profile                  │
│  • IP consistency across all signals                 │
└─────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Tegufox Toolkit                        │
├─────────────────────────────────────────────────────────┤
│  Developer Tools                                     │
│  tegufox-patch │ tegufox-config │ tegufox-profile     │
│  tegufox-test  │ tegufox-build  │ REST API            │
├─────────────────────────────────────────────────────────┤
│  Automation Framework (Python)                       │
│  TegufoxSession    | ProfileManager                   │
│  ProfileRotator    | SessionManager                   │
│  NeuromotorMouse   | NaturalTyping | NaturalScroll    │
├─────────────────────────────────────────────────────────┤
│  Fingerprint Consistency Engine                      │
│  Cross-layer validator | Profile generator v2         │
│  Anti-correlation | Scoring system                    │
├─────────────────────────────────────────────────────────┤
│  Tegufox Custom C++ Patches (20+)                    │
│  canvas-v2.patch       | webgl-enhanced.patch          │
│  webrtc-ice-v2.patch   | tls-ja3.patch                 │
│  http2-settings.patch  | navigator-v2.patch            │
│  audio-context.patch   | font-metrics-v2.patch         │
│  screen-v2.patch       | battery-api.patch             │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│  Camoufox (38 core patches + MaskConfig system)      │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│     Firefox Gecko Engine (C++ / Rust)               │
└─────────────────────────────────────────────────────────┘
```

---

## C++ Patch Architecture

Tất cả Tegufox patches đều sử dụng `MaskConfig.hpp` để đọc config từ JSON profile:

```cpp
// Chương lược access
if (auto value = MaskConfig::GetString("webgl:vendor"))
    vendorString = value.value();

if (auto value = MaskConfig::GetDouble("canvas:noise"))
    noiseLevel = value.value();

if (auto value = MaskConfig::GetBool("webrtc:enabled"))
    isEnabled = value.value();
```

### Patch categories (Phase 2)

#### L6: Hardware (6–8 patches)
| Patch | File modified | Config keys |
|-------|--------------|-------------|
| `canvas-v2.patch` | `dom/canvas/CanvasRenderingContext2D.cpp` | `canvas:noise`, `canvas:domain_seed` |
| `webgl-enhanced.patch` | `dom/canvas/WebGLContext.cpp` | `webgl:vendor`, `webgl:renderer`, `webgl:extensions` |
| `audio-context.patch` | `dom/media/AudioContext.cpp` | `audio:noise_level` |
| `font-metrics-v2.patch` | `gfx/thebes/gfxFont.cpp` | `fonts:metrics_offset` |
| `screen-v2.patch` | `dom/base/Screen.cpp` | `screen:width`, `screen:dpr` |
| `battery-api.patch` | `dom/battery/BatteryManager.cpp` | `battery:level`, `battery:charging` |

#### L4–5: Protocol & Environment (4–5 patches)
| Patch | File modified | Config keys |
|-------|--------------|-------------|
| `tls-ja3.patch` | `security/nss/*` | `tls:cipher_order`, `tls:extensions` |
| `http2-settings.patch` | `netwerk/protocol/http/Http2Session.cpp` | `http2:settings`, `http2:pseudo_header_order` |
| `navigator-v2.patch` | `dom/base/Navigator.cpp` | `navigator:hardware_concurrency`, `navigator:device_memory` |
| `juggler-isolation.patch` | `remote/juggler/*` | — (structural patch) |

#### L3: Network (3 patches)
| Patch | File modified | Config keys |
|-------|--------------|-------------|
| `webrtc-ice-v2.patch` | `media/webrtc/signaling/src/peerconnection/PeerConnectionImpl.cpp` | `webrtc:ipv4`, `webrtc:ipv6` |
| `webrtc-stun-block.patch` | `media/webrtc/transport/ice_ctx.cpp` | `webrtc:stun_whitelist` |
| `dns-doh-builtin.patch` | `netwerk/dns/TRR.cpp` | `dns:doh_url`, `dns:enabled` |

---

## Automation Framework

### Core classes (Phase 1, done)

```python
# tegufox_automation.py

class TegufoxSession:
    """
    High-level wrapper around Playwright + Camoufox.
    Lấy profile từ ProfileManager, launch browser,
    expose human-like interaction methods.
    """
    def goto(url: str) -> None
    def human_click(selector: str) -> None
    def human_type(selector: str, text: str) -> None
    def screenshot(path: str) -> None
    def wait_human(min=0.5, max=2.0) -> None

class ProfileRotator:
    """
    Xoay vòng qua list profiles.
    Chọn profile tip theo sau mỗi session.
    """
    def next_session() -> TegufoxSession
    def reset() -> None

class SessionManager:
    """
    Quản lý nhiều sessions song song.
    Mỗi session dùng một profile độc lập.
    """
    def create_session(profile_name: str) -> TegufoxSession
    def close_all() -> None
```

### Behavioral Modules (Phase 4)

```python
class NeuromotorMouse:
    """
    Fitts' Law based mouse movement.
    Gaussian noise trên trajectory.
    Distance-aware duration calculation.
    """

class NaturalTyping:
    """
    Inter-keystroke timing: log-normal distribution.
    Per-bigram timing (faster for common pairs).
    Typo + correction simulation.
    """

class NaturalScroll:
    """
    Easing curves (ease-out-cubic).
    Random micro-pauses.
    Platform-specific step sizes.
    """
```

---

## Profile Architecture

Một profile là một JSON document mô tả tất cả các tham số fingerprint của một browser identity:

```json
{
  "name": "chrome-120-win11",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
  "screen_resolution": "1920x1080",
  "tls_fingerprint": {
    "ja3_hash": "579ccef312d18482fc42e2b822ca2430",
    "cipher_suites": [...],
    "extensions": [...]
  },
  "http2_fingerprint": {
    "settings": { "HEADER_TABLE_SIZE": 65536, ... },
    "pseudo_header_order": [":method", ":authority", ":scheme", ":path"]
  },
  "dns_config": {
    "doh_enabled": true,
    "doh_provider": "cloudflare",
    "doh_url": "https://cloudflare-dns.com/dns-query"
  },
  "canvas_noise": { "enabled": true, "variance": 0.02 },
  "webgl_config": {
    "vendor": "Google Inc.",
    "renderer": "ANGLE (NVIDIA, GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
  },
  "navigator": {
    "hardware_concurrency": 8,
    "device_memory": 8
  }
}
```

**Templates có sẵn**: Chrome 120, Firefox 115 ESR, Safari 17

---

## Consistency Engine (Phase 3)

Sau khi Phase 2 patches xảy ra, Phase 3 xây dựng một engine validator kiểm tra cross-layer consistency:

```
Profile JSON
     │
     ▼
Consistency Engine
  ├─ OS ↔ Font list (Windows fonts ≠ Mac fonts ≠ Linux fonts)
  ├─ GPU vendor ↔ WebGL renderer string pattern
  ├─ Screen.width ↔ window.outerWidth ↔ devicePixelRatio
  ├─ User-Agent ↔ TLS cipher order (Chrome HA ≠ Firefox order)
  ├─ User-Agent ↔ HTTP/2 pseudo-header order
  ├─ navigator.language ↔ Intl.DateTimeFormat locale
  └─ navigator.hardwareConcurrency ↔ profile config value
     │
     ▼
Validation Result { score: 0.0—1.0, errors: [], warnings: [] }
```

---

## Directory Structure (Target)

```
tegufox-browser/
├── patches/                    # Tegufox custom C++ patches
│   ├── canvas-v2.patch
│   ├── webgl-enhanced.patch
│   ├── webrtc-ice-v2.patch
│   ├── tls-ja3.patch
│   └── ...
├── tegufox_automation.py       # Automation framework ✅
├── tegufox_mouse.py            # Neuromotor mouse ✅
├── profile_manager.py         # Profile CRUD + validation ✅
├── tegufox-profile             # Profile CLI ✅
├── tegufox-patch               # Patch management CLI ✅
├── tegufox-config              # Config management ✅
├── scripts/
│   └── configure-dns.py        # DNS leak prevention ✅
├── tests/
│   ├── test_automation_framework.py  ✅
│   ├── test_profile_manager.py       ✅
│   ├── test_dns_leak.py              ✅
│   └── fingerprint/
├── profiles/                   # Profile JSON files
├── docs/
│   ├── ARCHITECTURE.md            # This file
│   ├── CAMOUFOX_PATCH_SYSTEM.md
│   ├── PATCH_DEVELOPMENT.md
│   └── ...
├── examples/
├── README.md
├── ROADMAP.md
└── TODO.md
```

---

## Build & Patch Workflow

```
# 1. Init: clone Camoufox source
tegufox-build init

# 2. Create new patch
tegufox-patch create --name canvas-v2 --type fingerprint
# ⇒ generates patches/canvas-v2.patch with boilerplate

# 3. Developer modifies C++ in camoufox-source/
# ...

# 4. Generate diff
tegufox-generate-patch canvas-v2

# 5. Validate patch syntax
tegufox-validate-patch patches/canvas-v2.patch

# 6. Apply + build
tegufox-build apply-patches
tegufox-build compile

# 7. Test
tegufox-test fingerprint --suite canvas
```

---

**Version**: 0.2.0  
**Last Updated**: 2026-04-14  
**Status**: Phase 1 complete, Phase 2 planned
