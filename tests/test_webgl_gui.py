#!/usr/bin/env python3
"""
Test script to verify WebGL GUI functionality
"""

def test_webgl_generation():
    """Test that WebGL data is generated correctly"""
    from webgl_database import get_webgl_for_profile
    
    print("Testing WebGL generation for different browser/OS combinations:\n")
    
    test_cases = [
        ("firefox-120", "windows", 1920),
        ("firefox-128", "macos", 2560),
        ("safari-17", "macos", 1920),
        ("safari-19", "macos", 3840),
        ("chrome-144", "windows", 1920),
    ]
    
    for browser, os, width in test_cases:
        webgl = get_webgl_for_profile(browser, os, width)
        print(f"{browser} on {os} ({width}px):")
        print(f"  Vendor: {webgl['vendor']}")
        print(f"  Renderer: {webgl['renderer']}")
        
        # Verify no "Auto" or "Random" strings
        assert "Auto" not in webgl['vendor'], f"Found 'Auto' in vendor: {webgl['vendor']}"
        assert "Auto" not in webgl['renderer'], f"Found 'Auto' in renderer: {webgl['renderer']}"
        assert "Random" not in webgl['vendor'], f"Found 'Random' in vendor: {webgl['vendor']}"
        assert "Random" not in webgl['renderer'], f"Found 'Random' in renderer: {webgl['renderer']}"
        print("  ✓ No placeholder strings found\n")
    
    print("✅ All tests passed!")

def test_vendor_renderer_mapping():
    """Test vendor to GPU type mapping"""
    from webgl_database import WEBGL_CONFIGS
    
    print("\nTesting vendor to renderer mapping:\n")
    
    vendor_to_gpu = {
        "Google Inc. (NVIDIA)": "nvidia",
        "Google Inc. (Intel)": "intel",
        "Google Inc. (AMD)": "amd",
        "Intel Inc.": "intel",
        "NVIDIA Corporation": "nvidia",
        "Intel": "intel",
        "AMD": "amd",
        "Apple Inc.": "apple",
    }
    
    for vendor, gpu_type in vendor_to_gpu.items():
        print(f"Vendor: {vendor} → GPU Type: {gpu_type}")
        
        # Check if GPU type exists in database
        found = False
        for browser in WEBGL_CONFIGS:
            for os in WEBGL_CONFIGS[browser]:
                if gpu_type in WEBGL_CONFIGS[browser][os]:
                    found = True
                    renderers = WEBGL_CONFIGS[browser][os][gpu_type]
                    print(f"  Found {len(renderers)} renderers in {browser}/{os}")
                    break
            if found:
                break
        
        if not found:
            print(f"  ⚠️  Warning: No renderers found for {gpu_type}")
    
    print("\n✅ Vendor mapping test complete!")

if __name__ == "__main__":
    test_webgl_generation()
    test_vendor_renderer_mapping()
