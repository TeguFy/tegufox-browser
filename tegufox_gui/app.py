#!/usr/bin/env python3
"""
Tegufox Profile Manager - GUI Application
Modern PyQt6 interface for managing browser profiles
"""

import sys
from pathlib import Path

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QStackedWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from tegufox_gui.utils.styles import DarkPalette
from tegufox_gui.components import SidebarButton
from tegufox_gui.pages import (
    DashboardWidget,
    ProfilesListWidget,
    CreateProfileWidget,
    SessionsWidget,
    SettingsWidget,
    ProxiesWidget,
)


class TegufoxProfileManager(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tegufox Profile Manager")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        """Setup main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)

        self.home_page = DashboardWidget()
        self.content_stack.addWidget(self.home_page)

        self.sessions_page = SessionsWidget()
        self.content_stack.addWidget(self.sessions_page)

        self.profiles_list = ProfilesListWidget()
        self.profiles_list._main_window = self
        self.content_stack.addWidget(self.profiles_list)

        self.create_profile_page = CreateProfileWidget()
        self.create_profile_page.profile_created.connect(
            self.profiles_list.refresh_profiles
        )
        self.content_stack.addWidget(self.create_profile_page)

        self.proxies_page = ProxiesWidget()
        self.content_stack.addWidget(self.proxies_page)

        self.settings_page = SettingsWidget()
        self.content_stack.addWidget(self.settings_page)

    def create_sidebar(self):
        """Create compact sidebar with navigation"""
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background-color: {DarkPalette.SIDEBAR};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(6)

        logo_label = QLabel()
        logo_path = Path(__file__).parent / "tegufox-tool.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled_pixmap = pixmap.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("🦊")
            logo_label.setStyleSheet(f"font-size: 36px;")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_layout.addWidget(logo_label)

        title_label = QLabel("Tegufox")
        title_label.setStyleSheet(
            f"color: {DarkPalette.ACCENT}; font-size: 16px; font-weight: bold;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(title_label)

        layout.addWidget(logo_container)
        layout.addSpacing(16)

        self.nav_buttons = []

        home_btn = SidebarButton("Home", "🏠")
        home_btn.clicked.connect(lambda: self.switch_page(0))
        layout.addWidget(home_btn)
        self.nav_buttons.append(home_btn)

        sessions_btn = SidebarButton("Sessions", "🌐")
        sessions_btn.clicked.connect(lambda: self.switch_page(1))
        layout.addWidget(sessions_btn)
        self.nav_buttons.append(sessions_btn)

        proxies_btn = SidebarButton("Proxies", "🔌")
        proxies_btn.clicked.connect(lambda: self.switch_page(4))
        layout.addWidget(proxies_btn)
        self.nav_buttons.append(proxies_btn)

        layout.addSpacing(8)
        profiles_label = QLabel("PROFILES")
        profiles_label.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 10px; font-weight: 600; padding: 6px 12px; letter-spacing: 0.5px;"
        )
        layout.addWidget(profiles_label)

        create_btn = SidebarButton("Create", "➕")
        create_btn.clicked.connect(lambda: self.switch_page(3))
        layout.addWidget(create_btn)
        self.nav_buttons.append(create_btn)

        local_btn = SidebarButton("Browse", "📁")
        local_btn.clicked.connect(lambda: self.switch_page(2))
        layout.addWidget(local_btn)
        self.nav_buttons.append(local_btn)

        layout.addStretch()

        settings_btn = SidebarButton("Settings", "⚙️")
        settings_btn.clicked.connect(lambda: self.switch_page(5))
        layout.addWidget(settings_btn)
        self.nav_buttons.append(settings_btn)

        return sidebar

    def switch_page(self, index):
        """Switch to page and update button states"""
        self.content_stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(False)

    def apply_dark_theme(self):
        """Apply dark theme to application"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DarkPalette.BACKGROUND};
            }}
            QWidget {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
            }}
            QLabel {{
                color: {DarkPalette.TEXT};
            }}
            QScrollBar:vertical {{
                background-color: {DarkPalette.BACKGROUND};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DarkPalette.BORDER};
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DarkPalette.TEXT_DIM};
            }}
        """)


def main():
    app = QApplication(sys.argv)
    font = app.font()
    font.setPointSize(12)
    app.setFont(font)
    window = TegufoxProfileManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
