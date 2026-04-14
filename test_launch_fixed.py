"""Fixed viewport test - use context viewport instead"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen
import json

# Load profile
with open('profiles/test-ebay-profile.json') as f:
    profile = json.load(f)

config = profile['config']

# Clean config
clean_config = {k: v for k, v in config.items() 
                if not k.startswith(('screen.', 'navigator.', 'webGl:'))}

# Screen constraint
target_width = 1920
target_height = 1080

screen_constraint = Screen(
    min_width=target_width,
    max_width=target_width,
    min_height=target_height,
    max_height=target_height
)

print("🦊 Testing Fixed Viewport\n")

with Camoufox(
    os='windows',
    screen=screen_constraint,
    config=clean_config,
    headless=True,
    i_know_what_im_doing=True
) as browser:
    # Create context with viewport
    context = browser.new_context(
        viewport={'width': target_width, 'height': target_height - 70}
    )
    
    page = context.new_page()
    page.goto('data:text/html,<h1>Test</h1>')
    
    # Check dimensions
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        screen_height: screen.height,
        window_innerWidth: window.innerWidth,
        window_innerHeight: window.innerHeight,
        ratio: (window.innerWidth / screen.width * 100).toFixed(1)
    })''')
    
    print("📊 Dimensions:")
    print(f"   Screen: {dims['screen_width']}x{dims['screen_height']}")
    print(f"   Viewport: {dims['window_innerWidth']}x{dims['window_innerHeight']}")
    print(f"   Ratio: {dims['ratio']}%")
    
    print("\n🔍 Validation:")
    
    if dims['window_innerWidth'] > dims['screen_width']:
        print("   ❌ CRITICAL: viewport > screen")
    else:
        print("   ✅ viewport <= screen")
    
    ratio = float(dims['ratio'])
    if ratio == 100.0:
        print(f"   ✅ Perfect: viewport = screen")
    elif ratio >= 95:
        print(f"   ✅ Excellent: viewport = {ratio}% of screen")
    elif ratio >= 85:
        print(f"   ⚠️  Acceptable: viewport = {ratio}% of screen")
    else:
        print(f"   ❌ Poor: viewport only {ratio}% of screen")
    
    if dims['window_innerWidth'] <= dims['screen_width'] and ratio >= 95:
        print("\n✅ ✅ ✅ PERFECT! Viewport configuration is correct!")
    elif dims['window_innerWidth'] <= dims['screen_width']:
        print("\n✅ Viewport is consistent (but could be larger)")
    else:
        print("\n❌ Viewport configuration needs fixing")

print("\n✅ Test completed!")
