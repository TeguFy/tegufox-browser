"""Auto-detect screen size and create appropriate profile"""

from camoufox.sync_api import Camoufox
import subprocess

print("🔍 Auto-detecting your screen resolution...\n")

# Get screen resolution on macOS
try:
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType"],
        capture_output=True,
        text=True
    )
    
    output = result.stdout
    
    # Parse resolution
    for line in output.split('\n'):
        if 'Resolution' in line or 'resolution' in line:
            print(f"Found: {line.strip()}")
    
    print("\n💡 Common MacBook resolutions:")
    print("   - 14-inch: 3024x1964 (scaled to 1512x982 default)")
    print("   - 16-inch: 3456x2234 (scaled to 1728x1117 default)")
    print("   - Retina: Varies by model")
    print()
    
except Exception as e:
    print(f"Could not auto-detect: {e}\n")

# Test with adaptive sizing
print("Testing with MacBook-appropriate size...\n")

from browserforge.fingerprints import Screen

# Use MacBook 14-inch default scaled resolution
screen_constraint = Screen(
    min_width=1470,
    max_width=1470,
    min_height=956,
    max_height=956
)

print("Using: 1470x956 (MacBook Pro 14-inch default)\n")

with Camoufox(
    os='macos',
    screen=screen_constraint,
    headless=False,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(
        viewport={'width': 1470, 'height': 886}  # Full width, minus chrome
    )
    
    page = context.new_page()
    page.goto('https://example.com')
    
    dims = page.evaluate('''() => ({
        screen: {width: screen.width, height: screen.height},
        window: {width: window.innerWidth, height: window.innerHeight}
    })''')
    
    print(f"Screen: {dims['screen']['width']}x{dims['screen']['height']}")
    print(f"Window: {dims['window']['width']}x{dims['window']['height']}")
    
    print("\n✅ Browser opened!")
    print("👀 Can you see the full example.com page?")
    print("   If yes, this size works for your MacBook")
    print("\n⏱️  Closing in 15 seconds...")
    
    import time
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass

print("\n✅ Done!")
