# Patch 8/8: Navigator v2 Enhanced - COMPLETE

## Overview
Enhances Navigator API fingerprint spoofing by adding MaskConfig overrides for properties that Camoufox doesn't cover. These additions are critical for cross-browser profile consistency (e.g., when spoofing a Chrome user agent, all Navigator properties must match).

## What Camoufox Already Handles
- `navigator.userAgent` (per-context + global)
- `navigator.platform` (per-context + global)
- `navigator.oscpu` (per-context + global)
- `navigator.appVersion` (global)
- `navigator.hardwareConcurrency` (per-context + global)
- `navigator.language` / `navigator.languages` (via locale system)
- `navigator.webdriver` (hardcoded `false`)
- `navigator.getBattery()` (charging, level, times)
- `navigator.mediaDevices.enumerateDevices()` (fake devices)
- Timezone override

## Tegufox v2 Enhancements (6 New Overrides)

### 1. `navigator.maxTouchPoints` (Navigator.cpp:974)
- **Config key**: `navigator.maxTouchPoints` (uint32)
- **Firefox default**: 0 (desktop)
- **Use case**: Mobile profile emulation. Chrome Android returns 5, iOS Safari returns 5.
- **Priority**: Highest priority check - runs before RFP and RDM overrides.

### 2. `navigator.vendor` (Navigator.cpp:564)
- **Config key**: `navigator.vendor` (string)
- **Firefox default**: `""` (empty string)
- **Chrome value**: `"Google Inc."`
- **Safari value**: `"Apple Computer, Inc."`
- **Use case**: Without this, a Chrome UA with empty vendor instantly reveals Firefox.

### 3. `navigator.buildID` (Navigator.cpp:686)
- **Config key**: `navigator.buildID` (string)
- **Firefox default**: `"20181001000000"` (LEGACY_BUILD_ID)
- **Use case**: `buildID` is Firefox-only. Configurable to match expected values or prevent leaking exact build info.

### 4. `navigator.doNotTrack` (Navigator.cpp:749)
- **Config key**: `navigator.doNotTrack` (string)
- **Values**: `"1"` (enabled), `"0"` (disabled), `"unspecified"`
- **Use case**: Consistent DNT signaling across profiles without changing Firefox prefs.

### 5. `navigator.pdfViewerEnabled` (Navigator.cpp:603)
- **Config key**: `navigator.pdfViewerEnabled` (bool)
- **Firefox default**: `true` (unless pdfjs.disabled pref is set)
- **Use case**: Control PDF viewer visibility to match target browser profile.

### 6. `navigator.globalPrivacyControl` - Main Thread Parity (Navigator.cpp:760)
- **Config key**: `navigator.globalPrivacyControl` (bool)
- **Fix**: Camoufox only spoofed this in WorkerNavigator.cpp, NOT in main-thread Navigator.cpp. Fingerprinters could detect the mismatch by comparing `navigator.globalPrivacyControl` in main thread vs worker.
- **Now**: Both main thread and worker return the same MaskConfig value.

## Files Modified

### `dom/base/Navigator.cpp`
All 6 enhancements in a single file. No new includes needed (MaskConfig.hpp already included by Camoufox). No moz.build changes needed (LOCAL_INCLUDES already has `/camoucfg`).

## New Config Keys Summary

| Key | Type | Default | Use Case |
|-----|------|---------|----------|
| `navigator.maxTouchPoints` | uint32 | 0 | Mobile emulation |
| `navigator.vendor` | string | `""` | Chrome/Safari UA consistency |
| `navigator.buildID` | string | `"20181001000000"` | Firefox identity masking |
| `navigator.doNotTrack` | string | `"unspecified"` | DNT signal control |
| `navigator.pdfViewerEnabled` | bool | `true` | PDF viewer visibility |
| `navigator.globalPrivacyControl` | bool | (pref-based) | Main/worker parity fix |

## Example Chrome Desktop Profile
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  "navigator.platform": "Win32",
  "navigator.vendor": "Google Inc.",
  "navigator.maxTouchPoints": 0,
  "navigator.hardwareConcurrency": 8,
  "navigator.pdfViewerEnabled": true,
  "navigator.doNotTrack": "unspecified",
  "navigator.globalPrivacyControl": false
}
```

## Example Chrome Android Profile
```json
{
  "navigator.userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
  "navigator.platform": "Linux armv81",
  "navigator.vendor": "Google Inc.",
  "navigator.maxTouchPoints": 5,
  "navigator.hardwareConcurrency": 8,
  "navigator.pdfViewerEnabled": true
}
```

## Properties NOT Modified (Intentional)
- **`navigator.plugins`/`navigator.mimeTypes`**: Complex Firefox-specific behavior, consistent within Firefox versions
- **`navigator.connection`**: Firefox has limited NetworkInformation API support
- **`navigator.deviceMemory`**: Chrome-only API, Firefox doesn't expose it
- **`navigator.appCodeName`**: Hardcoded "Mozilla" across all browsers
- **`navigator.appName`**: Hardcoded "Netscape" across all browsers
- **`navigator.productSub`**: Same value ("20030107") across Firefox/Chrome
- **`navigator.oscpu` in workers**: Not exposed in Worker WebIDL by spec

## Patch File
`patches/tegufox/navigator-v2-enhanced.patch` (284 lines)

## Build & Test
- Build: `make build` - Clean compile (24s incremental)
- Run: `make run` - Browser launches without crashes
- No moz.build changes needed
