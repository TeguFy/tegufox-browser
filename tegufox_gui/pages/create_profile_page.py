"""Create profile page widget"""

import random
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QRadioButton,
    QTextEdit,
    QGroupBox,
    QGridLayout,
    QTabWidget,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from tegufox_gui.utils.styles import DarkPalette

# ---------------------------------------------------------------------------

_CREATE_ADJ = [
    "swift", "brave", "dark", "quiet", "sharp", "lucky", "cold", "iron",
    "bold",  "free",  "calm", "keen",  "wild",  "fast",  "cool", "deep",
    "slim",  "wise",  "blue", "grey",  "jade",  "void",  "nova", "echo",
]
_CREATE_NOUN = [
    "fox",  "hawk", "wolf", "bear", "deer", "lion", "crow", "seal",
    "pike", "monk", "sage", "duke", "flux", "reef", "vale", "zeal",
    "beam", "crab", "lynx", "mink",
]

# browser display label -> profile_manager key
_BROWSER_KEY = {
    "Firefox 115": "firefox",
    "Safari 17":   "safari",
}
_OS_LIST = ["Windows", "macOS", "Linux"]
_OS_KEY  = {"Windows": "windows", "macOS": "macos", "Linux": "linux"}
_OS_PLATFORM = {
    "Windows": "Win32",
    "macOS":   "MacIntel",
    "Linux":   "Linux x86_64",
}
_DOH_OPTIONS = ["cloudflare", "quad9", "mullvad"]
# Realistic concurrency pool per OS
_CONCURRENCY = {"Windows": [4, 6, 8, 12, 16], "macOS": [8, 10, 12, 14], "Linux": [4, 8, 16, 32]}
_SCREEN_BY_OS = {
    "Windows": [(1920, 1080), (1366, 768), (2560, 1440), (1536, 864)],
    "macOS":   [(2560, 1600), (1440, 900), (3024, 1964), (1920, 1080)],
    "Linux":   [(1920, 1080), (2560, 1440), (1366, 768)],
}


def _random_name() -> str:
    return f"{random.choice(_CREATE_ADJ)}-{random.choice(_CREATE_NOUN)}-{random.randint(10,99)}"


class CreateProfileWidget(QWidget):
    """Create profiles page - wraps ProfileCreatorDialog"""

    profile_created = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI by embedding ProfileCreatorDialog"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the dialog as a widget (not a popup)
        self.creator = ProfileCreatorDialog(self)
        
        # Connect its signal to ours
        self.creator.profileCreated.connect(self.profile_created.emit)
        
        layout.addWidget(self.creator)




class ProfileCreatorDialog(QWidget):
    """Profile Creator Dialog with 3 tabs: Network, Hardware, Bulk Creation"""
    
    profileCreated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Profiles")
        self.setMinimumSize(900, 600)  # Allow resizing instead of fixed size
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_ui(self):
        """Setup the UI with 3 tabs"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Create Profiles")
        title.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {DarkPalette.TEXT};")
        layout.addWidget(title)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DarkPalette.BORDER};
                
                background-color: {DarkPalette.CARD};
            }}
            QTabBar::tab {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT_DIM};
                padding: 10px 20px;
                border: 1px solid {DarkPalette.BORDER};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.ACCENT};
                font-weight: 600;
            }}
            QTabBar::tab:hover {{
                background-color: {DarkPalette.HOVER};
            }}
        """)
        
        # Create tabs
        self.overview_tab = self._create_overview_tab()
        self.network_tab = self._create_network_tab()
        self.hardware_tab = self._create_hardware_tab()
        self.advanced_tab = self._create_advanced_tab()
        self.cookies_tab = self._create_cookies_tab()
        self.url_tab = self._create_url_tab()
        self.variables_tab = self._create_variables_tab()
        
        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.network_tab, "Network")
        self.tabs.addTab(self.hardware_tab, "Hardware")
        self.tabs.addTab(self.advanced_tab, "Advanced")
        self.tabs.addTab(self.cookies_tab, "Cookies")
        self.tabs.addTab(self.url_tab, "URL")
        self.tabs.addTab(self.variables_tab, "Variables")
        
        layout.addWidget(self.tabs)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        
        # Reset button on the left
        reset_btn = QPushButton("Reset")
        reset_btn.setFixedHeight(36)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.TEXT_DIM};
                border: 1px solid {DarkPalette.BORDER};
                padding: 6px 24px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        reset_btn.clicked.connect(self._reset_form)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        
        # Random button
        random_btn = QPushButton("🎲 Random")
        random_btn.setFixedHeight(36)
        random_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                padding: 6px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        random_btn.clicked.connect(self._randomize_all)
        btn_layout.addWidget(random_btn)
        
        # Create Profile button
        self.create_btn = QPushButton("Create Profile")
        self.create_btn.setFixedHeight(36)
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white;
                border: none;
                padding: 6px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        self.create_btn.clicked.connect(self._create_profile)
        btn_layout.addWidget(self.create_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_overview_tab(self):
        """Create Overview tab with profile name and basic settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(20)  # Increased spacing
        
        # Profile name
        name_group = QGroupBox("Profile Name")
        name_group.setStyleSheet(self._groupbox_style())
        name_layout = QVBoxLayout(name_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., my-profile")
        self.name_input.setStyleSheet(self._input_style())
        self.name_input.setMinimumHeight(40)  # Better height
        name_layout.addWidget(self.name_input)
        layout.addWidget(name_group)
        
        # OS and Browser
        os_browser_group = QGroupBox("Operating System & Browser")
        os_browser_group.setStyleSheet(self._groupbox_style())
        os_browser_layout = QGridLayout(os_browser_group)
        os_browser_layout.setSpacing(15)  # Better spacing
        
        os_label = QLabel("OS:")
        os_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px;")
        os_browser_layout.addWidget(os_label, 0, 0)
        self.os_combo = QComboBox()
        self.os_combo.addItems(["Windows", "macOS", "Linux"])
        self.os_combo.setStyleSheet(self._combo_style())
        self.os_combo.setMinimumHeight(40)
        self.os_combo.currentTextChanged.connect(self._on_os_changed)
        os_browser_layout.addWidget(self.os_combo, 0, 1)
        
        browser_label = QLabel("Browser:")
        browser_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px;")
        os_browser_layout.addWidget(browser_label, 1, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Firefox", "Safari"])
        self.browser_combo.setStyleSheet(self._combo_style())
        self.browser_combo.setMinimumHeight(40)
        os_browser_layout.addWidget(self.browser_combo, 1, 1)
        
        layout.addWidget(os_browser_group)
        layout.addStretch()
        
        return widget
    
    def _create_network_tab(self):
        """Create Network tab matching screenshot layout"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(20)  # Increased spacing
        
        # Proxy type dropdown
        proxy_type_layout = QVBoxLayout()
        proxy_type_label = QLabel("Proxy type")
        proxy_type_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        proxy_type_layout.addWidget(proxy_type_label)
        
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["SOCKS5 Proxy", "HTTP Proxy", "No Proxy"])
        self.proxy_type_combo.setStyleSheet(self._combo_style())
        self.proxy_type_combo.setMinimumHeight(40)  # Better height
        proxy_type_layout.addWidget(self.proxy_type_combo)
        layout.addLayout(proxy_type_layout)
        
        # Proxy IP and Port (side by side)
        proxy_row1 = QHBoxLayout()
        proxy_row1.setSpacing(15)  # Better spacing
        
        proxy_ip_layout = QVBoxLayout()
        proxy_ip_label = QLabel("Proxy IP")
        proxy_ip_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        proxy_ip_layout.addWidget(proxy_ip_label)
        self.proxy_host_input = QLineEdit()
        self.proxy_host_input.setPlaceholderText("Proxy IP")
        self.proxy_host_input.setStyleSheet(self._input_style())
        self.proxy_host_input.setMinimumHeight(40)
        proxy_ip_layout.addWidget(self.proxy_host_input)
        proxy_row1.addLayout(proxy_ip_layout, 3)  # 3:1 ratio
        
        proxy_port_layout = QVBoxLayout()
        proxy_port_label = QLabel("Proxy port")
        proxy_port_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        proxy_port_layout.addWidget(proxy_port_label)
        self.proxy_port_input = QLineEdit()
        self.proxy_port_input.setPlaceholderText("Proxy port")
        self.proxy_port_input.setStyleSheet(self._input_style())
        self.proxy_port_input.setMinimumHeight(40)
        proxy_port_layout.addWidget(self.proxy_port_input)
        proxy_row1.addLayout(proxy_port_layout, 1)
        
        layout.addLayout(proxy_row1)
        
        # Proxy user and Password (side by side)
        proxy_row2 = QHBoxLayout()
        proxy_row2.setSpacing(15)
        
        proxy_user_layout = QVBoxLayout()
        proxy_user_label = QLabel("Proxy user")
        proxy_user_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        proxy_user_layout.addWidget(proxy_user_label)
        self.proxy_user_input = QLineEdit()
        self.proxy_user_input.setPlaceholderText("Proxy user")
        self.proxy_user_input.setStyleSheet(self._input_style())
        self.proxy_user_input.setMinimumHeight(40)
        proxy_user_layout.addWidget(self.proxy_user_input)
        proxy_row2.addLayout(proxy_user_layout)
        
        proxy_pass_layout = QVBoxLayout()
        proxy_pass_label = QLabel("Proxy password")
        proxy_pass_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        proxy_pass_layout.addWidget(proxy_pass_label)
        self.proxy_pass_input = QLineEdit()
        self.proxy_pass_input.setPlaceholderText("Proxy password")
        self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_pass_input.setStyleSheet(self._input_style())
        self.proxy_pass_input.setMinimumHeight(40)
        proxy_pass_layout.addWidget(self.proxy_pass_input)
        proxy_row2.addLayout(proxy_pass_layout)
        
        layout.addLayout(proxy_row2)
        
        # Bottom row: WebRTC, IPv4/6, Location, Timezone, Lat/Long
        # Split into two rows for better responsive layout
        bottom_row1 = QHBoxLayout()
        bottom_row1.setSpacing(15)
        
        # WebRTC combo
        webrtc_layout = QVBoxLayout()
        webrtc_label = QLabel("WebRTC")
        webrtc_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        webrtc_layout.addWidget(webrtc_label)
        self.webrtc_combo = QComboBox()
        self.webrtc_combo.addItems(["Default", "Disabled", "Enabled"])
        self.webrtc_combo.setStyleSheet(self._combo_style())
        self.webrtc_combo.setMinimumHeight(40)
        webrtc_layout.addWidget(self.webrtc_combo)
        bottom_row1.addLayout(webrtc_layout)
        
        # Masked IPv4
        ipv4_layout = QVBoxLayout()
        ipv4_label = QLabel("Masked IPv4")
        ipv4_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        ipv4_layout.addWidget(ipv4_label)
        self.ipv4_input = QLineEdit()
        self.ipv4_input.setPlaceholderText("Leave empty for auto matching")
        self.ipv4_input.setStyleSheet(self._input_style())
        self.ipv4_input.setMinimumHeight(40)
        ipv4_layout.addWidget(self.ipv4_input)
        bottom_row1.addLayout(ipv4_layout)
        
        # Masked IPv6
        ipv6_layout = QVBoxLayout()
        ipv6_label = QLabel("Masked IPv6")
        ipv6_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        ipv6_layout.addWidget(ipv6_label)
        self.ipv6_input = QLineEdit()
        self.ipv6_input.setPlaceholderText("Leave empty for auto matching")
        self.ipv6_input.setStyleSheet(self._input_style())
        self.ipv6_input.setMinimumHeight(40)
        ipv6_layout.addWidget(self.ipv6_input)
        bottom_row1.addLayout(ipv6_layout)
        
        layout.addLayout(bottom_row1)
        
        # Second bottom row
        bottom_row2 = QHBoxLayout()
        bottom_row2.setSpacing(15)
        
        # Location input
        location_layout = QVBoxLayout()
        location_label = QLabel("Location")
        location_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        location_layout.addWidget(location_label)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Auto matching")
        self.location_input.setStyleSheet(self._input_style())
        self.location_input.setMinimumHeight(40)
        location_layout.addWidget(self.location_input)
        bottom_row2.addLayout(location_layout)
        
        # Timezone dropdown
        tz_layout = QVBoxLayout()
        tz_label = QLabel("Timezone")
        tz_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        tz_layout.addWidget(tz_label)
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems([
            "Auto matching",
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Asia/Shanghai",
        ])
        self.timezone_combo.setStyleSheet(self._combo_style())
        self.timezone_combo.setMinimumHeight(40)
        tz_layout.addWidget(self.timezone_combo)
        bottom_row2.addLayout(tz_layout)
        
        # Latitude
        lat_layout = QVBoxLayout()
        lat_label = QLabel("Latitude")
        lat_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        lat_layout.addWidget(lat_label)
        self.latitude_input = QLineEdit()
        self.latitude_input.setPlaceholderText("34.000000")
        self.latitude_input.setStyleSheet(self._input_style())
        self.latitude_input.setMinimumHeight(40)
        lat_layout.addWidget(self.latitude_input)
        bottom_row2.addLayout(lat_layout)
        
        # Longitude
        long_layout = QVBoxLayout()
        long_label = QLabel("Longitude")
        long_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        long_layout.addWidget(long_label)
        self.longitude_input = QLineEdit()
        self.longitude_input.setPlaceholderText("-89.500000")
        self.longitude_input.setStyleSheet(self._input_style())
        self.longitude_input.setMinimumHeight(40)
        long_layout.addWidget(self.longitude_input)
        bottom_row2.addLayout(long_layout)
        
        layout.addLayout(bottom_row2)
        layout.addStretch()
        
        return widget
    
    def _create_hardware_tab(self):
        """Create Hardware tab with grid layout matching screenshot"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {DarkPalette.BACKGROUND}; }}")
        
        content = QWidget()
        layout = QGridLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(20)  # Increased spacing
        
        # Define fingerprint options (4 columns)
        options = [
            ("Canvas", "canvas"),
            ("Audio Context", "audio_context"),
            ("Client Rects", "client_rects"),
            ("Voice", "voice"),
            ("Media Devices", "media_devices"),
            ("Fonts", "fonts"),
            ("Window", "window"),
            ("SVG", "svg"),
            ("Text Metrics", "text_metrics"),
            ("Navigator", "navigator"),
            ("HTTP/2 Fingerprint", "http2"),
            ("SSL/TLS Fingerprint", "ssl_tls"),
            ("Web GPU", "webgpu"),
        ]
        
        # Store radio buttons
        self.hardware_options = {}
        
        row = 0
        col = 0
        for label, key in options:
            # Create group for each option
            group_widget = QWidget()
            group_layout = QVBoxLayout(group_widget)
            group_layout.setContentsMargins(15, 15, 15, 15)  # Better padding
            group_layout.setSpacing(8)
            group_widget.setMinimumHeight(80)  # Minimum height for consistency
            group_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {DarkPalette.CARD};
                    border: 1px solid {DarkPalette.BORDER};
                    
                }}
            """)
            
            # Label
            option_label = QLabel(label)
            option_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 13px;")
            group_layout.addWidget(option_label)
            
            # Radio buttons
            radio_layout = QHBoxLayout()
            default_radio = QRadioButton("Default")
            default_radio.setChecked(True)
            default_radio.setStyleSheet(self._radio_style())
            noise_radio = QRadioButton("Noise")
            noise_radio.setStyleSheet(self._radio_style())
            
            radio_layout.addWidget(default_radio)
            radio_layout.addWidget(noise_radio)
            radio_layout.addStretch()
            group_layout.addLayout(radio_layout)
            
            # Store references
            self.hardware_options[key] = (default_radio, noise_radio)
            
            layout.addWidget(group_widget, row, col)
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        # WebGL toggle and dropdowns (full width)
        webgl_widget = QWidget()
        webgl_layout = QHBoxLayout(webgl_widget)
        webgl_layout.setContentsMargins(15, 15, 15, 15)
        webgl_widget.setMinimumHeight(80)
        webgl_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        webgl_label = QLabel("WebGL")
        webgl_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 13px;")
        webgl_layout.addWidget(webgl_label)
        
        self.webgl_toggle = QCheckBox()
        self.webgl_toggle.setChecked(True)
        self.webgl_toggle.setStyleSheet(self._toggle_style())
        webgl_layout.addWidget(self.webgl_toggle)
        webgl_layout.addStretch()
        
        layout.addWidget(webgl_widget, row, col, 1, 4 - col if col > 0 else 4)
        row += 1
        
        # Vendor and Renderer dropdowns (side by side)
        vendor_widget = QWidget()
        vendor_layout = QVBoxLayout(vendor_widget)
        vendor_layout.setContentsMargins(15, 15, 15, 15)
        vendor_widget.setMinimumHeight(80)
        vendor_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        vendor_label = QLabel("Vendor")
        vendor_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 13px;")
        vendor_layout.addWidget(vendor_label)
        
        self.vendor_combo = QComboBox()
        # Populate with real vendor options
        vendor_options = [
            "Default",
            "Random",
            "Google Inc. (NVIDIA)",
            "Google Inc. (Intel)",
            "Google Inc. (AMD)",
            "Google Inc. (Apple)",
            "Intel Inc.",
            "Google Inc. (NVIDIA Corporation)",
            "Google Inc. (Unknown)",
            "NVIDIA Corporation",
            "Intel",
            "AMD",
            "Apple",
            "Apple Inc.",
        ]
        self.vendor_combo.addItems(vendor_options)
        self.vendor_combo.setStyleSheet(self._combo_style())
        self.vendor_combo.setMinimumHeight(40)
        vendor_layout.addWidget(self.vendor_combo)
        
        # Connect vendor change to update renderer options
        self.vendor_combo.currentTextChanged.connect(self._update_renderer_options)
        
        layout.addWidget(vendor_widget, row, 0, 1, 2)
        
        renderer_widget = QWidget()
        renderer_layout = QVBoxLayout(renderer_widget)
        renderer_layout.setContentsMargins(15, 15, 15, 15)
        renderer_widget.setMinimumHeight(80)
        renderer_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        renderer_label = QLabel("Renderer")
        renderer_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 13px;")
        renderer_layout.addWidget(renderer_label)
        
        self.renderer_combo = QComboBox()
        self.renderer_combo.addItems(["Default", "Random"])
        self.renderer_combo.setStyleSheet(self._combo_style())
        self.renderer_combo.setMinimumHeight(40)
        renderer_layout.addWidget(self.renderer_combo)
        
        layout.addWidget(renderer_widget, row, 2, 1, 2)
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        return widget
    
    def _create_advanced_tab(self):
        """Create Advanced tab with Speed/Secure/Disable columns"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(25)  # Increased spacing between columns
        
        # Speed column
        speed_widget = QWidget()
        speed_layout = QVBoxLayout(speed_widget)
        speed_layout.setContentsMargins(15, 15, 15, 15)  # Better padding
        speed_layout.setSpacing(12)  # Better spacing
        speed_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 15px;")
        speed_layout.addWidget(speed_label)
        
        self.speed_network = self._create_toggle_row("Network")
        speed_layout.addLayout(self.speed_network[1])
        
        self.speed_uiux = self._create_toggle_row("UI/UX")
        speed_layout.addLayout(self.speed_uiux[1])
        
        self.speed_plugin = self._create_toggle_row("Plugin")
        speed_layout.addLayout(self.speed_plugin[1])
        
        self.speed_audio = self._create_toggle_row("Audio")
        speed_layout.addLayout(self.speed_audio[1])
        
        # AkamaiJs with dropdown
        akamai_layout = QHBoxLayout()
        akamai_label = QLabel("AkamaiJs")
        akamai_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px;")
        akamai_layout.addWidget(akamai_label)
        self.akamai_combo = QComboBox()
        self.akamai_combo.addItems(["No", "Yes"])
        self.akamai_combo.setStyleSheet(self._combo_style())
        self.akamai_combo.setMinimumHeight(36)
        akamai_layout.addWidget(self.akamai_combo)
        speed_layout.addLayout(akamai_layout)
        
        speed_layout.addStretch()
        layout.addWidget(speed_widget)
        
        # Secure column
        secure_widget = QWidget()
        secure_layout = QVBoxLayout(secure_widget)
        secure_layout.setContentsMargins(15, 15, 15, 15)
        secure_layout.setSpacing(12)
        secure_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        secure_label = QLabel("Secure:")
        secure_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 15px;")
        secure_layout.addWidget(secure_label)
        
        self.secure_searchbar = self._create_toggle_row("Search bar")
        secure_layout.addLayout(self.secure_searchbar[1])
        
        self.secure_dns = self._create_toggle_row("DNS")
        secure_layout.addLayout(self.secure_dns[1])
        
        self.secure_dataleak = self._create_toggle_row("Data Leak")
        secure_layout.addLayout(self.secure_dataleak[1])
        
        self.secure_location = self._create_toggle_row("Location")
        secure_layout.addLayout(self.secure_location[1])
        
        self.secure_super = self._create_toggle_row("Super")
        secure_layout.addLayout(self.secure_super[1])
        
        secure_layout.addStretch()
        layout.addWidget(secure_widget)
        
        # Disable column
        disable_widget = QWidget()
        disable_layout = QVBoxLayout(disable_widget)
        disable_layout.setContentsMargins(15, 15, 15, 15)
        disable_layout.setSpacing(12)
        disable_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        
        disable_label = QLabel("Disable:")
        disable_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 15px;")
        disable_layout.addWidget(disable_label)
        
        self.disable_sensor = self._create_toggle_row("Sensor")
        disable_layout.addLayout(self.disable_sensor[1])
        
        self.disable_ipv6 = self._create_toggle_row("IPv6")
        disable_layout.addLayout(self.disable_ipv6[1])
        
        self.disable_stylecss = self._create_toggle_row("Style CSS")
        disable_layout.addLayout(self.disable_stylecss[1])
        
        self.disable_image = self._create_toggle_row("Image")
        disable_layout.addLayout(self.disable_image[1])
        
        self.disable_hqvideo = self._create_toggle_row("High Quality Video")
        disable_layout.addLayout(self.disable_hqvideo[1])
        
        disable_layout.addStretch()
        layout.addWidget(disable_widget)
        
        return widget
    
    def _create_toggle_row(self, label_text):
        """Helper to create a label + toggle checkbox row"""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px;")
        layout.addWidget(label)
        layout.addStretch()
        toggle = QCheckBox()
        toggle.setStyleSheet(self._toggle_style())
        layout.addWidget(toggle)
        return (toggle, layout)
    
    def _create_cookies_tab(self):
        """Create Cookies tab with JSON textarea"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(15)
        
        # Label
        label = QLabel("Cookies Data (JSON format)")
        label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 14px; font-weight: 600;")
        layout.addWidget(label)
        
        # Textarea
        self.cookies_text = QTextEdit()
        self.cookies_text.setPlaceholderText('[\n  {\n    name: "AEC",\n    value: "Ad49MVGdPi2AiRa29GB6LzxqGXz8KT3JMmk4CA6hV8SW-1YRCzEHuACW",\n    domain: ".google.com",\n    path: "/",\n    expires: 1708424675,\n    httpOnly: true,\n    secure: true,\n    sameSite: "Lax"\n  }\n]')
        self.cookies_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.BACKGROUND};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 15px;
                color: {DarkPalette.TEXT};
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border: 1px solid {DarkPalette.ACCENT};
            }}
        """)
        layout.addWidget(self.cookies_text)
        
        return widget
    
    def _create_url_tab(self):
        """Create URL tab with WHITELIST and BLACKLIST sections"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {DarkPalette.BACKGROUND}; }}")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)  # Increased margins
        layout.setSpacing(25)  # Increased spacing
        
        # WHITELIST section
        whitelist_label = QLabel("WHITELIST:")
        whitelist_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 15px;")
        layout.addWidget(whitelist_label)
        
        # Store all whitelist inputs in a list for reset
        self.whitelist_inputs = []
        
        # First row of whitelist inputs
        whitelist_row1 = QGridLayout()
        whitelist_row1.setSpacing(15)  # Better spacing
        
        whitelist_fields_row1 = ["Canvas", "Window", "Navigator", "Audio"]
        
        for i, field in enumerate(whitelist_fields_row1):
            field_layout = QVBoxLayout()
            field_label = QLabel(field)
            field_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
            field_layout.addWidget(field_label)
            
            field_input = QLineEdit()
            field_input.setPlaceholderText("Fill URLs separated by comma")
            field_input.setStyleSheet(self._input_style())
            field_input.setMinimumHeight(40)
            field_layout.addWidget(field_input)
            
            self.whitelist_inputs.append(field_input)
            whitelist_row1.addLayout(field_layout, 0, i)
        
        layout.addLayout(whitelist_row1)
        
        # Second row of whitelist inputs
        whitelist_row2 = QGridLayout()
        whitelist_row2.setSpacing(15)
        
        whitelist_fields_row2 = ["DOM Rect", "Text Metrics", "Iframe", "SVG"]
        
        for i, field in enumerate(whitelist_fields_row2):
            field_layout = QVBoxLayout()
            field_label = QLabel(field)
            field_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
            field_layout.addWidget(field_label)
            
            field_input = QLineEdit()
            field_input.setPlaceholderText("Fill URLs separated by comma")
            field_input.setStyleSheet(self._input_style())
            field_input.setMinimumHeight(40)
            field_layout.addWidget(field_input)
            
            self.whitelist_inputs.append(field_input)
            whitelist_row2.addLayout(field_layout, 0, i)
        
        layout.addLayout(whitelist_row2)
        
        # BLACKLIST section
        blacklist_label = QLabel("BLACKLIST:")
        blacklist_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-weight: 600; font-size: 15px;")
        layout.addWidget(blacklist_label)
        
        block_layout = QVBoxLayout()
        block_label = QLabel("Block URLs")
        block_label.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        block_layout.addWidget(block_label)
        
        self.blacklist_text = QTextEdit()
        self.blacklist_text.setPlaceholderText("Enter URLs to block, one per line")
        self.blacklist_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.BACKGROUND};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 15px;
                color: {DarkPalette.TEXT};
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border: 1px solid {DarkPalette.ACCENT};
            }}
        """)
        self.blacklist_text.setMinimumHeight(150)
        block_layout.addWidget(self.blacklist_text)
        
        layout.addLayout(block_layout)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        return widget
        
        layout.addLayout(block_layout)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        return widget
    
    def _create_variables_tab(self):
        """Create Variables tab (placeholder for now)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        label = QLabel("Variables")
        label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 14px;")
        layout.addWidget(label)
        
        info = QLabel("Custom variables can be defined here for profile automation.")
        info.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        
        return widget
    
    def _create_bulk_tab(self):
        """Create Bulk Creation tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Count and prefix
        config_group = QGroupBox("Bulk Configuration")
        config_group.setStyleSheet(self._groupbox_style())
        config_layout = QGridLayout(config_group)
        
        config_layout.addWidget(QLabel("Count:"), 0, 0)
        self.bulk_count_spin = QSpinBox()
        self.bulk_count_spin.setRange(1, 100)
        self.bulk_count_spin.setValue(10)
        self.bulk_count_spin.setStyleSheet(self._input_style())
        config_layout.addWidget(self.bulk_count_spin, 0, 1)
        
        config_layout.addWidget(QLabel("Prefix:"), 1, 0)
        self.bulk_prefix_input = QLineEdit()
        self.bulk_prefix_input.setPlaceholderText("e.g., bulk, test")
        self.bulk_prefix_input.setText("bulk")
        self.bulk_prefix_input.setStyleSheet(self._input_style())
        config_layout.addWidget(self.bulk_prefix_input, 1, 1)
        
        layout.addWidget(config_group)
        
        # Randomization options
        random_group = QGroupBox("Randomization Options")
        random_group.setStyleSheet(self._groupbox_style())
        random_layout = QVBoxLayout(random_group)
        
        self.bulk_random_fp_check = QCheckBox("Randomize fingerprints (canvas/audio seeds, screen, timezone, fonts)")
        self.bulk_random_fp_check.setChecked(True)
        self.bulk_random_fp_check.setStyleSheet(f"color: {DarkPalette.TEXT};")
        random_layout.addWidget(self.bulk_random_fp_check)
        
        self.bulk_random_webgl_check = QCheckBox("Randomize WebGL vendor/renderer")
        self.bulk_random_webgl_check.setChecked(True)
        self.bulk_random_webgl_check.setStyleSheet(f"color: {DarkPalette.TEXT};")
        random_layout.addWidget(self.bulk_random_webgl_check)
        
        layout.addWidget(random_group)
        
        # Info
        info_group = QGroupBox("Information")
        info_group.setStyleSheet(self._groupbox_style())
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "Bulk generation will create multiple profiles using settings from "
            "Network and Hardware tabs. Each profile will have unique fingerprints "
            "if randomization is enabled."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {DarkPalette.BORDER};
                
                text-align: center;
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
            }}
            QProgressBar::chunk {{
                background-color: {DarkPalette.ACCENT};
                
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        return widget
    
    def _on_os_changed(self, os_name):
        """Handle OS selection change"""
        # Disable Safari if not macOS
        if os_name != "macOS":
            if self.browser_combo.currentText() == "Safari":
                self.browser_combo.setCurrentText("Firefox")
            # Find Safari index and disable it
            for i in range(self.browser_combo.count()):
                if self.browser_combo.itemText(i) == "Safari":
                    self.browser_combo.model().item(i).setEnabled(False)
        else:
            # Enable Safari on macOS
            for i in range(self.browser_combo.count()):
                if self.browser_combo.itemText(i) == "Safari":
                    self.browser_combo.model().item(i).setEnabled(True)
        
        # Update WebGL options (simplified - would need to load from database)
        # For now, just keep "Auto (Random from database)"
    
    def _reset_form(self):
        """Reset all form fields to default values"""
        # Overview tab
        self.name_input.clear()
        self.os_combo.setCurrentIndex(0)  # Windows
        self.browser_combo.setCurrentIndex(0)  # Firefox
        
        # Network tab
        self.proxy_type_combo.setCurrentIndex(0)  # SOCKS5 Proxy
        self.proxy_host_input.clear()
        self.proxy_port_input.clear()
        self.proxy_user_input.clear()
        self.proxy_pass_input.clear()
        self.webrtc_combo.setCurrentIndex(0)  # Default
        self.ipv4_input.clear()
        self.ipv6_input.clear()
        self.location_input.clear()
        self.timezone_combo.setCurrentIndex(0)
        self.latitude_input.clear()
        self.longitude_input.clear()
        
        # Hardware tab - reset all to Default
        for key, (default_radio, noise_radio) in self.hardware_options.items():
            default_radio.setChecked(True)
        self.webgl_toggle.setChecked(True)
        self.vendor_combo.setCurrentIndex(0)  # Default
        self.renderer_combo.setCurrentIndex(0)  # Default
        
        # Advanced tab - uncheck all toggles
        self.speed_network[0].setChecked(False)
        self.speed_uiux[0].setChecked(False)
        self.speed_plugin[0].setChecked(False)
        self.speed_audio[0].setChecked(False)
        self.akamai_combo.setCurrentIndex(0)  # No
        
        self.secure_searchbar[0].setChecked(False)
        self.secure_dns[0].setChecked(False)
        self.secure_dataleak[0].setChecked(False)
        self.secure_location[0].setChecked(False)
        self.secure_super[0].setChecked(False)
        
        self.disable_sensor[0].setChecked(False)
        self.disable_ipv6[0].setChecked(False)
        self.disable_stylecss[0].setChecked(False)
        self.disable_image[0].setChecked(False)
        self.disable_hqvideo[0].setChecked(False)
        
        # Cookies tab
        self.cookies_text.clear()
        
        # URL tab
        for input_field in self.whitelist_inputs:
            input_field.clear()
        self.blacklist_text.clear()
    
    def _update_renderer_options(self):
        """Update renderer dropdown based on selected vendor"""
        vendor = self.vendor_combo.currentText()
        
        # Clear current renderer options
        self.renderer_combo.clear()
        
        # Always add Default and Random
        self.renderer_combo.addItems(["Default", "Random"])
        
        # If vendor is Default or Random, don't add specific renderers
        if vendor in ["Default", "Random"]:
            return
        
        # Import webgl_database to get renderer options
        try:
            from tegufox_core.webgl_database import WEBGL_CONFIGS
            
            # Get current OS and browser to determine which renderers to show
            current_os = self.os_combo.currentText().lower()
            current_browser = self.browser_combo.currentText().lower()
            
            # Map vendor to GPU type
            vendor_to_gpu = {
                "Google Inc. (NVIDIA)": "nvidia",
                "Google Inc. (Intel)": "intel",
                "Google Inc. (AMD)": "amd",
                "Google Inc. (Apple)": "apple",
                "Intel Inc.": "intel",
                "Google Inc. (NVIDIA Corporation)": "nvidia",
                "NVIDIA Corporation": "nvidia",
                "Intel": "intel",
                "AMD": "amd",
                "Apple": "apple",
                "Apple Inc.": "apple",
            }
            
            gpu_type = vendor_to_gpu.get(vendor)
            if not gpu_type:
                return
            
            # Get renderer list from database
            renderers = []
            if current_browser in WEBGL_CONFIGS:
                browser_data = WEBGL_CONFIGS[current_browser]
                if current_os in browser_data:
                    os_data = browser_data[current_os]
                    if gpu_type in os_data:
                        gpu_configs = os_data[gpu_type]
                        renderers = [config['renderer'] for config in gpu_configs]
            
            # Add renderers to dropdown
            if renderers:
                self.renderer_combo.addItems(renderers)
        except Exception as e:
            # If anything fails, just keep Default and Random
            pass
    
    def _randomize_all(self):
        """Randomize all settings with 100% antidetect"""
        import random
        from tegufox_core.profile_generator import SCREEN_RESOLUTIONS, TIMEZONES
        
        # Overview tab - random OS and browser
        os_options = ["Windows", "macOS", "Linux"]
        random_os = random.choice(os_options)
        self.os_combo.setCurrentText(random_os)
        
        # Browser: Safari only on macOS
        if random_os == "macOS":
            self.browser_combo.setCurrentText(random.choice(["Firefox", "Safari"]))
        else:
            self.browser_combo.setCurrentText("Firefox")
        
        # Network tab - leave proxy empty (user should configure)
        # But randomize other network settings
        self.webrtc_combo.setCurrentIndex(random.randint(0, 2))
        
        # Random timezone
        all_timezones = []
        for tz_list in TIMEZONES.values():
            all_timezones.extend(tz_list)
        random_tz = random.choice(all_timezones)
        # Find timezone in combo
        for i in range(self.timezone_combo.count()):
            if random_tz[0] in self.timezone_combo.itemText(i):
                self.timezone_combo.setCurrentIndex(i)
                break
        
        # Hardware tab - randomize between Default and Noise
        for key, (default_radio, noise_radio) in self.hardware_options.items():
            if random.choice([True, False]):
                default_radio.setChecked(True)
            else:
                noise_radio.setChecked(True)
        
        # WebGL always enabled for antidetect
        self.webgl_toggle.setChecked(True)
        
        # Random vendor (skip Default and Random, use exact existing dropdown values)
        vendors = [
            "Intel",
            "NVIDIA Corporation",
            "AMD",
            "Apple Inc.",
            "Google Inc. (Intel)",
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Google Inc. (Apple)",
        ]
        self.vendor_combo.setCurrentText(random.choice(vendors))
        # Keep renderer in random mode so generator can pick a valid entry.
        self.renderer_combo.setCurrentText("Random")
        
        # Advanced tab - randomize toggles for antidetect
        # Speed: enable some for performance
        self.speed_network[0].setChecked(random.choice([True, False]))
        self.speed_uiux[0].setChecked(random.choice([True, False]))
        self.speed_plugin[0].setChecked(False)  # Keep disabled for security
        self.speed_audio[0].setChecked(random.choice([True, False]))
        self.akamai_combo.setCurrentIndex(random.randint(0, 1))
        
        # Secure: enable all for maximum security
        self.secure_searchbar[0].setChecked(True)
        self.secure_dns[0].setChecked(True)
        self.secure_dataleak[0].setChecked(True)
        self.secure_location[0].setChecked(True)
        self.secure_super[0].setChecked(True)
        
        # Disable: enable IPv6 disable, others random
        self.disable_sensor[0].setChecked(random.choice([True, False]))
        self.disable_ipv6[0].setChecked(True)  # Always disable IPv6 for antidetect
        self.disable_stylecss[0].setChecked(False)  # Keep CSS enabled
        self.disable_image[0].setChecked(False)  # Keep images enabled
        self.disable_hqvideo[0].setChecked(random.choice([True, False]))
        
        # Cookies and URL tabs - leave empty (user should configure)
        
        # Generate random profile name
        adjectives = ["swift", "silent", "shadow", "phantom", "ghost", "stealth", "ninja", "cyber", "digital", "quantum"]
        nouns = ["fox", "wolf", "hawk", "eagle", "panther", "tiger", "dragon", "phoenix", "viper", "falcon"]
        random_name = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
        self.name_input.setText(random_name)
    
    def _create_profile(self):
        """Create a single profile"""
        # Validate inputs
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Profile name cannot be empty")
            return
        
        # Build config
        config = self._build_config(name)
        
        try:
            # Import here to avoid circular dependency
            from tegufox_core.profile_generator import generate_profile, save_profile
            
            # Generate profile
            profile = generate_profile(config)
            
            # Save profile
            filepath = save_profile(profile, f"{name}.json")
            
            # Success
            QMessageBox.information(
                self,
                "Success",
                f"Profile created successfully!\n\nSaved to: {filepath}"
            )
            
            # Emit signal to refresh profile list
            self.profileCreated.emit()
            
            # Reset form for next profile
            self._reset_form()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create profile:\n\n{str(e)}")
    
    def _generate_bulk(self):
        """Generate bulk profiles"""
        # Validate inputs
        count = self.bulk_count_spin.value()
        prefix = self.bulk_prefix_input.text().strip()
        
        if not prefix:
            QMessageBox.warning(self, "Validation Error", "Prefix cannot be empty")
            return
        
        # Build base config
        config = self._build_config(prefix)
        
        try:
            # Import here
            from tegufox_core.profile_generator import generate_bulk_profiles, save_profile
            
            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(count)
            self.progress_bar.setValue(0)
            
            # Generate profiles
            profiles = generate_bulk_profiles(config, count, prefix)
            
            # Save each profile
            saved_paths = []
            for i, profile in enumerate(profiles):
                filepath = save_profile(profile, f"{profile['name']}.json")
                saved_paths.append(filepath)
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()  # Update UI
            
            # Hide progress bar
            self.progress_bar.setVisible(False)
            
            # Success
            QMessageBox.information(
                self,
                "Success",
                f"Generated {count} profiles successfully!\n\nSaved to profiles/ directory"
            )
            
            # Emit signal
            self.profileCreated.emit()
            
            # Close dialog
            self.close()
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to generate profiles:\n\n{str(e)}")
    
    def _build_config(self, name):
        """Build config dict from form inputs"""
        # Map WebRTC combo selection to boolean
        webrtc_text = self.webrtc_combo.currentText()
        webrtc_enabled = webrtc_text == "Enabled"
        
        config = {
            'name': name,
            'os': self.os_combo.currentText().lower(),
            'browser': self.browser_combo.currentText().lower(),
            'webrtc': webrtc_enabled,
        }
        
        # Hardware fingerprint options
        config['hardware'] = {}
        if hasattr(self, 'hardware_options'):
            for key, (default_radio, noise_radio) in self.hardware_options.items():
                config['hardware'][key] = 'noise' if noise_radio.isChecked() else 'default'
        
        # Proxy
        proxy_type = self.proxy_type_combo.currentText()
        if proxy_type != "No Proxy":
            proxy_host = self.proxy_host_input.text().strip()
            proxy_port = self.proxy_port_input.text().strip()
            if proxy_host and proxy_port:
                config['proxy'] = {
                    'type': proxy_type.lower().replace(' proxy', ''),
                    'host': proxy_host,
                    'port': int(proxy_port) if proxy_port.isdigit() else 8080,
                    'username': self.proxy_user_input.text().strip() or None,
                    'password': self.proxy_pass_input.text().strip() or None,
                }
            else:
                config['proxy'] = None
        else:
            config['proxy'] = None
        
        # Timezone
        tz = self.timezone_combo.currentText()
        if tz == "Auto matching":
            config['timezone'] = None
        else:
            config['timezone'] = tz
        
        # Location
        if hasattr(self, 'latitude_input') and hasattr(self, 'longitude_input'):
            lat = self.latitude_input.text().strip()
            lon = self.longitude_input.text().strip()
            if lat and lon:
                try:
                    config['location'] = {
                        'latitude': float(lat),
                        'longitude': float(lon),
                    }
                except ValueError:
                    config['location'] = None
            else:
                config['location'] = None
        
        # WebGL
        if hasattr(self, 'webgl_toggle') and self.webgl_toggle.isChecked():
            vendor = self.vendor_combo.currentText()
            renderer = self.renderer_combo.currentText()
            
            # If user selected "Random" or "Default", generate real WebGL data based on browser/OS
            if vendor in ["Random", "Default"] or renderer in ["Random", "Default"]:
                try:
                    from tegufox_core.webgl_database import get_webgl_for_profile
                    
                    # Get screen width for better GPU selection
                    screen_width = 1920  # Default
                    if hasattr(self, 'screen_width_input'):
                        try:
                            screen_width = int(self.screen_width_input.text())
                        except:
                            pass
                    
                    # Generate WebGL based on selected browser/OS
                    browser = config.get('browser', 'firefox')
                    os = config.get('os', 'windows')
                    webgl_data = get_webgl_for_profile(browser, os, screen_width)
                    
                    config['webgl'] = {
                        'vendor': webgl_data['vendor'],
                        'renderer': webgl_data['renderer'],
                    }
                except Exception as e:
                    # Fallback: let profile_manager generate it
                    config['webgl'] = None
            else:
                # User manually selected specific vendor/renderer
                config['webgl'] = {
                    'vendor': vendor,
                    'renderer': renderer,
                }
        else:
            config['webgl'] = None
        
        # Cookies
        if hasattr(self, 'cookies_text'):
            cookies_data = self.cookies_text.toPlainText().strip()
            if cookies_data:
                try:
                    import json
                    config['cookies'] = json.loads(cookies_data)
                except:
                    config['cookies'] = None
            else:
                config['cookies'] = None
        
        # URL whitelist/blacklist
        if hasattr(self, 'whitelist_inputs') and self.whitelist_inputs:
            # whitelist_inputs is a list of QLineEdit widgets
            # Order: Canvas, Window, Navigator, Audio, DOM Rect, Text Metrics, Iframe, SVG
            whitelist_fields = ["canvas", "window", "navigator", "audio", "dom_rect", "text_metrics", "iframe", "svg"]
            config['url_whitelist'] = {}
            for i, field_name in enumerate(whitelist_fields):
                if i < len(self.whitelist_inputs):
                    urls = self.whitelist_inputs[i].text().strip()
                    if urls:
                        config['url_whitelist'][field_name] = [u.strip() for u in urls.split(',')]
        
        if hasattr(self, 'blacklist_text'):
            blacklist = self.blacklist_text.toPlainText().strip()
            if blacklist:
                config['url_blacklist'] = [u.strip() for u in blacklist.split('\n') if u.strip()]
        
        return config
    
    def _groupbox_style(self):
        """GroupBox style"""
        return f"""
            QGroupBox {{
                border: 1px solid {DarkPalette.BORDER};
                
                margin-top: 10px;
                padding-top: 10px;
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {DarkPalette.TEXT};
            }}
        """
    
    def _input_style(self):
        """Input field style"""
        return f"""
            QLineEdit, QSpinBox {{
                background-color: {DarkPalette.BACKGROUND};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 8px;
                color: {DarkPalette.TEXT};
                font-size: 13px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid {DarkPalette.ACCENT};
            }}
        """
    
    def _combo_style(self):
        """ComboBox style"""
        return f"""
            QComboBox {{
                background-color: {DarkPalette.BACKGROUND};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 8px;
                color: {DarkPalette.TEXT};
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 1px solid {DarkPalette.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                selection-background-color: {DarkPalette.ACCENT};
                color: {DarkPalette.TEXT};
            }}
        """
    
    def _toggle_style(self):
        """Toggle/Checkbox style for purple accent"""
        return f"""
            QCheckBox {{
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                
                background-color: {DarkPalette.BORDER};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DarkPalette.ACCENT};
            }}
            QCheckBox::indicator:hover {{
                background-color: {DarkPalette.HOVER};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {DarkPalette.ACCENT_HOVER};
            }}
        """
    
    def _radio_style(self):
        """Radio button style with purple accent"""
        return f"""
            QRadioButton {{
                color: {DarkPalette.TEXT};
                font-size: 12px;
                spacing: 5px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                
                border: 2px solid {DarkPalette.BORDER};
                background-color: {DarkPalette.BACKGROUND};
            }}
            QRadioButton::indicator:checked {{
                background-color: {DarkPalette.ACCENT};
                border: 2px solid {DarkPalette.ACCENT};
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid {DarkPalette.ACCENT};
            }}
        """
    
    def apply_dark_theme(self):
        """Apply dark theme to dialog"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
            }}
            QLabel {{
                color: {DarkPalette.TEXT};
            }}
        """)


