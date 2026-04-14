"""Test viewport with proper configuration"""

from camoufox.sync_api import Camoufox

print("🔍 Testing Viewport Fixes\n")

# Test: Use screen constraints + viewport size
print("📋 Using screen constraints + viewport\n")

with Camoufox(
    os='windows',
    screen={
        'min_width': 1900,
        'max_width': 1920,
        'min_height': 1060,
        'max_height': 1080
    },
    headless=False,
    i_know_what_im_doing=True
) as browser:
    # Set viewport size explicitly
    context = browser.contexts[0]
    page = browser.new_page()
    
    # Set viewport to match screen (minus browser chrome)
    page.set_viewport_size({'width': 1920, 'height': 1010})
    
    page.goto('data:text/html,<html><body><h1>Viewport Test</h1><p>Testing screen/viewport consistency</p></body></html>')
    
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
    
    print("📊 Final Dimensions:")
    print(f"   screen.width: {dimensions['screen_width']}px")
    print(f"   screen.height: {dimensions['screen_height']}px")
    print(f"   screen.availWidth: {dimensions['screen_availWidth']}px")
    print(f"   screen.availHeight: {dimensions['screen_availHeight']}px")
    print()
    print(f"   window.innerWidth: {dimensions['window_innerWidth']}px")
    print(f"   window.innerHeight: {dimensions['window_innerHeight']}px")
    print(f"   window.outerWidth: {dimensions['window_outerWidth']}px")
    print(f"   window.outerHeight: {dimensions['window_outerHeight']}px")
    print()
    
    viewport_ratio = dimensions['window_innerWidth'] / dimensions['screen_width']
    print(f"📐 Viewport to Screen Ratio: {viewport_ratio:.2%}")
    
    # Check consistency
    print("\n🔍 Consistency Checks:")
    
    if dimensions['window_innerWidth'] > dimensions['screen_width']:
        print("❌ CRITICAL: window.innerWidth > screen.width (IMPOSSIBLE)")
    else:
        print("✅ window.innerWidth <= screen.width (correct)")
    
    if dimensions['window_outerWidth'] > dimensions['screen_width']:
        print("❌ CRITICAL: window.outerWidth > screen.width (IMPOSSIBLE)")
    else:
        print("✅ window.outerWidth <= screen.width (correct)")
    
    if viewport_ratio >= 0.95:
        print("✅ Viewport fills most of screen (good)")
    elif viewport_ratio >= 0.85:
        print("⚠️  Viewport is reasonable but could be larger")
    else:
        print(f"❌ Viewport only {viewport_ratio:.0%} of screen (suspicious)")
    
    print("\n💡 Testing on real site...")
    page.goto('https://browserleaks.com/screen')
    
    print("✅ Browser launched successfully!")
    print("👀 Check the screen dimensions on browserleaks.com")
    print("\n💡 Press Ctrl+C to close browser...")
    
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Closing browser...")
