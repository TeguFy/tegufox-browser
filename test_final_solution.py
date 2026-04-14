"""Test final viewport solution"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen
import json

# Load profile
with open('profiles/test-ebay-profile.json') as f:
    profile = json.load(f)

config = profile['config']
target_width = 1920
target_height = 1080

# Clean config
clean_config = {k: v for k, v in config.items() 
                if not k.startswith(('screen.', 'navigator.', 'webGl:'))}

# Screen constraint
screen_constraint = Screen(
    min_width=target_width, max_width=target_width,
    min_height=target_height, max_height=target_height
)

# Viewport size (adjusted to prevent overflow)
viewport_size = {
    'width': target_width - 16,  # Compensate for Camoufox behavior
    'height': target_height - 70
}

print("🦊 Final Viewport Solution Test\n")
print(f"Screen constraint: {target_width}x{target_height}")
print(f"Viewport size: {viewport_size['width']}x{viewport_size['height']}")
print()

with Camoufox(
    os='windows',
    screen=screen_constraint,
    config=clean_config,
    headless=True,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(viewport=viewport_size)
    page = context.new_page()
    page.goto('data:text/html,<h1>Viewport Test</h1>')
    
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        screen_height: screen.height,
        window_innerWidth: window.innerWidth,
        window_innerHeight: window.innerHeight,
        ratio: (window.innerWidth / screen.width * 100).toFixed(1),
        diff: window.innerWidth - screen.width
    })''')
    
    print("📊 Measured Dimensions:")
    print(f"   Screen: {dims['screen_width']}x{dims['screen_height']}")
    print(f"   Viewport: {dims['window_innerWidth']}x{dims['window_innerHeight']}")
    print(f"   Ratio: {dims['ratio']}%")
    print(f"   Difference: {dims['diff']}px")
    print()
    
    print("🔍 Validation:")
    
    success = True
    
    if dims['window_innerWidth'] > dims['screen_width']:
        print(f"   ❌ CRITICAL: viewport ({dims['window_innerWidth']}px) > screen ({dims['screen_width']}px)")
        success = False
    else:
        print(f"   ✅ viewport ({dims['window_innerWidth']}px) <= screen ({dims['screen_width']}px)")
    
    ratio = float(dims['ratio'])
    if ratio >= 98 and ratio <= 100:
        print(f"   ✅ Excellent: viewport fills {ratio}% of screen")
    elif ratio >= 90:
        print(f"   ✅ Good: viewport fills {ratio}% of screen")
    elif ratio >= 80:
        print(f"   ⚠️  Acceptable: viewport fills {ratio}% of screen")
    else:
        print(f"   ❌ Poor: viewport only {ratio}% of screen")
        success = False
    
    print()
    
    if success:
        print("✅ ✅ ✅ SUCCESS! Viewport configuration is perfect!")
        print("🎉 The content width will match the browser window correctly!")
    else:
        print("❌ Viewport configuration still has issues")

print("\n✅ Test completed!")
