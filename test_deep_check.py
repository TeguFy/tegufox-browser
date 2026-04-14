"""Deep check of all screen/window properties"""

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

screen_constraint = Screen(
    min_width=1920, max_width=1920,
    min_height=1080, max_height=1080
)

with Camoufox(
    os='windows',
    screen=screen_constraint,
    headless=True,
    i_know_what_im_doing=True
) as browser:
    context = browser.new_context(viewport={'width': 1904, 'height': 1010})
    page = context.new_page()
    page.goto('data:text/html,<h1>Test</h1>')
    
    all_props = page.evaluate('''() => ({
        // Screen properties
        screen_width: screen.width,
        screen_height: screen.height,
        screen_availWidth: screen.availWidth,
        screen_availHeight: screen.availHeight,
        screen_colorDepth: screen.colorDepth,
        screen_pixelDepth: screen.pixelDepth,
        
        // Window properties
        window_innerWidth: window.innerWidth,
        window_innerHeight: window.innerHeight,
        window_outerWidth: window.outerWidth,
        window_outerHeight: window.outerHeight,
        
        // Document properties
        document_clientWidth: document.documentElement.clientWidth,
        document_clientHeight: document.documentElement.clientHeight,
        
        // Visual viewport
        visualViewport_width: window.visualViewport.width,
        visualViewport_height: window.visualViewport.height,
        visualViewport_scale: window.visualViewport.scale,
        
        // Device pixel ratio
        devicePixelRatio: window.devicePixelRatio
    })''')
    
    print("🔍 Complete Screen/Window Analysis\n")
    
    print("Screen Properties:")
    for key in ['screen_width', 'screen_height', 'screen_availWidth', 'screen_availHeight']:
        print(f"  {key}: {all_props[key]}")
    print()
    
    print("Window Properties:")
    for key in ['window_innerWidth', 'window_innerHeight', 'window_outerWidth', 'window_outerHeight']:
        print(f"  {key}: {all_props[key]}")
    print()
    
    print("Document Properties:")
    for key in ['document_clientWidth', 'document_clientHeight']:
        print(f"  {key}: {all_props[key]}")
    print()
    
    print("Visual Viewport:")
    for key in ['visualViewport_width', 'visualViewport_height', 'visualViewport_scale']:
        print(f"  {key}: {all_props[key]}")
    print()
    
    print(f"Device Pixel Ratio: {all_props['devicePixelRatio']}")
    print()
    
    print("Analysis:")
    print(f"  window.innerWidth / screen.width = {all_props['window_innerWidth'] / all_props['screen_width']:.4f}")
    print(f"  window.innerWidth - screen.width = {all_props['window_innerWidth'] - all_props['screen_width']}px")
    print(f"  visualViewport.scale = {all_props['visualViewport_scale']}")
    
    # Check if availWidth is different
    if all_props['screen_availWidth'] != all_props['screen_width']:
        print(f"\n💡 screen.availWidth ({all_props['screen_availWidth']}) != screen.width ({all_props['screen_width']})")
        print("  This might explain the viewport behavior")

print("\n✅ Analysis complete!")
