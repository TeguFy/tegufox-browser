"""Test eBay with MacBook-sized window"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen
import json

# Load MacBook profile
with open('profiles/macbook-test.json') as f:
    profile = json.load(f)

config = profile['config']

# Clean config (remove auto-generated keys)
clean_config = {k: v for k, v in config.items() 
                if not k.startswith(('screen.', 'navigator.', 'webGl:'))}

# MacBook size
screen_constraint = Screen(
    min_width=1470,
    max_width=1470,
    min_height=956,
    max_height=956
)

print("🛍️  Testing eBay with MacBook-sized window\n")
print("Screen: 1470x956 (MacBook Pro 14-inch)")
print("Config keys:", len(clean_config))
print()

with Camoufox(
    os='macos',
    screen=screen_constraint,
    config=clean_config,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(
        viewport={'width': 1470, 'height': 886}
    )
    
    page = context.new_page()
    
    print("🌐 Loading eBay...")
    page.goto('https://www.ebay.com', timeout=30000)
    
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        window_width: window.innerWidth,
        body_width: document.body.scrollWidth,
        viewport_width: document.documentElement.clientWidth
    })''')
    
    print(f"\n📊 Dimensions:")
    print(f"   Screen: {dims['screen_width']}px")
    print(f"   Window: {dims['window_width']}px")
    print(f"   Body: {dims['body_width']}px")
    print(f"   Viewport: {dims['viewport_width']}px")
    
    needs_scroll = dims['body_width'] > dims['window_width']
    
    print(f"\n👀 Visual Check:")
    if needs_scroll:
        print(f"   ⚠️  Body ({dims['body_width']}px) > Window ({dims['window_width']}px)")
        print(f"   You need to scroll horizontally by {dims['body_width'] - dims['window_width']}px")
    else:
        print(f"   ✅ Body fits in window - no horizontal scroll needed!")
    
    print("\n💡 Look at the eBay page:")
    print("   - Can you see the full header without scrolling?")
    print("   - Can you see product images properly?")
    print("   - Does the layout look normal?")
    
    print("\n⏱️  Browser will stay open for 30 seconds...")
    print("    Press Ctrl+C to close early\n")
    
    import time
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Closing...")

print("\n✅ Test completed!")
