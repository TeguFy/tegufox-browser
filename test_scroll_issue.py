"""Test scroll functionality"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

print("🔍 Testing Scroll Issue\n")

screen_constraint = Screen(
    min_width=1470,
    max_width=1470,
    min_height=956,
    max_height=956
)

with Camoufox(
    os='macos',
    screen=screen_constraint,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(
        viewport={'width': 1470, 'height': 886}
    )
    
    page = context.new_page()
    
    print("📄 Loading long page...")
    page.goto('https://example.com')
    
    # Check scroll properties
    scroll_info = page.evaluate('''() => {
        return {
            // Document dimensions
            scrollHeight: document.documentElement.scrollHeight,
            scrollWidth: document.documentElement.scrollWidth,
            clientHeight: document.documentElement.clientHeight,
            clientWidth: document.documentElement.clientWidth,
            
            // Body dimensions
            bodyScrollHeight: document.body.scrollHeight,
            bodyClientHeight: document.body.clientHeight,
            
            // Current scroll position
            scrollTop: window.scrollY || document.documentElement.scrollTop,
            scrollLeft: window.scrollX || document.documentElement.scrollLeft,
            
            // Overflow styles
            htmlOverflow: getComputedStyle(document.documentElement).overflow,
            htmlOverflowY: getComputedStyle(document.documentElement).overflowY,
            bodyOverflow: getComputedStyle(document.body).overflow,
            bodyOverflowY: getComputedStyle(document.body).overflowY,
            
            // Check if scrollable
            isScrollable: document.documentElement.scrollHeight > document.documentElement.clientHeight
        }
    }''')
    
    print("\n📊 Scroll Analysis:")
    print(f"   Document height: {scroll_info['scrollHeight']}px")
    print(f"   Visible height: {scroll_info['clientHeight']}px")
    print(f"   Can scroll: {scroll_info['scrollHeight'] - scroll_info['clientHeight']}px")
    print()
    print(f"   HTML overflow: {scroll_info['htmlOverflow']}")
    print(f"   HTML overflow-y: {scroll_info['htmlOverflowY']}")
    print(f"   Body overflow: {scroll_info['bodyOverflow']}")
    print(f"   Body overflow-y: {scroll_info['bodyOverflowY']}")
    print()
    print(f"   Is scrollable: {scroll_info['isScrollable']}")
    print()
    
    # Try to scroll
    print("🖱️  Attempting to scroll down...")
    
    try:
        # Scroll down 500px
        page.evaluate('window.scrollBy(0, 500)')
        
        # Check new position
        import time
        time.sleep(0.5)
        
        new_pos = page.evaluate('window.scrollY')
        print(f"   New scroll position: {new_pos}px")
        
        if new_pos > 0:
            print("   ✅ Scroll works!")
        else:
            print("   ❌ Scroll is blocked or page is too short")
    except Exception as e:
        print(f"   ❌ Scroll error: {e}")
    
    print("\n📝 Loading longer page (eBay)...")
    page.goto('https://www.ebay.com')
    
    import time
    time.sleep(2)  # Wait for page to load
    
    # Check eBay scroll
    ebay_scroll = page.evaluate('''() => {
        return {
            scrollHeight: document.documentElement.scrollHeight,
            clientHeight: document.documentElement.clientHeight,
            canScroll: document.documentElement.scrollHeight > document.documentElement.clientHeight,
            overflow: getComputedStyle(document.documentElement).overflow,
            overflowY: getComputedStyle(document.documentElement).overflowY
        }
    }''')
    
    print(f"\n📊 eBay Scroll Info:")
    print(f"   Page height: {ebay_scroll['scrollHeight']}px")
    print(f"   Visible: {ebay_scroll['clientHeight']}px")
    print(f"   Scrollable: {ebay_scroll['canScroll']}")
    print(f"   Overflow: {ebay_scroll['overflow']}")
    print(f"   Overflow-Y: {ebay_scroll['overflowY']}")
    
    # Try scrolling on eBay
    print("\n🖱️  Trying to scroll eBay...")
    
    initial_pos = page.evaluate('window.scrollY')
    page.evaluate('window.scrollBy(0, 1000)')
    time.sleep(0.5)
    final_pos = page.evaluate('window.scrollY')
    
    print(f"   Initial position: {initial_pos}px")
    print(f"   Final position: {final_pos}px")
    print(f"   Scrolled: {final_pos - initial_pos}px")
    
    if final_pos > initial_pos:
        print("\n   ✅ eBay scroll WORKS!")
    else:
        print("\n   ❌ eBay scroll is BLOCKED!")
        print("   This is the issue - scroll is disabled!")
    
    print("\n💡 Try using mouse/trackpad to scroll manually in the browser")
    print("   If manual scroll also doesn't work, there's a CSS/JS issue")
    
    print("\n⏱️  Browser stays open for 30 seconds...")
    print("    Try scrolling with mouse/trackpad")
    print("    Press Ctrl+C to close\n")
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Closing...")

print("\n✅ Test completed!")
