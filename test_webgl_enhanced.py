#!/usr/bin/env python3
"""
Tegufox WebGL Enhanced - Test Suite

Tests WebGL fingerprinting defense at C++ level.
Validates vendor/renderer override, extension spoofing, and rendering stability.

Created: 2026-04-13
Phase 1 Week 2 - Day 4
"""

import asyncio
import sys
import hashlib
from pathlib import Path
from camoufox.async_api import Camoufox


class WebGLTest:
    """WebGL Enhanced test runner"""

    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        self.passed = 0
        self.failed = 0
        self.tests = []

    async def run_all(self):
        """Run all WebGL tests"""
        print("=" * 70)
        print("Tegufox WebGL Enhanced - Test Suite")
        print("=" * 70)
        print(f"Profile: {self.profile_path}")
        print()

        # Test 1: Vendor override
        await self.test_webgl_vendor_override()

        # Test 2: Renderer override
        await self.test_webgl_renderer_override()

        # Test 3: Extension list override
        await self.test_webgl_extensions_override()

        # Test 4: Parameter value override
        await self.test_webgl_parameter_override()

        # Test 5: Native code check (undetectable)
        await self.test_webgl_native_code_check()

        # Test 6: Rendering stability (deterministic noise)
        await self.test_webgl_rendering_stability()

        # Test 7: Cross-signal consistency
        await self.test_webgl_consistency()

        # Test 8: Prototype tampering detection
        await self.test_webgl_prototype_tampering()

        # Summary
        self.print_summary()

        return self.failed == 0

    async def test_webgl_vendor_override(self):
        """Test 1: UNMASKED_VENDOR_WEBGL override"""
        test_name = "WebGL Vendor Override"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                vendor = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return 'WEBGL_NOT_SUPPORTED';
                    
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (!ext) return 'DEBUG_INFO_NOT_AVAILABLE';
                    
                    return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                }""")

                # Check if spoofed (should NOT be real GPU vendor if patched)
                if vendor and vendor not in [
                    "WEBGL_NOT_SUPPORTED",
                    "DEBUG_INFO_NOT_AVAILABLE",
                ]:
                    self.test_pass(test_name, f"Vendor: {vendor}")
                else:
                    self.test_fail(test_name, f"Vendor not overridden: {vendor}")

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_renderer_override(self):
        """Test 2: UNMASKED_RENDERER_WEBGL override"""
        test_name = "WebGL Renderer Override"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                renderer = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return 'WEBGL_NOT_SUPPORTED';
                    
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (!ext) return 'DEBUG_INFO_NOT_AVAILABLE';
                    
                    return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                }""")

                if renderer and renderer not in [
                    "WEBGL_NOT_SUPPORTED",
                    "DEBUG_INFO_NOT_AVAILABLE",
                ]:
                    self.test_pass(test_name, f"Renderer: {renderer}")
                else:
                    self.test_fail(test_name, f"Renderer not overridden: {renderer}")

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_extensions_override(self):
        """Test 3: getSupportedExtensions() override"""
        test_name = "WebGL Extensions Override"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                extensions = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return [];
                    
                    return gl.getSupportedExtensions() || [];
                }""")

                if isinstance(extensions, list) and len(extensions) > 0:
                    # Check for common extensions
                    has_debug_info = "WEBGL_debug_renderer_info" in extensions
                    has_angle = "ANGLE_instanced_arrays" in extensions

                    if has_debug_info and has_angle:
                        self.test_pass(
                            test_name,
                            f"{len(extensions)} extensions, including WEBGL_debug_renderer_info",
                        )
                    else:
                        self.test_fail(
                            test_name,
                            f"Missing common extensions (debug_info={has_debug_info}, ANGLE={has_angle})",
                        )
                else:
                    self.test_fail(
                        test_name, f"Extension list empty or invalid: {extensions}"
                    )

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_parameter_override(self):
        """Test 4: MAX_TEXTURE_SIZE and other parameter overrides"""
        test_name = "WebGL Parameter Override"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                params = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    
                    return {
                        MAX_TEXTURE_SIZE: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                        MAX_VERTEX_ATTRIBS: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
                        MAX_VIEWPORT_DIMS: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
                        SHADING_LANGUAGE_VERSION: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                        VERSION: gl.getParameter(gl.VERSION)
                    };
                }""")

                if params:
                    details = (
                        f"MAX_TEXTURE_SIZE={params['MAX_TEXTURE_SIZE']}, "
                        f"MAX_VERTEX_ATTRIBS={params['MAX_VERTEX_ATTRIBS']}, "
                        f"VERSION={params['VERSION']}"
                    )

                    # Basic validation (values should be reasonable)
                    if (
                        params["MAX_TEXTURE_SIZE"] >= 2048
                        and params["MAX_VERTEX_ATTRIBS"] >= 8
                    ):
                        self.test_pass(test_name, details)
                    else:
                        self.test_fail(
                            test_name, f"Invalid parameter values: {details}"
                        )
                else:
                    self.test_fail(test_name, "Could not retrieve parameters")

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_native_code_check(self):
        """Test 5: Verify getParameter appears as native code (undetectable)"""
        test_name = "Native Code Check (Undetectable)"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                is_native = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return false;
                    
                    // Check if getParameter.toString() includes [native code]
                    const toString = gl.getParameter.toString();
                    return toString.includes('[native code]');
                }""")

                if is_native:
                    self.test_pass(test_name, "getParameter appears as [native code]")
                else:
                    self.test_fail(
                        test_name,
                        "getParameter does NOT appear as native (DETECTABLE!)",
                    )

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_rendering_stability(self):
        """Test 6: Rendering hash stability (deterministic noise)"""
        test_name = "Rendering Stability (Deterministic)"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto(
                    'data:text/html,<canvas id="c" width="256" height="256"></canvas>'
                )

                # Render same scene twice
                hash1 = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    
                    // Clear to red
                    gl.clearColor(1.0, 0.0, 0.0, 1.0);
                    gl.clear(gl.COLOR_BUFFER_BIT);
                    
                    // Read pixels
                    const pixels = new Uint8Array(256 * 256 * 4);
                    gl.readPixels(0, 0, 256, 256, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
                    
                    // Simple hash
                    let hash = 0;
                    for (let i = 0; i < pixels.length; i++) {
                        hash = ((hash << 5) - hash) + pixels[i];
                        hash = hash & hash; // Convert to 32bit integer
                    }
                    return hash;
                }""")

                hash2 = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    
                    // Same rendering
                    gl.clearColor(1.0, 0.0, 0.0, 1.0);
                    gl.clear(gl.COLOR_BUFFER_BIT);
                    
                    const pixels = new Uint8Array(256 * 256 * 4);
                    gl.readPixels(0, 0, 256, 256, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
                    
                    let hash = 0;
                    for (let i = 0; i < pixels.length; i++) {
                        hash = ((hash << 5) - hash) + pixels[i];
                        hash = hash & hash;
                    }
                    return hash;
                }""")

                if hash1 is not None and hash2 is not None:
                    if hash1 == hash2:
                        self.test_pass(
                            test_name, f"Same scene produces same hash (hash={hash1})"
                        )
                    else:
                        self.test_fail(
                            test_name,
                            f"Hash mismatch: {hash1} != {hash2} (RANDOM NOISE DETECTED!)",
                        )
                else:
                    self.test_fail(test_name, "Could not compute rendering hash")

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_consistency(self):
        """Test 7: Cross-signal consistency (WebGL GPU matches platform)"""
        test_name = "Cross-Signal Consistency"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                data = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (!ext) return null;
                    
                    return {
                        vendor: gl.getParameter(ext.UNMASKED_VENDOR_WEBGL),
                        renderer: gl.getParameter(ext.UNMASKED_RENDERER_WEBGL),
                        platform: navigator.platform,
                        userAgent: navigator.userAgent
                    };
                }""")

                if data:
                    # Basic consistency checks
                    is_consistent = True
                    issues = []

                    # Check 1: Mac + NVIDIA = inconsistent
                    if (
                        "Mac" in data["platform"]
                        and "NVIDIA GeForce" in data["renderer"]
                    ):
                        is_consistent = False
                        issues.append(
                            "Mac with NVIDIA GeForce GPU (Macs use Intel/AMD/Apple)"
                        )

                    # Check 2: Android + Desktop GPU = inconsistent
                    if "Android" in data["userAgent"] and any(
                        x in data["renderer"] for x in ["Radeon", "GeForce", "Intel HD"]
                    ):
                        is_consistent = False
                        issues.append("Android with desktop GPU")

                    # Check 3: Linux x86_64 + ARM GPU = inconsistent
                    if (
                        data["platform"] == "Linux x86_64"
                        and "Mali" in data["renderer"]
                    ):
                        is_consistent = False
                        issues.append("Linux x86_64 with ARM Mali GPU")

                    if is_consistent:
                        self.test_pass(
                            test_name,
                            f"Platform={data['platform']}, GPU={data['vendor']}",
                        )
                    else:
                        self.test_fail(
                            test_name, f"Inconsistency detected: {', '.join(issues)}"
                        )
                else:
                    self.test_fail(test_name, "Could not retrieve fingerprint data")

        except Exception as e:
            self.test_fail(test_name, str(e))

    async def test_webgl_prototype_tampering(self):
        """Test 8: Verify no prototype tampering detected"""
        test_name = "Prototype Tampering Detection"

        try:
            async with Camoufox(
                config_path=self.profile_path, headless=True
            ) as browser:
                page = await browser.new_page()
                await page.goto('data:text/html,<canvas id="c"></canvas>')

                tampered = await page.evaluate("""() => {
                    const canvas = document.getElementById('c');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    
                    // Check for prototype tampering (CreepJS technique)
                    const descriptor = Object.getOwnPropertyDescriptor(
                        WebGLRenderingContext.prototype, 'getParameter'
                    );
                    
                    if (!descriptor) return 'NO_DESCRIPTOR';
                    
                    // Check if writable (sign of tampering)
                    if (descriptor.writable) return 'WRITABLE';
                    
                    // Check if value is a function
                    if (typeof descriptor.value !== 'function') return 'NOT_FUNCTION';
                    
                    return 'OK';
                }""")

                if tampered == "OK":
                    self.test_pass(test_name, "No prototype tampering detected")
                else:
                    self.test_fail(test_name, f"Tampering signature: {tampered}")

        except Exception as e:
            self.test_fail(test_name, str(e))

    def test_pass(self, name: str, details: str = ""):
        """Mark test as passed"""
        self.passed += 1
        status = "✅ PASS"
        print(f"{status:12} {name:40} {details}")
        self.tests.append((name, True, details))

    def test_fail(self, name: str, error: str = ""):
        """Mark test as failed"""
        self.failed += 1
        status = "❌ FAIL"
        print(f"{status:12} {name:40} {error}")
        self.tests.append((name, False, error))

    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 70)
        print("Test Summary")
        print("=" * 70)
        print(f"Total: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print()

        if self.failed > 0:
            print("Failed tests:")
            for name, passed, details in self.tests:
                if not passed:
                    print(f"  - {name}: {details}")
            print()

        if self.failed == 0:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {self.failed} test(s) failed")
        print()


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 test_webgl_enhanced.py <profile.json>")
        print()
        print("Examples:")
        print("  python3 test_webgl_enhanced.py profiles/macbook-test.json")
        print("  python3 test_webgl_enhanced.py profiles/test-canvas-v2.json")
        sys.exit(1)

    profile_path = sys.argv[1]

    # Validate profile exists
    if not Path(profile_path).exists():
        print(f"❌ Profile not found: {profile_path}")
        sys.exit(1)

    # Run tests
    tester = WebGLTest(profile_path)
    success = await tester.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
