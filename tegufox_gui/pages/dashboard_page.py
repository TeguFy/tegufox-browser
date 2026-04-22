"""Dashboard page widget"""

import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
)
from PyQt6.QtCore import QTimer

from tegufox_gui.utils.styles import DarkPalette
from tegufox_gui.components import StatCard

# Shared session store (referenced from main app)
_gui_sessions = {}


class DashboardWidget(QWidget):
    """Home page — live stats, profile distribution, and recent activity."""

    def __init__(self, parent=None, gui_sessions_ref=None):
        super().__init__(parent)
        # Allow injection of sessions dict reference
        global _gui_sessions
        if gui_sessions_ref is not None:
            _gui_sessions = gui_sessions_ref
        self._setup_ui()
        self._refresh_stats()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(8000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(24)

        hdr = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet(
            f"color: {DarkPalette.TEXT}; font-size: 28px; font-weight: bold;"
        )
        hdr.addWidget(title)
        hdr.addStretch()
        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkPalette.CARD};
                color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER};
                
                padding: 6px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {DarkPalette.HOVER}; }}
        """)
        refresh_btn.clicked.connect(self._refresh_stats)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.c_profiles = StatCard("📁", "—", "Total Profiles")
        self.c_sessions = StatCard("🌐", "0", "Active Sessions", DarkPalette.RED)
        self.c_score    = StatCard("⭐", "—", "Avg Score")
        self.c_registry = StatCard("🗄️", "—", "Registry Records")
        for c in (self.c_profiles, self.c_sessions, self.c_score, self.c_registry):
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        bot = QHBoxLayout()
        bot.setSpacing(16)

        def _panel(title_text):
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {DarkPalette.CARD};
                    border: 1px solid {DarkPalette.BORDER};
                    
                }}
            """)
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(20, 16, 20, 16)
            lay.setSpacing(10)
            lbl = QLabel(title_text)
            lbl.setStyleSheet(
                f"color: {DarkPalette.TEXT}; font-size: 15px; font-weight: bold;"
            )
            lay.addWidget(lbl)
            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setStyleSheet(f"""
                QTextEdit {{
                    background-color: transparent;
                    color: {DarkPalette.TEXT_DIM};
                    border: none;
                    font-size: 13px;
                }}
            """)
            lay.addWidget(txt)
            return frame, txt

        dist_frame, self.dist_text = _panel("Profile Distribution")
        bot.addWidget(dist_frame)
        act_frame, self.activity_text = _panel("Recent Profiles")
        bot.addWidget(act_frame)
        root.addLayout(bot)

    def _refresh_stats(self):
        # Get profiles from ProfileManager (database) instead of JSON files
        profile_count = 0
        try:
            from tegufox_core.profile_manager import ProfileManager
            pm = ProfileManager("profiles")
            profile_count = len(pm.list())
        except Exception as e:
            print(f"[Dashboard] ProfileManager error: {e}")
        
        self.c_profiles.set_value(str(profile_count))
        self.c_sessions.set_value(str(len(_gui_sessions)))

        try:
            from tegufox_core.fingerprint_registry import FingerprintRegistry
            reg = FingerprintRegistry()
            self.c_registry.set_value(str(reg.count()))
            reg.close()
        except Exception as e:
            print(f"[Dashboard] Registry error: {e}")
            self.c_registry.set_value("—")

        try:
            from tegufox_core.consistency_engine import ConsistencyEngine, default_rules
            from tegufox_core.profile_manager import ProfileManager
            engine = ConsistencyEngine(default_rules())
            pm = ProfileManager("profiles")
            scores = []
            for n in pm.list()[:8]:
                try:
                    scores.append(engine.evaluate(pm.load(n)).score)
                except Exception as e:
                    print(f"[Dashboard] Score eval error for {n}: {e}")
            self.c_score.set_value(f"{sum(scores)/len(scores):.2f}" if scores else "—")
        except Exception as e:
            print(f"[Dashboard] ProfileManager error: {e}")
            self.c_score.set_value("—")

        # Get profile distribution from ProfileManager
        dist: dict = {}
        recent_profiles = []
        try:
            from tegufox_core.profile_manager import ProfileManager
            pm = ProfileManager("profiles")
            all_profiles = pm.list()
            
            for name in all_profiles:
                try:
                    data = pm.load(name)
                    nav = data.get("navigator", {})
                    ua = nav.get("userAgent", "")
                    if "Chrome" in ua:
                        browser = "Chrome"
                    elif "Firefox" in ua:
                        browser = "Firefox"
                    elif "Safari" in ua and "Chrome" not in ua:
                        browser = "Safari"
                    else:
                        browser = "Other"
                    plat = nav.get("platform", data.get("platform", "unknown"))
                    key = f"{browser} / {plat}"
                    dist[key] = dist.get(key, 0) + 1
                    
                    # Track for recent activity
                    created = data.get("created", "")
                    if created:
                        recent_profiles.append((name, created))
                except Exception as e:
                    print(f"[Dashboard] Error loading profile {name}: {e}")
        except Exception as e:
            print(f"[Dashboard] Distribution error: {e}")
        
        if dist:
            lines = [f"  {k}: {v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])]
            self.dist_text.setPlainText("\n".join(lines))
        else:
            self.dist_text.setPlainText("  (no profiles found)")

        # Show recent profiles
        lines = []
        recent_profiles.sort(key=lambda x: x[1], reverse=True)
        for name, created in recent_profiles[:5]:
            try:
                dt = datetime.fromisoformat(created).strftime("%b %d %H:%M")
                lines.append(f"  {name}  —  {dt}")
            except Exception:
                lines.append(f"  {name}  —  —")
        self.activity_text.setPlainText("\n".join(lines) if lines else "  (none)")
