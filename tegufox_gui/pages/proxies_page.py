"""Proxies management page widget"""

from PyQt6.QtWidgets import (
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
    QFrame,
    QCheckBox,
    QFormLayout,
    QSpinBox,
    QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
import random

from tegufox_gui.utils.styles import DarkPalette
from tegufox_gui.utils.pagination import compute_page_window
from tegufox_core.proxy_manager import ProxyManager, pool_to_profile_snapshot
from tegufox_core.profile_manager import ProfileManager


class ProxyTestWorker(QThread):
    """Worker thread to test proxy"""
    
    test_completed = pyqtSignal(str, dict)  # proxy_name, result
    
    def __init__(self, proxy_name: str, proxy_manager: ProxyManager, parent=None):
        super().__init__(parent)
        self.proxy_name = proxy_name
        self.proxy_manager = proxy_manager
    
    def run(self):
        """Test proxy and emit result"""
        result = self.proxy_manager.test_proxy(self.proxy_name)
        self.test_completed.emit(self.proxy_name, result)


class ProxyCard(QFrame):
    """Compact proxy row"""
    
    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    test_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    selection_changed = pyqtSignal(str, bool)  # proxy_name, is_selected
    
    def __init__(self, proxy_data: dict, parent=None):
        super().__init__(parent)
        self.proxy_data = proxy_data
        self._name = proxy_data.get("name", "")
        self._selected = False
        self._testing = False
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
        
        # Checkbox
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
        
        # Name
        name_lbl = QLabel(self._name)
        name_lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
        row.addWidget(name_lbl, 1)
        
        # Host:Port
        host_port = f"{self.proxy_data.get('host', '')}:{self.proxy_data.get('port', '')}"
        host_lbl = QLabel(host_port)
        host_lbl.setFixedWidth(150)
        host_lbl.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 12px;")
        row.addWidget(host_lbl)
        
        # Username (masked)
        username = self.proxy_data.get("username", "")
        username_display = username if username else "—"
        if username and len(username) > 3:
            username_display = username[:2] + "***"
        user_lbl = QLabel(username_display)
        user_lbl.setFixedWidth(120)
        user_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 12px;")
        row.addWidget(user_lbl)
        
        # Status badge
        status = self.proxy_data.get("status", "inactive")
        self.status_badge = QLabel(status.upper())
        self.status_badge.setFixedWidth(80)
        self._update_status_style(status)
        row.addWidget(self.status_badge)
        
        # Last IP
        last_ip = self.proxy_data.get("last_ip", "")
        self.ip_lbl = QLabel(last_ip or "—")
        self.ip_lbl.setFixedWidth(120)
        self.ip_lbl.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 12px; font-family: 'Monaco', 'Menlo', 'Courier New', monospace;")
        row.addWidget(self.ip_lbl)
        
        # Action buttons
        self.test_btn = QPushButton("🔍")
        self.test_btn.setFixedSize(32, 32)
        self.test_btn.setToolTip("Test Proxy")
        self.test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        self.test_btn.clicked.connect(lambda: self.test_requested.emit(self._name))
        row.addWidget(self.test_btn)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setToolTip("Edit")
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._name))
        row.addWidget(edit_btn)
        
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(32, 32)
        del_btn.setToolTip("Delete")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(243,139,168,0.15);
                color: {DarkPalette.RED};
                border: 1px solid {DarkPalette.RED};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: rgba(243,139,168,0.3); }}
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))
        row.addWidget(del_btn)
    
    def _update_status_style(self, status: str):
        """Update status badge color"""
        if status == "active":
            bg_color = "rgba(166,227,161,0.15)"
            text_color = "#a6e3a1"
        elif status == "failed":
            bg_color = "rgba(243,139,168,0.15)"
            text_color = "#f38ba8"
        else:  # inactive
            bg_color = "rgba(186,194,222,0.15)"
            text_color = "#bac2de"
        
        self.status_badge.setStyleSheet(f"""
            color: {text_color};
            font-size: 10px;
            font-weight: 600;
            background-color: {bg_color};
            padding: 4px 8px;
            border-radius: 3px;
        """)
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change"""
        self._selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self._name, self._selected)
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self._selected = selected
        self.checkbox.setChecked(selected)
    
    def set_testing(self, testing: bool):
        """Set testing state"""
        self._testing = testing
        if testing:
            self.test_btn.setText("⏳")
            self.test_btn.setEnabled(False)
        else:
            self.test_btn.setText("🔍")
            self.test_btn.setEnabled(True)
    
    def update_status(self, status: str, last_ip: str = None):
        """Update proxy status and IP"""
        self.proxy_data["status"] = status
        self.status_badge.setText(status.upper())
        self._update_status_style(status)
        
        if last_ip:
            self.proxy_data["last_ip"] = last_ip
            self.ip_lbl.setText(last_ip)
    
    def matches(self, query: str) -> bool:
        """Check if proxy matches search query"""
        query = query.lower()
        return (
            query in self._name.lower()
            or query in self.proxy_data.get("host", "").lower()
            or query in self.proxy_data.get("username", "").lower()
        )


class ProxiesWidget(QWidget):
    """Proxy management page"""

    _SORT_OPTIONS = ["Name A→Z", "Name Z→A", "Date newest", "Date oldest"]
    _PAGE_SIZE_OPTIONS = [50, 100, 200, 0]  # 0 sentinel = "All"
    _PAGE_SIZE_LABELS = ["50", "100", "200", "All"]
    _DEFAULT_PAGE_SIZE = 100
    _SORT_NEWEST_INDEX = 2  # matches "Date newest" in _SORT_OPTIONS
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_cards = []
        self.proxy_manager = ProxyManager()
        self.profile_manager = ProfileManager()
        self._selected_proxies = set()
        self._active_tests = {}  # proxy_name -> ProxyTestWorker

        # Pagination state (spec §4)
        settings = QSettings("Tegufox", "GUI")
        raw_size = settings.value("proxies/page_size", self._DEFAULT_PAGE_SIZE, type=int)
        self._page_size = (
            raw_size if raw_size in self._PAGE_SIZE_OPTIONS else self._DEFAULT_PAGE_SIZE
        )
        self._current_page = 1
        self._visible_filtered: list = []

        self._setup_ui()
        self.load_proxies()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(8)
        
        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        
        self.title_lbl = QLabel("Proxies")
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

        # Page-size dropdown (spec §3.1)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(self._PAGE_SIZE_LABELS)
        self.page_size_combo.setCurrentIndex(self._PAGE_SIZE_OPTIONS.index(self._page_size))
        self.page_size_combo.setFixedHeight(32)
        self.page_size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 10px; min-width: 70px; font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                selection-background-color: {DarkPalette.ACCENT};
            }}
        """)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        hdr.addWidget(QLabel("Show:"))
        hdr.addWidget(self.page_size_combo)

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
        
        # Selection controls
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
        select_all_btn.clicked.connect(self.select_all_proxies)
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
        deselect_all_btn.clicked.connect(self.deselect_all_proxies)
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
        self.delete_selected_btn.clicked.connect(self.delete_selected_proxies)
        self.delete_selected_btn.setEnabled(False)
        hdr.addWidget(self.delete_selected_btn)
        
        # Test selected button
        self.test_selected_btn = QPushButton("🔍 Test")
        self.test_selected_btn.setFixedHeight(32)
        self.test_selected_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(166,227,161,0.15); 
                color: #a6e3a1;
                border: 1px solid #a6e3a1; border-radius: 4px;
                padding: 4px 12px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: rgba(166,227,161,0.3); }}
            QPushButton:disabled {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT_DIM};
                border-color: {DarkPalette.BORDER};
            }}
        """)
        self.test_selected_btn.clicked.connect(self.test_selected_proxies)
        self.test_selected_btn.setEnabled(False)
        hdr.addWidget(self.test_selected_btn)

        auto_assign_btn = QPushButton("⚡ Auto-Assign")
        auto_assign_btn.setFixedHeight(32)
        auto_assign_btn.setToolTip("Assign proxies to profiles that have none")
        auto_assign_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(249,226,175,0.15);
                color: #f9e2af;
                border: 1px solid #f9e2af; border-radius: 4px;
                padding: 4px 12px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: rgba(249,226,175,0.3); }}
        """)
        auto_assign_btn.clicked.connect(self.open_auto_assign_dialog)
        hdr.addWidget(auto_assign_btn)

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
        refresh_btn.clicked.connect(self.refresh_proxies)
        hdr.addWidget(refresh_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.setFixedHeight(32)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT}; color: white;
                border: none; border-radius: 4px;
                padding: 4px 14px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        import_btn.clicked.connect(self.open_import_dialog)
        hdr.addWidget(import_btn)
        
        layout.addLayout(hdr)
        
        # Column headers
        col_hdr = QWidget()
        col_hdr.setFixedHeight(24)
        ch_row = QHBoxLayout(col_hdr)
        ch_row.setContentsMargins(16, 0, 12, 0)
        ch_row.setSpacing(10)
        COL_STYLE = f"color: {DarkPalette.TEXT_DIM}; font-size: 11px; font-weight: 600;"
        
        spacer = QLabel("")
        spacer.setFixedWidth(20)
        ch_row.addWidget(spacer)
        
        for txt, w, stretch in [
            ("NAME", 0, 1), ("HOST:PORT", 150, 0), ("USERNAME", 120, 0),
            ("STATUS", 80, 0), ("LAST IP", 120, 0), ("", 100, 0),
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

        # Pagination footer (spec §3.2). Hidden until first render decides
        # whether it's needed.
        self.pagination_footer = QWidget()
        self.pagination_footer.setStyleSheet(
            f"background-color: {DarkPalette.BACKGROUND};"
        )
        footer_row = QHBoxLayout(self.pagination_footer)
        footer_row.setContentsMargins(0, 6, 0, 0)
        footer_row.setSpacing(6)

        self.page_bar_container = QWidget()
        self.page_bar_layout = QHBoxLayout(self.page_bar_container)
        self.page_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.page_bar_layout.setSpacing(4)
        footer_row.addWidget(self.page_bar_container)

        footer_row.addStretch()

        self.page_status_lbl = QLabel("")
        self.page_status_lbl.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;"
        )
        footer_row.addWidget(self.page_status_lbl)

        self.pagination_footer.setVisible(False)
        layout.addWidget(self.pagination_footer)
    
    def load_proxies(self):
        """Load all proxies from database"""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for card in self._all_cards:
            card.setParent(None)
            card.deleteLater()
        self._all_cards.clear()
        
        try:
            proxy_names = self.proxy_manager.list()
            for name in sorted(proxy_names):
                try:
                    data = self.proxy_manager.load(name)
                    if not data:
                        continue
                    card = ProxyCard(data)
                    card.clicked.connect(self.on_proxy_clicked)
                    card.delete_requested.connect(self.on_proxy_delete)
                    card.test_requested.connect(self.on_proxy_test)
                    card.edit_requested.connect(self.on_proxy_edit)
                    card.selection_changed.connect(self.on_selection_changed)
                    self._all_cards.append(card)
                except Exception as e:
                    print(f"[ProxiesList] Error loading proxy {name}: {e}")
        except Exception as e:
            print(f"[ProxiesList] Error listing proxies: {e}")
        
        self._update_title(len(self._all_cards))
        self._apply_filter()
    
    def refresh_proxies(self):
        """Refresh proxy list"""
        self.load_proxies()
    
    def select_all_proxies(self):
        """Select all visible proxies"""
        for card in self._all_cards:
            if card.isVisible():
                card.set_selected(True)
    
    def deselect_all_proxies(self):
        """Deselect all proxies"""
        for card in self._all_cards:
            card.set_selected(False)
    
    def on_selection_changed(self, proxy_name: str, is_selected: bool):
        """Handle proxy selection change"""
        if is_selected:
            self._selected_proxies.add(proxy_name)
        else:
            self._selected_proxies.discard(proxy_name)
        
        # Enable/disable buttons based on selection
        has_selection = len(self._selected_proxies) > 0
        self.delete_selected_btn.setEnabled(has_selection)
        self.test_selected_btn.setEnabled(has_selection)
    
    def delete_selected_proxies(self):
        """Delete all selected proxies"""
        if not self._selected_proxies:
            return
        
        count = len(self._selected_proxies)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {count} selected proxy(ies)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success_count, errors = self.proxy_manager.delete_multiple(list(self._selected_proxies))
        
        self._selected_proxies.clear()
        self.load_proxies()
        
        if errors:
            QMessageBox.warning(
                self, "Deletion Errors",
                f"Failed to delete some proxies:\n" + "\n".join(errors)
            )
    
    def test_selected_proxies(self):
        """Test all selected proxies"""
        if not self._selected_proxies:
            return
        
        count = len(self._selected_proxies)
        reply = QMessageBox.question(
            self, "Confirm Test",
            f"Test {count} selected proxy(ies)? This may take some time.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Set all selected proxies to testing state
        for proxy_name in self._selected_proxies:
            card = self._find_card(proxy_name)
            if card:
                card.set_testing(True)
        
        # Start testing each proxy
        for proxy_name in self._selected_proxies:
            self.on_proxy_test(proxy_name)
    
    def _update_title(self, count: int):
        """Update title with count"""
        self.title_lbl.setText(f"Proxies ({count})")

    def _on_page_size_changed(self, index: int):
        """Page-size dropdown changed. Persist + reset to page 1 + re-render."""
        if index < 0 or index >= len(self._PAGE_SIZE_OPTIONS):
            return
        self._page_size = self._PAGE_SIZE_OPTIONS[index]
        QSettings("Tegufox", "GUI").setValue("proxies/page_size", self._page_size)
        self._current_page = 1
        self._apply_filter()

    def _apply_filter(self):
        """Recompute visible+sorted list, clamp current page, render (spec §5)."""
        text = self.search_input.text() if hasattr(self, "search_input") else ""
        sort_idx = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0

        visible = [c for c in self._all_cards if c.matches(text)]

        if sort_idx == 0:
            visible.sort(key=lambda c: c._name.lower())
        elif sort_idx == 1:
            visible.sort(key=lambda c: c._name.lower(), reverse=True)
        elif sort_idx == 2:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""), reverse=True)
        elif sort_idx == 3:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""))

        self._visible_filtered = visible

        if self._page_size == 0:
            total_pages = 1
        else:
            total_pages = max(1, (len(visible) + self._page_size - 1) // self._page_size)
        self._current_page = max(1, min(self._current_page, total_pages))

        self._render_current_page()

    def _render_current_page(self):
        """Detach all, attach the current-page slice, refresh footer (spec §5)."""
        # 1. Detach every card currently in layout (no deleteLater — reused).
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)

        # 2. Hide every known card up-front (covers cards that weren't in
        #    the layout this round).
        for card in self._all_cards:
            card.setVisible(False)

        # 3. Compute the slice for the current page.
        if self._page_size == 0:
            slice_cards = self._visible_filtered
            total_pages = 1
        else:
            start = (self._current_page - 1) * self._page_size
            end = start + self._page_size
            slice_cards = self._visible_filtered[start:end]
            total_pages = max(1, (len(self._visible_filtered) + self._page_size - 1) // self._page_size)

        # 4. Attach + show the slice.
        for card in slice_cards:
            card.setParent(self._list_widget)
            self._list_layout.addWidget(card)
            card.setVisible(True)

        # 5. Refresh footer.
        self._rebuild_page_bar(self._current_page, total_pages)

        total = len(self._visible_filtered)
        if total == 0:
            self.page_status_lbl.setText("showing 0-0 of 0")
        elif self._page_size == 0:
            self.page_status_lbl.setText(f"showing 1-{total} of {total}")
        else:
            shown_start = (self._current_page - 1) * self._page_size + 1
            shown_end = shown_start + len(slice_cards) - 1
            self.page_status_lbl.setText(f"showing {shown_start}-{shown_end} of {total}")

        # 6. Show/hide the whole footer.
        #    Spec §3.2: hidden when total_pages <= 1; in "All" mode hide the
        #    page bar but still show the status label.
        self.page_bar_container.setVisible(self._page_size != 0 and total_pages > 1)
        self.pagination_footer.setVisible(total_pages > 1 or self._page_size == 0)

    def _rebuild_page_bar(self, current: int, total: int):
        """Rebuild numbered page buttons + Prev/Next (spec §6.2)."""
        # Destroy old buttons (cheap — at most ~9 widgets).
        while self.page_bar_layout.count():
            item = self.page_bar_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        if total <= 1:
            return

        prev_btn = QPushButton("<")
        prev_btn.setFixedSize(28, 28)
        prev_btn.setEnabled(current > 1)
        prev_btn.clicked.connect(lambda: self._goto_page(current - 1))
        self.page_bar_layout.addWidget(prev_btn)

        for token in compute_page_window(current, total):
            if token is None:
                lbl = QLabel("…")
                lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; padding: 0 4px;")
                self.page_bar_layout.addWidget(lbl)
                continue
            btn = QPushButton(str(token))
            btn.setFixedSize(28, 28)
            if token == current:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {DarkPalette.ACCENT}; color: white;
                        border: none; border-radius: 4px; font-weight: 600;
                    }}
                """)
            page = token
            btn.clicked.connect(lambda _=False, p=page: self._goto_page(p))
            self.page_bar_layout.addWidget(btn)

        next_btn = QPushButton(">")
        next_btn.setFixedSize(28, 28)
        next_btn.setEnabled(current < total)
        next_btn.clicked.connect(lambda: self._goto_page(current + 1))
        self.page_bar_layout.addWidget(next_btn)

    def _goto_page(self, page: int):
        """Page-bar button handler. Re-renders without re-filtering."""
        self._current_page = page
        self._render_current_page()

    def on_proxy_clicked(self, proxy_name: str):
        """Handle proxy card click - show details"""
        data = self.proxy_manager.load(proxy_name)
        if not data:
            return
        
        # Show detail dialog
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Proxy Detail - {proxy_name}")
        dlg.resize(600, 400)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(14, 14, 14, 14)
        dlg_layout.setSpacing(10)
        
        info_text = f"""Name: {data.get('name', '')}
Host: {data.get('host', '')}
Port: {data.get('port', '')}
Username: {data.get('username', '—')}
Password: {'***' if data.get('password') else '—'}
Protocol: {data.get('protocol', 'http')}
Status: {data.get('status', 'inactive')}
Last Checked: {data.get('last_checked', '—')}
Last IP: {data.get('last_ip', '—')}
Created: {data.get('created', '—')}
Notes: {data.get('notes', '—')}"""
        
        info_display = QTextEdit()
        info_display.setReadOnly(True)
        info_display.setPlainText(info_text)
        info_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                font-size: 12px;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
            }}
        """)
        dlg_layout.addWidget(info_display)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(close_btn)
        dlg_layout.addLayout(btn_row)
        
        dlg.exec()
    
    def on_proxy_delete(self, proxy_name: str):
        """Handle proxy delete request"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete proxy '{proxy_name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.proxy_manager.delete(proxy_name)
            self._selected_proxies.discard(proxy_name)
            remaining = []
            for c in self._all_cards:
                if c._name == proxy_name:
                    c.setParent(None)
                    c.deleteLater()
                else:
                    remaining.append(c)
            self._all_cards = remaining
            has_selection = len(self._selected_proxies) > 0
            self.delete_selected_btn.setEnabled(has_selection)
            self.test_selected_btn.setEnabled(has_selection)
            self._update_title(len(self._all_cards))
            self._apply_filter()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
    
    def on_proxy_test(self, proxy_name: str):
        """Handle proxy test request"""
        card = self._find_card(proxy_name)
        if card:
            card.set_testing(True)
        
        worker = ProxyTestWorker(proxy_name, self.proxy_manager)
        worker.test_completed.connect(self._on_test_completed)
        worker.start()
        
        self._active_tests[proxy_name] = worker
    
    def _on_test_completed(self, proxy_name: str, result: dict):
        """Handle test completion - update row only, no dialog"""
        card = self._find_card(proxy_name)
        if card:
            card.set_testing(False)
            if result["success"]:
                card.update_status("active", result["ip"])
            else:
                card.update_status("failed")
        
        if proxy_name in self._active_tests:
            worker = self._active_tests.pop(proxy_name)
            worker.wait()
    
    def on_proxy_edit(self, proxy_name: str):
        """Handle proxy edit request"""
        data = self.proxy_manager.load(proxy_name)
        if not data:
            return
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Proxy - {proxy_name}")
        dlg.resize(500, 400)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(14, 14, 14, 14)
        dlg_layout.setSpacing(10)
        
        form = QFormLayout()
        
        name_input = QLineEdit(data.get("name", ""))
        name_input.setEnabled(False)  # Name cannot be changed
        form.addRow("Name:", name_input)
        
        host_input = QLineEdit(data.get("host", ""))
        form.addRow("Host:", host_input)
        
        port_input = QSpinBox()
        port_input.setRange(1, 65535)
        port_input.setValue(data.get("port", 8080))
        form.addRow("Port:", port_input)
        
        username_input = QLineEdit(data.get("username", ""))
        form.addRow("Username:", username_input)
        
        password_input = QLineEdit(data.get("password", ""))
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", password_input)
        
        protocol_combo = QComboBox()
        protocol_combo.addItems(["http", "https", "socks5"])
        protocol_combo.setCurrentText(data.get("protocol", "http"))
        form.addRow("Protocol:", protocol_combo)
        
        notes_input = QTextEdit()
        notes_input.setPlainText(data.get("notes", ""))
        notes_input.setMaximumHeight(80)
        form.addRow("Notes:", notes_input)
        
        dlg_layout.addLayout(form)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        save_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(save_btn)
        
        dlg_layout.addLayout(btn_row)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.proxy_manager.update(
                    proxy_name,
                    host=host_input.text(),
                    port=port_input.value(),
                    username=username_input.text() or None,
                    password=password_input.text() or None,
                    protocol=protocol_combo.currentText(),
                    notes=notes_input.toPlainText() or None,
                )
                self.refresh_proxies()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update proxy: {e}")
    
    def open_import_dialog(self):
        """Open import dialog"""
        dlg = QDialog(self)
        dlg.setWindowTitle("Import Proxies")
        dlg.resize(700, 500)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(14, 14, 14, 14)
        dlg_layout.setSpacing(10)
        
        info_lbl = QLabel("Enter proxies (one per line):")
        info_lbl.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 13px; font-weight: 600;")
        dlg_layout.addWidget(info_lbl)
        
        format_lbl = QLabel("Supported formats:\n• ip:port:user:pass\n• user:pass@ip:port\n• ip:port (no auth)")
        format_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        dlg_layout.addWidget(format_lbl)
        
        text_area = QTextEdit()
        text_area.setPlaceholderText("192.168.1.1:8080:user:pass\nuser:pass@192.168.1.2:8080\n192.168.1.3:8080")
        text_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        dlg_layout.addWidget(text_area)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        
        import_btn = QPushButton("Import")
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        import_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(import_btn)
        
        dlg_layout.addLayout(btn_row)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = text_area.toPlainText()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if not lines:
                QMessageBox.warning(self, "No Data", "Please enter at least one proxy.")
                return
            
            success_count, errors = self.proxy_manager.bulk_import(lines)
            
            self.refresh_proxies()
            
            msg = f"Successfully imported {success_count} proxy(ies)."
            if errors:
                msg += f"\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    msg += f"\n... and {len(errors) - 10} more errors"
            
            QMessageBox.information(self, "Import Complete", msg)
    
    def _find_card(self, proxy_name: str):
        """Find proxy card by name"""
        for card in self._all_cards:
            if card._name == proxy_name:
                return card
        return None

    def open_auto_assign_dialog(self):
        """Open dialog to bulk-assign proxies to profiles without one."""
        try:
            unbound = self.profile_manager.list_profiles_without_proxy()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read profiles: {e}")
            return

        if not unbound:
            QMessageBox.information(
                self, "Auto-Assign",
                "Every profile already has a proxy assigned. Nothing to do."
            )
            return

        all_count = len(self._all_cards)
        sel_count = len(self._selected_proxies)

        dlg = QDialog(self)
        dlg.setWindowTitle("Auto-Assign Proxies")
        dlg.resize(440, 280)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(10)

        target_lbl = QLabel(f"Target: {len(unbound)} profile(s) without a proxy.")
        target_lbl.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 12px; font-weight: 600;")
        dlg_layout.addWidget(target_lbl)

        src_lbl = QLabel("Proxy source:")
        src_lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;")
        dlg_layout.addWidget(src_lbl)

        source_group = QButtonGroup(dlg)
        all_radio = QRadioButton(f"All proxies ({all_count} total)")
        sel_radio = QRadioButton(f"Selected proxies only ({sel_count} selected)")
        radio_style = f"color: {DarkPalette.TEXT}; font-size: 12px;"
        all_radio.setStyleSheet(radio_style)
        sel_radio.setStyleSheet(radio_style)
        source_group.addButton(all_radio, 0)
        source_group.addButton(sel_radio, 1)
        if sel_count > 0:
            sel_radio.setChecked(True)
        else:
            all_radio.setChecked(True)
            sel_radio.setEnabled(False)
        dlg_layout.addWidget(all_radio)
        dlg_layout.addWidget(sel_radio)

        warn_lbl = QLabel("")
        warn_lbl.setStyleSheet("color: #f9e2af; font-size: 11px;")
        warn_lbl.setWordWrap(True)
        dlg_layout.addWidget(warn_lbl)

        reuse_chk = QCheckBox("Allow re-use (same proxy for multiple profiles)")
        reuse_chk.setStyleSheet(f"color: {DarkPalette.TEXT}; font-size: 12px;")
        dlg_layout.addWidget(reuse_chk)

        def refresh_warn():
            available = sel_count if sel_radio.isChecked() else all_count
            need = len(unbound)
            if available == 0:
                warn_lbl.setText("⚠ No proxies available in this source.")
                reuse_chk.setEnabled(False)
            elif available < need:
                warn_lbl.setText(
                    f"⚠ Only {available} proxy(ies) for {need} profile(s). "
                    "Enable re-use to cover all profiles, or some will be skipped."
                )
                reuse_chk.setEnabled(True)
            else:
                warn_lbl.setText("")
                reuse_chk.setEnabled(True)

        all_radio.toggled.connect(lambda _=None: refresh_warn())
        sel_radio.toggled.connect(lambda _=None: refresh_warn())
        refresh_warn()

        dlg_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        assign_btn = QPushButton("Assign")
        assign_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.ACCENT}; color: white; border: none;
                border-radius: 4px; padding: 6px 16px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.ACCENT_HOVER}; }}
        """)
        assign_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(assign_btn)
        dlg_layout.addLayout(btn_row)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        use_selected = sel_radio.isChecked()
        allow_reuse = reuse_chk.isChecked()
        source_names = list(self._selected_proxies) if use_selected else [c._name for c in self._all_cards]

        assigned, skipped, errors = self._run_auto_assign(unbound, source_names, allow_reuse)

        msg = f"Assigned {assigned} of {len(unbound)} profile(s)."
        if skipped:
            msg += f"\nSkipped {skipped} (no proxy available — enable re-use)."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:8])
            if len(errors) > 8:
                msg += f"\n... and {len(errors) - 8} more"
        QMessageBox.information(self, "Auto-Assign Complete", msg)

        # Refresh profiles page (if mounted) so the new badges show next time it opens.
        profiles_list = getattr(self.window(), "profiles_list", None)
        if profiles_list is not None:
            try:
                profiles_list.refresh_profiles()
            except Exception:
                pass

    def _run_auto_assign(self, profiles_needing: list, source_names: list,
                         allow_reuse: bool):
        """Assign proxies from source pool to profiles. Returns (assigned, skipped, errors)."""
        # Load proxy details and order them: active first, inactive next, drop failed.
        loaded = []
        for name in source_names:
            try:
                p = self.proxy_manager.load(name)
            except Exception:
                p = None
            if not p:
                continue
            status = (p.get("status") or "inactive").lower()
            if status == "failed":
                continue
            loaded.append(p)

        random.shuffle(loaded)
        loaded.sort(key=lambda p: 0 if (p.get("status") == "active") else 1)

        if not loaded:
            return 0, len(profiles_needing), ["No usable proxies in source (all failed or empty)."]

        assigned = 0
        skipped = 0
        errors = []
        cursor = 0
        unique_used = set()

        for profile_name in profiles_needing:
            if not allow_reuse:
                # Pick the next not-yet-used proxy.
                pick = None
                while cursor < len(loaded):
                    candidate = loaded[cursor]
                    cursor += 1
                    if candidate["name"] not in unique_used:
                        pick = candidate
                        break
                if pick is None:
                    skipped += 1
                    continue
                unique_used.add(pick["name"])
            else:
                pick = loaded[cursor % len(loaded)]
                cursor += 1

            try:
                snapshot = pool_to_profile_snapshot(pick)
                self.profile_manager.assign_proxy(profile_name, snapshot)
                assigned += 1
            except Exception as e:
                errors.append(f"{profile_name}: {e}")

        return assigned, skipped, errors
