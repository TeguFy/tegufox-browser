# Tegufox Viewport Fix Guide

**Issue**: Browser window content width quá lớn, không khớp với GUI của browser

**Root Cause**: Screen dimensions và viewport size không được configure đúng cách

---

## Problem Analysis

### Vấn đề phát hiện

Khi mở Camoufox browser:
- **Screen dimensions** (screen.width, screen.height) có thể không match với actual browser window
- **Viewport dimensions** (window.innerWidth, window.innerHeight) có thể lớn hơn screen dimensions
- **Page content** render với width lớn hơn visible area → phải scroll ngang

### Nguyên nhân

1. **Camoufox auto-generates screen dimensions** dựa trên OS
2. **Viewport size** mặc định có thể nhỏ hơn hoặc lớn hơn screen
3. **Manual override** screen dimensions trong config bị Camoufox reject (warnings)

---

## Solution: Use Camoufox's Recommended Approach

### ❌ Wrong Approach (Gây ra warnings và inconsistency)

```python
# DON'T DO THIS
config = {
    'screen.width': 1920,
    'screen.height': 1080,
    # ... other config
}

with Camoufox(config=config) as browser:
    # Camoufox will warn and may ignore these values
    pass
```

**Problems**:
- Camoufox issues `LeakWarning` about manual screen override
- Screen dimensions may not be applied correctly
- Viewport không match với screen

---

### ✅ Correct Approach (Recommended)

#### Method 1: Use Screen Constraints (Best for consistency)

```python
from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

# Define screen constraint
screen_constraint = Screen(
    min_width=1900,
    max_width=1920,
    min_height=1060,
    max_height=1080
)

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=False
) as browser:
    page = browser.new_page()
    
    # Set viewport to match screen (minus browser chrome ~70px)
    page.set_viewport_size({'width': 1920, 'height': 1010})
    
    page.goto('https://example.com')
```

**Benefits**:
- ✅ Screen dimensions within specified range
- ✅ Viewport matches screen dimensions
- ✅ No warnings from Camoufox
- ✅ Consistent across page loads

---

#### Method 2: Let Camoufox Auto-Generate (Best for stealth)

```python
from camoufox.sync_api import Camoufox

with Camoufox(
    os='windows',  # Just specify OS
    headless=False
) as browser:
    page = browser.new_page()
    
    # Get auto-generated screen dimensions
    screen_dims = page.evaluate('''() => {
        return {width: screen.width, height: screen.height}
    }''')
    
    # Set viewport to match (minus browser chrome)
    page.set_viewport_size({
        'width': screen_dims['width'],
        'height': screen_dims['height'] - 70
    })
    
    page.goto('https://example.com')
```

**Benefits**:
- ✅ Fully random dimensions (better fingerprinting resistance)
- ✅ Camoufox handles all consistency checks
- ✅ No manual configuration needed

---

## Implementation for Tegufox Profiles

### Updated Profile Usage

Since Camoufox doesn't want us to override screen dimensions manually, we should:

1. **Remove screen.* from profile config** (or ignore them)
2. **Use Screen constraints** instead
3. **Set viewport size explicitly** after page creation

### Example: Modified Profile Launcher

```python
"""Launch browser with profile - corrected approach"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen
import json

# Load profile
with open('profiles/my-profile.json') as f:
    profile = json.load(f)

config = profile['config']

# Extract screen dimensions from profile
target_width = config.get('screen.width', 1920)
target_height = config.get('screen.height', 1080)

# Create screen constraint (allow small variation)
screen_constraint = Screen(
    min_width=target_width - 20,
    max_width=target_width,
    min_height=target_height - 20,
    max_height=target_height
)

# Extract OS from platform
platform = config.get('navigator.platform', 'Win32')
os_name = 'windows' if 'Win' in platform else 'macos' if 'Mac' in platform else 'linux'

# Remove screen.* keys from config (Camoufox will handle)
clean_config = {k: v for k, v in config.items() if not k.startswith('screen.')}

# Launch browser
with Camoufox(
    os=os_name,
    screen=screen_constraint,
    config=clean_config,  # Use cleaned config
    headless=False
) as browser:
    page = browser.new_page()
    
    # Set viewport to match screen (minus browser chrome)
    viewport_height = target_height - 70  # Account for browser UI
    page.set_viewport_size({'width': target_width, 'height': viewport_height})
    
    # Now screen and viewport are consistent
    page.goto('https://example.com')
```

---

## Testing Viewport Consistency

### Test Script

```python
"""Test viewport consistency"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

screen_constraint = Screen(min_width=1920, max_width=1920,
                          min_height=1080, max_height=1080)

with Camoufox(os='windows', screen=screen_constraint, headless=False) as browser:
    page = browser.new_page()
    page.set_viewport_size({'width': 1920, 'height': 1010})
    
    page.goto('data:text/html,<h1>Test</h1>')
    
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        screen_height: screen.height,
        window_innerWidth: window.innerWidth,
        window_innerHeight: window.innerHeight,
        ratio: window.innerWidth / screen.width
    })''')
    
    print(f"Screen: {dims['screen_width']}x{dims['screen_height']}")
    print(f"Viewport: {dims['window_innerWidth']}x{dims['window_innerHeight']}")
    print(f"Ratio: {dims['ratio']:.2%}")
    
    # Should be ~100%
    assert dims['ratio'] >= 0.95, "Viewport too small!"
    assert dims['window_innerWidth'] <= dims['screen_width'], "Viewport larger than screen!"
    
    print("✅ Viewport consistency check passed!")
```

---

## Common Screen Sizes

### Desktop (1920x1080 - Most Common)

```python
Screen(min_width=1920, max_width=1920, min_height=1080, max_height=1080)
page.set_viewport_size({'width': 1920, 'height': 1010})
```

### MacBook Pro 14" (1470x956)

```python
Screen(min_width=1470, max_width=1470, min_height=956, max_height=956)
page.set_viewport_size({'width': 1470, 'height': 886})
```

### High Resolution (2560x1440)

```python
Screen(min_width=2560, max_width=2560, min_height=1440, max_height=1440)
page.set_viewport_size({'width': 2560, 'height': 1370})
```

### Ultrawide (3440x1440)

```python
Screen(min_width=3440, max_width=3440, min_height=1440, max_height=1440)
page.set_viewport_size({'width': 3440, 'height': 1370})
```

---

## Browser Chrome Heights

Different browsers have different UI heights:

| Browser | Chrome Height | Viewport Height (from 1080px) |
|---------|---------------|-------------------------------|
| Firefox | ~70px | 1010px |
| Chrome | ~85px | 995px |
| Edge | ~85px | 995px |

For Camoufox (Firefox-based), use **~70px** chrome height.

---

## Updated Configuration Manager

We should update `tegufox-config` to:

1. ✅ **Keep screen dimensions in profiles** (for reference)
2. ✅ **Add helper function** to convert profile to Screen constraint
3. ✅ **Add helper function** to calculate viewport size
4. ✅ **Document the correct usage** in profile export

### Proposed Helper Functions

```python
def profile_to_screen_constraint(profile):
    """Convert profile screen dimensions to Screen constraint"""
    from browserforge.fingerprints import Screen
    
    config = profile.get('config', {})
    width = config.get('screen.width', 1920)
    height = config.get('screen.height', 1080)
    
    # Allow small variation for naturalness
    return Screen(
        min_width=width - 20,
        max_width=width,
        min_height=height - 20,
        max_height=height
    )

def profile_to_viewport_size(profile, chrome_height=70):
    """Calculate viewport size from profile screen dimensions"""
    config = profile.get('config', {})
    width = config.get('screen.width', 1920)
    height = config.get('screen.height', 1080)
    
    return {
        'width': width,
        'height': height - chrome_height
    }

def profile_to_os(profile):
    """Extract OS from profile platform"""
    config = profile.get('config', {})
    platform = config.get('navigator.platform', 'Win32')
    
    if 'Win' in platform:
        return 'windows'
    elif 'Mac' in platform:
        return 'macos'
    elif 'Linux' in platform:
        return 'linux'
    else:
        return 'windows'  # default
```

---

## Testing Checklist

When testing viewport consistency:

- [ ] Launch browser with profile
- [ ] Check `screen.width` matches configured value (±20px)
- [ ] Check `window.innerWidth` ≈ `screen.width` (allow -20px for scrollbar)
- [ ] Check `window.innerWidth` ≤ `screen.width` (CRITICAL)
- [ ] Check `window.outerWidth` ≤ `screen.width` (CRITICAL)
- [ ] Visit browserleaks.com/screen to verify visually
- [ ] Check page content doesn't require horizontal scrolling
- [ ] Test on actual e-commerce sites (eBay, Amazon, Etsy)

---

## Browser Console Test

Run this in browser console to check dimensions:

```javascript
console.log({
  screen: {width: screen.width, height: screen.height},
  window_inner: {width: window.innerWidth, height: window.innerHeight},
  window_outer: {width: window.outerWidth, height: window.outerHeight},
  ratio: (window.innerWidth / screen.width * 100).toFixed(1) + '%',
  consistent: window.innerWidth <= screen.width ? '✅' : '❌'
});
```

---

## Summary

**Problem**: Content width không khớp với browser window

**Root Cause**: Screen dimensions và viewport size không consistent

**Solution**:
1. Use `Screen` constraint object thay vì manual override
2. Set viewport size explicitly sau khi create page
3. Viewport width = screen width
4. Viewport height = screen height - chrome height (~70px)

**Implementation**:
- Update profile launcher để use Screen constraints
- Add helper functions to tegufox-config
- Document correct usage pattern
- Test viewport consistency on all platforms

---

**Document Version**: v1.0  
**Date**: 2026-04-13  
**Author**: Tegufox Development Team
