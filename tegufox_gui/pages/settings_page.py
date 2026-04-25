"""Settings page widget"""

import ast
import copy
import pprint
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QGridLayout,
    QScrollArea,
    QMessageBox,
    QFileDialog,
)

from tegufox_core.binary_locator import auto_detect_binary
from tegufox_gui.utils.styles import DarkPalette

_RULE_NAMES = [
    "PlatformUARule",
    "LanguageLocaleRule",
    "ScreenDPRViewportRule",
    "TLSCipherOrderRule",
    "GPUWebGLRule",
    "OSFontListRule",
    "HTTP2PseudoHeaderRule",
    "LocaleTimezoneRule",
]

_DEFAULT_SETTINGS = {
    "profiles_dir": "profiles",
    "api_port": 8420,
    "browser_binary": "",  # Empty = auto-detect
    "rules": {r: True for r in _RULE_NAMES},
    "market_weights": {
        "firefox/windows": 0.40,
        "firefox/macos":   0.30,
        "firefox/linux":   0.10,
        "safari/macos":    0.20,
    },
}

_SETTINGS_PATH = Path("data/settings.conf")


class SettingsWidget(QWidget):
    """Settings page — configure directories, API port, rules, and market weights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rule_cbs: dict = {}
        self._weight_spins: dict = {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"color: {DarkPalette.TEXT}; font-size: 28px; font-weight: bold;"
        )
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        root = QVBoxLayout(content)
        root.setSpacing(20)
        root.setContentsMargins(0, 0, 20, 0)

        CARD = f"""
            QGroupBox {{
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                
                margin-top: 12px;
                padding: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """
        LBL = f"color: {DarkPalette.TEXT_DIM}; font-size: 13px;"
        INP = f"""
            QLineEdit {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 6px 12px;
                font-size: 13px;
            }}
        """
        SPN = f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 4px 8px;
                font-size: 13px;
            }}
        """

        # ── General ──────────────────────────────────────────────────────────
        gen_grp = QGroupBox("General")
        gen_grp.setStyleSheet(CARD)
        gen_lay = QGridLayout()
        gen_lay.setHorizontalSpacing(12)
        gen_lay.setVerticalSpacing(10)

        gen_lay.addWidget(QLabel("Profiles directory:", styleSheet=LBL), 0, 0)
        self.profiles_dir_input = QLineEdit()
        self.profiles_dir_input.setStyleSheet(INP)
        gen_lay.addWidget(self.profiles_dir_input, 0, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedHeight(32)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                
                font-size: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        browse_btn.clicked.connect(self._browse_profiles_dir)
        gen_lay.addWidget(browse_btn, 0, 2)

        gen_lay.addWidget(QLabel("API port:", styleSheet=LBL), 1, 0)
        self.api_port_spin = QSpinBox()
        self.api_port_spin.setRange(1024, 65535)
        self.api_port_spin.setStyleSheet(SPN)
        gen_lay.addWidget(self.api_port_spin, 1, 1)

        gen_lay.addWidget(QLabel("Browser binary:", styleSheet=LBL), 2, 0)
        self.browser_binary_input = QLineEdit()
        _detected = auto_detect_binary()
        self.browser_binary_input.setPlaceholderText(
            f"Auto-detect: {_detected}" if _detected else "Auto-detect: not found"
        )
        self.browser_binary_input.setStyleSheet(INP)
        gen_lay.addWidget(self.browser_binary_input, 2, 1)
        browse_binary_btn = QPushButton("Browse…")
        browse_binary_btn.setFixedHeight(32)
        browse_binary_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};

                font-size: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        browse_binary_btn.clicked.connect(self._browse_browser_binary)
        gen_lay.addWidget(browse_binary_btn, 2, 2)

        # Effective-path label: shows what will actually be launched. Updates
        # live as the user edits the input (custom path overrides auto-detect).
        self.browser_binary_status = QLabel()
        self.browser_binary_status.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 11px; padding: 2px 0 0 0;"
        )
        self.browser_binary_status.setWordWrap(True)
        gen_lay.addWidget(self.browser_binary_status, 3, 1, 1, 2)
        self.browser_binary_input.textChanged.connect(self._refresh_browser_binary_status)
        self._refresh_browser_binary_status()

        gen_grp.setLayout(gen_lay)
        root.addWidget(gen_grp)

        # ── Consistency rules ─────────────────────────────────────────────────
        rules_grp = QGroupBox("Consistency Engine Rules")
        rules_grp.setStyleSheet(CARD)
        rules_lay = QGridLayout()
        rules_lay.setHorizontalSpacing(20)
        rules_lay.setVerticalSpacing(8)
        CB_STYLE = f"""
            QCheckBox {{
                color: {DarkPalette.TEXT};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {DarkPalette.BORDER};
                
                background-color: {DarkPalette.BACKGROUND};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DarkPalette.ACCENT};
                border-color: {DarkPalette.ACCENT};
            }}
        """
        for i, name in enumerate(_RULE_NAMES):
            cb = QCheckBox(name)
            cb.setStyleSheet(CB_STYLE)
            cb.setChecked(True)
            rules_lay.addWidget(cb, i // 2, i % 2)
            self._rule_cbs[name] = cb
        rules_grp.setLayout(rules_lay)
        root.addWidget(rules_grp)

        # ── Market weights ────────────────────────────────────────────────────
        mkt_grp = QGroupBox("Market Distribution Weights")
        mkt_grp.setStyleSheet(CARD)
        mkt_lay = QGridLayout()
        mkt_lay.setHorizontalSpacing(20)
        mkt_lay.setVerticalSpacing(8)
        for i, key in enumerate(_DEFAULT_SETTINGS["market_weights"]):
            mkt_lay.addWidget(QLabel(key + ":", styleSheet=LBL), i, 0)
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.01)
            spin.setDecimals(3)
            spin.setStyleSheet(SPN)
            mkt_lay.addWidget(spin, i, 1)
            self._weight_spins[key] = spin
        mkt_grp.setLayout(mkt_lay)
        root.addWidget(mkt_grp)

        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Save / Reset
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
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
        reset_btn.clicked.connect(self._reset_settings)
        btn_row.addWidget(reset_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white;
                border: none;
                
                padding: 6px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #7aa2f7; }}
        """)
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)

        outer.addLayout(btn_row)

    def _browse_profiles_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Profiles Directory", str(Path.cwd())
        )
        if directory:
            self.profiles_dir_input.setText(directory)

    def _browse_browser_binary(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Browser Binary",
            str(Path.cwd() / "build"),
            "Executables (tegufox camoufox);;All Files (*)"
        )
        if file_path:
            self.browser_binary_input.setText(file_path)

    def _refresh_browser_binary_status(self):
        custom = self.browser_binary_input.text().strip()
        if custom:
            self.browser_binary_status.setText(f"Custom path → {custom}")
            return
        detected = auto_detect_binary()
        if detected:
            self.browser_binary_status.setText(f"Auto-detected → {detected}")
        else:
            self.browser_binary_status.setText(
                "Auto-detect: no built binary found. Run 'make tegufox' to build."
            )

    def _load_settings(self):
        settings = copy.deepcopy(_DEFAULT_SETTINGS)
        if _SETTINGS_PATH.exists():
            try:
                loaded = ast.literal_eval(_SETTINGS_PATH.read_text())
                if not isinstance(loaded, dict):
                    loaded = {}
                for k in ("profiles_dir", "api_port", "browser_binary"):
                    if k in loaded:
                        settings[k] = loaded[k]
                if "rules" in loaded:
                    settings["rules"].update(loaded["rules"])
                if "market_weights" in loaded:
                    settings["market_weights"].update(loaded["market_weights"])
            except Exception:
                pass
        self.profiles_dir_input.setText(str(settings["profiles_dir"]))
        self.api_port_spin.setValue(int(settings["api_port"]))
        self.browser_binary_input.setText(str(settings.get("browser_binary", "")))
        for rule, cb in self._rule_cbs.items():
            cb.setChecked(settings["rules"].get(rule, True))
        for key, spin in self._weight_spins.items():
            spin.setValue(float(settings["market_weights"].get(key, 0.0)))

    def _save_settings(self):
        settings = {
            "profiles_dir": self.profiles_dir_input.text(),
            "api_port": self.api_port_spin.value(),
            "browser_binary": self.browser_binary_input.text(),
            "rules": {r: cb.isChecked() for r, cb in self._rule_cbs.items()},
            "market_weights": {k: sp.value() for k, sp in self._weight_spins.items()},
        }
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(pprint.pformat(settings, sort_dicts=True))
        QMessageBox.information(self, "Settings", "Settings saved.")

    def _reset_settings(self):
        self.profiles_dir_input.setText(_DEFAULT_SETTINGS["profiles_dir"])
        self.api_port_spin.setValue(_DEFAULT_SETTINGS["api_port"])
        self.browser_binary_input.setText(_DEFAULT_SETTINGS["browser_binary"])
        for rule, cb in self._rule_cbs.items():
            cb.setChecked(True)
        for key, spin in self._weight_spins.items():
            spin.setValue(_DEFAULT_SETTINGS["market_weights"].get(key, 0.0))


