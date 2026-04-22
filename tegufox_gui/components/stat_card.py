"""Stat card component for dashboard"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel

from tegufox_gui.utils.styles import DarkPalette


class StatCard(QFrame):
    """Compact metric card used on the Dashboard."""

    def __init__(self, icon: str, value: str, label: str, color: str = "", parent=None):
        super().__init__(parent)
        if not color:
            color = DarkPalette.ACCENT
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedHeight(110)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(4)

        ico = QLabel(icon)
        ico.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        lay.addWidget(ico)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color: {color}; font-size: 26px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        lay.addWidget(self._val)

        desc = QLabel(label)
        desc.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;"
            " background: transparent; border: none;"
        )
        lay.addWidget(desc)

    def set_value(self, v: str):
        self._val.setText(v)
