"""Test viewport dimensions vs window dimensions"""

from camoufox.sync_api import Camoufox
import json

# Load profile
with open('profiles/test-ebay-profile.json') as f:
    profile = json.load(f)

config = profile['config']

print("🔍 Testing Viewport Dimensions\n")
print(f"📋 Profile Configuration:")
print(f"   screen.width: {config.get('screen.width')}")
print(f"   screen.height: {config.get('screen.height')}")
print()

# Launch browser
print("🚀 Launching browser...\n")

with Camoufox(config=config, headless=False) as browser:
    page = browser.new_page()
    
    # Navigate to test page
    page.goto('data:text/html,<html><body><h1>Viewport Test</h1></body></html>')
    
    # Get dimensions
    dimensions = page.evaluate('''() => {
        return {
            // Window dimensions
            window_innerWidth: window.innerWidth,
            window_innerHeight: window.innerHeight,
            window_outerWidth: window.outerWidth,
            window_outerHeight: window.outerHeight,
            
            // Screen dimensions
            screen_width: screen.width,
            screen_height: screen.height,
            screen_availWidth: screen.availWidth,
            screen_availHeight: screen.availHeight,
            
            // Document dimensions
            document_clientWidth: document.documentElement.clientWidth,
            document_clientHeight: document.documentElement.clientHeight,
            
            // Viewport dimensions
            visualViewport_width: window.visualViewport ? window.visualViewport.width : null,
            visualViewport_height: window.visualViewport ? window.visualViewport.height : null,
            
            // Device pixel ratio
            devicePixelRatio: window.devicePixelRatio
        }
    }''')
    
    print("📊 Measured Dimensions:\n")
    print("Window:")
    print(f"   innerWidth: {dimensions['window_innerWidth']}px")
    print(f"   innerHeight: {dimensions['window_innerHeight']}px")
    print(f"   outerWidth: {dimensions['window_outerWidth']}px")
    print(f"   outerHeight: {dimensions['window_outerHeight']}px")
    print()
    
    print("Screen:")
    print(f"   width: {dimensions['screen_width']}px")
    print(f"   height: {dimensions['screen_height']}px")
    print(f"   availWidth: {dimensions['screen_availWidth']}px")
    print(f"   availHeight: {dimensions['screen_availHeight']}px")
    print()
    
    print("Document:")
    print(f"   clientWidth: {dimensions['document_clientWidth']}px")
    print(f"   clientHeight: {dimensions['document_clientHeight']}px")
    print()
    
    print("Visual Viewport:")
    print(f"   width: {dimensions['visualViewport_width']}px")
    print(f"   height: {dimensions['visualViewport_height']}px")
    print()
    
    print(f"Device Pixel Ratio: {dimensions['devicePixelRatio']}")
    print()
    
    # Check for mismatch
    configured_width = config.get('screen.width')
    configured_height = config.get('screen.height')
    
    print("🔍 Analysis:\n")
    
    if dimensions['screen_width'] != configured_width:
        print(f"⚠️  screen.width mismatch:")
        print(f"   Configured: {configured_width}px")
        print(f"   Actual: {dimensions['screen_width']}px")
        print()
    
    if dimensions['screen_height'] != configured_height:
        print(f"⚠️  screen.height mismatch:")
        print(f"   Configured: {configured_height}px")
        print(f"   Actual: {dimensions['screen_height']}px")
        print()
    
    # Check if viewport is reasonable
    expected_inner_width = configured_width
    actual_inner_width = dimensions['window_innerWidth']
    
    if actual_inner_width > expected_inner_width:
        print(f"❌ Problem detected:")
        print(f"   window.innerWidth ({actual_inner_width}px) > screen.width ({configured_width}px)")
        print(f"   This is impossible and will be flagged as suspicious!")
        print()
    
    if abs(actual_inner_width - expected_inner_width) > 100:
        print(f"⚠️  Large viewport difference:")
        print(f"   Expected ~{expected_inner_width}px (allowing for scrollbar)")
        print(f"   Got {actual_inner_width}px")
        print(f"   Difference: {actual_inner_width - expected_inner_width}px")
        print()
    
    print("💡 Press Enter to close browser...")
    input()
