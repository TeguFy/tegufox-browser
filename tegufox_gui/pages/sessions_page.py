"""Sessions page widget and worker thread"""

import sys
import json
import queue
import subprocess
import threading
import time
import uuid
import os
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QFrame,
    QScrollArea,
    QTextEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QPixmap

from tegufox_gui.utils.styles import DarkPalette
from tegufox_core.profile_manager import ProfileManager

# Shared session store
_gui_sessions = {}

# Settings path for browser binary detection
_SETTINGS_PATH = Path("data/settings.json")


class SessionWorker(QThread):
    """Dedicated QThread owning one TegufoxSession.

    Playwright sync API (greenlets) requires every call on the creating thread.
    SessionWorker mirrors the API's SessionSlot but uses QThread + pyqtSignal.
    """

    status_changed = pyqtSignal(str, str)  # (session_id, status)

    def __init__(self, session_id: str, profile: str, headless: bool, browser_binary: str = None, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.profile = profile
        self.headless = headless
        self.browser_binary = browser_binary
        self.status = "starting"
        self.error: str = ""
        self.created_at = time.time()
        self._cmd_q: queue.Queue = queue.Queue()
        self._session = None

    def run(self):
        from tegufox_automation import TegufoxSession, SessionConfig
        import logging
        logger = logging.getLogger("tegufox_gui")
        
        try:
            logger.info(f"[Session {self.session_id}] Creating TegufoxSession with profile={self.profile}, headless={self.headless}")
            _cfg = SessionConfig(headless=self.headless, browser_binary=self.browser_binary)
            self._session = TegufoxSession(profile=self.profile, config=_cfg)
            
            logger.info(f"[Session {self.session_id}] Starting session...")
            self._session.start()
            
            logger.info(f"[Session {self.session_id}] Session started successfully, entering command loop")
            self.status = "running"
            self.status_changed.emit(self.session_id, "running")
        except Exception as exc:
            logger.error(f"[Session {self.session_id}] Failed to start: {exc}", exc_info=True)
            self.status = "error"
            self.error = str(exc)
            self.status_changed.emit(self.session_id, "error")
            return

        logger.info(f"[Session {self.session_id}] Waiting for commands...")
        while True:
            item = self._cmd_q.get()
            if item is None:  # poison pill
                logger.info(f"[Session {self.session_id}] Received stop signal")
                break
            fn, rq = item
            try:
                logger.debug(f"[Session {self.session_id}] Executing command: {fn}")
                rq.put(("ok", fn(self._session)))
            except Exception as exc:
                logger.error(f"[Session {self.session_id}] Command failed: {exc}", exc_info=True)
                rq.put(("err", exc))

        logger.info(f"[Session {self.session_id}] Stopping session...")
        try:
            self._session.stop()
        except Exception as exc:
            logger.error(f"[Session {self.session_id}] Error during stop: {exc}", exc_info=True)
        self.status = "stopped"
        self.status_changed.emit(self.session_id, "stopped")
        logger.info(f"[Session {self.session_id}] Session stopped")

    def execute(self, fn, timeout: float = 30):
        if self.status != "running":
            raise RuntimeError(f"Session is {self.status}")
        rq: queue.Queue = queue.Queue()
        self._cmd_q.put((fn, rq))
        tag, val = rq.get(timeout=timeout)
        if tag == "err":
            raise val
        return val

    def stop_session(self):
        self._cmd_q.put(None)


class SessionsWidget(QWidget):
    """Sessions management: launch, monitor, screenshot browser sessions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._row_widgets: dict = {}      # session_id -> {row, status_lbl}
        self._detail_session_id: str = ""
        self._setup_ui()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(2000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        title = QLabel("Sessions")
        title.setStyleSheet(
            f"color: {DarkPalette.TEXT}; font-size: 24px; font-weight: 700;"
        )
        hdr.addWidget(title)
        self._session_count_lbl = QLabel("0")
        self._session_count_lbl.setFixedHeight(26)
        self._session_count_lbl.setMinimumWidth(26)
        self._session_count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._session_count_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(124, 58, 237, 0.2);
                color: {DarkPalette.ACCENT};
                border: 1px solid rgba(124, 58, 237, 0.4);
                border-radius: 13px;
                padding: 0 10px;
                font-size: 12px;
                font-weight: 700;
            }}
        """)
        hdr.addWidget(self._session_count_lbl)
        hdr.addStretch()
        reload_btn = QPushButton("↻  Refresh Profiles")
        reload_btn.setFixedHeight(34)
        reload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.TEXT_DIM};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: {DarkPalette.TEXT};
                border-color: {DarkPalette.ACCENT};
                background-color: {DarkPalette.HOVER};
            }}
        """)
        reload_btn.clicked.connect(self._reload_profiles)
        hdr.addWidget(reload_btn)
        root.addLayout(hdr)

        # Two-column body
        body = QHBoxLayout()
        body.setSpacing(16)

        # LEFT: Launch Configuration
        launch_frame = QFrame()
        launch_frame.setFixedWidth(360)
        launch_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 12px;
            }}
        """)
        lf_main = QVBoxLayout(launch_frame)
        lf_main.setContentsMargins(24, 20, 24, 20)
        lf_main.setSpacing(0)

        lf_section = QLabel("LAUNCH NEW SESSION")
        lf_section.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.2px; margin-bottom: 18px;"
        )
        lf_main.addWidget(lf_section)

        INPUT_H = 40
        LABEL_STYLE = (
            f"color: {DarkPalette.TEXT_DIM}; font-size: 10px; font-weight: 600; "
            f"letter-spacing: 0.8px; margin-top: 12px; margin-bottom: 5px;"
        )

        lf_main.addWidget(QLabel("PROFILE", styleSheet=LABEL_STYLE))
        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(INPUT_H)
        self.profile_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{ 
                border-color: rgba(124, 58, 237, 0.3);
                background-color: rgba(124, 58, 237, 0.03);
            }}
            QComboBox:focus {{ border-color: {DarkPalette.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                selection-background-color: {DarkPalette.ACCENT};
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 6px;
            }}
        """)
        self._reload_profiles()
        lf_main.addWidget(self.profile_combo)

        lf_main.addWidget(QLabel("OPTIONS", styleSheet=LABEL_STYLE))
        CB_STYLE = f"""
            QCheckBox {{
                color: {DarkPalette.TEXT};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                background-color: {DarkPalette.BACKGROUND};
            }}
            QCheckBox::indicator:hover {{ 
                border-color: rgba(124, 58, 237, 0.5);
                background-color: rgba(124, 58, 237, 0.05);
            }}
            QCheckBox::indicator:checked {{
                background-color: {DarkPalette.ACCENT};
                border-color: {DarkPalette.ACCENT};
            }}
        """
        opts_row = QHBoxLayout()
        opts_row.setSpacing(20)
        self.headless_cb = QCheckBox("Headless")
        self.headless_cb.setChecked(False)
        self.headless_cb.setStyleSheet(CB_STYLE)
        opts_row.addWidget(self.headless_cb)
        self.custom_build_cb = QCheckBox("Custom Build")
        self.custom_build_cb.setChecked(True)
        self.custom_build_cb.setToolTip(
            "Use the locally compiled Tegufox browser\n"
            "(canvas/WebGL/TLS/audio spoofing at engine level)"
        )
        self.custom_build_cb.setStyleSheet(CB_STYLE)
        opts_row.addWidget(self.custom_build_cb)
        opts_row.addStretch()
        lf_main.addLayout(opts_row)

        lf_main.addWidget(QLabel("WINDOW SIZE", styleSheet=LABEL_STYLE))
        SPIN_STYLE = f"""
            QSpinBox {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 32px 8px 12px;
                font-size: 13px;
            }}
            QSpinBox:hover {{ 
                border-color: rgba(124, 58, 237, 0.3);
                background-color: rgba(124, 58, 237, 0.03);
            }}
            QSpinBox:focus {{ border-color: {DarkPalette.ACCENT}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px; background-color: transparent; border: none;
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 4px solid {DarkPalette.TEXT_DIM};
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid {DarkPalette.TEXT_DIM};
            }}
        """
        win_row = QHBoxLayout()
        win_row.setSpacing(8)
        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(400, 3840)
        self.window_width_spin.setValue(500)
        self.window_width_spin.setSuffix(" px")
        self.window_width_spin.setFixedHeight(INPUT_H)
        self.window_width_spin.setStyleSheet(SPIN_STYLE)
        win_row.addWidget(self.window_width_spin)
        sep = QLabel("×")
        sep.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 15px;")
        sep.setFixedWidth(18)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        win_row.addWidget(sep)
        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(300, 2160)
        self.window_height_spin.setValue(600)
        self.window_height_spin.setSuffix(" px")
        self.window_height_spin.setFixedHeight(INPUT_H)
        self.window_height_spin.setStyleSheet(SPIN_STYLE)
        win_row.addWidget(self.window_height_spin)
        lf_main.addLayout(win_row)

        lf_main.addWidget(QLabel("TARGET URL", styleSheet=LABEL_STYLE))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        self.url_input.setText("https://fv.pro")
        self.url_input.setFixedHeight(INPUT_H)
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:hover {{ 
                border-color: rgba(124, 58, 237, 0.3);
                background-color: rgba(124, 58, 237, 0.03);
            }}
            QLineEdit:focus {{ border-color: {DarkPalette.ACCENT}; }}
        """)
        lf_main.addWidget(self.url_input)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        presets_row.setContentsMargins(0, 6, 0, 0)
        PRESET_STYLE = f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.ACCENT};
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(124, 58, 237, 0.12);
                border-color: {DarkPalette.ACCENT};
            }}
        """
        for label, qurl in [
            ("fv.pro", "https://fv.pro"),
            ("browserscan", "https://www.browserscan.net/bot-detection"),
            ("pixelscan", "https://pixelscan.net"),
            ("fp.com", "https://fingerprint.com/demo"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(PRESET_STYLE)
            btn.clicked.connect(lambda _=False, u=qurl: self.url_input.setText(u))
            presets_row.addWidget(btn)
        presets_row.addStretch()
        lf_main.addLayout(presets_row)
        lf_main.addStretch()

        launch_btn = QPushButton("▶  Launch Session")
        launch_btn.setFixedHeight(44)
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white; border: none;
                border-radius: 8px;
                font-size: 14px; font-weight: 600;
                margin-top: 10px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: #5b21b6; }}
        """)
        launch_btn.clicked.connect(self._launch_session)
        lf_main.addWidget(launch_btn)
        body.addWidget(launch_frame)

        # RIGHT: Sessions Monitor
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        sessions_frame = QFrame()
        sessions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                border: none;
            }}
        """)
        sf_layout = QVBoxLayout(sessions_frame)
        sf_layout.setContentsMargins(20, 18, 20, 18)
        sf_layout.setSpacing(12)
        sf_hdr = QHBoxLayout()
        sf_hdr.addWidget(QLabel("ACTIVE SESSIONS", styleSheet=
            f"color: {DarkPalette.TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 12px;"))
        sf_hdr.addStretch()
        sf_layout.addLayout(sf_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(140)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background-color: transparent; width: 6px; }
            QScrollBar::handle:vertical {
                background-color: rgba(255,255,255,0.1);
                border-radius: 3px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background-color: rgba(255,255,255,0.18); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._list_container = QWidget()
        self._list_container.setStyleSheet("background-color: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(10)
        self._list_layout.setContentsMargins(0, 0, 6, 0)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._empty_container = QWidget()
        self._empty_container.setMinimumHeight(120)
        empty_layout = QVBoxLayout(self._empty_container)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)
        empty_layout.setContentsMargins(0, 16, 0, 16)
        empty_icon = QLabel("◻")
        empty_icon.setStyleSheet(f"color: {DarkPalette.BORDER}; font-size: 28px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        self._empty_label = QLabel("No active sessions")
        self._empty_label.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 14px; font-weight: 500;"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_label)
        empty_hint = QLabel("Configure a session using the panel on the left")
        empty_hint.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_hint)
        self._list_layout.addWidget(self._empty_container)
        scroll.setWidget(self._list_container)
        sf_layout.addWidget(scroll)
        right_col.addWidget(sessions_frame, 1)

        # Inspector (bottom)
        inspector_frame = QFrame()
        inspector_frame.setFixedHeight(240)
        inspector_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 12px;
            }}
        """)
        insp_layout = QVBoxLayout(inspector_frame)
        insp_layout.setContentsMargins(20, 16, 20, 16)
        insp_layout.setSpacing(10)
        insp_hdr = QHBoxLayout()
        insp_hdr.addWidget(QLabel("INSPECTOR", styleSheet=
            f"color: {DarkPalette.TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 10px;"))
        insp_hdr.addStretch()
        insp_layout.addLayout(insp_hdr)

        insp_body = QHBoxLayout()
        insp_body.setSpacing(16)

        ss_col = QVBoxLayout()
        ss_col.setSpacing(6)
        ss_col.addWidget(QLabel("LIVE PREVIEW", styleSheet=
            f"color: {DarkPalette.TEXT_DIM}; font-size: 9px; font-weight: 600; letter-spacing: 0.5px;"))
        self.screenshot_label = QLabel("no screenshot")
        self.screenshot_label.setFixedSize(240, 152)
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setStyleSheet(f"""
            QLabel {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT_DIM};
                border: 1px dashed rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 11px;
            }}
        """)
        ss_col.addWidget(self.screenshot_label)
        insp_body.addLayout(ss_col)

        js_col = QVBoxLayout()
        js_col.setSpacing(6)
        js_col.addWidget(QLabel("JS CONSOLE", styleSheet=
            f"color: {DarkPalette.TEXT_DIM}; font-size: 9px; font-weight: 600; letter-spacing: 0.5px;"))
        self.js_input = QTextEdit()
        self.js_input.setPlaceholderText("navigator.userAgent")
        self.js_input.setFixedHeight(62)
        self.js_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
            }}
            QTextEdit:hover {{
                border-color: rgba(124, 58, 237, 0.3);
                background-color: rgba(124, 58, 237, 0.03);
            }}
            QTextEdit:focus {{ border-color: {DarkPalette.ACCENT}; }}
        """)
        palette = self.js_input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(DarkPalette.TEXT_DIM))
        self.js_input.setPalette(palette)
        js_col.addWidget(self.js_input)
        run_btn = QPushButton("▶  Run")
        run_btn.setFixedHeight(30)
        run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(124, 58, 237, 0.1);
                color: {DarkPalette.ACCENT};
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 5px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: rgba(124, 58, 237, 0.2); }}
        """)
        run_btn.clicked.connect(self._run_js)
        js_col.addWidget(run_btn)
        self.eval_result = QTextEdit()
        self.eval_result.setReadOnly(True)
        self.eval_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.BACKGROUND};
                color: #a6e3a1;
                border: 1px solid rgba(166, 227, 161, 0.1);
                border-radius: 6px;
                padding: 8px;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        js_col.addWidget(self.eval_result, 1)
        insp_body.addLayout(js_col, 1)
        insp_layout.addLayout(insp_body, 1)
        right_col.addWidget(inspector_frame)

        body.addLayout(right_col, 1)
        root.addLayout(body, 1)


    # ── helpers ──────────────────────────────────────────────────────────────

    def _reload_profiles(self):
        self.profile_combo.clear()
        try:
            pm = ProfileManager()
            profile_names = pm.list()
            for name in sorted(profile_names):
                self.profile_combo.addItem(name)
        except Exception as e:
            print(f"[SessionsPage] Error loading profiles: {e}")

    @staticmethod
    def _ff_version():
        try:
            with open(Path(__file__).parent.parent / "camoufox-source" / "upstream.sh") as f:
                for line in f:
                    if line.startswith("version="):
                        return line.strip().split("=", 1)[1]
        except Exception:
            pass
        return "146.0.1"

    @staticmethod
    def _ff_release():
        try:
            with open(Path(__file__).parent.parent / "camoufox-source" / "upstream.sh") as f:
                for line in f:
                    if line.startswith("release="):
                        return line.strip().split("=", 1)[1]
        except Exception:
            pass
        return "beta.25"

    @staticmethod
    def _build_target():
        import platform
        m = platform.machine()
        if m == "arm64":
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"

    def _launch_session(self):
        profile = self.profile_combo.currentText()
        if not profile:
            QMessageBox.warning(self, "Launch", "No profile selected.")
            return
        headless = self.headless_cb.isChecked()
        url = self.url_input.text().strip() or None
        sid = str(uuid.uuid4())[:8]
        
        # Get browser binary path
        _CUSTOM_BIN = None
        
        # Priority 1: Check settings
        if _SETTINGS_PATH.exists():
            try:
                settings = json.loads(_SETTINGS_PATH.read_text())
                browser_binary_setting = settings.get("browser_binary", "").strip()
                if browser_binary_setting and Path(browser_binary_setting).exists():
                    _CUSTOM_BIN = browser_binary_setting
            except Exception:
                pass
        
        # Priority 2: Auto-detect if not in settings
        if not _CUSTOM_BIN:
            # Auto-detect Tegufox binary from project structure
            _PROJECT_ROOT = str(Path(__file__).parent.parent)  # Go up one level from tegufox_gui/
            
            # First, check ./build/ directory (new location)
            for _app_name in ("Tegufox.app", "Camoufox.app"):
                for _bin_name in ("tegufox", "camoufox"):
                    _candidate = (
                        Path(_PROJECT_ROOT) / "build"
                        / _app_name / "Contents" / "MacOS" / _bin_name
                    )
                    if _candidate.exists():
                        _CUSTOM_BIN = str(_candidate)
                        break
                if _CUSTOM_BIN:
                    break
            
            # Fallback: check old location (camoufox-source/.../obj-*/dist/)
            if not _CUSTOM_BIN:
                for _app_name in ("Tegufox.app", "Camoufox.app"):
                    for _bin_name in ("tegufox", "camoufox"):
                        _candidate = (
                            Path(_PROJECT_ROOT) / "camoufox-source"
                            / f"camoufox-{self._ff_version()}-{self._ff_release()}"
                            / f"obj-{self._build_target()}" / "dist"
                            / _app_name / "Contents" / "MacOS" / _bin_name
                        )
                        if _candidate.exists():
                            _CUSTOM_BIN = str(_candidate)
                            break
                    if _CUSTOM_BIN:
                        break
            
            # Priority 3: env var
            if not _CUSTOM_BIN:
                _CUSTOM_BIN = os.environ.get("TEGUFOX_BINARY")
        
        browser_bin = _CUSTOM_BIN if self.custom_build_cb.isChecked() else None
        worker = SessionWorker(sid, profile, headless, browser_binary=browser_bin)
        worker.status_changed.connect(self._on_status_changed)
        _gui_sessions[sid] = worker
        self._add_session_row(sid, profile)
        worker.start()
        if url:
            nav_url = url

            def _nav():
                for _ in range(50):
                    if worker.status == "running":
                        try:
                            worker.execute(lambda s: s.goto(nav_url))
                        except Exception as exc:
                            print(f"[Sessions] goto error: {exc}")
                        return
                    time.sleep(0.1)

            threading.Thread(target=_nav, daemon=True).start()

    def _add_session_row(self, sid: str, profile: str):
        self._empty_container.setVisible(False)
        self._session_count_lbl.setText(str(len(_gui_sessions)))
        row = QFrame()
        row.setFixedHeight(72)
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkPalette.CARD};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 10px;
            }}
            QFrame:hover {{ 
                border-color: rgba(124, 58, 237, 0.5);
                background-color: rgba(124, 58, 237, 0.03);
            }}
            QLabel {{
                border: none;
                background-color: transparent;
            }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(20, 14, 18, 14)
        rl.setSpacing(16)
        
        # Left: Status indicator + Session info
        left_section = QHBoxLayout()
        left_section.setSpacing(14)
        
        status_dot = QLabel("●")
        status_dot.setFixedWidth(10)
        status_dot.setStyleSheet("color: #f9e2af; font-size: 10px; border: none;")
        left_section.addWidget(status_dot)
        
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        
        id_lbl = QLabel(sid)
        id_lbl.setStyleSheet(
            f"color: {DarkPalette.ACCENT}; font-size: 13px; "
            "font-family: 'Menlo', 'Monaco', monospace; font-weight: 700; border: none;"
        )
        info_col.addWidget(id_lbl)
        
        prof_lbl = QLabel(profile)
        prof_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px; font-weight: 500; border: none;")
        info_col.addWidget(prof_lbl)
        
        left_section.addLayout(info_col)
        rl.addLayout(left_section, 1)
        
        # Right: Status + Actions
        status_lbl = QLabel("starting")
        status_lbl.setFixedWidth(64)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_lbl.setStyleSheet("color: #f9e2af; font-size: 11px; font-weight: 600; border: none;")
        rl.addWidget(status_lbl)
        
        shot_btn = QPushButton("📷")
        shot_btn.setFixedSize(36, 36)
        shot_btn.setToolTip("Screenshot")
        shot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.ACCENT};
                border: 1px solid rgba(124, 58, 237, 0.25);
                border-radius: 8px; 
                font-size: 14px;
            }}
            QPushButton:hover {{ 
                background-color: rgba(124, 58, 237, 0.15);
                border-color: {DarkPalette.ACCENT};
            }}
        """)
        shot_btn.clicked.connect(lambda _chk, s=sid: self._take_screenshot(s))
        rl.addWidget(shot_btn)
        
        stop_btn = QPushButton("■")
        stop_btn.setFixedSize(36, 36)
        stop_btn.setToolTip("Stop session")
        stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkPalette.RED};
                border: 1px solid rgba(243, 139, 168, 0.25);
                border-radius: 8px; 
                font-size: 12px;
            }}
            QPushButton:hover {{ 
                background-color: rgba(243, 139, 168, 0.15);
                border-color: {DarkPalette.RED};
            }}
        """)
        stop_btn.clicked.connect(lambda _chk, s=sid: self._stop_session(s))
        rl.addWidget(stop_btn)
        
        self._list_layout.addWidget(row)
        self._row_widgets[sid] = {"row": row, "status_lbl": status_lbl, "dot": status_dot}
        self._detail_session_id = sid

    def _on_status_changed(self, sid: str, status: str):
        if sid not in self._row_widgets:
            return
        color_map = {
            "running":  "#a6e3a1",
            "error":    DarkPalette.RED,
            "stopped":  DarkPalette.TEXT_DIM,
            "starting": "#f9e2af",
        }
        color = color_map.get(status, DarkPalette.TEXT_DIM)
        lbl = self._row_widgets[sid]["status_lbl"]
        lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        lbl.setText(status)
        dot = self._row_widgets[sid].get("dot")
        if dot:
            dot.setStyleSheet(f"color: {color}; font-size: 9px;")

    def _poll_status(self):
        for sid, worker in list(_gui_sessions.items()):
            if sid in self._row_widgets:
                self._row_widgets[sid]["status_lbl"].setText(worker.status)

    def _take_screenshot(self, sid: str):
        worker = _gui_sessions.get(sid)
        if not worker:
            return
        try:
            raw = worker.execute(lambda s: s.page.screenshot())
            pixmap = QPixmap()
            pixmap.loadFromData(raw)
            scaled = pixmap.scaled(
                320, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.screenshot_label.setPixmap(scaled)
            self._detail_session_id = sid
        except Exception as exc:
            self.screenshot_label.setText(f"Error:\n{exc}")

    def _stop_session(self, sid: str):
        worker = _gui_sessions.pop(sid, None)
        if worker:
            worker.stop_session()
        if sid in self._row_widgets:
            self._row_widgets.pop(sid)["row"].deleteLater()
        self._session_count_lbl.setText(str(len(_gui_sessions)))
        if not _gui_sessions:
            self._empty_container.setVisible(True)

    def _run_js(self):
        sid = self._detail_session_id
        worker = _gui_sessions.get(sid)
        if not worker:
            self.eval_result.setPlainText("No session selected.")
            return
        expr = self.js_input.toPlainText().strip()
        if not expr:
            return
        try:
            result = worker.execute(lambda s: s.page.evaluate(expr))
            self.eval_result.setPlainText(str(result))
        except Exception as exc:
            self.eval_result.setPlainText(f"Error: {exc}")


