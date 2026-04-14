"""Test viewport - proper solution"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

print("🔍 Testing Viewport - Proper Solution\n")

# Create Screen constraint object
screen_constraint = Screen(
    min_width=1900,
    max_width=1920,
    min_height=1060,
    max_height=1080
)

print("📋 Configuration:")
print(f"   OS: Windows")
print(f"   Screen constraint: 1900-1920 x 1060-1080")
print()

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    page = browser.new_page()
    
    # Set viewport size
    page.set_viewport_size({'width': 1920, 'height': 1010})
    
    page.goto('data:text/html,<html><body style="margin:0"><h1>Viewport Test</h1><p>Screen/viewport consistency test</p></body></html>')
    
    dimensions = page.evaluate('''() => {
        return {
            window_innerWidth: window.innerWidth,
            window_innerHeight: window.innerHeight,
            window_outerWidth: window.outerWidth,
            window_outerHeight: window.outerHeight,
            screen_width: screen.width,
            screen_height: screen.height,
            screen_availWidth: screen.availWidth,
            screen_availHeight: screen.availHeight,
            devicePixelRatio: window.devicePixelRatio
        }
    }''')
    
    print("📊 Measured Dimensions:")
    print("\nScreen:")
    print(f"   width: {dimensions['screen_width']}px")
    print(f"   height: {dimensions['screen_height']}px")
    print(f"   availWidth: {dimensions['screen_availWidth']}px")
    print(f"   availHeight: {dimensions['screen_availHeight']}px")
    print("\nWindow:")
    print(f"   innerWidth: {dimensions['window_innerWidth']}px")
    print(f"   innerHeight: {dimensions['window_innerHeight']}px")
    print(f"   outerWidth: {dimensions['window_outerWidth']}px")
    print(f"   outerHeight: {dimensions['window_outerHeight']}px")
    print()
    
    viewport_ratio = dimensions['window_innerWidth'] / dimensions['screen_width']
    print(f"📐 Viewport/Screen Ratio: {viewport_ratio:.2%}")
    print()
    
    # Consistency checks
    print("🔍 Consistency Checks:")
    issues = []
    
    if dimensions['window_innerWidth'] > dimensions['screen_width']:
        issues.append("❌ CRITICAL: window.innerWidth > screen.width (IMPOSSIBLE)")
    else:
        print("✅ window.innerWidth <= screen.width")
    
    if dimensions['window_outerWidth'] > dimensions['screen_width']:
        issues.append("❌ CRITICAL: window.outerWidth > screen.width (IMPOSSIBLE)")
    else:
        print("✅ window.outerWidth <= screen.width")
    
    if viewport_ratio >= 0.95:
        print("✅ Viewport fills ~100% of screen")
    elif viewport_ratio >= 0.85:
        print(f"⚠️  Viewport is {viewport_ratio:.0%} of screen (reasonable)")
    else:
        issues.append(f"❌ Viewport only {viewport_ratio:.0%} of screen (suspicious)")
    
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ All checks passed!")
    
    print("\n💡 Testing on browserleaks.com...")
    page.goto('https://browserleaks.com/screen')
    
    print("✅ Browser opened with browserleaks.com")
    print("👀 Please check if screen dimensions look correct")
    print("\n💡 Press Ctrl+C to close...")
    
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Closing...")
