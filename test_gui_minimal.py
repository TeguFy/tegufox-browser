#!/usr/bin/env python3
"""
Minimal GUI test to debug profile card rendering
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt

# Dark theme colors
BG = "#1e1e2e"
CARD = "#262637"
TEXT = "#cdd6f4"
TEXT_DIM = "#7f849c"
ACCENT = "#89b4fa"


class SimpleProfileCard(QFrame):
    def __init__(self, profile_data):
        super().__init__()
        self.profile_data = profile_data
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border-radius: 12px;
                padding: 16px;
                margin: 8px;
            }}
        """)
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)

        layout = QVBoxLayout(self)

        # Name
        name = self.profile_data.get("name", "Unnamed")
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: bold;")
        layout.addWidget(name_label)

        # Platform
        platform = self.profile_data.get("platform", "unknown")
        platform_label = QLabel(f"Platform: {platform}")
        platform_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        layout.addWidget(platform_label)

        # Created
        created = self.profile_data.get("created", "")
        if created:
            created_label = QLabel(f"Created: {created[:19]}")
            created_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
            layout.addWidget(created_label)

        # Config count
        config_count = len(self.profile_data.get("config", {}))
        config_label = QLabel(f"{config_count} config keys")
        config_label.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
        layout.addWidget(config_label)


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Profile Card Test")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"background-color: {BG};")

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Profile Cards Test")
        title.setStyleSheet(f"color: {TEXT}; font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)

        # Load profiles
        profiles_dir = Path("profiles")
        count = 0
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    with open(profile_file) as f:
                        profile_data = json.load(f)
                        card = SimpleProfileCard(profile_data)
                        scroll_layout.addWidget(card)
                        count += 1
                        print(f"✅ Added card for: {profile_data.get('name')}")
                except Exception as e:
                    print(f"❌ Error loading {profile_file}: {e}")

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        print(f"\n✅ Loaded {count} profile cards")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
