"""Test actual window size issue - visual rendering"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

print("🔍 Testing Visual Rendering Issue\n")
print("Problem: Content too wide, can't see everything on screen\n")

# Your macOS screen resolution (check System Settings)
print("❓ What is your actual MacBook screen resolution?")
print("   Common: 1470x956 (14-inch), 1728x1117 (16-inch), 2560x1664 (retina)")
print()

# Test with smaller window that fits your screen
test_configs = [
    (1470, 956, "MacBook Pro 14-inch"),
    (1280, 800, "Safe smaller size"),
    (1024, 768, "Very safe size"),
]

for width, height, desc in test_configs:
    print(f"\n{'='*60}")
    print(f"Test: {desc} ({width}x{height})")
    
    screen_constraint = Screen(
        min_width=width,
        max_width=width,
        min_height=height,
        max_height=height
    )
    
    try:
        with Camoufox(
            os='macos',  # Your actual OS
            screen=screen_constraint,
            headless=False,
            i_know_what_im_doing=True
        ) as browser:
            # Don't set viewport - let it auto-size
            page = browser.new_page()
            
            page.goto('https://example.com')
            
            dims = page.evaluate('''() => ({
                screen_width: screen.width,
                window_innerWidth: window.innerWidth,
                window_innerHeight: window.innerHeight
            })''')
            
            print(f"  Screen: {dims['screen_width']}px")
            print(f"  Window: {dims['window_innerWidth']}x{dims['window_innerHeight']}px")
            print(f"\n  👀 Can you see the full page without scrolling horizontally?")
            print(f"  ✅ If yes, this size works for your screen")
            print(f"  ❌ If no, try a smaller size")
            
            input("\n  Press Enter to test next size...")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        continue

print("\n✅ Testing complete!")
print("\n💡 Use the size that let you see the full page comfortably")
