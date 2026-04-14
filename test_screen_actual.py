"""Check what screen dimensions Camoufox actually generates"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

# Test different screen constraints
tests = [
    (1920, 1080, "Standard 1920x1080"),
    (1900, 1060, "Slightly smaller 1900x1060"),
    (1850, 1040, "Even smaller 1850x1040"),
]

for width, height, desc in tests:
    print(f"\n{'='*60}")
    print(f"Test: {desc}")
    print(f"Constraint: {width}x{height}")
    
    screen_constraint = Screen(
        min_width=width, max_width=width,
        min_height=height, max_height=height
    )
    
    with Camoufox(
        os='windows',
        screen=screen_constraint,
        headless=True,
        i_know_what_im_doing=True
    ) as browser:
        context = browser.new_context(
            viewport={'width': width, 'height': height - 70}
        )
        page = context.new_page()
        page.goto('data:text/html,<h1>Test</h1>')
        
        dims = page.evaluate('''() => ({
            screen_width: screen.width,
            screen_height: screen.height,
            window_innerWidth: window.innerWidth,
            window_innerHeight: window.innerHeight,
        })''')
        
        print(f"Result:")
        print(f"  Screen: {dims['screen_width']}x{dims['screen_height']}")
        print(f"  Viewport: {dims['window_innerWidth']}x{dims['window_innerHeight']}")
        
        width_diff = dims['window_innerWidth'] - dims['screen_width']
        
        if width_diff > 0:
            print(f"  ❌ Viewport is {width_diff}px WIDER than screen!")
        elif width_diff == 0:
            print(f"  ✅ Perfect match!")
        else:
            print(f"  ✅ Viewport is {-width_diff}px narrower (scrollbar)")

print(f"\n{'='*60}")
print("\n💡 Conclusion:")
print("If viewport is consistently wider, this is a Camoufox behavior")
print("We need to account for this in our viewport calculation")
