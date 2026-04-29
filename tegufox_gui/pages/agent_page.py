"""AI Agent page — interactive realtime browser agent.

User types a goal, picks profile + proxy + limits, clicks Run. A
QThread spawns AgentRunner.run() and emits trace lines back to the UI.
The Stop button signals the runner's threading.Event. ask_user
callbacks open a blocking QInputDialog on the main thread.
"""

from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QInputDialog, QGroupBox,
    QFormLayout,
)


_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


class _AgentWorker(QThread):
    step_emitted = pyqtSignal(int, str, str)        # (step_i, verb, summary)
    finished_with = pyqtSignal(dict)                 # AgentResult-like dict
    ask_user = pyqtSignal(str)                       # question; reply via deliver_user_reply

    def __init__(self, *, goal, profile_name, proxy_name, max_steps, max_time,
                 provider, model, record_as_flow, db_path,
                 stop_event, parent=None):
        super().__init__(parent)
        self.kwargs = dict(
            goal=goal, profile_name=profile_name, proxy_name=proxy_name,
            max_steps=max_steps, max_time=max_time,
            provider=provider, model=model,
            record_as_flow=record_as_flow, db_path=db_path,
        )
        self.stop_event = stop_event
        self._ask_reply: Optional[str] = None
        self._ask_lock = threading.Event()

    def deliver_user_reply(self, reply: str) -> None:
        self._ask_reply = reply
        self._ask_lock.set()

    def _ask_user_callback(self, question: str) -> str:
        self._ask_lock.clear()
        self.ask_user.emit(question)
        self._ask_lock.wait(timeout=600)
        return self._ask_reply or ""

    def run(self) -> None:
        try:
            from tegufox_flow.agent import AgentRunner

            def on_step(idx, action, _result):
                args_short = json.dumps(action.args, default=str)[:80]
                self.step_emitted.emit(idx, action.verb, args_short)

            runner = AgentRunner(
                **self.kwargs,
                stop_event=self.stop_event,
                on_step=on_step,
                on_ask_user=self._ask_user_callback,
            )
            result = runner.run()
            self.finished_with.emit({
                "run_id": result.run_id, "status": result.status,
                "reason": result.reason, "steps": result.steps,
                "flow_yaml": result.flow_yaml,
            })
        except Exception as e:
            self.finished_with.emit({
                "status": "error", "reason": f"{type(e).__name__}: {e}",
            })


class AgentPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._worker: Optional[_AgentWorker] = None
        self._stop_event: Optional[threading.Event] = None

        layout = QVBoxLayout(self)

        top = QGroupBox("Goal")
        tg = QVBoxLayout(top)
        self.goal_edit = QPlainTextEdit()
        self.goal_edit.setPlaceholderText(
            "e.g. Login to Google with the email and password from inputs, "
            "then post 'Hello' on x.com home."
        )
        self.goal_edit.setMaximumHeight(110)
        tg.addWidget(self.goal_edit)
        layout.addWidget(top)

        opt_box = QGroupBox("Options")
        opt = QFormLayout(opt_box)
        self.profile_combo = QComboBox()
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("(none)", "")
        self._populate_combos()
        opt.addRow("Profile *", self.profile_combo)
        opt.addRow("Proxy", self.proxy_combo)

        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(1, 500)
        self.max_steps_spin.setValue(30)
        opt.addRow("Max steps", self.max_steps_spin)

        self.max_time_spin = QSpinBox()
        self.max_time_spin.setRange(10, 3600)
        self.max_time_spin.setValue(300)
        self.max_time_spin.setSuffix(" s")
        opt.addRow("Max time", self.max_time_spin)

        self.record_chk = QCheckBox("Save as flow after success (opt-in)")
        opt.addRow("", self.record_chk)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["(auto)", "anthropic", "openai", "gemini"])
        opt.addRow("Provider", self.provider_combo)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("(default)")
        opt.addRow("Model", self.model_edit)
        layout.addWidget(opt_box)

        actions = QHBoxLayout()
        self.run_btn = QPushButton("🦾 Run Agent")
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._on_run)
        self.stop_btn.clicked.connect(self._on_stop)
        actions.addStretch(1)
        actions.addWidget(self.run_btn)
        actions.addWidget(self.stop_btn)
        layout.addLayout(actions)

        trace_box = QGroupBox("Live trace")
        tlay = QVBoxLayout(trace_box)
        self.trace_view = QPlainTextEdit()
        self.trace_view.setReadOnly(True)
        self.trace_view.setFont(_MONO)
        tlay.addWidget(self.trace_view)
        layout.addWidget(trace_box, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _populate_combos(self) -> None:
        try:
            from tegufox_core.profile_manager import ProfileManager
            for p in ProfileManager().list():
                self.profile_combo.addItem(p)
        except Exception:
            pass
        try:
            from tegufox_core.proxy_manager import ProxyManager
            for n in ProxyManager().list():
                self.proxy_combo.addItem(n, n)
        except Exception:
            pass

    def _append_trace(self, line: str) -> None:
        self.trace_view.appendPlainText(line)

    def _on_run(self) -> None:
        goal = self.goal_edit.toPlainText().strip()
        if not goal:
            self.status_label.setText("Type a goal first.")
            return
        profile = self.profile_combo.currentText().strip()
        if not profile:
            self.status_label.setText("Pick a profile.")
            return

        provider = self.provider_combo.currentText()
        provider = "" if provider == "(auto)" else provider

        self.trace_view.clear()
        self._stop_event = threading.Event()
        self._worker = _AgentWorker(
            goal=goal,
            profile_name=profile,
            proxy_name=self.proxy_combo.currentData() or None,
            max_steps=self.max_steps_spin.value(),
            max_time=self.max_time_spin.value(),
            provider=provider or None,
            model=self.model_edit.text().strip() or None,
            record_as_flow=self.record_chk.isChecked(),
            db_path=self._db_path,
            stop_event=self._stop_event,
        )
        self._worker.step_emitted.connect(self._on_step)
        self._worker.finished_with.connect(self._on_finished)
        self._worker.ask_user.connect(self._on_ask_user)

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Agent running…")
        self._worker.start()

    def _on_stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        self.status_label.setText("Stop requested…")

    def _on_step(self, idx: int, verb: str, args_short: str) -> None:
        self._append_trace(f"Step {idx} [{verb}] {args_short}")

    def _on_finished(self, result: dict) -> None:
        status = result.get("status", "?")
        reason = result.get("reason", "")
        self.status_label.setText(f"{status}: {reason}")
        if result.get("flow_yaml"):
            self.status_label.setText(
                self.status_label.text() + "  (saved as flow)"
            )
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_ask_user(self, question: str) -> None:
        text, ok = QInputDialog.getText(self, "Agent needs info", question)
        reply = text if ok else ""
        if self._worker is not None:
            self._worker.deliver_user_reply(reply)
