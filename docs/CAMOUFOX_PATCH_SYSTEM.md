# Camoufox Patch System Analysis

## Overview

Camoufox uses a sophisticated C++ patch system to modify Firefox at the core level. Unlike browser extensions that use JavaScript injection, these patches directly modify Firefox's source code to implement deep anti-fingerprinting features.

## Patch Architecture

### Patch Types (38 patches total)

**Core Anti-Fingerprinting Patches:**
- `fingerprint-injection.patch` - Core fingerprint value injection system
- `canvas:` - Canvas fingerprinting protection
- `webgl-spoofing.patch` - WebGL vendor/renderer spoofing
- `audio-fingerprint-manager.patch` + `audio-context-spoofing.patch` - Audio API spoofing
- `font-list-spoofing.patch` + `anti-font-fingerprinting.patch` - Font enumeration protection
- `navigator-spoofing.patch` - Navigator properties (UA, platform, etc.)
- `screen-spoofing.patch` - Screen resolution/dimensions
- `timezone-spoofing.patch` - Timezone spoofing
- `locale-spoofing.patch` - Locale/language settings

**Advanced Spoofing:**
- `webrtc-ip-spoofing.patch` - WebRTC IP leak prevention (protocol level)
- `media-device-spoofing.patch` - Camera/microphone enumeration
- `geolocation-spoofing.patch` - GPS coordinates
- `speech-voices-spoofing.patch` + `voice-spoofing.patch` - Speech synthesis API
- `shadow-root-bypass.patch` - Shadow DOM access control

**Browser Modifications:**
- `browser-init.patch` - Browser initialization customizations
- `chromeutil.patch` - Chrome utilities (required for config system)
- `config.patch` - Configuration system setup
- `cross-process-storage.patch` - Cross-process data sharing

**Privacy & Security:**
- `all-addons-private-mode.patch` - Force extensions into private mode
- `disable-extension-newtab.patch` - Prevent extension new tab hijacking
- `disable-remote-subframes.patch` - Block remote subframes
- `network-patches.patch` - Network-level modifications

**UI/UX Patches:**
- `force-default-pointer.patch` - Consistent mouse pointer
- `global-style-sheets.patch` - Custom CSS injection
- `no-css-animations.patch` - Disable CSS animations
- `no-search-engines.patch` - Remove default search engines
- `pin-addons.patch` - Pin specific addons

**Platform-Specific:**
- `macos-sandbox-crash-fix.patch` - macOS sandbox stability
- `windows-theming-bug-modified.patch` - Windows theme rendering fix

**Third-Party Patches:**
- `librewolf/` - 15 patches from LibreWolf project
- `ghostery/` - Privacy patches from Ghostery
- `playwright/` - Playwright automation compatibility patches

## How Patches Work

### 1. Patch Structure

Patches are standard Git diff files that modify Firefox source:

```diff
diff --git a/dom/media/webaudio/AudioContext.cpp b/dom/media/webaudio/AudioContext.cpp
index 66184b683b..daf30882ea 100644
--- a/dom/media/webaudio/AudioContext.cpp
+++ b/dom/media/webaudio/AudioContext.cpp
@@ -45,6 +45,7 @@
 #include "mozilla/dom/Worklet.h"
 
+#include "MaskConfig.hpp"
 #include "AudioBuffer.h"
```

### 2. MaskConfig System

Most patches use `MaskConfig.hpp` - a C++ header that provides configuration injection:

```cpp
if (auto value = MaskConfig::GetDouble("AudioContext:outputLatency"))
    return value.value();
```

This allows runtime configuration of spoofed values via JSON config passed from Python API.

### 3. Build Integration

Patches modify `moz.build` files to include the configuration system:

```python
# DOM Mask
LOCAL_INCLUDES += ["/camoucfg"]
```

This links the C++ code with Camoufox's configuration system located in `/camoucfg`.

## Patch Development Workflow

### Using the Makefile

The Camoufox Makefile provides several targets for patch development:

**Setup & Preparation:**
```bash
make fetch           # Download Firefox source tarball
make setup           # Extract source + initialize git repo
make dir             # Apply all patches (prepare for build)
```

**Patch Management:**
```bash
make patch <file>    # Apply a single patch
make unpatch <file>  # Remove a single patch
make workspace <file> # Set workspace to a patch (assumes applied)
make revert          # Reset to unpatched state (git reset --hard unpatched)
```

**Development:**
```bash
make edits           # Interactive developer UI
make diff            # Show changes from first checkpoint
make checkpoint      # Create a git checkpoint
```

**Building & Testing:**
```bash
make build           # Build Camoufox
make run             # Run Camoufox with debug config
make clean           # Clean build artifacts + revert changes
```

### Patch Application Process

From `scripts/patch.py`:

1. **Reset to clean state:**
   ```bash
   git reset --hard unpatched
   git clean -fdx
   ./mach clobber
   ```

2. **Re-copy additions:**
   - Settings from `settings/`
   - Configuration from `camoucfg/`

3. **Create base mozconfig:**
   - Cross-compilation target setup
   - Build optimization flags

4. **Apply patches in order:**
   - Non-roverfox patches first
   - Roverfox patches last (dependent on others)
   - Track failures and report `.rej` files

5. **Mark as ready:**
   - Touch `_READY` file to indicate build-ready state

### Git Workflow

Camoufox uses git tags to track patch states:

- `unpatched` - Clean Firefox source (initial state)
- `first-checkpoint` - After first patch application
- `checkpoint` - Development milestones

## Key Insights for Tegufox

### 1. Configuration System is Central

All patches rely on `MaskConfig.hpp` which reads from:
- JSON config passed via Python API
- Cross-process shared storage
- Per-context (browser tab) settings

### 2. Patch Dependencies

Some patches depend on others:
- `chromeutil.patch` must be applied first (provides MaskConfig system)
- `browser-init.patch` initializes the config system
- Other patches then use MaskConfig for spoofing

### 3. Testing Approach

- Patches can be applied/unapplied individually
- Git checkpoints allow A/B testing
- Can build "vanilla Firefox + minimal patches" with `make ff-dbg`

### 4. Build System Complexity

- Full Firefox build: 6-7 months to understand from scratch
- Camoufox patch system: Much simpler, modifies existing Firefox
- Makefile abstracts away most complexity

## Opportunities for Tegufox

### 1. Patch Development Toolkit

Create tools to:
- Generate patch templates automatically
- Test patches in isolation before full build
- Validate patch compatibility with new Firefox versions
- Automated patch conflict resolution

### 2. Custom Patch Repository

- Version-controlled custom patches
- Patch categories (e-commerce specific, generic anti-detect, etc.)
- Dependency tracking between patches
- Community-contributed patches

### 3. Build Automation

- CI/CD for patch testing
- Automated Firefox version updates
- Regression testing for each patch
- Performance benchmarking

### 4. Configuration Management

- Enhanced MaskConfig with more data types
- Per-domain configuration profiles
- Machine learning-based fingerprint generation
- Real-time fingerprint adjustment

### 5. E-Commerce Specific Patches

New patches targeting:
- eBay bot detection (Canvas, WebGL, Audio)
- Amazon device fingerprinting (Fonts, Screen, Navigator)
- Etsy behavioral analysis (Mouse, Keyboard timing)
- Payment gateway fingerprinting

## Next Steps

1. **Study key patches in detail:**
   - `fingerprint-injection.patch` - Core injection mechanism
   - `webgl-spoofing.patch` - Most complex spoofing logic
   - `chromeutil.patch` + `browser-init.patch` - Configuration system

2. **Understand MaskConfig.hpp:**
   - Located in `/camoucfg/` directory
   - C++ header with JSON parsing
   - Cross-process communication

3. **Create Tegufox toolkit components:**
   - Patch generator CLI
   - Patch testing framework
   - Build automation scripts
   - Configuration profiles for e-commerce sites

4. **Develop first custom patch:**
   - Target specific e-commerce detection method
   - Test in isolation
   - Integrate with Camoufox build system
   - Document learnings
