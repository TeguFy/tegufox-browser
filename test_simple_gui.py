#!/usr/bin/env python3
"""
Ultra simple test - just show profile names in a list
"""

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
)
from PyQt6.QtCore import Qt


class SimpleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Profile List Test")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet("background-color: #1e1e2e;")

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Profiles Test - Should show 5 cards below:")
        title.setStyleSheet("color: white; font-size: 18px; padding: 10px;")
        layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 2px solid red;")  # Red border to see scroll area

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #262637;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # Load profiles and add simple widgets
        profiles_dir = Path("profiles")
        count = 0

        if profiles_dir.exists():
            for pfile in profiles_dir.glob("*.json"):
                try:
                    with open(pfile) as f:
                        data = json.load(f)

                    # Create a simple widget for each profile
                    profile_widget = QWidget()
                    profile_widget.setStyleSheet("""
                        background-color: #89b4fa;
                        border-radius: 8px;
                        padding: 15px;
                    """)
                    profile_widget.setMinimumHeight(80)
                    profile_widget.setMaximumHeight(120)

                    profile_layout = QVBoxLayout(profile_widget)

                    # Name label
                    name = QLabel(data.get("name", "Unknown"))
                    name.setStyleSheet(
                        "color: black; font-size: 16px; font-weight: bold;"
                    )
                    profile_layout.addWidget(name)

                    # Platform label
                    platform = QLabel(f"Platform: {data.get('platform', 'N/A')}")
                    platform.setStyleSheet("color: #1e1e2e; font-size: 12px;")
                    profile_layout.addWidget(platform)

                    # Add to scroll layout
                    scroll_layout.addWidget(profile_widget)
                    count += 1
                    print(f"✅ Added widget for: {data.get('name')}")

                except Exception as e:
                    print(f"❌ Error: {e}")

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Status label
        status = QLabel(f"Loaded {count} profiles")
        status.setStyleSheet("color: #89b4fa; font-size: 14px; padding: 10px;")
        layout.addWidget(status)

        print(f"\n✅ Window created with {count} profile widgets")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleWindow()
    window.show()
    print("✅ Window.show() called")
    sys.exit(app.exec())
