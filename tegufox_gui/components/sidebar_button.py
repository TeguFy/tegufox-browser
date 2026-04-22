"""Sidebar button component"""

from PyQt6.QtWidgets import QPushButton

from tegufox_gui.utils.styles import DarkPalette


class SidebarButton(QPushButton):
    """Styled sidebar button with icon"""

    def __init__(self, text, icon_text="", parent=None):
        super().__init__(parent)
        self.icon_text = icon_text
        self.button_text = text
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.TEXT_DIM};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {DarkPalette.HOVER};
                color: {DarkPalette.TEXT};
            }}
            QPushButton:checked {{
                background-color: {DarkPalette.ACCENT};
                color: white;
            }}
        """)
        self.setCheckable(True)
        
        # Set text with icon
        if icon_text:
            self.setText(f"{icon_text}  {text}")
        else:
            self.setText(text)
