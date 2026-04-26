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
    QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox, QCheckBox,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, ensure_schema, FlowRecord
from tegufox_core.profile_manager import ProfileManager
from tegufox_flow.dsl import parse_flow
from tegufox_flow.runtime import run_flow


class _RunWorker(QThread):
    finished_with = pyqtSignal(dict)

    def __init__(self, flow_path: Path, profile: str, inputs: dict,
                 proxy_name: str = "", keep_browser_open: bool = False):
        super().__init__()
        self.flow_path = flow_path
        self.profile = profile
        self.inputs = inputs
        self.proxy_name = proxy_name
        self.keep_browser_open = keep_browser_open

    def run(self):
        try:
            result = run_flow(
                self.flow_path,
                profile_name=self.profile,
                inputs=self.inputs,
                proxy_name=self.proxy_name or None,
                keep_browser_open=self.keep_browser_open,
            )
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
        self.proxy_combo = QComboBox()
        self.proxy_combo.setMinimumWidth(180)
        self.keep_browser_chk = QCheckBox("Keep browser open after run")
        self.keep_browser_chk.setToolTip(
            "After the flow finishes, leave the browser window open so you "
            "can interact manually. Close the window to release resources."
        )
        self.run_btn = QPushButton("Run")
        self.upload_btn = QPushButton("Upload YAML…")
        self.new_btn = QPushButton("New Flow")
        self.batch_btn = QPushButton("Run Batch…")
        self.run_btn.clicked.connect(self._on_run)
        self.upload_btn.clicked.connect(self._on_upload)
        self.new_btn.clicked.connect(self._on_new_flow)
        self.batch_btn.clicked.connect(self._on_batch)
        row.addWidget(QLabel("Profile:"))
        row.addWidget(self.profile_combo)
        row.addWidget(QLabel("Proxy:"))
        row.addWidget(self.proxy_combo)
        row.addWidget(self.keep_browser_chk)
        row.addWidget(self.new_btn)
        row.addWidget(self.upload_btn)
        row.addWidget(self.batch_btn)
        row.addWidget(self.run_btn)
        layout.addLayout(row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 2)

        self._refresh()
        self.list_widget.itemDoubleClicked.connect(self._on_edit_flow)

    def _session(self):
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)

        ensure_schema(eng)
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

        self.proxy_combo.clear()
        self.proxy_combo.addItem("(none — profile default)", "")
        try:
            from tegufox_core.proxy_manager import ProxyManager
            for name in ProxyManager().list():
                self.proxy_combo.addItem(name, name)
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

        # Collect inputs via a generated form so the engine doesn't reject
        # the run with missing required input.
        inputs: dict = {}
        try:
            import yaml as _yaml
            from tegufox_flow.dsl import parse_flow
            flow = parse_flow(_yaml.safe_load(yaml_text))
        except Exception as e:
            QMessageBox.critical(self, "Cannot parse flow", str(e))
            return

        # Proxy now lives on the toolbar, so the inputs dialog only opens
        # when the flow declares inputs.
        inputs: dict = {}
        if flow.inputs:
            from tegufox_gui.dialogs.run_inputs_dialog import RunInputsDialog
            dlg = RunInputsDialog(flow.name, flow.inputs, parent=self)
            if not dlg.exec():
                return
            inputs = dlg.values()
        proxy_name = self.proxy_combo.currentData() or ""

        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            tmp = Path(f.name)

        worker = _RunWorker(
            tmp, profile, inputs,
            proxy_name=proxy_name,
            keep_browser_open=self.keep_browser_chk.isChecked(),
        )
        worker.finished_with.connect(self._on_run_done)
        self._workers.append(worker)
        self.log.append(f"Starting {item.text()} on {profile}…")
        worker.start()

    def _on_run_done(self, result: dict):
        self.log.append(f"Result: {result}")

    def _on_new_flow(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        from tegufox_gui.pages.flow_editor_page import FlowEditorPage
        dlg = QDialog(self)
        dlg.setWindowTitle("New Flow")
        dlg.resize(1100, 700)
        lo = QVBoxLayout(dlg)
        editor = FlowEditorPage(db_path=self._db_path, parent=dlg)
        lo.addWidget(editor)
        dlg.exec()
        self._refresh()

    def _on_edit_flow(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        from tegufox_gui.pages.flow_editor_page import FlowEditorPage
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit: {item.text()}")
        dlg.resize(1100, 700)
        lo = QVBoxLayout(dlg)
        editor = FlowEditorPage(db_path=self._db_path, parent=dlg)
        editor.load_flow_by_name(item.text())
        lo.addWidget(editor)
        dlg.exec()
        self._refresh()

    def _on_batch(self):
        item = self.list_widget.currentItem()
        if item is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Pick a flow", "Select a flow first.")
            return

        s = self._session()
        try:
            from tegufox_core.database import FlowRecord
            rec = s.query(FlowRecord).filter_by(name=item.text()).one()
            flow_yaml = rec.yaml_text
        finally:
            s.close()

        profiles = []
        try:
            pm = ProfileManager()
            profiles = [name for name in pm.list()]
        except Exception:
            pass

        from tegufox_gui.dialogs.batch_run_dialog import BatchRunDialog
        dlg = BatchRunDialog(
            flow_name=item.text(), flow_yaml=flow_yaml,
            profile_names=profiles, db_path=self._db_path, parent=self,
        )
        dlg.exec()
