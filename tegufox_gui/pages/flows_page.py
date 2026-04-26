"""Minimal Flows page — list + run.

Real visual editor lives in sub-project #3.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, FlowRecord
from tegufox_core.profile_manager import ProfileManager
from tegufox_flow.dsl import parse_flow
from tegufox_flow.runtime import run_flow


class _RunWorker(QThread):
    finished_with = pyqtSignal(dict)

    def __init__(self, flow_path: Path, profile: str, inputs: dict):
        super().__init__()
        self.flow_path = flow_path
        self.profile = profile
        self.inputs = inputs

    def run(self):
        try:
            result = run_flow(self.flow_path, profile_name=self.profile, inputs=self.inputs)
            self.finished_with.emit({
                "run_id": result.run_id, "status": result.status,
                "last_step_id": result.last_step_id, "error": result.error,
            })
        except Exception as e:
            self.finished_with.emit({"status": "failed", "error": f"{type(e).__name__}: {e}"})


class FlowsPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._workers: List[_RunWorker] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Flows"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.run_btn = QPushButton("Run")
        self.upload_btn = QPushButton("Upload YAML…")
        self.run_btn.clicked.connect(self._on_run)
        self.upload_btn.clicked.connect(self._on_upload)
        row.addWidget(QLabel("Profile:"))
        row.addWidget(self.profile_combo)
        row.addWidget(self.upload_btn)
        row.addWidget(self.run_btn)
        layout.addLayout(row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 2)

        self._refresh()

    def _session(self):
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        return sessionmaker(bind=eng)()

    def _refresh(self):
        self.list_widget.clear()
        s = self._session()
        try:
            for rec in s.query(FlowRecord).order_by(FlowRecord.name):
                self.list_widget.addItem(QListWidgetItem(rec.name))
        finally:
            s.close()

        self.profile_combo.clear()
        try:
            pm = ProfileManager()
            for name in pm.list():
                self.profile_combo.addItem(name)
        except Exception:
            pass

    def _on_upload(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pick a flow YAML", "", "YAML (*.yaml *.yml)")
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8")
        try:
            import yaml as _yaml
            flow = parse_flow(_yaml.safe_load(text))
        except Exception as e:
            QMessageBox.critical(self, "Invalid flow", str(e))
            return
        s = self._session()
        try:
            now = datetime.utcnow()
            rec = s.query(FlowRecord).filter_by(name=flow.name).first()
            if rec is None:
                rec = FlowRecord(name=flow.name, yaml_text=text,
                                 schema_version=flow.schema_version,
                                 created_at=now, updated_at=now)
                s.add(rec)
            else:
                rec.yaml_text = text
                rec.updated_at = now
            s.commit()
        finally:
            s.close()
        self._refresh()

    def _on_run(self):
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(self, "Pick a flow", "Select a flow first.")
            return
        profile = self.profile_combo.currentText()
        if not profile:
            QMessageBox.warning(self, "Pick a profile", "No profile available.")
            return

        s = self._session()
        try:
            rec = s.query(FlowRecord).filter_by(name=item.text()).one()
            yaml_text = rec.yaml_text
        finally:
            s.close()

        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            tmp = Path(f.name)

        worker = _RunWorker(tmp, profile, {})
        worker.finished_with.connect(self._on_run_done)
        self._workers.append(worker)
        self.log.append(f"Starting {item.text()} on {profile}…")
        worker.start()

    def _on_run_done(self, result: dict):
        self.log.append(f"Result: {result}")
