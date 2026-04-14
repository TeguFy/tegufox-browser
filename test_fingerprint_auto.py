#!/usr/bin/env python3
"""
Automated fingerprint test suite
Collects baseline metrics without manual interaction
"""

from camoufox import Camoufox
import json
import time


def test_fingerprint_automated():
    """Run automated fingerprint tests and collect metrics"""

    print("🦊 Automated Fingerprint Testing\n")

    results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "tests": []}

    try:
        with Camoufox(headless=False) as browser:
            print("✅ Browser launched\n")

            # Test 1: Check navigator properties
            print("=" * 60)
            print("🧪 Test 1: Navigator Properties")
            print("=" * 60)

            page = browser.new_page()
            page.goto("about:blank")

            nav_props = page.evaluate("""() => {
                return {
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory || 'undefined',
                    webdriver: navigator.webdriver,
                    maxTouchPoints: navigator.maxTouchPoints,
                    vendor: navigator.vendor,
                    doNotTrack: navigator.doNotTrack,
                    cookieEnabled: navigator.cookieEnabled
                }
            }""")

            print(json.dumps(nav_props, indent=2))
            results["tests"].append(
                {
                    "name": "Navigator Properties",
                    "status": "pass" if not nav_props.get("webdriver") else "fail",
                    "data": nav_props,
                }
            )

            # Test 2: Screen properties
            print("\n" + "=" * 60)
            print("🧪 Test 2: Screen Properties")
            print("=" * 60)

            screen_props = page.evaluate("""() => {
                return {
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    devicePixelRatio: window.devicePixelRatio
                }
            }""")

            print(json.dumps(screen_props, indent=2))
            results["tests"].append(
                {"name": "Screen Properties", "status": "pass", "data": screen_props}
            )

            # Test 3: WebGL info
            print("\n" + "=" * 60)
            print("🧪 Test 3: WebGL Information")
            print("=" * 60)

            webgl_info = page.evaluate("""() => {
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (!gl) return { error: 'WebGL not supported' };
                    
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    return {
                        vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'unknown',
                        renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'unknown',
                        version: gl.getParameter(gl.VERSION),
                        shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                        maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                        maxViewportDims: String(gl.getParameter(gl.MAX_VIEWPORT_DIMS))
                    }
                } catch(e) {
                    return { error: e.message }
                }
            }""")

            print(json.dumps(webgl_info, indent=2))
            results["tests"].append(
                {
                    "name": "WebGL Information",
                    "status": "pass"
                    if webgl_info and not webgl_info.get("error")
                    else "fail",
                    "data": webgl_info or {"error": "null response"},
                }
            )

            # Test 4: Canvas fingerprint
            print("\n" + "=" * 60)
            print("🧪 Test 4: Canvas Fingerprint")
            print("=" * 60)

            canvas_fp = page.evaluate("""() => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 200;
                canvas.height = 50;
                
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f00';
                ctx.fillRect(0, 0, 100, 50);
                ctx.fillStyle = '#069';
                ctx.fillText('Browser Fingerprint', 2, 15);
                ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
                ctx.fillText('Test Canvas 🦊', 4, 30);
                
                return {
                    dataURL: canvas.toDataURL().substring(0, 100) + '...',
                    length: canvas.toDataURL().length,
                    hash: canvas.toDataURL().split('').reduce((a,b) => {
                        a = ((a << 5) - a) + b.charCodeAt(0);
                        return a & a;
                    }, 0)
                }
            }""")

            print(json.dumps(canvas_fp, indent=2))
            results["tests"].append(
                {"name": "Canvas Fingerprint", "status": "pass", "data": canvas_fp}
            )

            # Test 5: Audio context
            print("\n" + "=" * 60)
            print("🧪 Test 5: Audio Context")
            print("=" * 60)

            audio_info = page.evaluate("""() => {
                try {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    const context = new AudioContext();
                    return {
                        sampleRate: context.sampleRate,
                        state: context.state,
                        maxChannelCount: context.destination.maxChannelCount,
                        numberOfInputs: context.destination.numberOfInputs,
                        numberOfOutputs: context.destination.numberOfOutputs,
                        channelCount: context.destination.channelCount
                    }
                } catch(e) {
                    return { error: e.message }
                }
            }""")

            print(json.dumps(audio_info, indent=2))
            results["tests"].append(
                {
                    "name": "Audio Context",
                    "status": "pass" if not audio_info.get("error") else "fail",
                    "data": audio_info,
                }
            )

            # Test 6: Fonts detection
            print("\n" + "=" * 60)
            print("🧪 Test 6: Font Detection")
            print("=" * 60)

            fonts_info = page.evaluate("""() => {
                const baseFonts = ['monospace', 'sans-serif', 'serif'];
                const testFonts = ['Arial', 'Courier New', 'Georgia', 'Times New Roman', 
                                   'Verdana', 'Comic Sans MS', 'Impact', 'Trebuchet MS'];
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const text = 'mmmmmmmmmmlli';
                
                const baseMeasurements = {};
                for (const baseFont of baseFonts) {
                    ctx.font = `72px ${baseFont}`;
                    baseMeasurements[baseFont] = ctx.measureText(text).width;
                }
                
                const availableFonts = [];
                for (const testFont of testFonts) {
                    let detected = false;
                    for (const baseFont of baseFonts) {
                        ctx.font = `72px ${testFont}, ${baseFont}`;
                        const width = ctx.measureText(text).width;
                        if (width !== baseMeasurements[baseFont]) {
                            detected = true;
                            break;
                        }
                    }
                    if (detected) availableFonts.push(testFont);
                }
                
                return {
                    detectedFonts: availableFonts,
                    count: availableFonts.length
                }
            }""")

            print(json.dumps(fonts_info, indent=2))
            results["tests"].append(
                {"name": "Font Detection", "status": "pass", "data": fonts_info}
            )

            # Test 7: Plugin/MIME types
            print("\n" + "=" * 60)
            print("🧪 Test 7: Plugins & MIME Types")
            print("=" * 60)

            plugins_info = page.evaluate("""() => {
                return {
                    pluginsLength: navigator.plugins.length,
                    mimeTypesLength: navigator.mimeTypes.length,
                    plugins: Array.from(navigator.plugins).map(p => ({
                        name: p.name,
                        description: p.description
                    }))
                }
            }""")

            print(json.dumps(plugins_info, indent=2))
            results["tests"].append(
                {"name": "Plugins & MIME Types", "status": "pass", "data": plugins_info}
            )

            page.close()

            # Summary
            print("\n" + "=" * 60)
            print("📊 SUMMARY")
            print("=" * 60)

            passed = sum(1 for t in results["tests"] if t["status"] == "pass")
            total = len(results["tests"])

            print(f"✅ Tests Passed: {passed}/{total}")
            print(f"❌ Tests Failed: {total - passed}/{total}")
            print(f"\n🔍 Key Findings:")
            print(f"   - navigator.webdriver: {nav_props.get('webdriver')}")
            print(f"   - WebGL Vendor: {webgl_info.get('vendor', 'N/A')}")
            print(f"   - Canvas Hash: {canvas_fp.get('hash', 'N/A')}")
            print(f"   - Audio Sample Rate: {audio_info.get('sampleRate', 'N/A')}")
            print(f"   - Fonts Detected: {fonts_info.get('count', 0)}")

            # Save results
            with open("docs/phase0-fingerprint-results.json", "w") as f:
                json.dump(results, f, indent=2)

            print(f"\n💾 Results saved to: docs/phase0-fingerprint-results.json")

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_fingerprint_automated()
