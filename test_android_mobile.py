"""Test Android mobile profile with proper mobile viewport"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen
import json

# Load Android profile
with open('profiles/android-test.json') as f:
    profile = json.load(f)

config = profile['config']

# Clean config
clean_config = {k: v for k, v in config.items() 
                if not k.startswith(('screen.', 'navigator.', 'webGl:'))}

# Mobile screen size
mobile_width = 360
mobile_height = 800

screen_constraint = Screen(
    min_width=mobile_width,
    max_width=mobile_width,
    min_height=mobile_height,
    max_height=mobile_height
)

print("📱 Testing Android Mobile Profile\n")
print(f"Device: Samsung Galaxy S21")
print(f"Screen: {mobile_width}x{mobile_height}")
print()

with Camoufox(
    os='linux',  # Android is Linux-based
    screen=screen_constraint,
    config=clean_config,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    # Create mobile viewport
    context = browser.new_context(
        viewport={'width': mobile_width, 'height': mobile_height - 50},
        user_agent=config.get('navigator.userAgent'),  # Set mobile UA
        is_mobile=True,  # Enable mobile mode
        has_touch=True   # Enable touch events
    )
    
    page = context.new_page()
    
    print("🌐 Loading eBay mobile site...")
    page.goto('https://m.ebay.com', timeout=30000)
    
    import time
    time.sleep(2)
    
    # Check dimensions
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        screen_height: screen.height,
        window_width: window.innerWidth,
        window_height: window.innerHeight,
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        isMobile: /Mobi|Android/i.test(navigator.userAgent)
    })''')
    
    print(f"\n📊 Mobile Dimensions:")
    print(f"   Screen: {dims['screen_width']}x{dims['screen_height']}")
    print(f"   Window: {dims['window_width']}x{dims['window_height']}")
    print(f"   Platform: {dims['platform']}")
    print(f"   Is Mobile: {dims['isMobile']}")
    print()
    
    print("👀 Check the browser window:")
    print("   - Should show mobile version of eBay (m.ebay.com)")
    print("   - Layout should be mobile-optimized (single column)")
    print("   - Can you see the mobile menu/hamburger icon?")
    print("   - Does it look like a phone screen?")
    
    print("\n💡 Browser window size:")
    print("   Window should be NARROW (360px wide)")
    print("   If window is too big, you need to RESIZE it manually")
    print("   → Drag window edge to make it narrower")
    
    print("\n⏱️  Browser stays open for 30 seconds...")
    print("    Press Ctrl+C to close\n")
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Closing...")

print("\n✅ Test completed!")
print("\n📝 Summary:")
print("   If you can see mobile layout → Android profile works! ✅")
print("   If window is too wide → Resize browser window manually")
