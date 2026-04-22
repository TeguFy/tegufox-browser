"""
WebGL Vendor/Renderer selection and normalization logic.

Dataset entries live in `webgl_dataset.py` so they can be updated independently.
"""

import re
from typing import Any, Dict, List

try:
    from .webgl_dataset import WEBGL_CONFIGS
except ImportError:
    from webgl_dataset import WEBGL_CONFIGS

_SOFTWARE_RENDERER_KEYWORDS = (
    "swiftshader",
    "llvmpipe",
    "softpipe",
    "microsoft basic render",
    "software rasterizer",
)


def _normalize_renderer(renderer: str) -> str:
    """Normalize renderer strings to keep concrete GPU model names."""
    normalized = renderer.replace(", or similar", "")
    normalized = normalized.replace("AMD Radeon R9 200 Series", "AMD Radeon R9 270")
    normalized = normalized.replace("AMD Radeon R7 200 Series", "AMD Radeon R7 270")
    normalized = normalized.replace("AMD Radeon RX 580 Series", "AMD Radeon RX 580")
    normalized = re.sub(r"(AMD Radeon (?:R[0-9]\s+[0-9]{3}|RX\s*[0-9]{3,4}(?:\s+XT)?))\s+Series", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _is_software_renderer(renderer: str) -> bool:
    """Detect software/fallback renderers that are low realism for normal profiles."""
    lowered = (renderer or "").lower()
    return any(token in lowered for token in _SOFTWARE_RENDERER_KEYWORDS)


def _extract_end_year(common_on: str) -> int:
    """Extract end-year from strings like '2019-2021' for weighted selection."""
    years = re.findall(r"(\d{4})", common_on or "")
    if not years:
        return 2020
    if len(years) >= 2:
        return int(years[-1])
    return int(years[0])


def _get_entry_weight(common_on: str, current_year: int = 2026) -> float:
    """Give newer hardware higher probability while keeping older options possible."""
    end_year = _extract_end_year(common_on)
    age = max(0, current_year - end_year)
    if age <= 2:
        return 6.0
    if age <= 5:
        return 4.0
    if age <= 8:
        return 2.0
    return 1.0


def get_random_webgl(
    browser: str, os: str, gpu_vendor: str = None, allow_software: bool = False
) -> Dict[str, str]:
    """
    Get a random WebGL vendor/renderer pair for the given browser/OS/GPU combination.

    Args:
        browser: 'firefox', 'safari', or 'chrome'
        os: 'windows', 'macos', 'linux', 'ios'
        gpu_vendor: 'intel', 'nvidia', 'amd', 'apple', or None (random)
        allow_software: keep software fallback renderers like SwiftShader/llvmpipe

    Returns:
        dict with 'vendor' and 'renderer' keys
    """
    import random

    browser = browser.lower()
    os = os.lower()

    if browser not in WEBGL_CONFIGS:
        raise ValueError(f"Unknown browser: {browser}")

    if os not in WEBGL_CONFIGS[browser]:
        raise ValueError(f"OS '{os}' not supported for browser '{browser}'")

    os_configs = WEBGL_CONFIGS[browser][os]

    if isinstance(os_configs, list):
        configs = os_configs
    elif gpu_vendor:
        gpu_vendor = gpu_vendor.lower()
        if gpu_vendor not in os_configs:
            raise ValueError(f"GPU vendor '{gpu_vendor}' not available for {browser}/{os}")
        configs = os_configs[gpu_vendor]
    else:
        all_configs: List[Dict[str, Any]] = []
        for vendor_configs in os_configs.values():
            all_configs.extend(vendor_configs)
        configs = all_configs

    if not configs:
        raise ValueError(f"No WebGL configs available for {browser}/{os}/{gpu_vendor}")

    if not allow_software:
        filtered = [cfg for cfg in configs if not _is_software_renderer(cfg.get("renderer", ""))]
        if filtered:
            configs = filtered

    weights = [_get_entry_weight(cfg.get("common_on", "")) for cfg in configs]
    config = random.choices(configs, weights=weights, k=1)[0]
    renderer = _normalize_renderer(config["renderer"])

    return {
        "vendor": config["vendor"],
        "renderer": renderer,
        "common_on": config.get("common_on", "Unknown"),
    }


def get_webgl_for_profile(browser: str, os: str, screen_width: int = None) -> Dict[str, str]:
    """
    Get appropriate WebGL config based on browser, OS, and screen resolution.

    Heuristics:
    - macOS + high resolution (>= 2560) -> likely Apple Silicon or high-end Intel/AMD
    - Windows + high resolution (>= 1920) -> likely NVIDIA/AMD discrete GPU
    - Linux -> mixed Mesa/NVIDIA/AMD
    """
    import random

    os = os.lower()
    browser = browser.lower()

    if "-" in browser:
        browser = browser.split("-")[0]

    if browser == "safari":
        if os == "macos":
            if screen_width and screen_width >= 2560:
                if random.random() < 0.7:
                    return get_random_webgl("safari", "macos", "apple")
                return get_random_webgl("safari", "macos", "intel")
            return get_random_webgl("safari", "macos", random.choice(["intel", "apple"]))
        if os == "ios":
            return get_random_webgl("safari", "ios")

    elif browser == "firefox":
        if os == "macos":
            if screen_width and screen_width >= 2560:
                if random.random() < 0.6:
                    return get_random_webgl("firefox", "macos", "apple")
                return get_random_webgl("firefox", "macos", random.choice(["intel", "amd"]))
            return get_random_webgl("firefox", "macos", random.choice(["intel", "apple"]))
        if os == "windows":
            if screen_width and screen_width >= 1920:
                return get_random_webgl("firefox", "windows", random.choice(["nvidia", "amd"]))
            return get_random_webgl("firefox", "windows", "intel")
        if os == "linux":
            return get_random_webgl("firefox", "linux", random.choice(["intel", "nvidia", "amd"]))

    elif browser == "chrome":
        if os == "macos":
            if screen_width and screen_width >= 2560:
                if random.random() < 0.7:
                    return get_random_webgl("chrome", "macos", "apple")
                return get_random_webgl("chrome", "macos", random.choice(["intel", "amd"]))
            return get_random_webgl("chrome", "macos", random.choice(["intel", "apple"]))
        if os == "windows":
            if screen_width and screen_width >= 1920:
                return get_random_webgl("chrome", "windows", random.choice(["nvidia", "amd"]))
            return get_random_webgl("chrome", "windows", "intel")
        if os == "linux":
            return get_random_webgl("chrome", "linux", random.choice(["intel", "nvidia", "amd"]))

    return get_random_webgl(browser, os)


if __name__ == "__main__":
    print("=== Firefox on Windows (1920x1080) ===")
    for _ in range(3):
        config = get_webgl_for_profile("firefox", "windows", 1920)
        print(f"  {config['vendor']} / {config['renderer']}")

    print("\n=== Firefox on macOS (2560x1600) ===")
    for _ in range(3):
        config = get_webgl_for_profile("firefox", "macos", 2560)
        print(f"  {config['vendor']} / {config['renderer']}")

    print("\n=== Safari on macOS (3072x1920) ===")
    for _ in range(3):
        config = get_webgl_for_profile("safari", "macos", 3072)
        print(f"  {config['vendor']} / {config['renderer']}")

    print("\n=== Safari on iOS ===")
    config = get_webgl_for_profile("safari", "ios")
    print(f"  {config['vendor']} / {config['renderer']}")
