"""Profile card component"""

from datetime import datetime

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal

from tegufox_gui.utils.styles import DarkPalette


def _detect_browser_os(profile_data: dict) -> tuple:
    nav = profile_data.get("navigator", {})
    cfg = profile_data.get("config", {})
    ua = nav.get("userAgent") or cfg.get("navigator.userAgent") or ""
    platform = nav.get("platform") or cfg.get("navigator.platform") or ""
    if "Firefox" in ua:
        browser = "🦊 Firefox"
    elif "Chrome" in ua and "Chromium" not in ua:
        browser = "🌐 Chrome"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "🧭 Safari"
    else:
        tmpl = profile_data.get("platform", "")
        browser = tmpl.replace("-", " ").title() if tmpl else "Unknown"
    return browser, platform


class ProfileCard(QFrame):
    """Compact profile row — 56 px, shows browser/OS/date."""

    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)
    stop_requested = pyqtSignal(str)
    selection_changed = pyqtSignal(str, bool)  # profile_name, is_selected

    def __init__(self, profile_data: dict, parent=None):
        super().__init__(parent)
        self.profile_data = profile_data
        self._name = profile_data.get("name", "Unnamed")
        self._selected = False
        self._status = "stopped"  # stopped, loading, active
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
                margin: 2px 0;
            }}
            QFrame:hover {{
                background-color: {DarkPalette.HOVER};
                border-color: {DarkPalette.ACCENT};
            }}
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 8, 12, 8)
        row.setSpacing(10)

        # Checkbox for selection
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {DarkPalette.BORDER};
                border-radius: 3px;
                background-color: {DarkPalette.BACKGROUND};
            }}
            QCheckBox::indicator:hover {{
                border-color: {DarkPalette.ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DarkPalette.ACCENT};
                border-color: {DarkPalette.ACCENT};
            }}
        """)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        row.addWidget(self.checkbox)

        browser_str, platform_str = _detect_browser_os(self.profile_data)
        badge = QLabel(browser_str)
        badge.setFixedWidth(120)
        badge.setStyleSheet(
            f"color: {DarkPalette.ACCENT}; font-size: 12px; font-weight: 600;"
            " background-color: rgba(137,180,250,0.12);  padding: 3px 8px;"
        )
        row.addWidget(badge)

        name_lbl = QLabel(self._name)
        name_lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
        row.addWidget(name_lbl, 1)

        plat_lbl = QLabel(platform_str or "—")
        plat_lbl.setFixedWidth(68)
        plat_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        row.addWidget(plat_lbl)

        created = self.profile_data.get("created", "")
        date_str = "—"
        if created:
            try:
                dt = datetime.fromisoformat(created)
                date_str = dt.strftime("%b %d %H:%M")
            except Exception:
                pass
        date_lbl = QLabel(date_str)
        date_lbl.setFixedWidth(90)
        date_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        row.addWidget(date_lbl)

        self.launch_btn = QPushButton("▶")
        self.launch_btn.setFixedSize(32, 32)
        self.launch_btn.setToolTip("Launch Browser")
        self.launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white; border: none;
                 font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #7aa2f7; }}
            QPushButton:disabled {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT_DIM};
            }}
        """)
        self.launch_btn.clicked.connect(self._on_launch_clicked)
        row.addWidget(self.launch_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(32, 32)
        self.del_btn.setToolTip("Delete Profile")
        self.del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(243,139,168,0.12);
                color: {DarkPalette.RED}; border: none;
                 font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(243,139,168,0.25); }}
            QPushButton:disabled {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT_DIM};
            }}
        """)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))
        row.addWidget(self.del_btn)

    def _on_checkbox_changed(self, state):
        """Handle checkbox state change"""
        self._selected = (state == Qt.CheckState.Checked.value)
        self.selection_changed.emit(self._name, self._selected)

    def _on_launch_clicked(self):
        """Handle launch/stop button click based on current status"""
        if self._status == "stopped":
            self.launch_requested.emit(self._name)
        elif self._status == "active":
            self.stop_requested.emit(self._name)
        # Do nothing if loading

    def set_status(self, status: str):
        """Update profile status and UI accordingly
        
        Args:
            status: One of 'stopped', 'loading', 'active'
        """
        self._status = status
        
        if status == "stopped":
            self.launch_btn.setText("▶")
            self.launch_btn.setToolTip("Launch Browser")
            self.launch_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.launch_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DarkPalette.ACCENT};
                    color: white; border: none;
                    font-size: 13px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #7aa2f7; }}
            """)
        elif status == "loading":
            self.launch_btn.setText("⏳")
            self.launch_btn.setToolTip("Launching...")
            self.launch_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.launch_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DarkPalette.CARD};
                    color: {DarkPalette.TEXT_DIM}; border: none;
                    font-size: 13px; font-weight: bold;
                }}
            """)
        elif status == "active":
            self.launch_btn.setText("■")
            self.launch_btn.setToolTip("Stop Browser")
            self.launch_btn.setEnabled(True)
            self.del_btn.setEnabled(False)
            self.launch_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DarkPalette.RED};
                    color: white; border: none;
                    font-size: 13px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #f38ba8; }}
            """)

    def get_status(self) -> str:
        """Get current profile status"""
        return self._status

    def set_selected(self, selected: bool):
        """Set selection state programmatically"""
        self._selected = selected
        self.checkbox.setChecked(selected)

    def is_selected(self) -> bool:
        """Get selection state"""
        return self._selected

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child is None or not isinstance(child, (QPushButton, QCheckBox)):
                self.clicked.emit(self._name)
        super().mousePressEvent(event)

    def matches(self, text: str) -> bool:
        return text.lower() in self._name.lower()
