# Camoufox Patch Patterns Analysis

**Date**: 2026-04-13  
**Purpose**: Understand common patterns in Camoufox patches to create Tegufox templates  
**Analyzed**: 32 patches from Camoufox source

---

## 📊 Patch Statistics

**Total patches**: 32  
**Size range**: 14 lines → 1,424 lines  
**Average size**: ~200 lines

**Categories**:
- Fingerprinting (12 patches): canvas, webgl, fonts, audio, screen
- Privacy (8 patches): geolocation, media devices, battery
- Browser behavior (6 patches): addons, navigation, theming
- Network (4 patches): headers, WebRTC
- Other (2 patches): utilities, fixes

---

## 🎯 Common Patterns

### Pattern 1: Simple Value Override

**Use case**: Override single API return value

**Structure**:
```diff
diff --git a/path/to/source.cpp
index abc123..def456 100644
--- a/path/to/source.cpp
+++ b/path/to/source.cpp
@@ -10,6 +10,7 @@
 #include "Header.h"
+#include "MaskConfig.hpp"
 
 namespace mozilla::dom {
 
@@ -100,6 +101,8 @@ ReturnType ClassName::GetSomeValue() {
+  if (auto value = MaskConfig::GetType("config.key"))
+    return value.value();
   return originalImplementation();
 }
```

**Real Example** (geolocation-spoofing.patch):
```cpp
NS_IMETHODIMP
nsGeoPositionCoords::GetLatitude(double* aLatitude) {
+  if (auto value = MaskConfig::GetDouble("geolocation:latitude"))
+    *aLatitude = value.value();
+  else
    *aLatitude = mLat;
  return NS_OK;
}
```

**Properties**:
- ✅ Simple: 2-4 lines of code
- ✅ Non-invasive: Fallback to original behavior
- ✅ Type-safe: Uses `std::optional`

---

### Pattern 2: Conditional Behavior Change

**Use case**: Enable/disable features or change logic flow

**Structure**:
```diff
diff --git a/path/to/source.cpp
@@ -50,6 +51,10 @@ bool ClassName::ShouldDoSomething() {
+  if (MaskConfig::CheckBool("feature:enabled")) {
+    return performAlternativeBehavior();
+  }
+
   return originalBehavior();
 }
```

**Real Example** (disable-remote-subframes.patch):
```cpp
bool nsDocShell::ShouldLoadInParent(nsDocShellLoadState* aLoadState) {
+  if (MaskConfig::GetBool("enableRemoteSubframes")) {
+    return CheckLoadInParentProcess();
+  }
+
   return false;  // Always load in current process
}
```

**Properties**:
- ✅ Feature flag pattern
- ✅ Boolean logic
- ✅ Clean separation of concerns

---

### Pattern 3: Value with Fallback

**Use case**: Provide default value if config not set

**Structure**:
```cpp
Type value = MaskConfig::GetType("key").value_or(defaultValue);
```

**Real Example** (media-device-spoofing.patch):
```cpp
uint32_t numMics = MaskConfig::GetUint32("mediaDevices:micros").value_or(3);
uint32_t numWebcams = MaskConfig::GetUint32("mediaDevices:webcams").value_or(1);
uint32_t numSpeakers = MaskConfig::GetUint32("mediaDevices:speakers").value_or(1);
```

**Properties**:
- ✅ One-liner
- ✅ Always has value
- ✅ Predictable behavior

---

### Pattern 4: Complex Structure Override

**Use case**: Override multiple related values

**Structure**:
```cpp
if (auto rect = MaskConfig::GetRect("left", "top", "width", "height")) {
    auto values = rect.value();
    applyValues(values[0], values[1], values[2], values[3]);
}
```

**Real Example** (fingerprint-injection.patch):
```cpp
if (auto conf = MaskConfig::GetInt32Rect(
        "document.body.clientLeft", 
        "document.body.clientTop",
        "document.body.clientWidth", 
        "document.body.clientHeight")) {
    auto values = conf.value();
    return nsRect(values[0] * 60, values[1] * 60, 
                  values[2] * 60, values[3] * 60);
}
```

**Properties**:
- ✅ Groups related config
- ✅ Atomic: all or nothing
- ✅ Type-safe array

---

### Pattern 5: Nested Config Access

**Use case**: WebGL parameters, complex hierarchies

**Structure**:
```cpp
if (auto value = MaskConfig::GetNested("domain", "key")) {
    return value.value().get<Type>();
}
```

**Real Example** (webgl-spoofing.patch):
```cpp
if (auto vendor = MaskConfig::GetString("webGl:vendor")) {
    return vendor.value();
}

// Get specific GL parameter
auto data = MaskConfig::GetNested("webGl:parameters", "3379");
if (data) {
    return data.value().get<std::string>();
}
```

**Properties**:
- ✅ Hierarchical config
- ✅ Flexible structure
- ✅ JSON-like access

---

### Pattern 6: Early Return Pattern

**Use case**: Override at function start

**Structure**:
```cpp
ReturnType ClassName::GetValue() {
+  if (auto value = MaskConfig::GetType("key")) 
+    return value.value();
+
   // Original implementation continues...
   complexLogic();
   return computedValue;
}
```

**Real Example** (fingerprint-injection.patch):
```cpp
double nsGlobalWindowInner::GetInnerWidth(ErrorResult& aError) {
+  if (auto value = MaskConfig::GetDouble("window.innerWidth"))
+    return value.value();
+
  FORWARD_TO_OUTER_OR_THROW(GetInnerWidthOuter, (aError), aError, 0);
}
```

**Properties**:
- ✅ Minimal code change
- ✅ Clear override intent
- ✅ Original logic preserved

---

## 🏗️ Patch File Structure

All patches follow unified diff format:

```diff
diff --git a/path/to/file.cpp b/path/to/file.cpp
index oldsha..newsha 100644
--- a/path/to/file.cpp
+++ b/path/to/file.cpp
@@ -line,count +line,count @@
 context line
-removed line
+added line
 context line
```

### Common Components

**1. File modification**:
```diff
diff --git a/dom/geolocation/Geolocation.cpp
index 274cdebc2e..b0183ecc6a 100644
--- a/dom/geolocation/Geolocation.cpp
+++ b/dom/geolocation/Geolocation.cpp
```

**2. Include MaskConfig.hpp**:
```diff
@@ -34,6 +34,7 @@
 #include "nsServiceManagerUtils.h"
 #include "nsThreadUtils.h"
+#include "MaskConfig.hpp"
 
 class nsIPrincipal;
```

**3. Code changes**:
```diff
@@ -1267,6 +1268,12 @@ void Geolocation::NotifyAllowedRequest() {
 bool Geolocation::RegisterRequestWithPrompt(nsGeolocationRequest* request) {
   nsIEventTarget* target = GetMainThreadSerialEventTarget();
+  if (MaskConfig::GetDouble("geolocation:latitude") &&
+      MaskConfig::GetDouble("geolocation:longitude")) {
+    // Allow geolocation request
+    return true;
+  }
   ContentPermissionRequestBase::PromptResult pr = request->CheckPromptPrefs();
```

**4. Update moz.build**:
```diff
diff --git a/dom/geolocation/moz.build
index 2d6b6b5fab..0c7ed74c6d 100644
--- a/dom/geolocation/moz.build
+++ b/dom/geolocation/moz.build
@@ -84,4 +84,7 @@
 MOCHITEST_MANIFESTS += ["test/mochitest/mochitest.toml"]
 XPCSHELL_TESTS_MANIFESTS += ["test/unit/xpcshell.toml"]
+
+# Camoufox: include path for MaskConfig.hpp
+LOCAL_INCLUDES += ["/camoucfg"]
```

---

## 📐 Patch Template Structure

Based on analysis, a patch template should include:

### Required Components

1. **Header comment**:
```diff
# Description: What this patch does
# Config keys: List of MaskConfig keys used
# Files modified: List of files
```

2. **File diffs**:
   - Source file (`.cpp`, `.h`, etc.)
   - Build file (`moz.build`)

3. **MaskConfig include**:
```cpp
+#include "MaskConfig.hpp"
```

4. **Build system update**:
```makefile
+LOCAL_INCLUDES += ["/camoucfg"]
```

5. **Code changes**:
   - Use appropriate MaskConfig getter
   - Follow pattern (early return, fallback, etc.)
   - Preserve original logic

---

## 🎨 Config Key Naming

From 111+ MaskConfig usages:

### Dot Notation (Browser APIs)

```
navigator.userAgent
navigator.platform
navigator.hardwareConcurrency
screen.width
screen.height
screen.colorDepth
window.innerWidth
window.innerHeight
window.devicePixelRatio
battery.level
battery.charging
```

### Colon Notation (Custom Features)

```
canvas:seed
canvas:noise
AudioContext:sampleRate
AudioContext:maxChannelCount
webGl:vendor
webGl:renderer
webGl:parameters
webGl2:supportedExtensions
geolocation:latitude
geolocation:longitude
mediaDevices:micros
mediaDevices:webcams
fonts:spacing_seed
```

### Nested Structure

```json
{
  "webGl:parameters": {
    "3379": "Intel Iris Graphics"
  },
  "webGl:contextAttributes": {
    "antialias": true,
    "powerPreference": "high-performance"
  }
}
```

---

## 🔧 MaskConfig API Usage Frequency

From grep analysis (111 usages):

| Method | Count | Use Cases |
|--------|-------|-----------|
| `GetString()` | 28 | User agent, platform, vendor |
| `GetInt32()` | 22 | Screen dimensions, counts |
| `GetDouble()` | 18 | Ratios, latitudes, levels |
| `GetBool()` | 15 | Feature flags |
| `CheckBool()` | 8 | Quick boolean checks |
| `GetUint32()` | 10 | Seeds, hardware values |
| `GetNested()` | 6 | WebGL, complex configs |
| `GetRect()` | 2 | Screen areas |
| `GetStringList()` | 2 | Fonts, extensions |

---

## 💡 Best Practices (From Real Patches)

### ✅ DO

1. **Check before use**:
```cpp
if (auto value = MaskConfig::GetString("key")) {
    use(value.value());
}
```

2. **Provide fallbacks**:
```cpp
double ratio = MaskConfig::GetDouble("window.devicePixelRatio")
                   .value_or(1.0);
```

3. **Use appropriate types**:
```cpp
// Screen dimensions → int32
int32_t width = MaskConfig::GetInt32("screen.width");

// Ratios, percentages → double
double ratio = MaskConfig::GetDouble("battery.level");

// Feature flags → bool
bool enabled = MaskConfig::CheckBool("feature:enabled");
```

4. **Keep original logic**:
```cpp
double GetValue() {
+  if (auto value = MaskConfig::GetDouble("key"))
+    return value.value();
+
  // Original implementation preserved
  return computeValue();
}
```

### ❌ DON'T

1. **Don't access without checking**:
```cpp
// BAD: May throw!
return MaskConfig::GetString("key").value();

// GOOD:
if (auto value = MaskConfig::GetString("key")) {
    return value.value();
}
```

2. **Don't use wrong types**:
```cpp
// BAD: Screen width is integer!
double width = MaskConfig::GetDouble("screen.width");

// GOOD:
int32_t width = MaskConfig::GetInt32("screen.width");
```

3. **Don't skip moz.build**:
```
Every patch that includes MaskConfig.hpp MUST update moz.build!
```

---

## 🚀 Tegufox Patch Templates

Based on patterns, we can create templates for:

### Template 1: Simple Value Override

```cpp
// File: patches/templates/simple-value-override.patch
diff --git a/{{SOURCE_PATH}}
index {{OLD_SHA}}..{{NEW_SHA}} 100644
--- a/{{SOURCE_PATH}}
+++ b/{{SOURCE_PATH}}
@@ -{{LINE}},{{COUNT}} +{{LINE}},{{COUNT}} @@
 #include "{{HEADER}}"
+#include "MaskConfig.hpp"
 
 {{RETURN_TYPE}} {{CLASS}}::{{METHOD}}({{PARAMS}}) {
+  if (auto value = MaskConfig::{{GETTER}}("{{CONFIG_KEY}}"))
+    return value.value();
+
   {{ORIGINAL_LOGIC}}
 }

diff --git a/{{MOZ_BUILD_PATH}}
@@ -{{LINE}},{{COUNT}} +{{LINE}},{{COUNT}} @@
 FINAL_LIBRARY = "xul"
+
+# Tegufox: Custom patch
+LOCAL_INCLUDES += ["/camoucfg"]
```

### Template 2: Feature Flag

```cpp
// File: patches/templates/feature-flag.patch
diff --git a/{{SOURCE_PATH}}
+#include "MaskConfig.hpp"

 {{RETURN_TYPE}} {{CLASS}}::{{METHOD}}({{PARAMS}}) {
+  if (MaskConfig::CheckBool("{{CONFIG_KEY}}")) {
+    {{CUSTOM_LOGIC}}
+  }
+
   {{ORIGINAL_LOGIC}}
 }
```

### Template 3: Value with Fallback

```cpp
// One-liner pattern
{{TYPE}} {{VAR}} = MaskConfig::{{GETTER}}("{{KEY}}").value_or({{DEFAULT}});
```

---

## 📊 Complexity Analysis

### Simple Patches (< 50 lines)

Examples:
- `shadow-root-bypass.patch` (14 lines)
- `disable-extension-newtab.patch` (28 lines)
- `force-default-pointer.patch` (31 lines)

**Characteristics**:
- Single file modification
- 1-3 code changes
- Minimal logic

**Time to create**: 10-15 minutes

### Medium Patches (50-200 lines)

Examples:
- `audio-context-spoofing.patch` (74 lines)
- `geolocation-spoofing.patch` (151 lines)
- `media-device-spoofing.patch` (~100 lines)

**Characteristics**:
- 2-3 file modifications
- Multiple MaskConfig calls
- Some custom logic

**Time to create**: 30-60 minutes

### Complex Patches (200+ lines)

Examples:
- `webgl-spoofing.patch` (~800 lines)
- `anti-font-fingerprinting.patch` (1,424 lines)
- `navigator-spoofing.patch` (~600 lines)

**Characteristics**:
- Multiple file modifications
- New files created
- Complex logic
- Nested configs

**Time to create**: 2-4 hours

---

## 🎯 Recommendations for Tegufox

### Phase 1: Start with Simple Patterns

Create patches using Pattern 1 (Simple Value Override):
- Mouse jitter parameters
- Typing rhythm config
- Scroll behavior settings

**Estimated time**: 30 min per patch

### Phase 2: Medium Complexity

Use Pattern 2 (Conditional Behavior):
- Payment form interaction
- Behavioral timing
- Platform-specific logic

**Estimated time**: 1 hour per patch

### Phase 3: Advanced Features

Use Pattern 5 (Nested Config):
- TLS fingerprint tuning
- Complex behavioral profiles
- Multi-parameter coordination

**Estimated time**: 2-3 hours per patch

---

## 📚 Next Steps

1. **Create patch generator**:
   - Input: Pattern type, config keys, target file
   - Output: Complete patch file
   - Validation: Check syntax, verify includes

2. **Build testing framework**:
   - Apply patch to Firefox source
   - Compile
   - Test MaskConfig values
   - Verify behavior

3. **Documentation**:
   - Template catalog
   - Step-by-step guides
   - Common pitfalls
   - Debugging tips

---

**Analysis Complete**: ✅  
**Patterns Identified**: 6  
**Templates Ready**: 3  
**Confidence**: High 🚀

Ready to build patch generator! 🎯
