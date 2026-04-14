# MaskConfig System - Technical Analysis

## Overview

`MaskConfig.hpp` là hệ thống cấu hình trung tâm của Camoufox, cho phép inject fingerprint values từ Python API vào Firefox C++ core. Đây là cầu nối giữa user configuration (JSON) và browser behavior (C++ patches).

**Location**: `/camoufox-source/additions/camoucfg/MaskConfig.hpp`  
**Language**: C++ Header-only library  
**Dependencies**: `nlohmann/json.hpp` (JSON parsing)

---

## Architecture

### Configuration Flow

```
Python API                Environment Variables          C++ MaskConfig
┌─────────────┐          ┌──────────────────┐          ┌─────────────────┐
│ config = {  │          │ CAMOU_CONFIG_1   │          │ GetJson()       │
│   "canvas": │  ─────>  │ CAMOU_CONFIG_2   │  ─────>  │ GetString()     │
│   {...}     │          │ CAMOU_CONFIG_N   │          │ GetDouble()     │
│ }           │          │ (or CAMOU_CONFIG)│          │ GetBool()       │
└─────────────┘          └──────────────────┘          └─────────────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────────┐
                                                        │ Firefox Patches │
                                                        │ Use values to   │
                                                        │ spoof APIs      │
                                                        └─────────────────┘
```

### Environment Variable Chunking

Config có thể lớn hơn env var limit, nên được split thành chunks:

```cpp
// Read config from multiple env vars
CAMOU_CONFIG_1 = '{"canvas":{"noise":0.02},'
CAMOU_CONFIG_2 = '"webgl":{"vendor":"NVIDIA"}}'
```

Fallback to `CAMOU_CONFIG` nếu không có `CAMOU_CONFIG_N`.

---

## Core Functions

### 1. JSON Retrieval

```cpp
const nlohmann::json& GetJson()
```

**Purpose**: Lazy-load và cache JSON config từ environment variables

**Implementation Details**:
- Uses `std::once_flag` để ensure initialization chỉ 1 lần
- Đọc `CAMOU_CONFIG_1`, `CAMOU_CONFIG_2`, ... cho đến khi không còn
- Fallback to `CAMOU_CONFIG` nếu không tìm thấy chunked vars
- Validates JSON với `nlohmann::json::accept()`
- Returns empty JSON object `{}` nếu invalid hoặc không có config

**Thread-Safety**: ✅ Thread-safe via `std::call_once`

### 2. String Operations

```cpp
std::optional<std::string> GetString(const std::string& key)
```

Lấy string value từ JSON config.

**Example**:
```cpp
// Config: {"canvas:vendor": "Google Inc."}
if (auto vendor = MaskConfig::GetString("canvas:vendor"))
    return vendor.value();
```

```cpp
std::vector<std::string> GetStringList(const std::string& key)
```

Lấy array of strings.

**Example**:
```cpp
// Config: {"fonts": ["Arial", "Helvetica"]}
auto fonts = MaskConfig::GetStringList("fonts");
```

```cpp
std::vector<std::string> GetStringListLower(const std::string& key)
```

Same as `GetStringList` nhưng convert tất cả về lowercase.

### 3. Numeric Operations

```cpp
std::optional<uint64_t> GetUint64(const std::string& key)
std::optional<uint32_t> GetUint32(const std::string& key)
std::optional<int32_t> GetInt32(const std::string& key)
std::optional<double> GetDouble(const std::string& key)
```

**Features**:
- Type-safe retrieval
- Returns `std::nullopt` nếu key không tồn tại
- Validates type (unsigned, signed, float)
- Prints error to stderr nếu type mismatch
- `GetDouble` accepts both float và integer (auto-convert)

**Example**:
```cpp
// Config: {"AudioContext:sampleRate": 48000}
if (auto rate = MaskConfig::GetUint32("AudioContext:sampleRate"))
    return rate.value();
```

### 4. Boolean Operations

```cpp
std::optional<bool> GetBool(const std::string& key)
```

Returns optional bool.

```cpp
bool CheckBool(const std::string& key)
```

Returns bool với default `false` nếu không tồn tại.

**Example**:
```cpp
// Config: {"feature:enabled": true}
if (MaskConfig::CheckBool("feature:enabled")) {
    // Feature is enabled
}
```

### 5. Rectangle Operations

```cpp
std::optional<std::array<uint32_t, 4>> GetRect(
    const std::string& left, const std::string& top,
    const std::string& width, const std::string& height)
```

Lấy 4 values để define rectangle (used for screen dimensions).

```cpp
std::optional<std::array<int32_t, 4>> GetInt32Rect(...)
```

Same nhưng return signed integers.

**Example**:
```cpp
// Config: {
//   "document.body.clientLeft": 0,
//   "document.body.clientTop": 0,
//   "document.body.clientWidth": 1920,
//   "document.body.clientHeight": 1080
// }
if (auto rect = MaskConfig::GetInt32Rect(
    "document.body.clientLeft", "document.body.clientTop",
    "document.body.clientWidth", "document.body.clientHeight")) {
    auto [left, top, width, height] = rect.value();
}
```

### 6. Nested Object Access

```cpp
std::optional<nlohmann::json> GetNested(
    const std::string& domain, std::string keyStr)
```

Access nested JSON objects.

**Example**:
```cpp
// Config: {
//   "webGl": {
//     "parameters": {
//       "3379": "NVIDIA Corporation"
//     }
//   }
// }
auto value = MaskConfig::GetNested("webGl", "parameters");
```

---

## WebGL Specific Functions

WebGL spoofing requires complex nested configurations.

### 1. Context Attributes

```cpp
template <typename T>
std::optional<T> GetAttribute(const std::string attrib, bool isWebGL2)
```

Get WebGL context attributes.

**Example**:
```cpp
// Config: {
//   "webGl:contextAttributes": {
//     "antialias": true,
//     "alpha": false
//   }
// }
auto antialias = MaskConfig::GetAttribute<bool>("antialias", false);
```

### 2. GL Parameters

```cpp
std::optional<std::variant<int64_t, bool, double, std::string, std::nullptr_t>>
GLParam(uint32_t pname, bool isWebGL2)
```

Get WebGL parameter values by GL constant.

**Example**:
```cpp
// Config: {
//   "webGl:parameters": {
//     "3379": "NVIDIA Corporation",  // GL_VENDOR
//     "7937": "GeForce RTX 3060"     // GL_RENDERER
//   }
// }
auto vendor = MaskConfig::GLParam(3379, false);  // GL_VENDOR
```

### 3. Shader Precision

```cpp
std::optional<std::array<int32_t, 3>> MShaderData(
    uint32_t shaderType, uint32_t precisionType, bool isWebGL2)
```

Get shader precision format data.

**Example**:
```cpp
// Config: {
//   "webGl:shaderPrecisionFormats": {
//     "35633,36338": {  // VERTEX_SHADER, HIGH_FLOAT
//       "rangeMin": 127,
//       "rangeMax": 127,
//       "precision": 23
//     }
//   }
// }
auto precision = MaskConfig::MShaderData(35633, 36338, false);
if (precision) {
    auto [rangeMin, rangeMax, precisionBits] = precision.value();
}
```

---

## Voice Synthesis Configuration

```cpp
std::optional<std::vector<std::tuple<std::string, std::string, std::string, bool, bool>>>
MVoices()
```

Get voice synthesis configurations.

**Example**:
```cpp
// Config: {
//   "voices": [
//     {
//       "lang": "en-US",
//       "name": "Google US English",
//       "voiceUri": "Google US English",
//       "isDefault": true,
//       "isLocalService": false
//     }
//   ]
// }
auto voices = MaskConfig::MVoices();
if (voices) {
    for (const auto& [lang, name, uri, isDefault, isLocal] : voices.value()) {
        // Use voice data
    }
}
```

---

## Platform-Specific Handling

### Windows UTF-16 Support

```cpp
std::optional<std::string> get_env_utf8(const std::string& name)
```

Handles Windows wide character environment variables:
- Windows: Uses `GetEnvironmentVariableW()` and converts UTF-16 to UTF-8
- Unix: Uses standard `std::getenv()`

---

## Usage Patterns in Patches

### Pattern 1: Simple Value Replacement

```cpp
double AudioContext::OutputLatency() {
    // Check MaskConfig first
    if (auto value = MaskConfig::GetDouble("AudioContext:outputLatency"))
        return value.value();
    
    // Fallback to original logic
    if (mShouldResistFingerprinting) {
        return 0.015;  // Default fingerprint resistance value
    }
    return GetActualLatency();
}
```

### Pattern 2: Conditional Spoofing

```cpp
uint32_t AudioContext::MaxChannelCount() const {
    // Only spoof if config provided
    if (auto value = MaskConfig::GetUint32("AudioContext:maxChannelCount"))
        return value.value();
    
    // Otherwise use fingerprint resistance or real value
    if (mShouldResistFingerprinting) {
        return 2;
    }
    return mDestination->MaxChannelCount();
}
```

### Pattern 3: Complex Object Spoofing

```cpp
void GetClientRect(nsRect& aRect) {
    if (doc->GetBodyElement() == this) {
        if (auto conf = MaskConfig::GetInt32Rect(
                "document.body.clientLeft", "document.body.clientTop",
                "document.body.clientWidth", "document.body.clientHeight")) {
            auto values = conf.value();
            aRect = nsRect(values[0] * 60, values[1] * 60, 
                          values[2] * 60, values[3] * 60);
            return;
        }
    }
    // Fallback to real dimensions
    GetActualClientRect(aRect);
}
```

---

## Configuration Examples

### Example 1: Basic Canvas Spoofing

```json
{
  "canvas:seed": 12345,
  "canvas:noise": 0.02
}
```

### Example 2: WebGL Complete Configuration

```json
{
  "webGl:contextAttributes": {
    "antialias": true,
    "alpha": true,
    "depth": true
  },
  "webGl:parameters": {
    "3379": "NVIDIA Corporation",
    "7937": "GeForce RTX 3060",
    "7938": "OpenGL ES 3.0",
    "3386": 16384
  },
  "webGl:shaderPrecisionFormats": {
    "35633,36338": {
      "rangeMin": 127,
      "rangeMax": 127,
      "precision": 23
    }
  }
}
```

### Example 3: Complete Profile

```json
{
  "AudioContext:sampleRate": 48000,
  "AudioContext:outputLatency": 0.015,
  "AudioContext:maxChannelCount": 2,
  "canvas:seed": 98765,
  "canvas:noise": 0.03,
  "window.innerWidth": 1920,
  "window.innerHeight": 1080,
  "document.body.clientLeft": 0,
  "document.body.clientTop": 0,
  "document.body.clientWidth": 1920,
  "document.body.clientHeight": 1080,
  "webGl:contextAttributes": {
    "antialias": true
  },
  "webGl:parameters": {
    "3379": "NVIDIA Corporation"
  },
  "fonts": ["Arial", "Helvetica", "Times New Roman"],
  "voices": [
    {
      "lang": "en-US",
      "name": "Google US English",
      "voiceUri": "Google US English",
      "isDefault": true,
      "isLocalService": false
    }
  ]
}
```

---

## Extension Opportunities for Tegufox

### 1. Add New Data Types

```cpp
// Add Date/Time support
inline std::optional<std::chrono::system_clock::time_point> 
GetDateTime(const std::string& key) {
    const auto& data = GetJson();
    if (!HasKey(key, data)) return std::nullopt;
    // Parse ISO 8601 timestamp
    return ParseISO8601(data[key].get<std::string>());
}
```

### 2. Add Validation Helpers

```cpp
// Validate correlation between values
inline bool ValidateConsistency() {
    // Check OS ↔ GPU correlation
    auto os = GetString("navigator:platform");
    auto gpu = GetString("webGl:vendor");
    
    if (os == "Win32" && gpu.has_value()) {
        // Windows should have compatible GPU vendors
        return ValidateWindowsGPU(gpu.value());
    }
    return true;
}
```

### 3. Add Profile Templates

```cpp
// Load pre-configured profiles
inline void LoadProfile(const std::string& profileType) {
    static const std::map<std::string, std::string> profiles = {
        {"windows-chrome", R"({"navigator:platform":"Win32",...})"},
        {"macos-safari", R"({"navigator:platform":"MacIntel",...})"},
    };
    // Merge profile with existing config
}
```

### 4. Add Dynamic Value Generation

```cpp
// Generate realistic random values
inline std::optional<double> GetOrGenerate(
    const std::string& key,
    std::function<double()> generator) {
    
    if (auto value = GetDouble(key)) {
        return value;
    }
    // Generate and cache value
    return generator();
}
```

---

## Performance Considerations

### Caching Strategy

- JSON parsed **once** via `std::once_flag`
- Config stored in static variable (process lifetime)
- No re-parsing on subsequent calls
- Thread-safe initialization

### Memory Usage

- JSON config kept in memory for entire browser session
- Typical config size: 5-50 KB
- Negligible impact on Firefox memory footprint

### Lookup Performance

- Direct JSON key access: O(1) average case
- Nested access: O(depth)
- No significant performance impact on rendering

---

## Security Considerations

### Input Validation

- JSON syntax validated before parsing
- Type checking for all Get operations
- Graceful fallback on invalid config
- Error messages to stderr (not exposed to web content)

### Isolation

- Config read from environment variables (isolated per process)
- No web content can access MaskConfig
- No leakage of configuration to JavaScript

---

## Best Practices for Patch Development

### 1. Always Use Optional

```cpp
// ✅ Good: Check if config exists
if (auto value = MaskConfig::GetDouble("feature:param"))
    return value.value();

// ❌ Bad: Assume config exists
return MaskConfig::GetDouble("feature:param").value();  // May crash!
```

### 2. Provide Fallbacks

```cpp
// ✅ Good: Fallback chain
if (auto value = MaskConfig::GetDouble("param"))
    return value.value();
if (mShouldResistFingerprinting)
    return kFingerprintResistanceValue;
return GetRealValue();
```

### 3. Use Semantic Keys

```cpp
// ✅ Good: Descriptive keys
MaskConfig::GetDouble("AudioContext:outputLatency")
MaskConfig::GetString("webGl:vendor")

// ❌ Bad: Cryptic keys
MaskConfig::GetDouble("ac_ol")
MaskConfig::GetString("wgl_v")
```

### 4. Document Config Schema

```cpp
// At top of patch file:
/*
 * Required MaskConfig keys:
 * - "AudioContext:sampleRate" (uint32): Sample rate in Hz
 * - "AudioContext:outputLatency" (double): Latency in seconds
 * - "AudioContext:maxChannelCount" (uint32): Max audio channels
 */
```

---

## Tegufox Enhancements

### Planned Improvements

1. **Schema Validation**:
   - JSON schema for config validation
   - Type checking at config load time
   - Error reporting for invalid configs

2. **Config Merging**:
   - Load base profile + platform-specific overrides
   - Support inheritance/composition

3. **Dynamic Updates**:
   - Hot-reload config without browser restart
   - Per-tab configuration

4. **Debugging Tools**:
   - Dump current config to console
   - Trace which patches use which keys
   - Validation warnings

---

## Summary

**MaskConfig.hpp** is the backbone of Camoufox's spoofing system:

✅ **Strengths**:
- Simple, elegant API
- Thread-safe
- Type-safe
- Extensible
- Performant

✅ **Use Cases**:
- Fingerprint value injection
- WebGL parameter spoofing
- Audio API manipulation
- Navigator property masking
- Any C++ level spoofing

✅ **Extension Points** for Tegufox:
- Add new data types
- Add validation helpers
- Add profile templates
- Add dynamic generation

**Next Steps**:
1. Study existing patches that use MaskConfig
2. Identify common patterns
3. Design Tegufox-specific extensions
4. Create patch templates with MaskConfig integration

---

**File**: `docs/MASKCONFIG_ANALYSIS.md`  
**Version**: 1.0  
**Date**: 2026-04-13
