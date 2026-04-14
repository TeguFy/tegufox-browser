"""Test in non-headless mode"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

target_width = 1920
actual_width = target_width + 16

screen_constraint = Screen(
    min_width=actual_width,
    max_width=actual_width,
    min_height=1080,
    max_height=1080
)

print("Testing in non-headless mode...")
print(f"Screen constraint: {actual_width}x1080\n")

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=False,  # Non-headless
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(viewport={'width': target_width, 'height': 1010})
    page = context.new_page()
    page.goto('https://browserleaks.com/screen')
    
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        window_innerWidth: window.innerWidth,
        diff: window.innerWidth - screen.width
    })''')
    
    print(f"Screen: {dims['screen_width']}px")
    print(f"Viewport: {dims['window_innerWidth']}px")
    print(f"Difference: {dims['diff']}px")
    
    if dims['diff'] <= 0:
        print("\n✅ SUCCESS! viewport <= screen")
    else:
        print(f"\n❌ viewport is {dims['diff']}px wider than screen")
    
    print("\n👀 Check browserleaks.com visually")
    print("⏱️  Closing in 20 seconds...")
    
    import time
    try:
        time.sleep(20)
    except KeyboardInterrupt:
        pass

print("\n✅ Done!")
