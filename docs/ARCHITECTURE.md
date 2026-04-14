# Tegufox Toolkit - Architecture Design

## Overview

Tegufox is a **development toolkit** built on top of Camoufox to enable:
1. Custom patch development for advanced anti-detect capabilities
2. High-level automation framework for e-commerce platforms
3. Pluggable spoofing modules with easy configuration
4. Streamlined testing and deployment workflow

**Core Principle**: Build ON TOP of Camoufox, not replace it. Leverage Camoufox's 38 existing patches and add our own.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Tegufox Toolkit                           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Layer 3: Developer Tools                    │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐   │ │
│  │  │ Patch Dev   │ │   Config     │ │    Testing      │   │ │
│  │  │    CLI      │ │   Manager    │ │   Framework     │   │ │
│  │  └─────────────┘ └──────────────┘ └─────────────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         Layer 2: Automation Framework (Python)           │ │
│  │  ┌────────────────┐  ┌───────────────────────────────┐  │ │
│  │  │   Behavioral   │  │   Profile Management          │  │ │
│  │  │    Modules     │  │   - eBay/Amazon/Etsy          │  │ │
│  │  │  - Mouse       │  │   - Fingerprint validation    │  │ │
│  │  │  - Keyboard    │  │   - Session persistence       │  │ │
│  │  │  - Scroll      │  │   - Config templates          │  │ │
│  │  └────────────────┘  └───────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           Layer 1: Custom Patches (15-20)                │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Canvas   │ │  WebGL   │ │  Mouse   │ │  Fonts   │   │ │
│  │  │   v2     │ │  Enhanced│ │  Neuro   │ │ Metrics  │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │   TLS    │ │ Payment  │ │  Timing  │ │  WebRTC  │   │ │
│  │  │  JA3/4   │ │ Gateway  │ │ Behavior │ │  STUN    │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                   Camoufox (Base Browser)                      │
│  - 38 Core Patches        - MaskConfig System                  │
│  - Python API             - Playwright Integration             │
│  - Fingerprint Generation - Profile Management                 │
└────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                     Firefox 135+                               │
│                   (Gecko Engine)                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Layer 1: Custom Patches (C++)

**Purpose**: Extend Camoufox's anti-detect capabilities with e-commerce specific patches

#### Patch Categories:

**1. Enhanced Fingerprinting (6-8 patches)**
- `canvas-v2.patch` - Improved canvas noise injection
- `webgl-enhanced.patch` - Better GPU parameter consistency
- `font-metrics-v2.patch` - Advanced font measurement protection
- `screen-dimensions-v2.patch` - Multi-monitor simulation
- `audio-timing.patch` - Audio context timing variations
- `battery-api.patch` - Battery API masking

**2. Behavioral Patches (4-5 patches)**
- `mouse-neuromotor.patch` - Fitts' Law based mouse movement at C++ level
- `keyboard-timing.patch` - Natural keystroke timing variations
- `form-interaction.patch` - Form filling behavior patterns
- `scroll-momentum.patch` - Natural scroll physics

**3. Network/Protocol Patches (3-4 patches)**
- `tls-ja3-tuning.patch` - JA3/JA4 fingerprint customization
- `webrtc-stun-block.patch` - STUN server blocking
- `http2-priority.patch` - HTTP/2 priority frame customization
- `payment-gateway.patch` - Payment processor API consistency

**4. Platform-Specific Patches (2-3 patches)**
- `ebay-specific.patch` - eBay bot detection bypasses
- `amazon-specific.patch` - Amazon device fingerprinting
- `cloudflare-optimization.patch` - Turnstile challenge optimization

#### Patch Structure:

Each patch follows standard Git diff format:
```diff
diff --git a/path/to/file.cpp b/path/to/file.cpp
index xxxxx..yyyyy
--- a/path/to/file.cpp
+++ b/path/to/file.cpp
@@ -10,6 +10,7 @@
+#include "MaskConfig.hpp"
 
 void SomeFunction() {
+  if (auto value = MaskConfig::GetDouble("feature:parameter"))
+    return value.value();
   // existing code
 }
```

#### Integration with MaskConfig:

All patches use `MaskConfig.hpp` for runtime configuration:
```cpp
// String values
if (auto value = MaskConfig::GetString("webgl:vendor"))
    vendorString = value.value();

// Numeric values
if (auto value = MaskConfig::GetDouble("canvas:noise"))
    noiseLevel = value.value();

// Boolean flags
if (auto value = MaskConfig::GetBool("feature:enabled"))
    isEnabled = value.value();
```

---

### Layer 2: Automation Framework (Python)

**Purpose**: Provide high-level API for e-commerce automation

#### 2.1 Behavioral Modules

**Mouse Movement Module** (`tegufox/behavior/mouse.py`):
```python
class NeuromotorMouse:
    """Fitts' Law based mouse movement"""
    
    def move_to(self, x, y, duration=None):
        """
        Move mouse with human-like trajectory
        - Applies Fitts' Law for movement time
        - Adds micro-fluctuations (tremor)
        - Natural acceleration/deceleration
        """
        
    def click_with_jitter(self, x, y, offset=2):
        """Click with small random offset"""
        
    def drag(self, from_x, from_y, to_x, to_y):
        """Drag with realistic movement"""
```

**Keyboard Module** (`tegufox/behavior/keyboard.py`):
```python
class NaturalTyping:
    """Human-like typing behavior"""
    
    def type_text(self, text, wpm=60, error_rate=0.02):
        """
        Type text with natural rhythm
        - Inter-keystroke timing variations
        - Occasional typos with corrections
        - Realistic WPM distribution
        """
        
    def fill_form(self, fields: dict):
        """Fill form fields with natural pauses"""
```

**Scroll Module** (`tegufox/behavior/scroll.py`):
```python
class NaturalScroll:
    """Human-like scrolling patterns"""
    
    def scroll_to(self, y, speed='medium'):
        """
        Scroll with momentum simulation
        - Random pauses
        - Acceleration/deceleration
        - Platform-specific patterns
        """
```

#### 2.2 Profile Management

**Profile Manager** (`tegufox/profiles/manager.py`):
```python
class ProfileManager:
    """Manage browser profiles for e-commerce platforms"""
    
    def create_profile(self, platform: str, config: dict) -> Profile:
        """
        Create platform-specific profile
        - platform: 'ebay', 'amazon', 'etsy'
        - config: fingerprint parameters
        """
        
    def validate_consistency(self, profile: Profile) -> bool:
        """
        Validate fingerprint consistency
        - Check OS ↔ GPU ↔ Fonts correlation
        - Verify screen resolution matches
        - Ensure TLS fingerprint alignment
        """
        
    def export_profile(self, profile: Profile, path: str):
        """Export profile with encryption"""
        
    def import_profile(self, path: str) -> Profile:
        """Import encrypted profile"""
```

**Profile Templates** (`tegufox/profiles/templates/`):
- `ebay_seller.json` - eBay seller profile template
- `amazon_fba.json` - Amazon FBA seller template
- `etsy_shop.json` - Etsy shop owner template
- `buyer_generic.json` - Generic buyer profile

#### 2.3 Session Management

**Session Manager** (`tegufox/session/manager.py`):
```python
class SessionManager:
    """Manage browser sessions and persistence"""
    
    def rotate_cookies(self, strategy='time_based'):
        """Rotate cookies based on strategy"""
        
    def manage_storage(self, profile: Profile):
        """
        Manage LocalStorage/SessionStorage
        - Consistent storage patterns
        - Realistic data sizes
        - Platform-specific keys
        """
        
    def clear_cache(self, selective=True):
        """Selective cache clearing"""
```

#### 2.4 Anti-Detection Utilities

**Detection Tests** (`tegufox/utils/detection.py`):
```python
class DetectionTester:
    """Test for bot detection"""
    
    async def test_fingerprint(self, url='https://creepjs.com'):
        """Run fingerprint detection test"""
        
    async def test_webrtc_leak(self):
        """Check for WebRTC IP leaks"""
        
    async def test_cloudflare(self):
        """Test Cloudflare Turnstile pass rate"""
        
    async def generate_report(self) -> dict:
        """Generate comprehensive test report"""
```

---

### Layer 3: Developer Tools

#### 3.1 Patch Development CLI

**Command-Line Interface** (`tegufox-patch` command):

```bash
# Create new patch from template
tegufox-patch create --name "canvas-v2" --type fingerprint

# Validate patch syntax
tegufox-patch validate patches/canvas-v2.patch

# Test patch in isolation
tegufox-patch test patches/canvas-v2.patch

# Apply patch to Camoufox source
tegufox-patch apply patches/canvas-v2.patch

# Remove patch
tegufox-patch remove patches/canvas-v2.patch

# Check patch compatibility with Firefox version
tegufox-patch check-compat patches/canvas-v2.patch --firefox-version 136
```

**Patch Template Generator**:
```python
# tegufox/tools/patch_generator.py

class PatchGenerator:
    def create_from_template(self, name: str, patch_type: str):
        """
        Generate patch boilerplate
        - Creates .patch file with proper structure
        - Adds MaskConfig integration
        - Includes moz.build modifications
        - Generates test stubs
        """
```

#### 3.2 Configuration Manager

**CLI Tool** (`tegufox-config` command):

```bash
# Create new configuration profile
tegufox-config create --platform ebay --name "seller-1"

# Validate configuration
tegufox-config validate config/ebay-seller-1.json

# Test configuration consistency
tegufox-config test-consistency config/ebay-seller-1.json

# Export configuration
tegufox-config export config/ebay-seller-1.json --encrypted

# Generate configuration from fingerprint
tegufox-config generate --os macos --gpu nvidia
```

**Configuration Schema**:
```json
{
  "platform": "ebay",
  "fingerprint": {
    "os": "Windows 10",
    "gpu": {
      "vendor": "NVIDIA Corporation",
      "renderer": "GeForce RTX 3060"
    },
    "screen": {
      "width": 1920,
      "height": 1080,
      "colorDepth": 24
    },
    "fonts": ["Arial", "Helvetica", ...],
    "canvas": {
      "noise": 0.02,
      "seed": 12345
    },
    "webgl": {
      "vendor": "Google Inc. (NVIDIA)",
      "renderer": "ANGLE (NVIDIA, GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
    }
  },
  "behavior": {
    "mouse": {
      "tremor": 0.5,
      "fitts_law": true
    },
    "typing": {
      "wpm": 65,
      "error_rate": 0.015
    }
  }
}
```

#### 3.3 Testing Framework

**Automated Tests** (`tegufox-test` command):

```bash
# Run fingerprint tests
tegufox-test fingerprint --suite all

# Run e-commerce platform tests
tegufox-test ecommerce --platform ebay

# Run bot detection tests
tegufox-test detection --sites creepjs,browserleaks

# Run full test suite
tegufox-test all --report json

# Benchmark performance
tegufox-test benchmark --iterations 100
```

**Test Suite Structure**:
```
tests/
├── fingerprint/
│   ├── test_canvas.py
│   ├── test_webgl.py
│   ├── test_fonts.py
│   ├── test_webrtc.py
│   └── test_consistency.py
├── ecommerce/
│   ├── test_ebay.py
│   ├── test_amazon.py
│   └── test_etsy.py
├── behavior/
│   ├── test_mouse.py
│   ├── test_keyboard.py
│   └── test_scroll.py
└── integration/
    ├── test_profile_switching.py
    └── test_session_persistence.py
```

---

## Build System Integration

### Build Workflow

```bash
# 1. Clone Camoufox source (one-time)
tegufox-build init

# 2. Apply Tegufox patches
tegufox-build apply-patches

# 3. Build Camoufox with Tegufox patches
tegufox-build compile

# 4. Package for distribution
tegufox-build package --platform linux

# 5. Run tests
tegufox-build test
```

### Automated Build Pipeline

```yaml
# .github/workflows/build.yml

name: Tegufox Build
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Camoufox source
        run: tegufox-build init
        
      - name: Apply patches
        run: tegufox-build apply-patches
        
      - name: Validate patches
        run: tegufox-patch validate-all
        
      - name: Build
        run: tegufox-build compile
        
      - name: Run tests
        run: tegufox-test all
        
      - name: Package
        run: tegufox-build package
```

---

## Directory Structure

```
tegufox-browser/
├── patches/                    # Tegufox custom patches
│   ├── canvas-v2.patch
│   ├── webgl-enhanced.patch
│   ├── mouse-neuromotor.patch
│   └── ...
│
├── tegufox/                    # Python toolkit
│   ├── __init__.py
│   ├── behavior/              # Behavioral modules
│   │   ├── mouse.py
│   │   ├── keyboard.py
│   │   └── scroll.py
│   ├── profiles/              # Profile management
│   │   ├── manager.py
│   │   ├── templates/
│   │   │   ├── ebay_seller.json
│   │   │   ├── amazon_fba.json
│   │   │   └── etsy_shop.json
│   │   └── validator.py
│   ├── session/               # Session management
│   │   └── manager.py
│   ├── tools/                 # Developer tools
│   │   ├── patch_generator.py
│   │   ├── config_manager.py
│   │   └── test_runner.py
│   └── utils/                 # Utilities
│       ├── detection.py
│       └── helpers.py
│
├── tests/                      # Test suite
│   ├── fingerprint/
│   ├── ecommerce/
│   ├── behavior/
│   └── integration/
│
├── scripts/                    # Build/automation scripts
│   ├── apply_patches.sh
│   ├── build_camoufox.sh
│   └── run_tests.sh
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # This file
│   ├── CAMOUFOX_PATCH_SYSTEM.md
│   ├── PATCH_DEVELOPMENT.md    # How to develop patches
│   ├── API_REFERENCE.md        # Python API docs
│   └── EXAMPLES.md             # Usage examples
│
├── examples/                   # Example scripts
│   ├── ebay_automation.py
│   ├── amazon_automation.py
│   └── custom_profile.py
│
├── camoufox-source/           # Camoufox source (gitignored)
├── .gitignore
├── README.md
├── ROADMAP.md
├── setup.py                    # Python package setup
└── pyproject.toml
```

---

## Data Flow

### 1. Patch Development Flow

```
Developer writes patch
         │
         ▼
tegufox-patch create
         │
         ▼
Template generated
         │
         ▼
Developer modifies C++ code
         │
         ▼
tegufox-patch validate
         │
         ▼
tegufox-patch test (isolated)
         │
         ▼
tegufox-build apply-patches
         │
         ▼
Camoufox build with patch
         │
         ▼
tegufox-test fingerprint
         │
         ▼
Patch merged to main
```

### 2. Profile Usage Flow

```
User creates profile
         │
         ▼
tegufox-config create --platform ebay
         │
         ▼
Configuration generated (JSON)
         │
         ▼
ProfileManager.validate_consistency()
         │
         ▼
Load profile into Camoufox
         │
         ▼
MaskConfig reads JSON config
         │
         ▼
C++ patches use MaskConfig values
         │
         ▼
Browser launches with fingerprint
```

### 3. Automation Flow

```
Python script imports tegufox
         │
         ▼
profile = ProfileManager.load('ebay-seller')
         │
         ▼
browser = Camoufox(config=profile.to_dict())
         │
         ▼
Behavioral modules control browser
  - NeuromotorMouse.move_to()
  - NaturalTyping.type_text()
  - NaturalScroll.scroll_to()
         │
         ▼
SessionManager handles persistence
         │
         ▼
Task completed, session saved
```

---

## API Examples

### Example 1: Basic Automation with Tegufox

```python
from tegufox import ProfileManager, Camoufox
from tegufox.behavior import NeuromotorMouse, NaturalTyping

# Load eBay seller profile
profile = ProfileManager.load('ebay-seller-1')

# Launch browser with profile
async with Camoufox(config=profile.to_dict()) as browser:
    page = await browser.new_page()
    
    # Initialize behavioral modules
    mouse = NeuromotorMouse(page)
    keyboard = NaturalTyping(page)
    
    # Navigate to eBay
    await page.goto('https://www.ebay.com')
    
    # Search with human-like behavior
    await mouse.move_to(500, 100)  # Move to search box
    await page.click('#gh-ac')
    await keyboard.type_text('vintage camera', wpm=65)
    
    # Click search with jitter
    await mouse.click_with_jitter(700, 100)
    
    # Wait and close
    await page.wait_for_timeout(5000)
```

### Example 2: Creating Custom Profile

```python
from tegufox import ProfileManager

manager = ProfileManager()

# Create eBay seller profile
profile = manager.create_profile(
    platform='ebay',
    config={
        'os': 'Windows 10',
        'gpu': {
            'vendor': 'NVIDIA Corporation',
            'renderer': 'GeForce RTX 3060'
        },
        'screen': {'width': 1920, 'height': 1080},
        'canvas': {'noise': 0.02},
        'behavior': {
            'mouse': {'tremor': 0.5},
            'typing': {'wpm': 65, 'error_rate': 0.015}
        }
    }
)

# Validate consistency
if manager.validate_consistency(profile):
    # Export encrypted profile
    manager.export_profile(profile, 'my-ebay-profile.enc')
```

### Example 3: Running Tests

```python
from tegufox.utils import DetectionTester

async def test_profile():
    tester = DetectionTester()
    
    # Test fingerprint
    fingerprint_score = await tester.test_fingerprint()
    print(f"CreepJS Score: {fingerprint_score}")
    
    # Check WebRTC leaks
    leak_detected = await tester.test_webrtc_leak()
    print(f"WebRTC Leak: {leak_detected}")
    
    # Test Cloudflare
    cf_pass_rate = await tester.test_cloudflare()
    print(f"Cloudflare Pass Rate: {cf_pass_rate}%")
    
    # Generate report
    report = await tester.generate_report()
    print(report)
```

---

## Deployment Strategy

### For Developers

1. **Install Tegufox toolkit**:
   ```bash
   pip install tegufox
   ```

2. **Clone Camoufox source**:
   ```bash
   tegufox-build init
   ```

3. **Develop custom patches**:
   ```bash
   tegufox-patch create --name my-patch
   ```

4. **Build with patches**:
   ```bash
   tegufox-build compile
   ```

### For End Users

1. **Install pre-built Camoufox** (with Tegufox patches):
   ```bash
   pip install camoufox-tegufox
   ```

2. **Use Tegufox automation library**:
   ```bash
   pip install tegufox
   ```

3. **Run automation scripts**:
   ```python
   from tegufox import ProfileManager, Camoufox
   # ... automation code
   ```

---

## Next Steps

1. **Implement Patch Generator CLI** (Phase 1, Week 1)
2. **Create Behavioral Modules** (Phase 1, Week 2-3)
3. **Build Profile Manager** (Phase 1, Week 4)
4. **Develop First Custom Patch** (Phase 2, Week 1)
5. **Setup CI/CD Pipeline** (Phase 1, Week 3)

---

**Version**: 0.1.0  
**Last Updated**: 2026-04-13  
**Status**: Draft - Phase 0
