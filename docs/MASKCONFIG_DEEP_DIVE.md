# MaskConfig System - Deep Dive

**Date**: 2026-04-13  
**Author**: Tegufox Research  
**Status**: Phase 0 Technical Analysis

---

## 📋 Overview

MaskConfig là hệ thống cấu hình trung tâm của Camoufox, cho phép patches C++ đọc configuration từ Python API thông qua environment variables. Đây là "cầu nối" giữa high-level Python code và low-level C++ browser patches.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Python API Layer                       │
│   config = {"canvas:seed": 123, "screen.width": 1920}  │
└─────────────────────────────────────────────────────────┘
                            │
                            ├── JSON.stringify()
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Environment Variables                      │
│   CAMOU_CONFIG_1 = '{"canvas:seed":123,"screen.wi...'  │
│   CAMOU_CONFIG_2 = 'dth":1920}'                         │
└─────────────────────────────────────────────────────────┘
                            │
                            ├── Read by C++ at runtime
                            ▼
┌─────────────────────────────────────────────────────────┐
│              MaskConfig.hpp (C++)                       │
│   - GetJson() - Parse env vars into JSON object        │
│   - GetString(), GetInt32(), GetDouble(), etc.         │
│   - Type-safe accessors with std::optional             │
└─────────────────────────────────────────────────────────┘
                            │
                            ├── Used by patches
                            ▼
┌─────────────────────────────────────────────────────────┐
│           Firefox C++ Patches                           │
│   if (auto seed = MaskConfig::GetUint32("canvas:seed")) │
│       applyCanvasNoise(seed.value());                   │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 File Location

**Location**: `/camoufox-source/additions/camoucfg/MaskConfig.hpp`

**Size**: 313 lines of C++ code

**Dependencies**:
- `json.hpp` - nlohmann/json library (919KB, single header)
- `mozilla/glue/Debug.h` - Firefox debugging utilities

---

## 🔑 Key Components

### 1. Environment Variable Reading

MaskConfig reads config từ environment variables với UTF-8 support:

```cpp
inline std::optional<std::string> get_env_utf8(const std::string& name) {
#ifdef _WIN32
  // Windows: Use GetEnvironmentVariableW for UTF-16
  std::wstring wName(name.begin(), name.end());
  DWORD size = GetEnvironmentVariableW(wName.c_str(), nullptr, 0);
  if (size == 0) return std::nullopt;
  
  std::vector<wchar_t> buffer(size);
  GetEnvironmentVariableW(wName.c_str(), buffer.data(), size);
  
  // Convert UTF-16 to UTF-8
  std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter;
  return converter.to_bytes(wValue);
#else
  // Unix/Linux/macOS: Use std::getenv
  const char* value = std::getenv(name.c_str());
  if (!value) return std::nullopt;
  return std::string(value);
#endif
}
```

**Why Important**:
- Cross-platform compatibility (Windows vs Unix)
- UTF-8 encoding support (important for international configs)
- Returns `std::optional` (type-safe null handling)

---

### 2. JSON Parsing with Chunking

Config JSON được split thành multiple environment variables để bypass OS limits:

```cpp
inline const nlohmann::json& GetJson() {
  static std::once_flag initFlag;
  static nlohmann::json jsonConfig;

  std::call_once(initFlag, []() {
    std::string jsonString;
    int index = 1;

    // Read CAMOU_CONFIG_1, CAMOU_CONFIG_2, ... sequentially
    while (true) {
      std::string envName = "CAMOU_CONFIG_" + std::to_string(index);
      auto partialConfig = get_env_utf8(envName);
      if (!partialConfig) break;
      
      jsonString += *partialConfig;  // Concatenate chunks
      index++;
    }

    // Fallback to original CAMOU_CONFIG
    if (jsonString.empty()) {
      auto originalConfig = get_env_utf8("CAMOU_CONFIG");
      if (originalConfig) jsonString = *originalConfig;
    }

    // Validate JSON
    if (!nlohmann::json::accept(jsonString)) {
      printf_stderr("ERROR: Invalid JSON passed to CAMOU_CONFIG!\n");
      jsonConfig = nlohmann::json{};
      return;
    }

    jsonConfig = nlohmann::json::parse(jsonString);
  });

  return jsonConfig;
}
```

**Key Features**:
1. **Chunking**: Large configs split across `CAMOU_CONFIG_1`, `CAMOU_CONFIG_2`, etc.
2. **Lazy loading**: JSON parsed once on first access (`std::once_flag`)
3. **Thread-safe**: `std::call_once` ensures single initialization
4. **Fallback**: Supports legacy `CAMOU_CONFIG` single variable
5. **Validation**: Checks JSON validity before parsing

**Why Chunking?**
- Environment variables have size limits (typically 32KB on Unix, 32KB on Windows)
- Large fingerprint configs can exceed this limit
- Solution: Split JSON string across multiple variables

---

### 3. Type-Safe Accessors

MaskConfig provides type-safe getters returning `std::optional<T>`:

#### String Values

```cpp
inline std::optional<std::string> GetString(const std::string& key) {
  const auto& data = GetJson();
  if (!HasKey(key, data)) return std::nullopt;
  return data[key].get<std::string>();
}
```

**Usage in patches**:
```cpp
if (auto userAgent = MaskConfig::GetString("navigator.userAgent")) {
    return userAgent.value();
}
```

#### Numeric Values

```cpp
// Unsigned integers
inline std::optional<uint32_t> GetUint32(const std::string& key);
inline std::optional<uint64_t> GetUint64(const std::string& key);

// Signed integers  
inline std::optional<int32_t> GetInt32(const std::string& key);

// Floating point
inline std::optional<double> GetDouble(const std::string& key) {
  const auto& data = GetJson();
  if (!HasKey(key, data)) return std::nullopt;
  
  // Support both float and integer JSON types
  if (data[key].is_number_float()) 
      return data[key].get<double>();
  if (data[key].is_number_unsigned() || data[key].is_number_integer())
      return static_cast<double>(data[key].get<int64_t>());
      
  printf_stderr("ERROR: Value for key '%s' is not a double\n", key.c_str());
  return std::nullopt;
}
```

**Error Handling**: Prints to stderr but doesn't crash browser

#### Boolean Values

```cpp
inline std::optional<bool> GetBool(const std::string& key);

// Convenience: Get bool with default false
inline bool CheckBool(const std::string& key) {
  return GetBool(key).value_or(false);
}
```

**Usage**:
```cpp
if (MaskConfig::CheckBool("disableTheming")) {
    // Disable theme...
}
```

#### String Lists

```cpp
inline std::vector<std::string> GetStringList(const std::string& key) {
  std::vector<std::string> result;
  const auto& data = GetJson();
  if (!HasKey(key, data)) return {};
  
  for (const auto& item : data[key]) {
    result.push_back(item.get<std::string>());
  }
  return result;
}

// Lowercase variant (for case-insensitive matching)
inline std::vector<std::string> GetStringListLower(const std::string& key);
```

**Usage in font hijacking**:
```cpp
std::vector<std::string> fonts = MaskConfig::GetStringList("fonts");
```

---

### 4. Complex Data Types

#### Rectangles (for screen/window dimensions)

```cpp
inline std::optional<std::array<uint32_t, 4>> GetRect(
    const std::string& left, 
    const std::string& top, 
    const std::string& width,
    const std::string& height
) {
  std::array<std::optional<uint32_t>, 4> values = {
      GetUint32(left).value_or(0),   // Default left=0
      GetUint32(top).value_or(0),    // Default top=0
      GetUint32(width),              // Required
      GetUint32(height)              // Required
  };

  // Both width and height must be provided
  if (!values[2].has_value() || !values[3].has_value()) {
    return std::nullopt;
  }

  return std::array<uint32_t, 4>{
      values[0].value(), 
      values[1].value(),
      values[2].value(), 
      values[3].value()
  };
}
```

**Usage in screen spoofing**:
```cpp
auto rect = MaskConfig::GetRect(
    "screen.availLeft", 
    "screen.availTop",
    "screen.availWidth", 
    "screen.availHeight"
);
if (rect) {
    // rect = [left, top, width, height]
}
```

---

### 5. WebGL-Specific Helpers

#### Nested JSON Access

```cpp
inline std::optional<nlohmann::json> GetNested(
    const std::string& domain,
    std::string keyStr
) {
  auto data = GetJson();
  if (!data.contains(domain)) return std::nullopt;
  if (!data[domain].contains(keyStr)) return std::nullopt;
  
  return data[domain][keyStr];
}
```

**Example JSON Structure**:
```json
{
  "webGl:parameters": {
    "3379": "Intel Inc.",       // GL_RENDERER
    "7936": "ANGLE"             // GL_VENDOR
  },
  "webGl:contextAttributes": {
    "antialias": true,
    "powerPreference": "high-performance"
  }
}
```

#### WebGL Parameters

```cpp
template <typename T>
inline T MParamGL(uint32_t pname, T defaultValue, bool isWebGL2) {
  if (auto value = MaskConfig::GetNested(
          isWebGL2 ? "webGl2:parameters" : "webGl:parameters",
          std::to_string(pname));
      value.has_value()) {
    return value.value().get<T>();
  }
  return defaultValue;
}
```

**Usage in WebGL spoofing**:
```cpp
// Get GL_BLEND state (default: false)
bool blend = MaskConfig::MParamGL<bool>(
    LOCAL_GL_BLEND, 
    false,      // default
    webgl2      // isWebGL2?
);
```

#### WebGL Shader Precision

```cpp
inline std::optional<std::array<int32_t, 3>> MShaderData(
    uint32_t shaderType,      // VERTEX_SHADER or FRAGMENT_SHADER
    uint32_t precisionType,   // LOW_FLOAT, MEDIUM_FLOAT, HIGH_FLOAT
    bool isWebGL2
) {
  std::string valueName = 
      std::to_string(shaderType) + "," + std::to_string(precisionType);
  
  if (auto value = MaskConfig::GetNested(
          isWebGL2 ? "webGl2:shaderPrecisionFormats" 
                   : "webGl:shaderPrecisionFormats",
          valueName)) {
    auto data = value.value();
    return std::array<int32_t, 3>{
        data["rangeMin"].get<int32_t>(),
        data["rangeMax"].get<int32_t>(),
        data["precision"].get<int32_t>()
    };
  }
  return std::nullopt;
}
```

**JSON Structure**:
```json
{
  "webGl:shaderPrecisionFormats": {
    "35633,36336": {  // VERTEX_SHADER, HIGH_FLOAT
      "rangeMin": 127,
      "rangeMax": 127,
      "precision": 23
    }
  }
}
```

---

## 🎨 Property Naming Conventions

Camoufox uses **mixed naming conventions** based on category:

### Dot Notation (`.`)

Used for standard browser APIs:

```
navigator.userAgent
navigator.platform
navigator.hardwareConcurrency
screen.width
screen.height
screen.colorDepth
window.innerWidth
window.innerHeight
```

**Why**: Matches JavaScript property paths

### Colon Notation (`:`)

Used for custom/spoofing configs:

```
canvas:seed
canvas:noise
AudioContext:sampleRate
AudioContext:maxChannelCount
webGl:vendor
webGl:renderer
webGl:parameters
webGl2:supportedExtensions
```

**Why**: Distinguishes custom properties from browser APIs

### Examples from Real Patches

**Navigator Spoofing** (`navigator-spoofing.patch`):
```cpp
MaskConfig::GetString("navigator.userAgent")     // Dot notation
MaskConfig::GetString("navigator.platform")
MaskConfig::GetUint64("navigator.hardwareConcurrency")
```

**Audio Context Spoofing** (`audio-context-spoofing.patch`):
```cpp
MaskConfig::GetUint32("AudioContext:sampleRate")        // Colon notation
MaskConfig::GetUint32("AudioContext:maxChannelCount")
MaskConfig::GetDouble("AudioContext:outputLatency")
```

**WebGL Spoofing** (`webgl-spoofing.patch`):
```cpp
MaskConfig::GetString("webGl:vendor")            // Colon for category
MaskConfig::GetString("webGl:renderer")
MaskConfig::GetNested("webGl:parameters", "3379")  // Nested structure
```

---

## 📊 Data Flow Example

### From Python to C++

**1. Python API Call**:
```python
from camoufox import Camoufox

config = {
    "navigator.userAgent": "Mozilla/5.0 ...",
    "screen.width": 1920,
    "screen.height": 1080,
    "canvas:seed": 42,
    "AudioContext:sampleRate": 48000,
    "webGl:vendor": "Intel Inc.",
    "webGl:parameters": {
        "3379": "Intel Iris Graphics"  # GL_RENDERER
    }
}

browser = Camoufox(config=config)
```

**2. Python sets environment variables**:
```python
import json
import os

json_string = json.dumps(config)

# Split into chunks if needed
chunks = [json_string[i:i+30000] for i in range(0, len(json_string), 30000)]

for idx, chunk in enumerate(chunks, 1):
    os.environ[f'CAMOU_CONFIG_{idx}'] = chunk
```

**3. C++ patches read values**:

**Navigator Patch**:
```cpp
#include "MaskConfig.hpp"

if (auto ua = MaskConfig::GetString("navigator.userAgent")) {
    mUserAgent = ua.value();
}
```

**Screen Patch**:
```cpp
if (auto width = MaskConfig::GetInt32("screen.width"),
    height = MaskConfig::GetInt32("screen.height");
    width && height) {
    mScreenWidth = width.value();
    mScreenHeight = height.value();
}
```

**Canvas Patch**:
```cpp
if (auto seed = MaskConfig::GetUint32("canvas:seed")) {
    std::srand(seed.value());
    applyNoise();
}
```

**WebGL Patch**:
```cpp
if (auto vendor = MaskConfig::GetString("webGl:vendor")) {
    return vendor.value();
}

// Get specific GL parameter
auto renderer = MaskConfig::GetNested("webGl:parameters", "3379");
if (renderer) {
    return renderer.value().get<std::string>();
}
```

---

## 🔧 How to Extend MaskConfig

### Adding New Property Types

**Example: Add Tuple Support**

```cpp
// In MaskConfig.hpp

inline std::optional<std::tuple<int, int, int>> GetTuple3(
    const std::string& key
) {
  const auto& data = GetJson();
  if (!HasKey(key, data)) return std::nullopt;
  
  if (!data[key].is_array() || data[key].size() != 3) {
      printf_stderr("ERROR: Key '%s' is not a 3-element array\n", key.c_str());
      return std::nullopt;
  }
  
  return std::make_tuple(
      data[key][0].get<int>(),
      data[key][1].get<int>(),
      data[key][2].get<int>()
  );
}
```

**Usage**:
```cpp
// Config: {"rgb:color": [255, 128, 64]}
if (auto rgb = MaskConfig::GetTuple3("rgb:color")) {
    auto [r, g, b] = rgb.value();
}
```

---

### Adding New Nested Structures

**Example: Battery API Config**

```cpp
// In MaskConfig.hpp

struct BatteryConfig {
    bool charging;
    double level;
    double chargingTime;
    double dischargingTime;
};

inline std::optional<BatteryConfig> GetBatteryConfig() {
  const auto& data = GetJson();
  if (!data.contains("battery")) return std::nullopt;
  
  auto battery = data["battery"];
  return BatteryConfig{
      battery.value("charging", true),
      battery.value("level", 1.0),
      battery.value("chargingTime", 0.0),
      battery.value("dischargingTime", std::numeric_limits<double>::infinity())
  };
}
```

**JSON Config**:
```json
{
  "battery": {
    "charging": false,
    "level": 0.75,
    "dischargingTime": 3600
  }
}
```

**Usage in patch**:
```cpp
if (auto battery = MaskConfig::GetBatteryConfig()) {
    mCharging = battery->charging;
    mLevel = battery->level;
}
```

---

## 🎯 Best Practices for Custom Patches

### 1. Always Use `std::optional`

**❌ Bad**:
```cpp
int width = MaskConfig::GetInt32("screen.width");  // Compile error!
```

**✅ Good**:
```cpp
if (auto width = MaskConfig::GetInt32("screen.width")) {
    applyWidth(width.value());
}
```

### 2. Provide Fallback Values

**❌ Bad**:
```cpp
if (auto seed = MaskConfig::GetUint32("canvas:seed")) {
    std::srand(seed.value());
} else {
    // No fallback - deterministic behavior!
}
```

**✅ Good**:
```cpp
uint32_t seed = MaskConfig::GetUint32("canvas:seed")
                    .value_or(generateRandomSeed());
std::srand(seed);
```

### 3. Use Appropriate Types

**❌ Bad**:
```cpp
// "screen.width" should be int32_t, not double!
if (auto width = MaskConfig::GetDouble("screen.width")) {
    mWidth = static_cast<int>(width.value());
}
```

**✅ Good**:
```cpp
if (auto width = MaskConfig::GetInt32("screen.width")) {
    mWidth = width.value();
}
```

### 4. Validate Nested Structures

**❌ Bad**:
```cpp
auto data = MaskConfig::GetNested("webGl:parameters", "3379");
return data.value().get<std::string>();  // May throw!
```

**✅ Good**:
```cpp
if (auto data = MaskConfig::GetNested("webGl:parameters", "3379")) {
    if (data->is_string()) {
        return data->get<std::string>();
    }
}
return "Default Renderer";
```

### 5. Include MaskConfig Properly

**In your patch** (`.patch` file):
```diff
diff --git a/dom/canvas/CanvasRenderingContext2D.cpp
index 1234567890..abcdefghij 100644
--- a/dom/canvas/CanvasRenderingContext2D.cpp
+++ b/dom/canvas/CanvasRenderingContext2D.cpp
@@ -10,6 +10,7 @@
 #include "mozilla/dom/CanvasRenderingContext2D.h"
+#include "MaskConfig.hpp"
 
 namespace mozilla::dom {
```

**In moz.build**:
```diff
diff --git a/dom/canvas/moz.build
index 1234567890..abcdefghij 100644
--- a/dom/canvas/moz.build
+++ b/dom/canvas/moz.build
@@ -100,3 +100,6 @@ CXXFLAGS += ["-Wno-error=shadow"]
 
 FINAL_LIBRARY = "xul"
+
+# DOM Mask
+LOCAL_INCLUDES += ["/camoucfg"]
```

---

## 🚀 Example: Creating a Custom Patch

### Goal: Add Mouse Acceleration Spoofing

**1. Define Config Schema**

```json
{
  "mouse:acceleration": 1.5,
  "mouse:sensitivity": 0.8,
  "mouse:jitter": 0.02
}
```

**2. Add MaskConfig Helper (optional)**

```cpp
// In MaskConfig.hpp

struct MouseConfig {
    double acceleration;
    double sensitivity;
    double jitter;
};

inline std::optional<MouseConfig> GetMouseConfig() {
  return MouseConfig{
      GetDouble("mouse:acceleration").value_or(1.0),
      GetDouble("mouse:sensitivity").value_or(1.0),
      GetDouble("mouse:jitter").value_or(0.0)
  };
}
```

**3. Create Patch File**

```diff
diff --git a/widget/nsBaseWidget.cpp
index 1234567890..abcdefghij 100644
--- a/widget/nsBaseWidget.cpp
+++ b/widget/nsBaseWidget.cpp
@@ -15,6 +15,7 @@
 #include "nsBaseWidget.h"
+#include "MaskConfig.hpp"
 
 namespace mozilla {
 
@@ -500,6 +501,15 @@ void nsBaseWidget::DispatchEventToAPZOnly() {
 
 nsEventStatus nsBaseWidget::DispatchInputEvent(WidgetInputEvent* aEvent) {
+  // Apply mouse acceleration spoofing
+  if (auto mouseConfig = MaskConfig::GetMouseConfig()) {
+    if (aEvent->mClass == eMouseEventClass) {
+      auto* mouseEvent = aEvent->AsMouseEvent();
+      mouseEvent->mScreenPoint.x *= mouseConfig->sensitivity;
+      mouseEvent->mScreenPoint.y *= mouseConfig->sensitivity;
+    }
+  }
+
   nsEventStatus status = nsEventStatus_eIgnore;
```

**4. Update moz.build**

```diff
diff --git a/widget/moz.build
index 1234567890..abcdefghij 100644
--- a/widget/moz.build
+++ b/widget/moz.build
@@ -250,3 +250,6 @@ if CONFIG["MOZ_WAYLAND"]:
 
 FINAL_LIBRARY = "xul"
+
+# DOM Mask
+LOCAL_INCLUDES += ["/camoucfg"]
```

**5. Usage from Python**

```python
from camoufox import Camoufox

config = {
    "mouse:acceleration": 1.2,
    "mouse:sensitivity": 0.9,
    "mouse:jitter": 0.01
}

browser = Camoufox(config=config)
# Mouse movements now spoofed with acceleration/sensitivity
```

---

## 📈 Performance Considerations

### 1. Lazy Initialization

```cpp
inline const nlohmann::json& GetJson() {
  static std::once_flag initFlag;
  static nlohmann::json jsonConfig;
  
  std::call_once(initFlag, []() {
      // Parse JSON only ONCE
  });
  
  return jsonConfig;
}
```

**Benefits**:
- JSON parsed once on first access
- Thread-safe initialization
- No parsing overhead on subsequent calls

### 2. Return by Reference

```cpp
const nlohmann::json& GetJson()  // Returns const reference, no copy
```

**Benefits**:
- No JSON object copying
- Minimal memory overhead

### 3. std::optional

```cpp
std::optional<std::string> GetString(const std::string& key)
```

**Benefits**:
- Zero-cost abstraction for nullable values
- No exceptions thrown
- Compiler can optimize away optional wrapper

---

## 🔒 Security Considerations

### 1. Input Validation

```cpp
if (!nlohmann::json::accept(jsonString)) {
  printf_stderr("ERROR: Invalid JSON passed to CAMOU_CONFIG!\n");
  jsonConfig = nlohmann::json{};
  return;
}
```

**Protects Against**:
- Malformed JSON injection
- Buffer overflow attempts
- Crash from invalid data

### 2. Type Checking

```cpp
if (!data[key].is_number_integer()) {
  printf_stderr("ERROR: Value for key '%s' is not an integer\n", key.c_str());
  return std::nullopt;
}
```

**Protects Against**:
- Type confusion
- Unexpected data types
- Runtime crashes from type mismatch

### 3. UTF-8 Encoding

```cpp
std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter;
return converter.to_bytes(wValue);
```

**Protects Against**:
- Encoding attacks
- Character set confusion
- Cross-platform encoding issues

---

## 🎓 Key Takeaways

### What MaskConfig Does

1. **Bridge**: Connects Python API ↔ C++ patches
2. **Type-Safe**: std::optional prevents crashes from missing config
3. **Flexible**: Supports strings, numbers, bools, arrays, nested objects
4. **Cross-Platform**: Works on Windows, macOS, Linux
5. **Performance**: Lazy initialization, thread-safe, zero-copy

### How to Use It

1. **Reading simple values**:
   ```cpp
   if (auto value = MaskConfig::GetString("key")) {
       use(value.value());
   }
   ```

2. **Reading nested values**:
   ```cpp
   if (auto value = MaskConfig::GetNested("domain", "key")) {
       use(value.value());
   }
   ```

3. **With defaults**:
   ```cpp
   int width = MaskConfig::GetInt32("screen.width").value_or(1920);
   ```

### How to Extend It

1. Add new type helpers in `MaskConfig.hpp`
2. Follow naming conventions (dots for APIs, colons for spoofing)
3. Always return `std::optional<T>`
4. Validate input and provide error messages
5. Document your additions

---

## 🔗 Related Files

- **MaskConfig.hpp**: `/camoufox-source/additions/camoucfg/MaskConfig.hpp`
- **JSON Library**: `/camoufox-source/additions/camoucfg/json.hpp` (nlohmann/json)
- **Mouse Trajectories**: `/camoufox-source/additions/camoucfg/MouseTrajectories.hpp`
- **Example Patches**: `/camoufox-source/patches/*.patch`

---

## 📚 Next Steps for Tegufox

Based on this analysis, Tegufox can:

1. **Extend MaskConfig** with custom data types:
   - Behavioral timing configs
   - Neural jitter parameters
   - E-commerce platform profiles

2. **Add validation helpers**:
   - Fingerprint consistency checking
   - Cross-property validation (OS ↔ GPU correlation)
   - Config schema validation

3. **Create patch templates** that use MaskConfig:
   - Canvas noise v2
   - Enhanced font metrics
   - TLS fingerprint tuning
   - Neuromotor mouse movement

4. **Build CLI tools** for config generation:
   - Profile template generator
   - Consistency validator
   - Config migration tools

---

**Last Updated**: 2026-04-13  
**Next**: Create first Tegufox custom patch using MaskConfig
