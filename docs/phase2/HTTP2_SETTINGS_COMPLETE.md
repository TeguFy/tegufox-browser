# Patch 7/8: HTTP/2 Settings Fingerprint Spoofing - COMPLETE

## Overview
HTTP/2 connection-level fingerprinting allows servers to distinguish browsers by their SETTINGS frame parameters, WINDOW_UPDATE values, and pseudo-header ordering. This patch makes all three configurable via MaskConfig JSON, enabling Tegufox to impersonate any browser's HTTP/2 fingerprint.

## Fingerprinting Surface

### Firefox 146 Default
```
SETTINGS: 1:65536;2:0;4:131072;5:16384 | WINDOW_UPDATE: 12517377 | PSEUDO: m,p,a,s
```

### Chrome (example)
```
SETTINGS: 1:65536;2:0;3:1000;4:6291456;6:262144 | WINDOW_UPDATE: 15663105 | PSEUDO: m,a,s,p
```

### Key Differences
1. **INITIAL_WINDOW_SIZE** (ID 4): Firefox 131072 vs Chrome 6291456
2. **Missing settings**: Firefox omits IDs 3 (MAX_CONCURRENT) and 6 (MAX_HEADER_LIST)
3. **WINDOW_UPDATE**: Firefox 12517377 vs Chrome 15663105
4. **Pseudo-header order**: Firefox `m,p,a,s` vs Chrome `m,a,s,p`

## Files Modified

### `netwerk/protocol/http/Http2Session.cpp`
- Added `#include "MaskConfig.hpp"`
- Rewrote `SendHello()` to be fully config-driven:
  - `http2:settings_order` - Controls which settings IDs are sent and in what order
  - `http2:header_table_size` (ID 1) - Default: 65536
  - `http2:enable_push` (ID 2) - Default: 0
  - `http2:max_concurrent_streams` (ID 3) - Default: 0 (not sent by Firefox)
  - `http2:initial_window_size` (ID 4) - Default: 131072
  - `http2:max_frame_size` (ID 5) - Default: 16384
  - `http2:max_header_list_size` (ID 6) - Default: 0 (not sent by Firefox)
  - `http2:window_update` - Default: 12517377

### `netwerk/protocol/http/Http2Compression.cpp`
- Added `#include "MaskConfig.hpp"`
- Modified `EncodeHeaderBlock()` pseudo-header section:
  - `http2:pseudo_header_order` - Comma-separated order string (default: "m,p,a,s")
  - Maps: m=`:method`, p=`:path`, a=`:authority`, s=`:scheme`
  - `:path` always sent with `neverIndex=true` (privacy-sensitive)
  - Safety fallback emits any unmapped headers
  - `simpleConnectForm` (CONNECT method) unchanged - always sends method+authority

## Config Keys Summary

| Key | Type | Default (Firefox) | Chrome Example |
|-----|------|-------------------|----------------|
| `http2:settings_order` | string | "1,2,4,5" | "1,2,3,4,6" |
| `http2:header_table_size` | uint32 | 65536 | 65536 |
| `http2:enable_push` | uint32 | 0 | 0 |
| `http2:max_concurrent_streams` | uint32 | (omitted) | 1000 |
| `http2:initial_window_size` | uint32 | 131072 | 6291456 |
| `http2:max_frame_size` | uint32 | 16384 | (omitted) |
| `http2:max_header_list_size` | uint32 | (omitted) | 262144 |
| `http2:window_update` | uint32 | 12517377 | 15663105 |
| `http2:pseudo_header_order` | string | "m,p,a,s" | "m,a,s,p" |

## Design Decisions

1. **Per-browser, not per-domain**: HTTP/2 fingerprint is a browser-level property (unlike canvas/fonts which are domain-seeded with XXH64). Uses MaskConfig JSON config directly.

2. **Validation > Enforcement**: Falls back to Firefox defaults when no config is present. Invalid config entries are silently skipped with safety fallback.

3. **NO_RFC7540_PRIORITIES**: Still sent when applicable and no custom `settings_order` is configured, maintaining compatibility with HTTP/2 priority negotiation.

4. **maxSettings increased to 8**: From original 6, to accommodate Chrome-like profiles that send more settings entries.

## Example Chrome Configuration
```json
{
  "http2:settings_order": "1,2,3,4,6",
  "http2:header_table_size": 65536,
  "http2:enable_push": 0,
  "http2:max_concurrent_streams": 1000,
  "http2:initial_window_size": 6291456,
  "http2:max_header_list_size": 262144,
  "http2:window_update": 15663105,
  "http2:pseudo_header_order": "m,a,s,p"
}
```

## Patch File
`patches/tegufox/http2-settings-enhanced.patch` (310 lines)

## Build & Test
- Build: `make build` - Compiles cleanly (20s incremental)
- Run: `make run` - Browser launches without crashes
- No moz.build changes needed (LOCAL_INCLUDES already set)
