"""Check what WebGL values Camoufox accepts"""

from camoufox.sync_api import Camoufox

print("🔍 Testing WebGL configurations\n")

# Test 1: No WebGL config (let Camoufox auto-generate)
print("Test 1: Auto-generated WebGL")
try:
    with Camoufox(os='windows', headless=True, i_know_what_im_doing=True) as browser:
        page = browser.new_page()
        page.goto('data:text/html,<h1>Test</h1>')
        
        webgl = page.evaluate('''() => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl');
            const info = gl.getExtension('WEBGL_debug_renderer_info');
            return {
                vendor: gl.getParameter(info.UNMASKED_VENDOR_WEBGL),
                renderer: gl.getParameter(info.UNMASKED_RENDERER_WEBGL)
            }
        }''')
        
        print(f"✅ Auto-generated WebGL:")
        print(f"   Vendor: {webgl['vendor']}")
        print(f"   Renderer: {webgl['renderer']}")
        print()
except Exception as e:
    print(f"❌ Error: {e}\n")

print("💡 Recommendation: Remove webGl:* keys from profile config")
print("   Camoufox will auto-generate appropriate WebGL values based on OS")
