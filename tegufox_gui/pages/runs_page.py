"""Run dashboard — browse flow run history, drill into details, replay.

Lists every row in flow_runs ordered by recency. Selecting a row reveals
its inputs / error / last step / duration plus action buttons:

  • Replay   — run the same flow + inputs against the same profile
  • Resume   — re-run from the last successful checkpoint (only if failed)
  • Open dir — open data/runs/<run_id>/ in Finder if it exists
  • Delete   — purge the run row + checkpoints

A second tab shows batches (flow_batches) for multi-profile orchestrator
runs.
"""

from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QTextEdit, QSplitter, QMessageBox,
    QComboBox, QLineEdit,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import (
    Base, ensure_schema, FlowRun, FlowRecord, FlowCheckpoint, FlowBatch,
)


_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


def _open_in_finder(path: Path) -> None:
    if not path.exists():
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", str(path)])
    elif sys.platform == "win32":
        subprocess.Popen(["explorer", str(path)])


class _ReplayWorker(QThread):
    finished_with = pyqtSignal(dict)

    def __init__(self, flow_yaml: str, profile: str, inputs: dict,
                 resume: Optional[str] = None):
        super().__init__()
        self.flow_yaml = flow_yaml
        self.profile = profile
        self.inputs = inputs
        self.resume = resume

    def run(self):
        try:
            import tempfile
            from tegufox_flow.runtime import run_flow
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(self.flow_yaml)
                path = Path(f.name)
            result = run_flow(path, profile_name=self.profile, inputs=self.inputs,
                              resume=self.resume)
            self.finished_with.emit({
                "run_id": result.run_id, "status": result.status,
                "error": result.error,
            })
        except Exception as e:
            self.finished_with.emit({"status": "failed", "error": f"{type(e).__name__}: {e}"})


class RunsPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._workers: List[_ReplayWorker] = []
        self._current_run_id: Optional[str] = None
        self._current_yaml: str = ""

        layout = QVBoxLayout(self)

        # ---- Filter / refresh row ---------------------------------------
        filt_row = QHBoxLayout()
        filt_row.addWidget(QLabel("Filter:"))
        self.flow_filter = QComboBox()
        self.flow_filter.setMinimumWidth(160)
        self.flow_filter.addItem("(all flows)", "")
        filt_row.addWidget(self.flow_filter)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["(all)", "succeeded", "failed", "running", "aborted"])
        filt_row.addWidget(QLabel("Status:"))
        filt_row.addWidget(self.status_filter)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("search profile / run_id")
        filt_row.addWidget(self.search_edit, 1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh)
        filt_row.addWidget(self.refresh_btn)
        layout.addLayout(filt_row)

        self.flow_filter.currentIndexChanged.connect(self._refresh)
        self.status_filter.currentIndexChanged.connect(self._refresh)
        self.search_edit.textChanged.connect(self._refresh)

        # ---- Tabs: Runs / Batches ---------------------------------------
        self.tabs = QTabWidget()

        # Runs tab
        runs_tab = QWidget()
        rt_layout = QVBoxLayout(runs_tab)
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.runs_table = QTableWidget(0, 6)
        self.runs_table.setHorizontalHeaderLabels(
            ["Started", "Flow", "Profile", "Status", "Last step", "Run ID"]
        )
        self.runs_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.runs_table.horizontalHeader().setStretchLastSection(True)
        self.runs_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.runs_table.itemSelectionChanged.connect(self._on_run_selected)
        splitter.addWidget(self.runs_table)

        # Detail panel
        detail = QWidget()
        d_layout = QVBoxLayout(detail)
        action_row = QHBoxLayout()
        self.replay_btn = QPushButton("Replay")
        self.resume_btn = QPushButton("Resume from checkpoint")
        self.open_dir_btn = QPushButton("Open run dir")
        self.delete_btn = QPushButton("Delete")
        for b in (self.replay_btn, self.resume_btn, self.open_dir_btn, self.delete_btn):
            b.setEnabled(False)
            action_row.addWidget(b)
        action_row.addStretch(1)
        self.replay_btn.clicked.connect(self._on_replay)
        self.resume_btn.clicked.connect(self._on_resume)
        self.open_dir_btn.clicked.connect(self._on_open_dir)
        self.delete_btn.clicked.connect(self._on_delete)
        d_layout.addLayout(action_row)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setFont(_MONO)
        d_layout.addWidget(self.detail_view)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        rt_layout.addWidget(splitter)
        self.tabs.addTab(runs_tab, "Runs")

        # Batches tab
        batches_tab = QWidget()
        bt_layout = QVBoxLayout(batches_tab)
        self.batches_table = QTableWidget(0, 6)
        self.batches_table.setHorizontalHeaderLabels(
            ["Started", "Flow", "Status", "Total", "Succeeded", "Failed"]
        )
        self.batches_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.batches_table.horizontalHeader().setStretchLastSection(True)
        self.batches_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        bt_layout.addWidget(self.batches_table)
        self.tabs.addTab(batches_tab, "Batches")

        layout.addWidget(self.tabs, 1)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self._refresh()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------
    def _session(self):
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        ensure_schema(eng)
        return sessionmaker(bind=eng)()

    def _refresh(self) -> None:
        s = self._session()
        try:
            # Populate flow filter (one-time per refresh).
            existing_flows = {self.flow_filter.itemText(i)
                              for i in range(self.flow_filter.count())}
            for r in s.query(FlowRecord).order_by(FlowRecord.name):
                if r.name not in existing_flows:
                    self.flow_filter.addItem(r.name, r.name)

            # Runs query
            q = (s.query(FlowRun, FlowRecord)
                 .join(FlowRecord, FlowRecord.id == FlowRun.flow_id)
                 .order_by(FlowRun.started_at.desc())
                 .limit(500))
            sel_flow = self.flow_filter.currentData() or ""
            sel_status = self.status_filter.currentText()
            search = (self.search_edit.text() or "").strip().lower()
            rows = []
            for run, rec in q:
                if sel_flow and rec.name != sel_flow:
                    continue
                if sel_status not in ("", "(all)") and run.status != sel_status:
                    continue
                if search and search not in (run.profile_name or "").lower() \
                        and search not in (run.run_id or "").lower():
                    continue
                rows.append((run, rec))

            self.runs_table.setRowCount(len(rows))
            for i, (run, rec) in enumerate(rows):
                started = run.started_at.strftime("%Y-%m-%d %H:%M:%S") if run.started_at else ""
                self.runs_table.setItem(i, 0, QTableWidgetItem(started))
                self.runs_table.setItem(i, 1, QTableWidgetItem(rec.name))
                self.runs_table.setItem(i, 2, QTableWidgetItem(run.profile_name or ""))
                status_item = QTableWidgetItem(run.status or "")
                self.runs_table.setItem(i, 3, status_item)
                self.runs_table.setItem(i, 4, QTableWidgetItem(run.last_step_id or ""))
                self.runs_table.setItem(i, 5, QTableWidgetItem(run.run_id or ""))

            self.status_label.setText(f"{len(rows)} run(s) shown")

            # Batches
            batches = (s.query(FlowBatch, FlowRecord)
                       .join(FlowRecord, FlowRecord.id == FlowBatch.flow_id)
                       .order_by(FlowBatch.started_at.desc())
                       .limit(200).all())
            self.batches_table.setRowCount(len(batches))
            for i, (b, rec) in enumerate(batches):
                started = b.started_at.strftime("%Y-%m-%d %H:%M:%S") if b.started_at else ""
                self.batches_table.setItem(i, 0, QTableWidgetItem(started))
                self.batches_table.setItem(i, 1, QTableWidgetItem(rec.name))
                self.batches_table.setItem(i, 2, QTableWidgetItem(b.status or ""))
                self.batches_table.setItem(i, 3, QTableWidgetItem(str(b.total)))
                self.batches_table.setItem(i, 4, QTableWidgetItem(str(b.succeeded)))
                self.batches_table.setItem(i, 5, QTableWidgetItem(str(b.failed)))
        finally:
            s.close()

    def _on_run_selected(self) -> None:
        row = self.runs_table.currentRow()
        if row < 0:
            return
        run_id_item = self.runs_table.item(row, 5)
        if run_id_item is None:
            return
        run_id = run_id_item.text()
        self._current_run_id = run_id

        s = self._session()
        try:
            run = s.query(FlowRun).filter_by(run_id=run_id).first()
            rec = s.query(FlowRecord).filter_by(id=run.flow_id).first() if run else None
            if not run or not rec:
                return
            self._current_yaml = rec.yaml_text or ""

            duration = ""
            if run.finished_at and run.started_at:
                duration = str(run.finished_at - run.started_at)

            inputs = {}
            try:
                inputs = json.loads(run.inputs_json or "{}")
            except Exception:
                pass

            checkpoints = (s.query(FlowCheckpoint)
                           .filter_by(run_id=run_id)
                           .order_by(FlowCheckpoint.seq.desc())
                           .limit(10).all())

            details = [
                f"run_id:        {run.run_id}",
                f"flow:          {rec.name}",
                f"profile:       {run.profile_name}",
                f"status:        {run.status}",
                f"started_at:    {run.started_at.isoformat() if run.started_at else ''}",
                f"finished_at:   {run.finished_at.isoformat() if run.finished_at else ''}",
                f"duration:      {duration}",
                f"last_step_id:  {run.last_step_id or ''}",
                f"batch_id:      {run.batch_id or ''}",
                f"",
                f"inputs:",
                json.dumps(inputs, indent=2, ensure_ascii=False),
                f"",
                f"error:",
                run.error_text or "(none)",
                f"",
                f"recent checkpoints (newest first):",
            ]
            for cp in checkpoints:
                details.append(f"  seq={cp.seq:<4} step={cp.step_id}  vars={cp.vars_json[:120]}")
            self.detail_view.setPlainText("\n".join(details))

            self.replay_btn.setEnabled(True)
            self.resume_btn.setEnabled(run.status == "failed")
            self.open_dir_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _selected_run(self):
        if not self._current_run_id:
            return None
        s = self._session()
        try:
            run = s.query(FlowRun).filter_by(run_id=self._current_run_id).first()
            return (run, self._current_yaml) if run else None
        finally:
            s.close()

    def _on_replay(self) -> None:
        sel = self._selected_run()
        if not sel:
            return
        run, yaml_text = sel
        try:
            inputs = json.loads(run.inputs_json or "{}")
        except Exception:
            inputs = {}
        worker = _ReplayWorker(yaml_text, run.profile_name, inputs)
        worker.finished_with.connect(self._on_replay_done)
        self._workers.append(worker)
        self.status_label.setText(f"Replaying {run.run_id[:8]}…")
        worker.start()

    def _on_resume(self) -> None:
        sel = self._selected_run()
        if not sel:
            return
        run, yaml_text = sel
        try:
            inputs = json.loads(run.inputs_json or "{}")
        except Exception:
            inputs = {}
        worker = _ReplayWorker(yaml_text, run.profile_name, inputs,
                               resume=run.run_id)
        worker.finished_with.connect(self._on_replay_done)
        self._workers.append(worker)
        self.status_label.setText(f"Resuming {run.run_id[:8]}…")
        worker.start()

    def _on_replay_done(self, result: dict) -> None:
        self.status_label.setText(
            f"Done: status={result.get('status')} run_id={result.get('run_id', '')[:8]}"
        )
        self._refresh()

    def _on_open_dir(self) -> None:
        if not self._current_run_id:
            return
        path = Path("data/runs") / self._current_run_id
        if path.exists():
            _open_in_finder(path)
        else:
            QMessageBox.information(self, "No artifacts",
                                    f"No directory at {path}")

    def _on_delete(self) -> None:
        if not self._current_run_id:
            return
        ans = QMessageBox.question(
            self, "Delete run",
            f"Delete run {self._current_run_id} and its checkpoints?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        s = self._session()
        try:
            s.query(FlowCheckpoint).filter_by(run_id=self._current_run_id).delete()
            s.query(FlowRun).filter_by(run_id=self._current_run_id).delete()
            s.commit()
        finally:
            s.close()
        self._current_run_id = None
        self.detail_view.clear()
        for b in (self.replay_btn, self.resume_btn, self.open_dir_btn, self.delete_btn):
            b.setEnabled(False)
        self._refresh()
