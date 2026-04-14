"""Simple mobile viewport test"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

# Mobile size (360x800 = Samsung Galaxy)
mobile_width = 360
mobile_height = 800

screen_constraint = Screen(
    min_width=mobile_width,
    max_width=mobile_width,
    min_height=mobile_height,
    max_height=mobile_height
)

print("📱 Mobile Viewport Test (360x800)\n")

with Camoufox(
    os='windows',  # Use Windows for compatibility
    screen=screen_constraint,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    # Mobile viewport
    context = browser.new_context(
        viewport={'width': mobile_width, 'height': mobile_height - 50},
        is_mobile=True,
        has_touch=True
    )
    
    page = context.new_page()
    page.goto('https://m.ebay.com')
    
    import time
    time.sleep(2)
    
    dims = page.evaluate('''() => ({
        screen: {w: screen.width, h: screen.height},
        window: {w: window.innerWidth, h: window.innerHeight}
    })''')
    
    print(f"Screen: {dims['screen']['w']}x{dims['screen']['h']}")
    print(f"Window: {dims['window']['w']}x{dims['window']['h']}")
    
    print("\n👀 Browser window should be NARROW (like a phone)")
    print("   - Can you see mobile eBay layout?")
    print("   - Window width should be ~360px")
    print("   - If too wide, manually resize window narrower")
    
    print("\n⏱️  Closing in 30 seconds...\n")
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass

print("\n✅ Done!")
