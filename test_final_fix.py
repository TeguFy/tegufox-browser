"""Test final fix - enlarge screen to accommodate viewport padding"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

# Target dimensions from profile
target_width = 1920
target_height = 1080

# Enlarge screen to account for Camoufox's 16px viewport padding
actual_width = target_width + 16
actual_height = target_height

screen_constraint = Screen(
    min_width=actual_width,
    max_width=actual_width,
    min_height=actual_height,
    max_height=actual_height
)

viewport_size = {
    'width': target_width,  # Use target width (Camoufox will add 16px)
    'height': target_height - 70
}

print("🦊 Final Fix Test\n")
print(f"Target screen: {target_width}x{target_height}")
print(f"Actual screen constraint: {actual_width}x{actual_height}")
print(f"Viewport size: {viewport_size['width']}x{viewport_size['height']}")
print()

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=True,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(viewport=viewport_size)
    page = context.new_page()
    page.goto('data:text/html,<h1>Test</h1>')
    
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
    elif ratio >= 95:
        print(f"   ✅ Very good: viewport fills {ratio}% of screen")
    elif ratio >= 90:
        print(f"   ✅ Good: viewport fills {ratio}% of screen")
    else:
        print(f"   ⚠️  Viewport fills {ratio}% of screen")
    
    print()
    
    if success and ratio >= 95:
        print("✅ ✅ ✅ PERFECT! Viewport configuration is correct!")
        print("🎉 Content width will match browser window properly!")
        print(f"\n📝 Note: Screen is {dims['screen_width']}px (enlarged from {target_width}px target)")
        print("     This accounts for Camoufox's viewport padding behavior")
    elif success:
        print("✅ Viewport is consistent (dimensions are valid)")
    else:
        print("❌ Still has issues")

print("\n✅ Test completed!")
