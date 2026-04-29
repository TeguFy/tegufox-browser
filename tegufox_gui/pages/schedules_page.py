"""Schedules page — list / create / toggle / delete flow schedules.

The actual scheduler daemon runs as a SchedulerDaemon thread started by
the main app on launch. This page is a CRUD surface over flow_schedules.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QMessageBox, QDateTimeEdit,
)
from PyQt6.QtCore import QDateTime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, ensure_schema, FlowRecord
from tegufox_core.profile_manager import ProfileManager
from tegufox_flow.scheduler import (
    add_schedule, list_schedules, delete_schedule, set_enabled,
)


def _proxies_or_empty():
    try:
        from tegufox_core.proxy_manager import ProxyManager
        return ProxyManager().list()
    except Exception:
        return []


class _AddScheduleDialog(QDialog):
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Schedule")
        self.setMinimumWidth(560)
        self._db_path = db_path

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("daily-signup")
        form.addRow("Name *", self.name_edit)

        self.flow_combo = QComboBox()
        self._populate_flows()
        form.addRow("Flow *", self.flow_combo)

        self.profile_combo = QComboBox()
        try:
            for p in ProfileManager().list():
                self.profile_combo.addItem(p)
        except Exception:
            pass
        form.addRow("Profile *", self.profile_combo)

        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("(none)", "")
        for n in _proxies_or_empty():
            self.proxy_combo.addItem(n, n)
        form.addRow("Proxy", self.proxy_combo)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["cron", "one-shot"])
        self.kind_combo.currentIndexChanged.connect(self._toggle_kind)
        form.addRow("Schedule kind", self.kind_combo)

        self.cron_edit = QLineEdit("0 3 * * *")
        self.cron_edit.setPlaceholderText('e.g. "0 3 * * *" — daily at 03:00 UTC')
        form.addRow("Cron *", self.cron_edit)

        self.run_at_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(300))
        self.run_at_edit.setCalendarPopup(True)
        form.addRow("Run at", self.run_at_edit)
        self.run_at_edit.setEnabled(False)

        self.inputs_edit = QLineEdit()
        self.inputs_edit.setPlaceholderText('JSON, e.g. {"email": "x@y.com"}')
        form.addRow("Inputs (JSON)", self.inputs_edit)

        self.enabled_chk = QCheckBox("Enabled")
        self.enabled_chk.setChecked(True)
        form.addRow("", self.enabled_chk)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.create_btn = QPushButton("Create")
        self.cancel_btn.clicked.connect(self.reject)
        self.create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.create_btn)
        layout.addLayout(btn_row)

    def _populate_flows(self) -> None:
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        ensure_schema(eng)
        S = sessionmaker(bind=eng)
        with S() as s:
            for r in s.query(FlowRecord).order_by(FlowRecord.name):
                self.flow_combo.addItem(r.name)

    def _toggle_kind(self, idx: int) -> None:
        is_cron = self.kind_combo.currentText() == "cron"
        self.cron_edit.setEnabled(is_cron)
        self.run_at_edit.setEnabled(not is_cron)

    def _on_create(self) -> None:
        name = self.name_edit.text().strip()
        flow = self.flow_combo.currentText().strip()
        profile = self.profile_combo.currentText().strip()
        if not (name and flow and profile):
            QMessageBox.warning(self, "Missing fields",
                                "Name, Flow and Profile are required.")
            return
        proxy = self.proxy_combo.currentData() or None
        kind = self.kind_combo.currentText()
        cron_expr = self.cron_edit.text().strip() if kind == "cron" else None
        run_at = (self.run_at_edit.dateTime().toPyDateTime()
                  if kind == "one-shot" else None)

        inputs_text = self.inputs_edit.text().strip()
        try:
            inputs = json.loads(inputs_text) if inputs_text else {}
        except Exception as e:
            QMessageBox.critical(self, "Invalid JSON inputs", str(e))
            return

        try:
            add_schedule(
                self._db_path, name=name, flow_name=flow,
                profile_name=profile, proxy_name=proxy,
                cron_expression=cron_expr, run_at=run_at,
                inputs=inputs, enabled=self.enabled_chk.isChecked(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Failed to create", str(e))
            return
        self.accept()


class SchedulesPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Schedules"))
        toolbar.addStretch(1)
        self.refresh_btn = QPushButton("Refresh")
        self.add_btn = QPushButton("New schedule…")
        self.toggle_btn = QPushButton("Toggle enabled")
        self.delete_btn = QPushButton("Delete")
        self.refresh_btn.clicked.connect(self._refresh)
        self.add_btn.clicked.connect(self._on_add)
        self.toggle_btn.clicked.connect(self._on_toggle)
        self.delete_btn.clicked.connect(self._on_delete)
        for b in (self.refresh_btn, self.add_btn, self.toggle_btn, self.delete_btn):
            toolbar.addWidget(b)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Flow", "Profile", "Schedule",
            "Enabled", "Next run", "Last run",
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self._refresh()

    def _refresh(self) -> None:
        rows = list_schedules(self._db_path)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            sched_str = (r["cron_expression"] or
                         (f"once @ {r['run_at']}" if r["run_at"] else "?"))
            self.table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["flow_name"]))
            self.table.setItem(i, 3, QTableWidgetItem(r["profile_name"]))
            self.table.setItem(i, 4, QTableWidgetItem(sched_str))
            self.table.setItem(i, 5, QTableWidgetItem("✓" if r["enabled"] else "✗"))
            self.table.setItem(i, 6, QTableWidgetItem(r["next_run_at"] or ""))
            self.table.setItem(i, 7, QTableWidgetItem(r["last_run_at"] or ""))
        self.status_label.setText(f"{len(rows)} schedule(s)")

    def _selected_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _selected_enabled(self) -> Optional[bool]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 5)
        return (item.text() == "✓") if item else None

    def _on_add(self) -> None:
        dlg = _AddScheduleDialog(self._db_path, parent=self)
        if dlg.exec():
            self._refresh()

    def _on_toggle(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        cur = self._selected_enabled()
        set_enabled(self._db_path, sid, not cur)
        self._refresh()

    def _on_delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        ans = QMessageBox.question(
            self, "Delete schedule",
            f"Delete schedule #{sid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            delete_schedule(self._db_path, sid)
            self._refresh()
