"""Modal dialog to launch a multi-profile batch run."""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QPushButton, QProgressBar, QMessageBox,
)

from tegufox_flow.orchestrator import Orchestrator, BatchResult


class _BatchWorker(QThread):
    finished_with = pyqtSignal(object)   # BatchResult

    def __init__(self, flow_path: Path, db_path: Path, profiles: List[str],
                 max_concurrent: int, fail_fast: bool):
        super().__init__()
        self.flow_path = flow_path
        self.db_path = db_path
        self.profiles = profiles
        self.max_concurrent = max_concurrent
        self.fail_fast = fail_fast

    def run(self):
        try:
            orch = Orchestrator(
                flow_path=self.flow_path, db_path=self.db_path,
                max_concurrent=self.max_concurrent, fail_fast=self.fail_fast,
            )
            result = orch.run(profiles=self.profiles, inputs={})
            self.finished_with.emit(result)
        except Exception as e:
            self.finished_with.emit(BatchResult(
                batch_id="error", flow_name="?", total=0,
                succeeded=0, failed=0, status=f"crashed: {e}", runs=[],
            ))


class BatchRunDialog(QDialog):
    def __init__(self, *, flow_name: str, flow_yaml: str,
                 profile_names: List[str], db_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Run batch: {flow_name}")
        self.resize(500, 500)

        self._flow_yaml = flow_yaml
        self._db_path = Path(db_path)
        self._worker: _BatchWorker | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Profiles (Ctrl/Cmd-click to multi-select):"))
        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for p in profile_names:
            self.profile_list.addItem(QListWidgetItem(p))
        layout.addWidget(self.profile_list, 1)

        row = QHBoxLayout()
        row.addWidget(QLabel("Max concurrent:"))
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 16)
        self.max_concurrent_spin.setValue(3)
        row.addWidget(self.max_concurrent_spin)

        self.fail_fast_check = QCheckBox("Fail fast")
        row.addWidget(self.fail_fast_check)
        row.addStretch(1)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # indeterminate until run starts
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.run_btn = QPushButton("Run")
        self.close_btn = QPushButton("Close")
        self.run_btn.clicked.connect(self._on_run)
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)
        btn_row.addWidget(self.run_btn)
        layout.addLayout(btn_row)

    def _selected_profiles(self) -> List[str]:
        return [self.profile_list.item(i).text()
                for i in range(self.profile_list.count())
                if self.profile_list.item(i).isSelected()]

    def _on_run(self):
        profiles = self._selected_profiles()
        if not profiles:
            QMessageBox.warning(self, "Select profiles", "Pick at least one profile.")
            return

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(self._flow_yaml); flow_path = Path(f.name)

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText(f"Running on {len(profiles)} profile(s)...")

        self._worker = _BatchWorker(
            flow_path=flow_path, db_path=self._db_path,
            profiles=profiles,
            max_concurrent=self.max_concurrent_spin.value(),
            fail_fast=self.fail_fast_check.isChecked(),
        )
        self._worker.finished_with.connect(self._on_done)
        self._worker.start()

    def _on_done(self, result: BatchResult):
        self.progress.setVisible(False)
        self.status_label.setText(
            f"{result.status}: {result.succeeded}/{result.total} succeeded; "
            f"{result.failed} failed (batch {result.batch_id[:8]}...)"
        )
        self.run_btn.setEnabled(True)
