"""Automated test of profile launcher"""

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
screen_constraint = Screen(
    min_width=1900, max_width=1920,
    min_height=1060, max_height=1080
)

print("🦊 Testing Profile Launch\n")
print(f"Original config keys: {len(config)}")
print(f"Cleaned config keys: {len(clean_config)}")
print(f"Removed: {', '.join(set(config.keys()) - set(clean_config.keys()))}")
print()

print("🚀 Launching browser...")

with Camoufox(
    os='windows',
    screen=screen_constraint,
    config=clean_config,
    headless=True,  # Headless for automated testing
    i_know_what_im_doing=True
) as browser:
    page = browser.new_page()
    
    # Set viewport
    page.set_viewport_size({'width': 1920, 'height': 1010})
    
    page.goto('data:text/html,<h1>Test</h1>')
    
    # Check dimensions
    dims = page.evaluate('''() => ({
        screen_width: screen.width,
        screen_height: screen.height,
        window_innerWidth: window.innerWidth,
        window_innerHeight: window.innerHeight,
        ratio: (window.innerWidth / screen.width * 100).toFixed(1)
    })''')
    
    print("\n📊 Measured Dimensions:")
    print(f"   Screen: {dims['screen_width']}x{dims['screen_height']}")
    print(f"   Viewport: {dims['window_innerWidth']}x{dims['window_innerHeight']}")
    print(f"   Ratio: {dims['ratio']}%")
    
    # Validation
    print("\n🔍 Validation:")
    
    issues = []
    
    if dims['window_innerWidth'] > dims['screen_width']:
        issues.append("❌ CRITICAL: viewport > screen")
    else:
        print("   ✅ viewport <= screen")
    
    ratio = float(dims['ratio'])
    if ratio >= 95:
        print(f"   ✅ Viewport fills {ratio}% of screen")
    elif ratio >= 85:
        print(f"   ⚠️  Viewport fills {ratio}% of screen (acceptable)")
    else:
        issues.append(f"❌ Viewport only {ratio}% of screen")
    
    if issues:
        print("\n❌ Issues:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ All checks passed!")
        print("🎉 Viewport configuration is correct!")

print("\n✅ Test completed successfully!")
