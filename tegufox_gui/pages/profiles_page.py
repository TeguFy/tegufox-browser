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

    _SORT_OPTIONS = ["Name A→Z", "Name Z→A", "Date newest", "Date oldest"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_cards: list = []
        self._main_window = None  # Will be set by main window
        self.profile_manager = ProfileManager()
        self._selected_profiles = set()  # Track selected profile names
        self._setup_ui()
        self.load_profiles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(8)

        # Compact header row
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        self.title_lbl = QLabel("Profiles")
        self.title_lbl.setStyleSheet(
            f"color: {DarkPalette.TEXT}; font-size: 18px; font-weight: 600;"
        )
        hdr.addWidget(self.title_lbl)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(self._SORT_OPTIONS)
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 10px; min-width: 110px; font-size: 12px;
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
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 12px; min-width: 160px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {DarkPalette.ACCENT}; }}
        """)
        self.search_input.textChanged.connect(self._apply_filter)
        hdr.addWidget(self.search_input)

        hdr.addStretch()

        # Selection controls group
        select_all_btn = QPushButton("All")
        select_all_btn.setFixedSize(42, 32)
        select_all_btn.setToolTip("Select All")
        select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        select_all_btn.clicked.connect(self.select_all_profiles)
        hdr.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("None")
        deselect_all_btn.setFixedSize(48, 32)
        deselect_all_btn.setToolTip("Deselect All")
        deselect_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        deselect_all_btn.clicked.connect(self.deselect_all_profiles)
        hdr.addWidget(deselect_all_btn)

        # Delete selected button
        self.delete_selected_btn = QPushButton("🗑 Delete")
        self.delete_selected_btn.setFixedHeight(32)
        self.delete_selected_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(243,139,168,0.15); 
                color: {DarkPalette.RED};
                border: 1px solid {DarkPalette.RED}; border-radius: 4px;
                padding: 4px 12px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: rgba(243,139,168,0.3); }}
            QPushButton:disabled {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT_DIM};
                border-color: {DarkPalette.BORDER};
            }}
        """)
        self.delete_selected_btn.clicked.connect(self.delete_selected_profiles)
        self.delete_selected_btn.setEnabled(False)
        hdr.addWidget(self.delete_selected_btn)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        refresh_btn.clicked.connect(self.refresh_profiles)
        hdr.addWidget(refresh_btn)

        create_btn = QPushButton("+ New")
        create_btn.setFixedHeight(32)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT}; color: white;
                border: none; border-radius: 4px;
                padding: 4px 14px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        create_btn.clicked.connect(self.open_profile_creator)
        hdr.addWidget(create_btn)

        layout.addLayout(hdr)

        # Column header bar
        col_hdr = QWidget()
        col_hdr.setFixedHeight(24)
        ch_row = QHBoxLayout(col_hdr)
        ch_row.setContentsMargins(16, 0, 12, 0)
        ch_row.setSpacing(10)
        COL_STYLE = f"color: {DarkPalette.TEXT_DIM}; font-size: 11px; font-weight: 600;"
        
        # Add checkbox column spacer
        spacer = QLabel("")
        spacer.setFixedWidth(20)
        ch_row.addWidget(spacer)
        
        for txt, w, stretch in [
            ("BROWSER", 120, 0), ("NAME", 0, 1), ("PLATFORM", 68, 0),
            ("CREATED", 90, 0), ("", 76, 0),
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

        try:
            profile_names = self.profile_manager.list()
            for name in sorted(profile_names):
                try:
                    data = self.profile_manager.load(name)
                    if not data:
                        continue
                    card = ProfileCard(data)
                    card.clicked.connect(self.on_profile_clicked)
                    card.delete_requested.connect(self.on_profile_delete)
                    card.launch_requested.connect(self.on_profile_launch)
                    card.selection_changed.connect(self.on_selection_changed)
                    self._all_cards.append(card)
                except Exception as e:
                    print(f"[ProfilesList] Error loading profile {name}: {e}")
        except Exception as e:
            print(f"[ProfilesList] Error listing profiles: {e}")

        self._update_title(len(self._all_cards))
        self._apply_filter()

    def refresh_profiles(self):
        self.load_profiles()
    
    def select_all_profiles(self):
        """Select all visible profiles"""
        for card in self._all_cards:
            if card.isVisible():
                card.set_selected(True)
    
    def deselect_all_profiles(self):
        """Deselect all profiles"""
        for card in self._all_cards:
            card.set_selected(False)
    
    def on_selection_changed(self, profile_name: str, is_selected: bool):
        """Handle profile selection change"""
        if is_selected:
            self._selected_profiles.add(profile_name)
        else:
            self._selected_profiles.discard(profile_name)
        
        # Enable/disable delete button based on selection
        self.delete_selected_btn.setEnabled(len(self._selected_profiles) > 0)
    
    def delete_selected_profiles(self):
        """Delete all selected profiles"""
        if not self._selected_profiles:
            return
        
        count = len(self._selected_profiles)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {count} selected profile(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete profiles
        failed = []
        for profile_name in list(self._selected_profiles):
            try:
                self.profile_manager.delete(profile_name)
            except Exception as e:
                failed.append(f"{profile_name}: {str(e)}")
        
        # Clear selection
        self._selected_profiles.clear()
        
        # Reload profiles
        self.load_profiles()
        
        # Show error if any deletions failed
        if failed:
            QMessageBox.warning(
                self, "Deletion Errors",
                f"Failed to delete some profiles:\n" + "\n".join(failed)
            )
    
    def open_profile_creator(self):
        """Switch to Create Profile page"""
        if self._main_window:
            self._main_window.switch_page(3)  # Index 3 is Create Profile page

    def _update_title(self, count: int):
        self.title_lbl.setText(f"Profiles ({count})")

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
