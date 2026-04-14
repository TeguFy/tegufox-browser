"""Test viewport with Camoufox's recommended approach"""

from camoufox.sync_api import Camoufox
import json

print("🔍 Testing Viewport with Camoufox Defaults\n")

# Test 1: Use Camoufox's automatic screen generation
print("📋 Test 1: Using Camoufox defaults (no manual override)\n")

with Camoufox(
    os='windows',  # Just specify OS
    headless=False,
    i_know_what_im_doing=True  # Suppress warnings for testing
) as browser:
    page = browser.new_page()
    page.goto('data:text/html,<html><body><h1>Viewport Test</h1></body></html>')
    
    dimensions = page.evaluate('''() => {
        return {
            window_innerWidth: window.innerWidth,
            window_innerHeight: window.innerHeight,
            screen_width: screen.width,
            screen_height: screen.height,
            devicePixelRatio: window.devicePixelRatio
        }
    }''')
    
    print("📊 Camoufox Auto-Generated Dimensions:")
    print(f"   screen.width: {dimensions['screen_width']}px")
    print(f"   screen.height: {dimensions['screen_height']}px")
    print(f"   window.innerWidth: {dimensions['window_innerWidth']}px")
    print(f"   window.innerHeight: {dimensions['window_innerHeight']}px")
    print(f"   devicePixelRatio: {dimensions['devicePixelRatio']}")
    print()
    
    viewport_ratio = dimensions['window_innerWidth'] / dimensions['screen_width']
    print(f"📐 Viewport to Screen Ratio: {viewport_ratio:.2%}")
    
    if dimensions['window_innerWidth'] > dimensions['screen_width']:
        print("❌ PROBLEM: window.innerWidth > screen.width")
    elif viewport_ratio > 0.95:
        print("✅ Good: Viewport fills most of screen")
    else:
        print(f"⚠️  Viewport only {viewport_ratio:.0%} of screen width")
    
    print("\n💡 Press Enter to close browser...")
    input()
