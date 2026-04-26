"""Dialog that prompts for a flow's declared inputs before running.

flow.inputs declares typed parameters with optional defaults; the GUI
needs to collect values for them or the engine raises
ValueError('missing required input ...'). This dialog auto-builds a
QFormLayout from those declarations.

Field rules:
  - type=string + name contains 'password' / 'token' / 'secret' →
    password-style line edit (echoMode = Password)
  - type=string             → QLineEdit
  - type=int                → QSpinBox
  - type=float              → QDoubleSpinBox
  - type=bool               → QCheckBox
  - type=list / map         → QPlainTextEdit (parsed as JSON; falls back
                              to comma-split for simple list-of-strings)
"""

from __future__ import annotations
import json
from typing import Any, Dict, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QPlainTextEdit, QPushButton, QLabel, QComboBox,
)


_SECRET_HINTS = ("password", "token", "secret", "api_key", "apikey")


def _is_secret(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _SECRET_HINTS)


class RunInputsDialog(QDialog):
    """Prompt for inputs of a flow.

    `inputs_decl` is the dict from `flow.inputs`, where each value is a
    pydantic Input model (has .type, .required, .default).
    """

    def __init__(self, flow_name: str, inputs_decl: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Run {flow_name}")
        self.setMinimumWidth(500)
        self._decl = inputs_decl
        self._widgets: Dict[str, Any] = {}

        layout = QVBoxLayout(self)

        # ---- Proxy selector --------------------------------------------
        proxy_form = QFormLayout()
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("(none — use profile default)", "")
        try:
            from tegufox_core.proxy_manager import ProxyManager
            for name in ProxyManager().list():
                self.proxy_combo.addItem(name, name)
        except Exception:
            pass
        proxy_form.addRow("Proxy:", self.proxy_combo)
        layout.addLayout(proxy_form)

        if not inputs_decl:
            layout.addWidget(QLabel(f"<i>{flow_name}</i> declares no inputs."))
        else:
            layout.addWidget(QLabel(f"Inputs for <b>{flow_name}</b>:"))
            form = QFormLayout()
            for name, decl in inputs_decl.items():
                w = self._build_widget(name, decl)
                self._widgets[name] = w
                marker = " *" if getattr(decl, "required", False) else ""
                form.addRow(name + marker, w)
            layout.addLayout(form)

        self._missing_label = QLabel("")
        self._missing_label.setStyleSheet("color: #b00020;")
        layout.addWidget(self._missing_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.run_btn = QPushButton("Run")
        self.cancel_btn.clicked.connect(self.reject)
        self.run_btn.clicked.connect(self._on_run)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.run_btn)
        layout.addLayout(btn_row)

    def _build_widget(self, name: str, decl) -> Any:
        kind = getattr(decl, "type", "string")
        default = getattr(decl, "default", None)

        if kind == "string":
            w = QLineEdit()
            if default is not None:
                w.setText(str(default))
            if _is_secret(name):
                w.setEchoMode(QLineEdit.EchoMode.Password)
            return w
        if kind == "int":
            w = QSpinBox()
            w.setRange(-(2**31), 2**31 - 1)
            if default is not None:
                try:
                    w.setValue(int(default))
                except (TypeError, ValueError):
                    pass
            return w
        if kind == "float":
            w = QDoubleSpinBox()
            w.setRange(-1e12, 1e12)
            w.setDecimals(6)
            if default is not None:
                try:
                    w.setValue(float(default))
                except (TypeError, ValueError):
                    pass
            return w
        if kind == "bool":
            w = QCheckBox()
            if default is not None:
                w.setChecked(bool(default))
            return w
        # list / map → JSON
        w = QPlainTextEdit()
        w.setMaximumHeight(80)
        if default is not None:
            w.setPlainText(json.dumps(default))
        else:
            w.setPlaceholderText('JSON, e.g. ["a","b"] or {"k":"v"}')
        return w

    def _read_widget(self, name: str, decl) -> Any:
        kind = getattr(decl, "type", "string")
        w = self._widgets[name]
        if kind == "string":
            return w.text()
        if kind == "int":
            return int(w.value())
        if kind == "float":
            return float(w.value())
        if kind == "bool":
            return bool(w.isChecked())
        # list / map
        text = w.toPlainText().strip()
        if not text:
            return [] if kind == "list" else {}
        try:
            return json.loads(text)
        except Exception:
            if kind == "list":
                return [s.strip() for s in text.split(",") if s.strip()]
            raise

    def proxy_name(self) -> str:
        """Selected proxy name; empty string when 'none' picked."""
        data = self.proxy_combo.currentData()
        return data or ""

    def values(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, decl in self._decl.items():
            try:
                v = self._read_widget(name, decl)
            except Exception as e:
                raise ValueError(f"input {name!r}: {e}") from e
            # Only include if user typed something OR it's required.
            required = getattr(decl, "required", False)
            default = getattr(decl, "default", None)
            if isinstance(v, str) and not v and not required and default is None:
                continue
            out[name] = v
        return out

    def _on_run(self) -> None:
        missing: List[str] = []
        try:
            collected = self.values()
        except Exception as e:
            self._missing_label.setText(str(e))
            return
        for name, decl in self._decl.items():
            required = getattr(decl, "required", False)
            default = getattr(decl, "default", None)
            if not required:
                continue
            if name not in collected and default is None:
                missing.append(name)
            elif name in collected:
                v = collected[name]
                if isinstance(v, str) and not v.strip():
                    missing.append(name)
        if missing:
            self._missing_label.setText(
                "Missing required: " + ", ".join(missing)
            )
            return
        self.accept()
