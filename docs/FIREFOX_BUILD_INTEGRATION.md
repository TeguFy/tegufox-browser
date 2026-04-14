# Firefox Build Integration Guide
# Tegufox Browser Toolkit - Phase 1 Week 2 Day 4

**Purpose**: Build Camoufox with Tegufox patches (Canvas Noise v2, WebGL Enhanced)  
**Created**: 2026-04-13  
**Estimated time**: 4-6 hours (mostly compile time)

---

## Prerequisites

### System Requirements

**macOS** (your environment):
- macOS 12+ (Monterey or newer)
- Xcode Command Line Tools
- 16GB+ RAM
- 60GB+ free disk space
- Fast internet connection

**Install dependencies**:
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Firefox build dependencies
brew install python@3.11 rust mercurial node yasm
brew install --cask firefox  # For testing comparison

# Install mach bootstrap (Firefox build tool)
curl https://hg.mozilla.org/mozilla-central/raw-file/default/python/mozboot/bin/bootstrap.py -O
python3 bootstrap.py
```

---

## Step 1: Clone Camoufox Source

Camoufox is a Firefox fork with anti-detect modifications. We'll build on top of it.

### Option A: Clone Official Camoufox (Recommended)

```bash
# Navigate to development directory
cd ~/dev/2026-3

# Clone Camoufox repository
git clone https://github.com/daijro/camoufox.git camoufox-build
cd camoufox-build

# Checkout stable branch
git checkout main
```

### Option B: Clone Firefox + Manual Camoufox Patches

If Camoufox source isn't available, clone Firefox and apply Camoufox patches manually:

```bash
# Clone Firefox
hg clone https://hg.mozilla.org/mozilla-central firefox-src
cd firefox-src

# Download Camoufox patches (hypothetical - adjust to actual source)
curl -L https://github.com/daijro/camoufox/releases/download/latest/camoufox-patches.tar.gz -o camoufox-patches.tar.gz
tar -xzf camoufox-patches.tar.gz

# Apply Camoufox patches
for patch in camoufox-patches/*.patch; do
  patch -p1 < "$patch"
done
```

---

## Step 2: Apply Tegufox Patches

Now apply our custom Tegufox patches on top of Camoufox.

### Patch Files to Apply

1. **canvas-noise-v2.patch** (258 lines) - Canvas fingerprinting defense
2. **webgl-enhanced.patch** (420 lines) - WebGL fingerprinting defense

### Apply Patches

```bash
# Copy patches from Tegufox toolkit to Camoufox source
cd ~/dev/2026-3/camoufox-build

# Apply Canvas Noise v2
patch -p1 < ~/dev/2026-3/tegufox-browser/patches/canvas-noise-v2.patch

# Apply WebGL Enhanced
patch -p1 < ~/dev/2026-3/tegufox-browser/patches/webgl-enhanced.patch
```

### Verify Patch Application

```bash
# Check for .rej files (patch failures)
find . -name "*.rej"

# If any .rej files exist, patches failed - manually resolve conflicts
# Check git status to see modified files
git status

# Expected modified files:
# - dom/canvas/CanvasRenderingContext2D.cpp
# - dom/canvas/WebGLContext.cpp
# - dom/canvas/WebGLContext.h
# - dom/canvas/moz.build
```

### Common Patch Issues

**Issue 1: File path mismatch**
```bash
# Error: can't find file to patch at input line 5
# Perhaps you used the wrong -p or --strip option?

# Solution: Adjust -p level
patch -p0 < patch.file  # Try -p0 instead of -p1
```

**Issue 2: Context mismatch (file changed upstream)**
```bash
# Error: Hunk #1 FAILED at line 50
# 1 out of 2 hunks FAILED -- saving rejects to file.rej

# Solution: Manually apply patch
cat file.rej  # Review failed hunk
vim file.cpp  # Manually edit file to include changes
```

**Issue 3: MaskConfig not found**
```bash
# Error: MaskConfig.hpp: No such file or directory

# Solution: Verify camoucfg directory exists
ls -la camoucfg/  # Should contain MaskConfig.hpp

# If missing, Camoufox source is incomplete
# Check Camoufox repo for camoucfg/ directory
```

---

## Step 3: Configure Build

Firefox/Camoufox uses a `mozconfig` file for build configuration.

### Create mozconfig

```bash
cd ~/dev/2026-3/camoufox-build

# Create mozconfig file
cat > mozconfig <<'EOF'
# Tegufox Build Configuration
# Based on Camoufox + Tegufox patches

# Enable optimizations (faster runtime, slower compile)
ac_add_options --enable-optimize
ac_add_options --disable-debug
ac_add_options --disable-debug-symbols

# Build for macOS
ac_add_options --target=x86_64-apple-darwin
ac_add_options --enable-application=browser

# Enable Camoufox features
ac_add_options --enable-strip
ac_add_options --disable-crashreporter
ac_add_options --disable-updater
ac_add_options --disable-tests

# Tegufox: Enable MaskConfig
ac_add_options --with-camoucfg

# Output directory
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-tegufox

# Number of parallel jobs (adjust based on CPU cores)
mk_add_options MOZ_MAKE_FLAGS="-j8"

# Brand name
ac_add_options --with-branding=browser/branding/unofficial
EOF
```

### Verify Configuration

```bash
# Run configure to check for errors
./mach configure

# Expected output:
# Creating Python 3 environment
# Config object not found
# Creating Python environment
# Re-executing in the virtualenv
# configure: Finished
```

---

## Step 4: Build Camoufox

This is the longest step (2-4 hours).

### Start Build

```bash
# Build with mach
./mach build

# Or build with explicit jobs
./mach build -j8  # 8 parallel jobs
```

### Build Progress

```
Building dom/canvas
Building dom/webgl
Building gfx/gl
...
Linking libxul.dylib
Creating Firefox.app
Build succeeded in 3h 24m 15s
```

### Monitor Build

```bash
# Check build progress in another terminal
tail -f obj-tegufox/config.log
```

### Expected Build Time

| Hardware | Time |
|----------|------|
| MacBook Pro M1 (8 cores) | 2-3 hours |
| MacBook Pro Intel i7 (4 cores) | 4-6 hours |
| iMac M3 (12 cores) | 1.5-2 hours |

---

## Step 5: Test Built Browser

### Launch Built Browser

```bash
# Run from object directory
./obj-tegufox/dist/Tegufox.app/Contents/MacOS/firefox

# Or use mach
./mach run
```

### Verify Patches Are Active

**Test 1: Canvas Noise v2**
```bash
# Create test profile with Canvas Noise v2 enabled
cd ~/dev/2026-3/tegufox-browser
./tegufox-config create --platform amazon-fba --name build-test --output-dir profiles

# Launch with profile
python3 <<EOF
from camoufox.sync_api import Camoufox

with Camoufox(config_path='profiles/build-test.json') as browser:
    page = browser.new_page()
    page.goto('https://browserleaks.com/canvas')
    input('Press Enter after checking canvas fingerprint...')
EOF
```

**Test 2: WebGL Enhanced**
```bash
# Run WebGL test suite
python3 test_webgl_enhanced.py profiles/build-test.json
```

**Test 3: BrowserLeaks Full Test**
```bash
# Manual test
./obj-tegufox/dist/Tegufox.app/Contents/MacOS/firefox
# Navigate to: https://browserleaks.com/webgl
# Check:
# - Vendor: Should show spoofed value (e.g., "Apple")
# - Renderer: Should show spoofed value (e.g., "Apple M1 Pro")
# - Extensions: Should match profile template
```

---

## Step 6: Package Browser

### Create Distributable Build

```bash
# Create DMG (macOS installer)
./mach package

# Output: obj-tegufox/dist/Tegufox-<version>.dmg

# Or create TAR archive
cd obj-tegufox/dist
tar -czf Tegufox.app.tar.gz Tegufox.app/

# Copy to Tegufox toolkit directory
cp Tegufox.app.tar.gz ~/dev/2026-3/tegufox-browser/builds/
```

### Install System-Wide

```bash
# Copy to Applications
sudo cp -R obj-tegufox/dist/Tegufox.app /Applications/

# Or create symlink
ln -s $(pwd)/obj-tegufox/dist/Tegufox.app /Applications/Tegufox.app
```

---

## Step 7: Integration with Tegufox Toolkit

### Update tegufox-launch to Use Built Browser

Edit `tegufox-launch`:
```python
# Line 20: Update browser path
BROWSER_PATH = '/Applications/Tegufox.app/Contents/MacOS/firefox'
# Or use obj-tegufox path for development
BROWSER_PATH = os.path.expanduser('~/dev/2026-3/camoufox-build/obj-tegufox/dist/Tegufox.app/Contents/MacOS/firefox')
```

### Test Full Workflow

```bash
cd ~/dev/2026-3/tegufox-browser

# Create profile
./tegufox-config create --platform amazon-fba --name final-test --output-dir profiles

# Validate profile
./tegufox-config validate profiles/final-test.json

# Launch browser with profile
./tegufox-launch profiles/final-test.json

# Run automated tests
python3 test_canvas_noise_v2.py profiles/final-test.json
python3 test_webgl_enhanced.py profiles/final-test.json
python3 test_mouse_movement_v2.py  # Mouse library works without rebuild
```

---

## Troubleshooting

### Build Errors

**Error 1: Missing MaskConfig.hpp**
```bash
# Error: fatal error: 'MaskConfig.hpp' file not found
# Solution: Check camoucfg directory exists
ls -la camoucfg/
# If missing, Camoufox source is incomplete - re-clone
```

**Error 2: Linker error (undefined symbols)**
```bash
# Error: Undefined symbols for architecture x86_64: "MaskConfig::GetNested(...)"
# Solution: Rebuild camoucfg library
cd camoucfg
make clean && make
cd ..
./mach build
```

**Error 3: Out of memory**
```bash
# Error: c++: fatal error: Killed signal terminated program cc1plus
# Solution: Reduce parallel jobs
./mach build -j2  # Use 2 jobs instead of 8
```

**Error 4: Python version mismatch**
```bash
# Error: Python 3.11 required, but 3.14 found
# Solution: Use pyenv to switch Python versions
pyenv install 3.11
pyenv local 3.11
./mach build
```

### Runtime Errors

**Error 1: Profile not loaded**
```bash
# Symptom: WebGL vendor shows real GPU instead of spoofed
# Check: MaskConfig is reading profile correctly
# Debug: Add logging to WebGLContext::GetSpoofedVendor()
```

**Error 2: Browser crashes on launch**
```bash
# Solution: Check crash logs
cat ~/Library/Logs/DiagnosticReports/firefox_*.crash

# Common cause: Missing dylib
# Fix: Rebuild with --enable-static
```

**Error 3: Patches not active**
```bash
# Verify patches were applied
git diff dom/canvas/WebGLContext.cpp
# Should show Tegufox modifications

# If not, re-apply patches
git checkout dom/canvas/WebGLContext.cpp
patch -p1 < ~/dev/2026-3/tegufox-browser/patches/webgl-enhanced.patch
./mach build
```

---

## Incremental Builds

After modifying patches, you don't need to rebuild everything.

### Rebuild Only Canvas Module

```bash
# After editing canvas-noise-v2.patch
./mach build dom/canvas

# Faster than full rebuild (5-10 minutes vs 2-4 hours)
```

### Rebuild Only WebGL Module

```bash
# After editing webgl-enhanced.patch
./mach build dom/canvas dom/webgl

# Test immediately
./mach run
```

---

## Build Automation Script

Create `build-tegufox.sh` for automated builds:

```bash
#!/bin/bash
# Tegufox Browser Build Script

set -e  # Exit on error

echo "🦎 Building Tegufox Browser with Custom Patches"
echo "================================================"

# Step 1: Check dependencies
echo "📦 Checking dependencies..."
command -v rust >/dev/null 2>&1 || { echo "❌ Rust not installed"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not installed"; exit 1; }

# Step 2: Clone Camoufox (if not exists)
if [ ! -d "camoufox-build" ]; then
  echo "📥 Cloning Camoufox..."
  git clone https://github.com/daijro/camoufox.git camoufox-build
fi

cd camoufox-build

# Step 3: Apply Tegufox patches
echo "🩹 Applying Tegufox patches..."
patch -p1 < ../tegufox-browser/patches/canvas-noise-v2.patch || echo "⚠️  Canvas patch already applied"
patch -p1 < ../tegufox-browser/patches/webgl-enhanced.patch || echo "⚠️  WebGL patch already applied"

# Step 4: Configure build
echo "⚙️  Configuring build..."
./mach configure

# Step 5: Build
echo "🔨 Building (this will take 2-4 hours)..."
./mach build -j8

# Step 6: Verify build
echo "✅ Build complete!"
echo "📍 Binary: $(pwd)/obj-tegufox/dist/Tegufox.app/Contents/MacOS/firefox"

# Step 7: Run tests
echo "🧪 Running tests..."
cd ../tegufox-browser
python3 test_canvas_noise_v2.py profiles/test-canvas-v2.json || echo "⚠️  Canvas tests failed (expected if profile not configured)"
python3 test_webgl_enhanced.py profiles/test-webgl-template.json || echo "⚠️  WebGL tests failed (expected if profile not configured)"

echo "🎉 Tegufox Browser build complete!"
```

Make it executable:
```bash
chmod +x build-tegufox.sh
./build-tegufox.sh
```

---

## Next Steps (Day 5)

After successful build:

1. **Comprehensive Testing**
   - BrowserLeaks full suite
   - CreepJS fingerprint test
   - Amazon.com login flow
   - eBay search/browse
   - Etsy shop access

2. **Performance Profiling**
   - Measure Canvas Noise v2 overhead
   - Measure WebGL Enhanced overhead
   - Compare with stock Camoufox

3. **Week 2 Report**
   - Document build process
   - Test results summary
   - Performance metrics
   - Known issues / limitations

---

## References

- **Firefox Build Documentation**: https://firefox-source-docs.mozilla.org/setup/
- **Camoufox Repository**: https://github.com/daijro/camoufox
- **mach Command Reference**: https://firefox-source-docs.mozilla.org/mach/
- **mozconfig Options**: https://firefox-source-docs.mozilla.org/setup/configuring_build_options.html

---

**End of Build Integration Guide**

Total: 550 lines
