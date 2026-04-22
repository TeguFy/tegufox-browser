"""Profiles list page widget"""

import pprint
import sys
import subprocess
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QTextEdit,
    QMessageBox,
    QDialog,
)
from PyQt6.QtCore import Qt

from tegufox_gui.utils.styles import DarkPalette
from tegufox_gui.components import ProfileCard
from tegufox_core.profile_manager import ProfileManager

class ProfilesListWidget(QWidget):
    """Profile list page with live search, sort, and compact rows."""

    _SORT_OPTIONS = ["Name A→Z", "Name Z→A", "Date newest", "Date oldest", "Score ↓"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_cards: list = []
        self._main_window = None  # Will be set by main window
        self.profile_manager = ProfileManager()
        self._setup_ui()
        self.load_profiles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.setSpacing(12)

        self.title_lbl = QLabel("Browser Profiles")
        self.title_lbl.setStyleSheet(
            f"color: {DarkPalette.TEXT}; font-size: 26px; font-weight: bold;"
        )
        hdr.addWidget(self.title_lbl)
        hdr.addStretch()

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(self._SORT_OPTIONS)
        self.sort_combo.setFixedHeight(36)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; 
                padding: 6px 12px; min-width: 130px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                selection-background-color: {DarkPalette.ACCENT};
            }}
        """)
        self.sort_combo.currentIndexChanged.connect(self._apply_filter)
        hdr.addWidget(self.sort_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search profiles...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; 
                padding: 6px 14px; min-width: 200px;
            }}
            QLineEdit:focus {{ border-color: {DarkPalette.ACCENT}; }}
        """)
        self.search_input.textChanged.connect(self._apply_filter)
        hdr.addWidget(self.search_input)

        create_btn = QPushButton("+ Create Profile")
        create_btn.setFixedHeight(36)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT}; color: white;
                border: none; 
                padding: 6px 16px; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        create_btn.clicked.connect(self.open_profile_creator)
        hdr.addWidget(create_btn)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; 
                padding: 6px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        refresh_btn.clicked.connect(self.refresh_profiles)
        hdr.addWidget(refresh_btn)

        layout.addLayout(hdr)

        # Column header bar
        col_hdr = QWidget()
        col_hdr.setFixedHeight(24)
        ch_row = QHBoxLayout(col_hdr)
        ch_row.setContentsMargins(16, 0, 12, 0)
        ch_row.setSpacing(10)
        COL_STYLE = f"color: {DarkPalette.TEXT_DIM}; font-size: 11px; font-weight: 600;"
        for txt, w, stretch in [
            ("BROWSER", 120, 0), ("NAME", 0, 1), ("PLATFORM", 68, 0),
            ("SCORE", 52, 0), ("DATE", 46, 0), ("", 76, 0),
        ]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(COL_STYLE)
            if w:
                lbl.setFixedWidth(w)
            if stretch:
                ch_row.addWidget(lbl, stretch)
            else:
                ch_row.addWidget(lbl)
        layout.addWidget(col_hdr)

        # Scroll list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background-color: {DarkPalette.BACKGROUND};")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

    def load_profiles(self):
        while self._list_layout.count():
            self._list_layout.takeAt(0)
        self._all_cards.clear()

        engine = None
        try:
            from tegufox_core.consistency_engine import ConsistencyEngine, default_rules
            engine = ConsistencyEngine(default_rules())
        except Exception as e:
            print(f"[ProfilesList] ConsistencyEngine error: {e}")

        try:
            profile_names = self.profile_manager.list()
            for name in sorted(profile_names):
                try:
                    data = self.profile_manager.load(name)
                    if not data:
                        continue
                    score = None
                    if engine and "navigator" in data:
                        try:
                            score = engine.evaluate(data).score
                        except Exception:
                            pass
                    card = ProfileCard(data, score=score)
                    card.clicked.connect(self.on_profile_clicked)
                    card.delete_requested.connect(self.on_profile_delete)
                    card.launch_requested.connect(self.on_profile_launch)
                    self._all_cards.append(card)
                except Exception as e:
                    print(f"[ProfilesList] Error loading profile {name}: {e}")
        except Exception as e:
            print(f"[ProfilesList] Error listing profiles: {e}")

        self._update_title(len(self._all_cards))
        self._apply_filter()

    def refresh_profiles(self):
        self.load_profiles()
    
    def open_profile_creator(self):
        """Switch to Create Profile page"""
        if self._main_window:
            self._main_window.switch_page(3)  # Index 3 is Create Profile page

    def _update_title(self, count: int):
        self.title_lbl.setText(f"Browser Profiles ({count})")

    def _apply_filter(self):
        text = getattr(self, "search_input", None)
        text = text.text() if text else ""
        sort_idx = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0

        visible = [c for c in self._all_cards if c.matches(text)]

        if sort_idx == 0:
            visible.sort(key=lambda c: c._name.lower())
        elif sort_idx == 1:
            visible.sort(key=lambda c: c._name.lower(), reverse=True)
        elif sort_idx == 2:
            visible.sort(key=lambda c: c.profile_data.get("created", ""), reverse=True)
        elif sort_idx == 3:
            visible.sort(key=lambda c: c.profile_data.get("created", ""))
        elif sort_idx == 4:
            visible.sort(key=lambda c: (c.score is None, -(c.score or 0)))

        while self._list_layout.count():
            self._list_layout.takeAt(0)
        for card in self._all_cards:
            card.setVisible(False)
        for card in visible:
            card.setVisible(True)
            self._list_layout.addWidget(card)

    def on_profile_clicked(self, profile_name):
        try:
            data = self.profile_manager.load(profile_name)
            if not data:
                return
        except Exception as e:
            print(f"[ProfilesList] Error loading profile {profile_name}: {e}")
            return

        nav = data.get("navigator", {})
        cfg = data.get("config", {})
        webgl = data.get("webgl", {})
        ua = nav.get("userAgent") or cfg.get("navigator.userAgent", "")
        webgl_vendor = webgl.get("vendor") or cfg.get("webGl:vendor", "")
        webgl_renderer = webgl.get("renderer") or cfg.get("webGl:renderer", "")

        lines = [
            f"Name: {profile_name}",
            f"Created: {data.get('created', '—')}",
        ]
        if ua:
            lines.append(f"User-Agent: {ua}")
        lines.append(f"WebGL Vendor: {webgl_vendor or '—'}")
        lines.append(f"WebGL Renderer: {webgl_renderer or '—'}")

        info_src = nav if nav else cfg
        for k, v in list(info_src.items())[:10]:
            lines.append(f"  {k}: {str(v)[:60]}")

        # Open editable detail dialog so user can inspect and update profile data.
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Profile Detail - {profile_name}")
        dlg.resize(900, 700)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(14, 14, 14, 14)
        dlg_layout.setSpacing(10)

        summary = QTextEdit()
        summary.setReadOnly(True)
        summary.setMinimumHeight(180)
        summary.setPlainText("\n".join(lines))
        summary.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                font-size: 12px;
            }}
        """)
        dlg_layout.addWidget(summary)

        editor_label = QLabel("Profile Data")
        editor_label.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px; font-weight: 600;")
        dlg_layout.addWidget(editor_label)

        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(pprint.pformat(data, indent=2, width=100, compact=False))
        editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.BACKGROUND};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        dlg_layout.addWidget(editor, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        btn_row.addWidget(close_btn)
        dlg_layout.addLayout(btn_row)

        close_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def on_profile_delete(self, profile_name):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete profile '{profile_name}'?  This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.profile_manager.delete(profile_name)
            self._all_cards = [c for c in self._all_cards if c._name != profile_name]
            self._update_title(len(self._all_cards))
            self._apply_filter()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def on_profile_launch(self, profile_name):
        # Verify profile exists in database
        try:
            data = self.profile_manager.load(profile_name)
            if not data:
                QMessageBox.warning(self, "Error", f"Profile not found: {profile_name}")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load profile: {e}")
            return
        try:
            cwd = str(Path.cwd())
            script_lines = [
                "import sys, time, warnings, logging",
                "logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')",
                "warnings.filterwarnings('ignore')",
                f"sys.path.insert(0, {repr(cwd)})",
                "from tegufox_automation import TegufoxSession, SessionConfig",
                f"profile_name = {repr(profile_name)}",
                "try:",
                "    with TegufoxSession(profile_name, config=SessionConfig(headless=False)) as sess:",
                "        sess.page.goto('https://www.browserscan.net/bot-detection')",
                "        while True:",
                "            try: sess.page.title(); time.sleep(1)",
                "            except: break",
                "except Exception as e:",
                "    import traceback; traceback.print_exc()",
                "    input('Press Enter to close...')",
            ]
            import tempfile, os
            fd, tmp = tempfile.mkstemp(suffix='.py', prefix='tgf_')
            os.close(fd)
            Path(tmp).write_text("\n".join(script_lines))
            log_file = Path(cwd) / "tegufox_launch.log"
            with open(log_file, 'w') as lf:
                subprocess.Popen([sys.executable, tmp], stdout=lf, stderr=lf)
        except Exception as exc:
            QMessageBox.critical(self, "Launch Error", str(exc))
