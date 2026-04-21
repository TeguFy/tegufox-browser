#!/usr/bin/env python3
"""
Integration test: Create profile and verify WebGL data
"""
import json
import os

def test_profile_creation():
    """Test creating a profile with WebGL data"""
    from profile_generator import generate_profile
    
    print("Testing profile creation with WebGL data:\n")
    
    # Test 1: Create profile with "Random" WebGL (should auto-generate)
    print("Test 1: Profile with auto-generated WebGL")
    config1 = {
        'name': 'test_profile_auto_webgl',
        'os': 'windows',
        'browser': 'firefox',
        'webrtc': True,
        'webgl': None,  # None means auto-generate
    }
    
    profile1 = generate_profile(config1)
    print(f"  Profile: {profile1['name']}")
    print(f"  OS: {profile1['os']}")
    print(f"  WebGL Vendor: {profile1['webgl']['vendor']}")
    print(f"  WebGL Renderer: {profile1['webgl']['renderer']}")
    
    # Verify no placeholder strings
    assert "Auto" not in profile1['webgl']['vendor'], "Found 'Auto' in vendor"
    assert "Auto" not in profile1['webgl']['renderer'], "Found 'Auto' in renderer"
    assert "Random" not in profile1['webgl']['vendor'], "Found 'Random' in vendor"
    assert "Random" not in profile1['webgl']['renderer'], "Found 'Random' in renderer"
    print("  ✓ No placeholder strings\n")
    
    # Test 2: Create profile with manually specified WebGL
    print("Test 2: Profile with manually specified WebGL")
    config2 = {
        'name': 'test_profile_manual_webgl',
        'os': 'macos',
        'browser': 'safari',
        'webrtc': False,
        'webgl': {
            'vendor': 'Apple Inc.',
            'renderer': 'Apple M1 Pro',
        }
    }
    
    profile2 = generate_profile(config2)
    print(f"  Profile: {profile2['name']}")
    print(f"  OS: {profile2['os']}")
    print(f"  WebGL Vendor: {profile2['webgl']['vendor']}")
    print(f"  WebGL Renderer: {profile2['webgl']['renderer']}")
    
    # Verify manual values are preserved
    assert profile2['webgl']['vendor'] == 'Apple Inc.', "Vendor mismatch"
    assert profile2['webgl']['renderer'] == 'Apple M1 Pro', "Renderer mismatch"
    print("  ✓ Manual values preserved\n")
    
    # Test 3: Create profile with different browser versions
    print("Test 3: Multiple Firefox profiles")
    
    for i in range(3):
        config = {
            'name': f'test_firefox_{i}',
            'os': 'windows',
            'browser': 'firefox',
            'webrtc': True,
            'webgl': None,
        }
        profile = generate_profile(config)
        print(f"  Profile {i+1}: {profile['webgl']['vendor']} / {profile['webgl']['renderer'][:50]}...")
        assert "Auto" not in profile['webgl']['vendor']
        assert "Auto" not in profile['webgl']['renderer']
    
    print("  ✓ All Firefox profiles work\n")
    
    # Test 4: Safari profiles
    print("Test 4: Multiple Safari profiles")
    
    for i in range(3):
        config = {
            'name': f'test_safari_{i}',
            'os': 'macos',
            'browser': 'safari',
            'webrtc': True,
            'webgl': None,
        }
        profile = generate_profile(config)
        print(f"  Profile {i+1}: {profile['webgl']['vendor']} / {profile['webgl']['renderer']}")
        assert profile['webgl']['vendor'] == 'Apple Inc.', f"Safari should use Apple Inc., got {profile['webgl']['vendor']}"
    
    print("  ✓ All Safari profiles work\n")
    
    print("\n✅ All integration tests passed!")

if __name__ == "__main__":
    test_profile_creation()
