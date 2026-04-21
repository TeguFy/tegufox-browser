"""
WebGL Vendor/Renderer Database
Real-world WebGL strings for Firefox and Safari across different hardware.
Compiled from GitHub fingerprint databases, browser automation repos, and detection systems.
"""

# Firefox sanitizes WebGL strings via SanitizeRenderer.cpp
# See: https://searchfox.org/mozilla-central/source/dom/canvas/SanitizeRenderer.cpp
# Firefox returns generic strings like "GeForce GTX 980, or similar" instead of exact models

WEBGL_CONFIGS = {
    'firefox': {
        'windows': {
            'intel': [
                {'vendor': 'Intel', 'renderer': 'Intel(R) HD Graphics', 'common_on': 'Laptops 2012-2016'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) HD Graphics 4400', 'common_on': 'Laptops 2013-2015'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) HD Graphics 530', 'common_on': 'Desktops 2015-2017'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) HD Graphics 620', 'common_on': 'Laptops 2016-2018'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) HD Graphics 630', 'common_on': 'Desktops 2017-2019'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) UHD Graphics 620', 'common_on': 'Laptops 2018-2020'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) UHD Graphics 630', 'common_on': 'Desktops 2019-2021'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) Iris(R) Xe Graphics', 'common_on': 'Laptops 2020-2023'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) UHD Graphics 770', 'common_on': 'Desktops 2022-2024'},
                {'vendor': 'Intel', 'renderer': 'Intel(R) Arc(TM) Graphics', 'common_on': 'Desktops/laptops 2023-2026'},
            ],
            'nvidia': [
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 750, or similar', 'common_on': 'Budget desktops 2014-2016'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 960, or similar', 'common_on': 'Mid-range desktops 2015-2017'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1050, or similar', 'common_on': 'Budget laptops 2017-2019'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1050 Ti, or similar', 'common_on': 'Budget desktops 2017-2019'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1060, or similar', 'common_on': 'Mid-range 2016-2019'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1650, or similar', 'common_on': 'Budget laptops 2019-2021'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1660, or similar', 'common_on': 'Mid-range 2019-2021'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 2060, or similar', 'common_on': 'Mid-range 2019-2021'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 3060, or similar', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 3070, or similar', 'common_on': 'High-end 2021-2023'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 4060, or similar', 'common_on': 'Mid-range 2023-2025'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 4070, or similar', 'common_on': 'High-end 2023-2026'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 5070, or similar', 'common_on': 'High-end 2025-2026'},
            ],
            'amd': [
                {'vendor': 'AMD', 'renderer': 'Radeon HD 3200 Graphics', 'common_on': 'Old desktops 2008-2012'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon R9 200 Series', 'common_on': 'Mid-range 2013-2016'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 580', 'common_on': 'Mid-range 2017-2020'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 5700', 'common_on': 'High-end 2019-2021'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 6600', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 7600', 'common_on': 'Mid-range 2023-2025'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 7800 XT', 'common_on': 'High-end 2023-2026'},
            ],
        },
        'macos': {
            'intel': [
                {'vendor': 'Intel Inc.', 'renderer': 'Intel(R) Iris(TM) Plus Graphics', 'common_on': 'MacBook Pro 2016-2019'},
                {'vendor': 'Intel Inc.', 'renderer': 'Intel(R) UHD Graphics 630', 'common_on': 'iMac 2017-2020'},
                {'vendor': 'Intel Inc.', 'renderer': 'Intel(R) Iris(TM) Plus Graphics 655', 'common_on': 'MacBook Air 2018-2020'},
            ],
            'amd': [
                {'vendor': 'AMD', 'renderer': 'AMD Radeon Pro 555X', 'common_on': 'MacBook Pro 15" 2018-2019'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon Pro 5300', 'common_on': 'iMac 27" 2019-2020'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon Pro 5500 XT', 'common_on': 'iMac 27" 2020'},
            ],
            'apple': [
                # Apple Silicon Macs (M1/M2/M3) - Firefox on macOS
                {'vendor': 'Apple', 'renderer': 'Apple M1', 'common_on': 'MacBook Air/Pro 2020-2021, Mac Mini 2020, iMac 24" 2021'},
                {'vendor': 'Apple', 'renderer': 'Apple M1 Pro', 'common_on': 'MacBook Pro 14"/16" 2021'},
                {'vendor': 'Apple', 'renderer': 'Apple M1 Max', 'common_on': 'MacBook Pro 14"/16" 2021, Mac Studio 2022'},
                {'vendor': 'Apple', 'renderer': 'Apple M2', 'common_on': 'MacBook Air 2022, MacBook Pro 13" 2022, Mac Mini 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M2 Pro', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Mini 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M2 Max', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Studio 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M3', 'common_on': 'MacBook Pro 14" 2023, iMac 24" 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M3 Pro', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M3 Max', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Apple', 'renderer': 'Apple M4', 'common_on': 'MacBook Pro 2024, Mac Mini 2024'},
                {'vendor': 'Apple', 'renderer': 'Apple M4 Pro', 'common_on': 'MacBook Pro 14"/16" 2024'},
                {'vendor': 'Apple', 'renderer': 'Apple M4 Max', 'common_on': 'MacBook Pro 16" 2024'},
            ],
        },
        'linux': {
            'intel': [
                {'vendor': 'Intel', 'renderer': 'Mesa Intel(R) HD Graphics 620 (KBL GT2)', 'common_on': 'Laptops 2016-2018'},
                {'vendor': 'Intel', 'renderer': 'Mesa Intel(R) UHD Graphics 620 (KBL GT2)', 'common_on': 'Laptops 2018-2020'},
                {'vendor': 'Intel', 'renderer': 'Mesa Intel(R) UHD Graphics 630 (CFL GT2)', 'common_on': 'Desktops 2019-2021'},
                {'vendor': 'Intel', 'renderer': 'Mesa Intel(R) Iris(R) Xe Graphics (TGL GT2)', 'common_on': 'Laptops 2020-2023'},
            ],
            'nvidia': [
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1050/PCIe/SSE2', 'common_on': 'Budget laptops 2017-2019'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce GTX 1650/PCIe/SSE2', 'common_on': 'Budget laptops 2019-2021'},
                {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA GeForce RTX 3060/PCIe/SSE2', 'common_on': 'Mid-range 2021-2023'},
            ],
            'amd': [
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 580 Series (POLARIS10, DRM 3.35.0, 5.4.0, LLVM 11.0.0)', 'common_on': 'Mid-range 2017-2020'},
                {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 6600 (NAVI23, DRM 3.42.0, 5.15.0, LLVM 13.0.1)', 'common_on': 'Mid-range 2021-2023'},
            ],
        },
    },
    'safari': {
        'macos': {
            'intel': [
                # Safari on Intel Macs - WebKit masks as "WebKit WebGL" but unmasked shows real GPU
                {'vendor': 'Intel Inc.', 'renderer': 'Intel(R) Iris(TM) Plus Graphics OpenGL Engine', 'common_on': 'MacBook Pro 2016-2019'},
                {'vendor': 'Intel Inc.', 'renderer': 'Intel(R) UHD Graphics 630 OpenGL Engine', 'common_on': 'iMac 2017-2020'},
                {'vendor': 'ATI Technologies Inc.', 'renderer': 'AMD Radeon Pro 555X OpenGL Engine', 'common_on': 'MacBook Pro 15" 2018-2019'},
                {'vendor': 'ATI Technologies Inc.', 'renderer': 'AMD Radeon Pro 5300 OpenGL Engine', 'common_on': 'iMac 27" 2019-2020'},
            ],
            'apple': [
                # Safari on Apple Silicon - masks as "Apple GPU" (iOS 12.2+ behavior)
                # Unmasked renderer shows "Apple M1", "Apple M2", etc.
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M1', 'common_on': 'MacBook Air/Pro 2020-2021, Mac Mini 2020, iMac 24" 2021'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M1 Pro', 'common_on': 'MacBook Pro 14"/16" 2021'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M1 Max', 'common_on': 'MacBook Pro 14"/16" 2021, Mac Studio 2022'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M2', 'common_on': 'MacBook Air 2022, MacBook Pro 13" 2022, Mac Mini 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M2 Pro', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Mini 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M2 Max', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Studio 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M3', 'common_on': 'MacBook Pro 14" 2023, iMac 24" 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M3 Pro', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M3 Max', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M4', 'common_on': 'MacBook Pro 2024, Mac Mini 2024'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M4 Pro', 'common_on': 'MacBook Pro 14"/16" 2024'},
                {'vendor': 'Apple Inc.', 'renderer': 'Apple M4 Max', 'common_on': 'MacBook Pro 16" 2024'},
            ],
        },
        'ios': [
            # Safari on iOS - always returns "Apple GPU" (obfuscated since iOS 12.2)
            {'vendor': 'Apple Inc.', 'renderer': 'Apple GPU', 'common_on': 'All iOS devices (iPhone, iPad) iOS 12.2+'},
        ],
    },
    # Chrome uses ANGLE (Almost Native Graphics Layer Engine) wrapper
    # Format: "ANGLE (Vendor, Renderer Direct3D11 vs_5_0 ps_5_0, D3D11)" on Windows
    # Format: "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)" on macOS
    'chrome': {
        'windows': {
            'intel': [
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Laptops 2016-2018'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Desktops 2017-2019'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Laptops 2018-2020'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Desktops 2019-2021'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Laptops 2020-2023'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Desktops 2022-2024'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Desktops 2023-2026'},
            ],
            'nvidia': [
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.9729)', 'common_on': 'Budget desktops 2017-2019'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'Mid-range 2016-2019'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.7208)', 'common_on': 'Budget laptops 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'Mid-range 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15.1179)', 'common_on': 'Mid-range 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'Mid-range 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.7280)', 'common_on': 'High-end 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'High-end 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5751)', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15.1179)', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'High-end 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.9729)', 'common_on': 'High-end 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)', 'common_on': 'High-end 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15.1179)', 'common_on': 'Mid-range 2023-2025'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15.1179)', 'common_on': 'Mid-range 2023-2025'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15.1179)', 'common_on': 'High-end 2023-2025'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 5070 Direct3D11 vs_5_0 ps_5_0, D3D11-32.0.15.6109)', 'common_on': 'High-end 2025-2026'},
            ],
            'amd': [
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Mid-range 2017-2020'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 5700 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'High-end 2019-2021'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'High-end 2019-2021'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'High-end 2021-2023'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'Mid-range 2023-2025'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 7700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'High-end 2023-2025'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 7800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)', 'common_on': 'High-end 2023-2026'},
            ],
        },
        'macos': {
            'intel': [
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, ANGLE Metal Renderer: Intel(R) Iris(TM) Plus Graphics, Unspecified Version)', 'common_on': 'MacBook Pro 2016-2019'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, ANGLE Metal Renderer: Intel(R) UHD Graphics 630, Unspecified Version)', 'common_on': 'iMac 2017-2020'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, ANGLE Metal Renderer: Intel(R) Iris(TM) Plus Graphics 655, Unspecified Version)', 'common_on': 'MacBook Air 2018-2020'},
            ],
            'amd': [
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, ANGLE Metal Renderer: AMD Radeon Pro 555X, Unspecified Version)', 'common_on': 'MacBook Pro 15" 2018-2019'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, ANGLE Metal Renderer: AMD Radeon Pro 5300, Unspecified Version)', 'common_on': 'iMac 27" 2019-2020'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, ANGLE Metal Renderer: AMD Radeon Pro 5500 XT, Unspecified Version)', 'common_on': 'iMac 27" 2020'},
            ],
            'apple': [
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)', 'common_on': 'MacBook Air/Pro 2020-2021, Mac Mini 2020, iMac 24" 2021'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M1 Pro, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2021'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M1 Max, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2021, Mac Studio 2022'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)', 'common_on': 'MacBook Air 2022, MacBook Pro 13" 2022, Mac Mini 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Mini 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Max, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2023, Mac Studio 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)', 'common_on': 'MacBook Pro 14" 2023, iMac 24" 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M3 Pro, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M3 Max, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2023'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M4, Unspecified Version)', 'common_on': 'MacBook Pro 2024, Mac Mini 2024'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M4 Pro, Unspecified Version)', 'common_on': 'MacBook Pro 14"/16" 2024'},
                {'vendor': 'Google Inc. (Apple)', 'renderer': 'ANGLE (Apple, ANGLE Metal Renderer: Apple M4 Max, Unspecified Version)', 'common_on': 'MacBook Pro 16" 2024'},
            ],
        },
        'linux': {
            'intel': [
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Mesa Intel(R) HD Graphics 620 (KBL GT2), OpenGL 4.6)', 'common_on': 'Laptops 2016-2018'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6)', 'common_on': 'Laptops 2018-2020'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Mesa Intel(R) UHD Graphics 630 (CFL GT2), OpenGL 4.6)', 'common_on': 'Desktops 2019-2021'},
                {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Mesa Intel(R) Iris(R) Xe Graphics (TGL GT2), OpenGL 4.6)', 'common_on': 'Laptops 2020-2023'},
            ],
            'nvidia': [
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050/PCIe/SSE2, OpenGL 4.6.0)', 'common_on': 'Budget laptops 2017-2019'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650/PCIe/SSE2, OpenGL 4.6.0)', 'common_on': 'Budget laptops 2019-2021'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060/PCIe/SSE2, OpenGL 4.6.0)', 'common_on': 'Mid-range 2021-2023'},
                {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4060/PCIe/SSE2, OpenGL 4.6.0)', 'common_on': 'Mid-range 2023-2025'},
            ],
            'amd': [
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 580 Series (POLARIS10, DRM 3.35.0, 5.4.0, LLVM 11.0.0), OpenGL 4.6)', 'common_on': 'Mid-range 2017-2020'},
                {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 6600 (NAVI23, DRM 3.42.0, 5.15.0, LLVM 13.0.1), OpenGL 4.6)', 'common_on': 'Mid-range 2021-2023'},
            ],
        },
    },
}

def get_random_webgl(browser: str, os: str, gpu_vendor: str = None) -> dict:
    """
    Get a random WebGL vendor/renderer pair for the given browser/OS/GPU combination.
    
    Args:
        browser: 'firefox' or 'safari'
        os: 'windows', 'macos', 'linux', 'ios'
        gpu_vendor: 'intel', 'nvidia', 'amd', 'apple', or None (random)
    
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
    
    # Handle iOS (list) vs other OS (dict)
    if isinstance(os_configs, list):
        configs = os_configs
    elif gpu_vendor:
        gpu_vendor = gpu_vendor.lower()
        if gpu_vendor not in os_configs:
            raise ValueError(f"GPU vendor '{gpu_vendor}' not available for {browser}/{os}")
        configs = os_configs[gpu_vendor]
    else:
        # Random vendor
        all_configs = []
        for vendor_configs in os_configs.values():
            all_configs.extend(vendor_configs)
        configs = all_configs
    
    if not configs:
        raise ValueError(f"No WebGL configs available for {browser}/{os}/{gpu_vendor}")
    
    config = random.choice(configs)
    return {
        'vendor': config['vendor'],
        'renderer': config['renderer'],
        'common_on': config.get('common_on', 'Unknown')
    }


def get_webgl_for_profile(browser: str, os: str, screen_width: int = None) -> dict:
    """
    Get appropriate WebGL config based on browser, OS, and screen resolution.
    
    Heuristics:
    - macOS + high resolution (>= 2560) → likely Apple Silicon or high-end Intel/AMD
    - macOS + medium resolution → Intel integrated
    - Windows + high resolution → likely NVIDIA/AMD discrete GPU
    - Windows + medium resolution → Intel integrated
    - Linux → Mesa drivers
    
    Args:
        browser: Browser name (e.g., 'firefox', 'firefox-120', 'safari', 'safari-17', 'chrome', 'chrome-144')
        os: Operating system ('windows', 'macos', 'linux', 'ios')
        screen_width: Screen width in pixels (optional, used for heuristics)
    """
    import random
    
    os = os.lower()
    browser = browser.lower()
    
    # Normalize browser name (strip version number)
    # 'firefox-120' → 'firefox', 'safari-17' → 'safari', 'chrome-144' → 'chrome'
    if '-' in browser:
        browser = browser.split('-')[0]
    
    if browser == 'safari':
        if os == 'macos':
            # Safari on macOS
            if screen_width and screen_width >= 2560:
                # High-res display → likely Apple Silicon or high-end
                if random.random() < 0.7:  # 70% chance Apple Silicon
                    return get_random_webgl('safari', 'macos', 'apple')
                else:
                    return get_random_webgl('safari', 'macos', 'intel')
            else:
                # Medium-res → Intel or older AMD
                return get_random_webgl('safari', 'macos', random.choice(['intel', 'apple']))
        elif os == 'ios':
            return get_random_webgl('safari', 'ios')
    
    elif browser == 'firefox':
        if os == 'macos':
            # Firefox on macOS
            if screen_width and screen_width >= 2560:
                # High-res → Apple Silicon or high-end
                if random.random() < 0.6:
                    return get_random_webgl('firefox', 'macos', 'apple')
                else:
                    return get_random_webgl('firefox', 'macos', random.choice(['intel', 'amd']))
            else:
                return get_random_webgl('firefox', 'macos', random.choice(['intel', 'apple']))
        
        elif os == 'windows':
            # Firefox on Windows
            if screen_width and screen_width >= 1920:
                # High-res → likely discrete GPU
                return get_random_webgl('firefox', 'windows', random.choice(['nvidia', 'amd']))
            else:
                # Medium-res → Intel integrated
                return get_random_webgl('firefox', 'windows', 'intel')
        
        elif os == 'linux':
            # Firefox on Linux
            return get_random_webgl('firefox', 'linux', random.choice(['intel', 'nvidia', 'amd']))
    
    elif browser == 'chrome':
        if os == 'macos':
            # Chrome on macOS
            if screen_width and screen_width >= 2560:
                # High-res → Apple Silicon or high-end
                if random.random() < 0.7:
                    return get_random_webgl('chrome', 'macos', 'apple')
                else:
                    return get_random_webgl('chrome', 'macos', random.choice(['intel', 'amd']))
            else:
                return get_random_webgl('chrome', 'macos', random.choice(['intel', 'apple']))
        
        elif os == 'windows':
            # Chrome on Windows
            if screen_width and screen_width >= 1920:
                # High-res → likely discrete GPU
                return get_random_webgl('chrome', 'windows', random.choice(['nvidia', 'amd']))
            else:
                # Medium-res → Intel integrated
                return get_random_webgl('chrome', 'windows', 'intel')
        
        elif os == 'linux':
            # Chrome on Linux
            return get_random_webgl('chrome', 'linux', random.choice(['intel', 'nvidia', 'amd']))
    
    # Fallback
    return get_random_webgl(browser, os)


if __name__ == '__main__':
    # Test
    print("=== Firefox on Windows (1920x1080) ===")
    for _ in range(3):
        config = get_webgl_for_profile('firefox', 'windows', 1920)
        print(f"  {config['vendor']} / {config['renderer']}")
    
    print("\n=== Firefox on macOS (2560x1600) ===")
    for _ in range(3):
        config = get_webgl_for_profile('firefox', 'macos', 2560)
        print(f"  {config['vendor']} / {config['renderer']}")
    
    print("\n=== Safari on macOS (3072x1920) ===")
    for _ in range(3):
        config = get_webgl_for_profile('safari', 'macos', 3072)
        print(f"  {config['vendor']} / {config['renderer']}")
    
    print("\n=== Safari on iOS ===")
    config = get_webgl_for_profile('safari', 'ios')
    print(f"  {config['vendor']} / {config['renderer']}")
