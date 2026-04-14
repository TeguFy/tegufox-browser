"""Check if viewport > screen is actually a problem on real sites"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

screen_constraint = Screen(
    min_width=1920, max_width=1920,
    min_height=1080, max_height=1080
)

print("🌐 Testing on Real Sites\n")
print("Checking if window.innerWidth > screen.width is flagged as suspicious...\n")

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=False,  # Non-headless to see actual rendering
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(viewport={'width': 1904, 'height': 1010})
    page = context.new_page()
    
    # Check browserleaks
    print("📊 Test 1: BrowserLeaks Screen Detection")
    page.goto('https://browserleaks.com/screen')
    
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        window_innerWidth: window.innerWidth,
        diff: window.innerWidth - screen.width
    })''')
    
    print(f"   Screen width: {dims['screen_width']}px")
    print(f"   Window width: {dims['window_innerWidth']}px")
    print(f"   Difference: {dims['diff']}px")
    
    if dims['diff'] > 0:
        print(f"   ⚠️  window.innerWidth is {dims['diff']}px WIDER than screen.width")
        print("   This is technically impossible and MAY be flagged")
    else:
        print("   ✅ Dimensions are consistent")
    
    print("\n💡 Visually check if browserleaks.com shows any warnings...")
    print("💡 Check the 'Window Size' vs 'Screen Resolution' section")
    print("\n⏱️  Browser will close in 30 seconds (or press Ctrl+C)...\n")
    
    import time
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Closing...")

print("\n✅ Test completed!")
