"""Right-pane parameter editor.

Builds a QFormLayout from STEP_FORM[step.type]. Reading back returns an
EditableStep with the same params but values pulled from widgets. Nested
"steps" kind keeps its original list (button opens NestedBodyDialog elsewhere).
"""

from __future__ import annotations
from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QPlainTextEdit, QPushButton, QLabel, QGroupBox,
)

from .editable_flow import EditableStep
from .step_form_schema import Field, fields_for


_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


class _NestedStepsButton(QPushButton):
    """Placeholder button for `kind="steps"` fields — opens NestedBodyDialog
    when clicked. We just store the list and update label."""

    def __init__(self, label_prefix: str, items: List[EditableStep]):
        super().__init__(f"{label_prefix} ({len(items)} step{'s' if len(items)!=1 else ''})…")
        self._items = list(items)
        self._label_prefix = label_prefix
        self.clicked.connect(self._open)

    def items(self) -> List[EditableStep]:
        return list(self._items)

    def set_items(self, xs: List[EditableStep]) -> None:
        self._items = list(xs)
        self.setText(f"{self._label_prefix} ({len(xs)} step{'s' if len(xs)!=1 else ''})…")

    def _open(self):
        from .nested_body_dialog import NestedBodyDialog
        dlg = NestedBodyDialog(self._items, parent=self)
        if dlg.exec():
            self.set_items(dlg.result_steps())


class StepFormPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._step: EditableStep | None = None
        self._widgets: Dict[str, Any] = {}
        self._unknown_params: Dict[str, Any] = {}
        self._layout = QVBoxLayout(self)
        self._inner = QWidget()
        self._inner_layout = QVBoxLayout(self._inner)
        self._layout.addWidget(self._inner)
        self._layout.addStretch(1)

    def _clear(self):
        while self._inner_layout.count():
            item = self._inner_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._widgets.clear()
        self._unknown_params.clear()

    def bind(self, step: EditableStep) -> None:
        self._step = step
        self._clear()

        settings = QGroupBox("Step settings")
        sf = QFormLayout(settings)
        id_edit = QLineEdit(step.id)
        sf.addRow("ID", id_edit)
        type_label = QLabel(step.type)
        type_label.setFont(_MONO)
        sf.addRow("Type", type_label)
        when_edit = QLineEdit(step.when or "")
        when_edit.setPlaceholderText("optional Jinja guard, e.g. {{ vars.ok }}")
        sf.addRow("When", when_edit)
        self._widgets["__id"] = id_edit
        self._widgets["__when"] = when_edit
        self._inner_layout.addWidget(settings)

        type_group = QGroupBox("Parameters")
        tf = QFormLayout(type_group)
        schema = fields_for(step.type)

        if not schema:
            note = QLabel(f"<i>No form schema for {step.type!r}; params kept verbatim.</i>")
            tf.addRow(note)
            self._unknown_params = dict(step.params)
        else:
            for f in schema:
                widget = self._build_widget(f, step.params.get(f.name, f.default))
                tf.addRow(f.label + (" *" if f.required else ""), widget)
                self._widgets[f.name] = widget

        self._inner_layout.addWidget(type_group)

    def _build_widget(self, f: Field, value: Any) -> QWidget:
        if f.kind == "string":
            if f.multiline:
                w = QPlainTextEdit(str(value) if value is not None else "")
                w.setPlaceholderText(f.placeholder)
                return w
            w = QLineEdit(str(value) if value is not None else "")
            if f.placeholder:
                w.setPlaceholderText(f.placeholder)
            return w
        if f.kind == "code":
            w = QPlainTextEdit(str(value) if value is not None else "")
            w.setFont(_MONO)
            if f.placeholder:
                w.setPlaceholderText(f.placeholder)
            return w
        if f.kind == "int":
            w = QSpinBox()
            w.setMaximum(2**31 - 1)
            try:
                w.setValue(int(value) if value is not None else 0)
            except (TypeError, ValueError):
                w.setValue(0)
            return w
        if f.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            return w
        if f.kind == "select":
            w = QComboBox()
            w.addItems(f.choices)
            cur = value if value in f.choices else (f.default if f.default in f.choices else f.choices[0] if f.choices else "")
            if cur:
                w.setCurrentText(cur)
            return w
        if f.kind == "steps":
            items = value if isinstance(value, list) else []
            return _NestedStepsButton(f.label, items)
        raise ValueError(f"unhandled kind {f.kind!r}")

    def read_back(self) -> EditableStep:
        if self._step is None:
            raise RuntimeError("bind() must be called first")
        s = self._step
        new_id = self._widgets["__id"].text().strip() or s.id
        when_text = self._widgets["__when"].text().strip()
        new_when = when_text or None

        new_params: Dict[str, Any] = {}
        if not fields_for(s.type):
            new_params = dict(self._unknown_params)
        else:
            for f in fields_for(s.type):
                w = self._widgets[f.name]
                new_params[f.name] = self._read_widget(f, w)

        return EditableStep(
            id=new_id, type=s.type, params=new_params,
            when=new_when, on_error=s.on_error,
        )

    @staticmethod
    def _read_widget(f: Field, w) -> Any:
        if f.kind == "string":
            return (w.toPlainText() if f.multiline else w.text())
        if f.kind == "code":
            return w.toPlainText()
        if f.kind == "int":
            return int(w.value())
        if f.kind == "bool":
            return bool(w.isChecked())
        if f.kind == "select":
            return w.currentText()
        if f.kind == "steps":
            return w.items()
        raise ValueError(f"unhandled kind {f.kind!r}")
