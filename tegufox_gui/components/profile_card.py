"""Profile card component"""

from datetime import datetime

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
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
    """Compact profile row — 56 px, shows browser/OS/score/date."""

    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)

    def __init__(self, profile_data: dict, score=None, parent=None):
        super().__init__(parent)
        self.profile_data = profile_data
        self.score = score
        self._name = profile_data.get("name", "Unnamed")
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

        if self.score is not None:
            sc_color = "#a6e3a1" if self.score >= 0.8 else ("#f9e2af" if self.score >= 0.6 else DarkPalette.RED)
            sc_lbl = QLabel(f"● {self.score:.2f}")
            sc_lbl.setStyleSheet(f"color: {sc_color}; font-size: 12px; font-weight: 600;")
        else:
            sc_lbl = QLabel("—")
            sc_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        sc_lbl.setFixedWidth(52)
        row.addWidget(sc_lbl)

        created = self.profile_data.get("created", "")
        date_str = "—"
        if created:
            try:
                date_str = datetime.fromisoformat(created).strftime("%b %d")
            except Exception:
                pass
        date_lbl = QLabel(date_str)
        date_lbl.setFixedWidth(46)
        date_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        row.addWidget(date_lbl)

        launch_btn = QPushButton("▶")
        launch_btn.setFixedSize(32, 32)
        launch_btn.setToolTip("Launch Browser")
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white; border: none;
                 font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #7aa2f7; }}
        """)
        launch_btn.clicked.connect(lambda: self.launch_requested.emit(self._name))
        row.addWidget(launch_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(32, 32)
        del_btn.setToolTip("Delete Profile")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(243,139,168,0.12);
                color: {DarkPalette.RED}; border: none;
                 font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(243,139,168,0.25); }}
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))
        row.addWidget(del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child is None or not isinstance(child, QPushButton):
                self.clicked.emit(self._name)
        super().mousePressEvent(event)

    def matches(self, text: str) -> bool:
        return text.lower() in self._name.lower()
