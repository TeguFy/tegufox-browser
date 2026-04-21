"""
Profile Generator for Tegufox Browser
Generates browser profiles with randomized fingerprints for anti-detection.
"""

import json
import random
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from .webgl_database import WEBGL_CONFIGS, get_random_webgl, get_webgl_for_profile
from .database import ProfileDatabase


# Common screen resolutions by OS
SCREEN_RESOLUTIONS = {
    'windows': [
        {'width': 1920, 'height': 1080, 'availHeight': 1040},  # Full HD (most common)
        {'width': 1366, 'height': 768, 'availHeight': 728},    # HD (laptops)
        {'width': 2560, 'height': 1440, 'availHeight': 1400},  # 2K
        {'width': 1536, 'height': 864, 'availHeight': 824},    # HD+ (laptops)
        {'width': 1600, 'height': 900, 'availHeight': 860},    # HD+
        {'width': 3840, 'height': 2160, 'availHeight': 2120},  # 4K
    ],
    'macos': [
        {'width': 1470, 'height': 956, 'availHeight': 916},    # MacBook Pro 14" (Retina scaled)
        {'width': 1728, 'height': 1117, 'availHeight': 1077},  # MacBook Pro 16" (Retina scaled)
        {'width': 1680, 'height': 1050, 'availHeight': 1010},  # MacBook Pro 15" (older)
        {'width': 2560, 'height': 1440, 'availHeight': 1400},  # iMac 27"
        {'width': 1920, 'height': 1080, 'availHeight': 1040},  # iMac 24"
        {'width': 1512, 'height': 982, 'availHeight': 942},    # MacBook Air 13" (Retina scaled)
    ],
    'linux': [
        {'width': 1920, 'height': 1080, 'availHeight': 1040},  # Full HD
        {'width': 1366, 'height': 768, 'availHeight': 728},    # HD
        {'width': 2560, 'height': 1440, 'availHeight': 1400},  # 2K
        {'width': 1600, 'height': 900, 'availHeight': 860},    # HD+
        {'width': 3840, 'height': 2160, 'availHeight': 2120},  # 4K
    ],
}

# Common timezones by region
TIMEZONES = {
    'americas': [
        ('America/New_York', -300),      # EST/EDT
        ('America/Chicago', -360),       # CST/CDT
        ('America/Denver', -420),        # MST/MDT
        ('America/Los_Angeles', -480),   # PST/PDT
        ('America/Toronto', -300),       # EST/EDT
        ('America/Mexico_City', -360),   # CST
        ('America/Sao_Paulo', -180),     # BRT
    ],
    'europe': [
        ('Europe/London', 0),            # GMT/BST
        ('Europe/Paris', 60),            # CET/CEST
        ('Europe/Berlin', 60),           # CET/CEST
        ('Europe/Madrid', 60),           # CET/CEST
        ('Europe/Rome', 60),             # CET/CEST
        ('Europe/Amsterdam', 60),        # CET/CEST
        ('Europe/Moscow', 180),          # MSK
    ],
    'asia': [
        ('Asia/Tokyo', 540),             # JST
        ('Asia/Shanghai', 480),          # CST
        ('Asia/Hong_Kong', 480),         # HKT
        ('Asia/Singapore', 480),         # SGT
        ('Asia/Seoul', 540),             # KST
        ('Asia/Dubai', 240),             # GST
        ('Asia/Kolkata', 330),           # IST
    ],
    'oceania': [
        ('Australia/Sydney', 600),       # AEST/AEDT
        ('Australia/Melbourne', 600),    # AEST/AEDT
        ('Pacific/Auckland', 720),       # NZST/NZDT
    ],
}

# OS-specific fonts
FONTS = {
    'windows': [
        'Arial', 'Arial Black', 'Calibri', 'Cambria', 'Comic Sans MS',
        'Consolas', 'Courier New', 'Georgia', 'Impact', 'Lucida Console',
        'Microsoft Sans Serif', 'Palatino Linotype', 'Segoe UI', 'Tahoma',
        'Times New Roman', 'Trebuchet MS', 'Verdana',
    ],
    'macos': [
        'Arial', 'Arial Black', 'Comic Sans MS', 'Courier New', 'Georgia',
        'Helvetica', 'Helvetica Neue', 'Impact', 'Lucida Grande', 'Menlo',
        'Monaco', 'Palatino', 'SF Pro', 'Tahoma', 'Times New Roman',
        'Trebuchet MS', 'Verdana',
    ],
    'linux': [
        'Arial', 'Courier New', 'DejaVu Sans', 'DejaVu Sans Mono',
        'DejaVu Serif', 'FreeSans', 'FreeMono', 'FreeSerif', 'Georgia',
        'Liberation Sans', 'Liberation Mono', 'Liberation Serif',
        'Noto Sans', 'Tahoma', 'Times New Roman', 'Ubuntu', 'Verdana',
    ],
}

# User-Agent templates
USER_AGENTS = {
    'firefox': {
        'windows': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0',
        'macos': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/115.0',
        'linux': 'Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0',
    },
    'safari': {
        'macos': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
    },
}

# DNS providers
DNS_PROVIDERS = {
    'firefox': {
        'provider': 'quad9',
        'rationale': 'Firefox privacy-focused, Quad9 non-profit aligns with Mozilla values',
        'uri': 'https://dns.quad9.net/dns-query',
        'bootstrap': '9.9.9.9',
    },
    'safari': {
        'provider': 'cloudflare',
        'rationale': 'Apple uses Cloudflare for iCloud Private Relay',
        'uri': 'https://mozilla.cloudflare-dns.com/dns-query',
        'bootstrap': '1.1.1.1',
    },
}


def _generate_random_fingerprint() -> Dict:
    """Generate random canvas and audio seeds."""
    return {
        'canvas_seed': random.randint(1000000000, 9999999999),
        'audio_seed': random.randint(1000000000, 9999999999),
    }


def _get_random_screen_resolution(os: str) -> Dict:
    """Get random screen resolution for OS."""
    if os not in SCREEN_RESOLUTIONS:
        raise ValueError(f"Invalid OS: {os}. Must be 'windows', 'macos', or 'linux'")
    
    res = random.choice(SCREEN_RESOLUTIONS[os])
    return {
        'width': res['width'],
        'height': res['height'],
        'availWidth': res['width'],
        'availHeight': res['availHeight'],
        'colorDepth': 30 if os == 'macos' else 24,
        'pixelDepth': 30 if os == 'macos' else 24,
    }


def _get_random_timezone(region: Optional[str] = None) -> Tuple[str, int]:
    """Get random timezone (name, offset in minutes)."""
    if region and region in TIMEZONES:
        return random.choice(TIMEZONES[region])
    
    # Random from all regions
    all_timezones = []
    for tz_list in TIMEZONES.values():
        all_timezones.extend(tz_list)
    return random.choice(all_timezones)


def _get_random_fonts(os: str) -> List[str]:
    """Get OS-appropriate font list."""
    if os not in FONTS:
        raise ValueError(f"Invalid OS: {os}. Must be 'windows', 'macos', or 'linux'")
    
    # Return all fonts for the OS (no randomization for now)
    return FONTS[os].copy()


def _get_canvas_noise_config(seed: int, os: str) -> Dict:
    """Generate canvas noise configuration."""
    return {
        'seed': seed,
        'intensity': round(random.uniform(0.01, 0.02), 3),
        'magnitude': 1,
        'edge_bias': round(random.uniform(1.0, 1.2), 1),
        'strategy': 'gpu' if os == 'macos' else 'hybrid',
        'temporal_variation': round(random.uniform(0.0003, 0.0005), 4),
        'sparse_probability': round(random.uniform(0.015, 0.02), 3),
    }


def _get_dns_config(browser: str, webrtc_enabled: bool) -> Dict:
    """Generate DNS configuration."""
    dns = DNS_PROVIDERS.get(browser, DNS_PROVIDERS['firefox'])
    
    return {
        'enabled': True,
        'provider': dns['provider'],
        'rationale': dns['rationale'],
        'doh': {
            'uri': dns['uri'],
            'bootstrap_address': dns['bootstrap'],
            'mode': 3,
            'strict_fallback': True,
            'disable_ecs': True,
        },
        'ipv6': {
            'enabled': False,
            'reason': 'Prevent IPv6 leaks (most VPNs IPv4-only)',
        },
        'webrtc': {
            'enabled': webrtc_enabled,
            'reason': 'Prevent WebRTC IP leaks' if not webrtc_enabled else 'WebRTC enabled',
        },
        'prefetch': {
            'dns_prefetch': False,
            'link_prefetch': False,
            'reason': 'Prevent speculative DNS queries',
        },
    }


def _get_firefox_preferences(dns_config: Dict, webrtc_enabled: bool) -> Dict:
    """Generate Firefox preferences."""
    return {
        'network.trr.mode': 3,
        'network.trr.uri': dns_config['doh']['uri'],
        'network.trr.bootstrapAddress': dns_config['doh']['bootstrap_address'],
        'network.trr.strict_native_fallback': True,
        'network.trr.max_fails': 5,
        'network.trr.request_timeout_ms': 3000,
        'network.trr.disable-ECS': True,
        'network.trr.early-AAAA': False,
        'network.dns.disableIPv6': True,
        'media.peerconnection.enabled': webrtc_enabled,
        'media.navigator.enabled': webrtc_enabled,
        'media.getusermedia.screensharing.enabled': webrtc_enabled,
        'media.peerconnection.ice.no_host': False,
        'media.peerconnection.ice.obfuscate_host_addresses': False,
        'network.dns.disablePrefetch': True,
        'network.prefetch-next': False,
        'network.http.speculative-parallel-limit': 0,
    }


def _resolve_webgl_selection(selected_webgl: Optional[Dict], browser: str, os: str, screen_width: int) -> Optional[Dict[str, str]]:
    """Resolve GUI/manual WebGL selection to a concrete vendor/renderer pair.

    Returns None when caller should use automatic profile-based selection.
    """
    if not isinstance(selected_webgl, dict):
        return None

    vendor_raw = str(selected_webgl.get('vendor', '')).strip()
    renderer_raw = str(selected_webgl.get('renderer', '')).strip()
    placeholders = {'', 'default', 'random', 'auto', 'none'}

    vendor_is_placeholder = vendor_raw.lower() in placeholders
    renderer_is_placeholder = renderer_raw.lower() in placeholders

    # Let auto selection decide both fields.
    if vendor_is_placeholder and renderer_is_placeholder:
        return None

    vendor_to_gpu = {
        'google inc. (nvidia)': 'nvidia',
        'google inc. (intel)': 'intel',
        'google inc. (amd)': 'amd',
        'google inc. (apple)': 'apple',
        'google inc. (nvidia corporation)': 'nvidia',
        'intel inc.': 'intel',
        'nvidia corporation': 'nvidia',
        'intel': 'intel',
        'amd': 'amd',
        'apple': 'apple',
        'apple inc.': 'apple',
    }

    normalized_browser = browser.lower()
    normalized_os = os.lower()

    # If vendor is fixed but renderer is placeholder, randomize renderer within that vendor pool.
    if not vendor_is_placeholder and renderer_is_placeholder:
        gpu_type = vendor_to_gpu.get(vendor_raw.lower())
        if gpu_type:
            try:
                pick = get_random_webgl(normalized_browser, normalized_os, gpu_type)
                return {'vendor': pick['vendor'], 'renderer': pick['renderer']}
            except Exception:
                return None
        return None

    # If renderer is fixed but vendor is placeholder, infer vendor from DB entry.
    if vendor_is_placeholder and not renderer_is_placeholder:
        try:
            browser_data = WEBGL_CONFIGS.get(normalized_browser, {})
            os_data = browser_data.get(normalized_os)
            if isinstance(os_data, dict):
                for gpu_entries in os_data.values():
                    for entry in gpu_entries:
                        if entry.get('renderer') == renderer_raw:
                            return {'vendor': entry.get('vendor', ''), 'renderer': renderer_raw}
        except Exception:
            return None
        return None

    # Both explicitly selected by user.
    return {'vendor': vendor_raw, 'renderer': renderer_raw}


def generate_profile(config: Dict) -> Dict:
    """
    Generate a single browser profile from config.
    
    Args:
        config: Profile configuration dict with keys:
            - name (str): Profile name
            - os (str): "windows", "macos", or "linux"
            - browser (str): "firefox" or "safari"
            - proxy (dict | None): Proxy config
            - webrtc (bool): Enable WebRTC
            - canvas_noise (bool): Enable canvas noise
            - audio_noise (bool): Enable audio noise
            - fonts_noise (bool): Enable font randomization
            - timezone (str | None): Specific timezone or None for random
            - screen_resolution (dict | None): {"width": int, "height": int} or None
            - webgl (dict | None): {"vendor": str, "renderer": str} or None
    
    Returns:
        Profile dict ready to be saved as JSON
    """
    # Validate required fields
    required = ['name', 'os', 'browser']
    for field in required:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate values
    if config['os'] not in ['windows', 'macos', 'linux']:
        raise ValueError(f"Invalid OS: {config['os']}")
    
    if config['browser'] not in ['firefox', 'safari']:
        raise ValueError(f"Invalid browser: {config['browser']}")
    
    if config['browser'] == 'safari' and config['os'] != 'macos':
        raise ValueError("Safari is only available on macOS")
    
    # Generate fingerprints
    fingerprint = _generate_random_fingerprint()
    
    # Screen resolution
    if config.get('screen_resolution'):
        screen = {
            'width': config['screen_resolution']['width'],
            'height': config['screen_resolution']['height'],
            'availWidth': config['screen_resolution']['width'],
            'availHeight': config['screen_resolution']['height'] - 40,
            'colorDepth': 30 if config['os'] == 'macos' else 24,
            'pixelDepth': 30 if config['os'] == 'macos' else 24,
        }
    else:
        screen = _get_random_screen_resolution(config['os'])
    
    # Timezone
    if config.get('timezone'):
        # Find timezone offset (simplified - would need proper timezone library)
        timezone = config['timezone']
        timezone_offset = -300  # Default EST
        for region_tzs in TIMEZONES.values():
            for tz_name, tz_offset in region_tzs:
                if tz_name == timezone:
                    timezone_offset = tz_offset
                    break
    else:
        timezone, timezone_offset = _get_random_timezone()
    
    # WebGL
    resolved_webgl = _resolve_webgl_selection(config.get('webgl'), config['browser'], config['os'], screen['width'])
    if resolved_webgl:
        webgl_vendor = resolved_webgl['vendor']
        webgl_renderer = resolved_webgl['renderer']
    else:
        webgl_data = get_webgl_for_profile(
            browser=config['browser'],
            os=config['os'],
            screen_width=screen['width']
        )
        webgl_vendor = webgl_data['vendor']
        webgl_renderer = webgl_data['renderer']
    
    # Fonts
    fonts = _get_random_fonts(config['os'])
    
    # User-Agent
    if config['browser'] == 'safari':
        user_agent = USER_AGENTS['safari']['macos']
    else:
        user_agent = USER_AGENTS['firefox'][config['os']]
    
    # Platform
    platform_map = {
        'windows': 'Win32',
        'macos': 'MacIntel',
        'linux': 'Linux x86_64',
    }
    platform = platform_map[config['os']]
    
    # Hardware
    hardware_concurrency = random.choice([4, 8, 12, 16])
    device_memory = random.choice([4, 8, 16])
    
    # DNS config
    webrtc_enabled = config.get('webrtc', False)
    dns_config = _get_dns_config(config['browser'], webrtc_enabled)
    
    # Build profile
    profile = {
        'name': config['name'],
        'description': f"{config['browser'].title()} on {config['os'].title()} - Generated profile",
        'created': datetime.now().strftime('%Y-%m-%d'),
        'version': '1.0',
        'screen': screen,
        'navigator': {
            'userAgent': user_agent,
            'platform': platform,
            'hardwareConcurrency': hardware_concurrency,
            'deviceMemory': device_memory,
            'maxTouchPoints': 0,
            'vendor': 'Apple Computer, Inc.' if config['browser'] == 'safari' else '',
            'language': 'en-US',
            'languages': ['en-US', 'en'],
        },
        'webgl': {
            'vendor': webgl_vendor,
            'renderer': webgl_renderer,
            'extensions': [],  # Simplified for now
            'parameters': {},  # Simplified for now
        },
        'canvas': {
            'noise': _get_canvas_noise_config(fingerprint['canvas_seed'], config['os']) if config.get('canvas_noise', True) else None,
        },
        'dns_config': dns_config,
        'firefox_preferences': _get_firefox_preferences(dns_config, webrtc_enabled),
        'fingerprints': {
            'ja3': '',  # Optional
            'ja4': '',  # Optional
            'akamai_http2': '',  # Optional
            'notes': f"Generated profile for {config['browser']} on {config['os']}",
        },
        'os': config['os'],
        'fingerprint': fingerprint,
        'timezone': timezone,
        'timezoneOffset': timezone_offset,
        'fonts': fonts,
    }
    
    # Add proxy if configured
    if config.get('proxy'):
        profile['proxy'] = config['proxy']
    
    return profile


def generate_bulk_profiles(config: Dict, count: int, prefix: str) -> List[Dict]:
    """
    Generate multiple profiles with randomized fingerprints.
    
    Args:
        config: Base profile configuration (same as generate_profile)
        count: Number of profiles to generate
        prefix: Profile name prefix (e.g., "bulk", "test")
    
    Returns:
        List of profile dicts
    """
    if count < 1 or count > 100:
        raise ValueError("Count must be between 1 and 100")
    
    if not prefix:
        raise ValueError("Prefix cannot be empty")
    
    profiles = []
    for i in range(count):
        # Create config for this profile
        profile_config = config.copy()
        profile_config['name'] = f"{prefix}-{i+1:03d}"
        
        # Randomize fingerprints
        profile_config['screen_resolution'] = None  # Random
        profile_config['timezone'] = None  # Random
        profile_config['webgl'] = None  # Random
        
        # Generate profile
        profile = generate_profile(profile_config)
        profiles.append(profile)
    
    return profiles


def save_profile(profile: Dict, filename: str = None, use_database: bool = True) -> str:
    """
    Save profile to database or legacy JSON file.
    
    Args:
        profile: Profile dict
        filename: Filename for JSON (deprecated, only used if use_database=False)
        use_database: Use database storage (default: True)
    
    Returns:
        Path to database or JSON file
    """
    if use_database:
        # Save to database
        db = ProfileDatabase()
        
        # Delete existing if present
        if db.profile_exists(profile["name"]):
            db.delete_profile(profile["name"])
        
        # Create new profile
        db.create_profile_from_dict(profile)
        return db.db_path
    else:
        # Legacy JSON file storage
        profiles_dir = os.path.join(os.path.dirname(__file__), 'profiles')
        os.makedirs(profiles_dir, exist_ok=True)
        
        filepath = os.path.join(profiles_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        
        return filepath


if __name__ == '__main__':
    # Test profile generation
    test_config = {
        'name': 'test-profile',
        'os': 'windows',
        'browser': 'firefox',
        'proxy': None,
        'webrtc': False,
        'canvas_noise': True,
        'audio_noise': True,
        'fonts_noise': True,
        'timezone': None,
        'screen_resolution': None,
        'webgl': None,
    }
    
    profile = generate_profile(test_config)
    print(json.dumps(profile, indent=2))
