"""Top-level visual flow editor page."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QLabel,
    QPushButton, QStatusBar, QMessageBox,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, FlowRecord

from tegufox_flow.dsl import parse_flow
from tegufox_flow.errors import ValidationError

from tegufox_gui.widgets.editable_flow import (
    EditableFlow, EditableStep, from_pydantic, to_dict,
)
from tegufox_gui.widgets.step_palette import StepPalette
from tegufox_gui.widgets.step_list_widget import StepListWidget
from tegufox_gui.widgets.step_form_panel import StepFormPanel


def _next_id(steps, prefix: str) -> str:
    used = {s.id for s in steps}
    i = 1
    while f"{prefix}_{i}" in used:
        i += 1
    return f"{prefix}_{i}"


class FlowEditorPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._original_meta: dict = {}
        self._description: str = ""

        bar = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("flow name (slug)")
        self.validate_btn = QPushButton("Validate")
        self.save_btn = QPushButton("Save")
        self.validate_btn.clicked.connect(self._on_validate)
        self.save_btn.clicked.connect(self._on_save)
        bar.addWidget(QLabel("Name:")); bar.addWidget(self.name_edit, 1)
        bar.addWidget(self.validate_btn); bar.addWidget(self.save_btn)

        self.palette = StepPalette()
        self.list_widget = StepListWidget()
        self.form_panel = StepFormPanel(selector_picker=self._open_selector_picker)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.palette)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.form_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)

        self.status = QStatusBar()

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.status)

        self.palette.step_chosen.connect(self._on_palette_choice)
        self.list_widget.step_selected.connect(self._on_step_selected)

    def _open_selector_picker(self, current: str) -> Optional[str]:
        """Open SelectorPickerDialog for the user to click an element in
        a real Camoufox session. Returns the picked selector or None."""
        try:
            from tegufox_core.profile_manager import ProfileManager
            pm = ProfileManager()
            try:
                profiles = list(pm.list())
            except AttributeError:
                profiles = [p["name"] if isinstance(p, dict) else getattr(p, "name", str(p))
                            for p in pm.list_profiles()]
        except Exception:
            profiles = []

        from tegufox_gui.dialogs.selector_picker_dialog import SelectorPickerDialog
        dlg = SelectorPickerDialog(
            profile_names=profiles,
            default_url=current if current.startswith("http") else "",
            parent=self,
        )
        if dlg.exec():
            return dlg.selected_selector() or None
        return None

    def load_flow_by_name(self, name: str) -> None:
        s = self._session()
        try:
            rec = s.query(FlowRecord).filter_by(name=name).first()
            if rec is None:
                self.status.showMessage(f"flow {name!r} not found", 4000)
                return
            yaml_text = rec.yaml_text
        finally:
            s.close()

        import yaml as _yaml
        data = _yaml.safe_load(yaml_text)
        flow = parse_flow(data)
        ef = from_pydantic(flow)
        self.name_edit.setText(ef.name)
        self._description = ef.description
        self._original_meta = {
            "inputs": ef.inputs, "defaults": ef.defaults,
            "editor": ef.editor_meta, "description": ef.description,
        }
        self.list_widget.set_steps(ef.steps)

    def _session(self):
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        return sessionmaker(bind=eng)()

    def _current_flow(self) -> EditableFlow:
        cur_row = self.list_widget.currentRow()
        if cur_row >= 0 and self.form_panel._step is not None:
            try:
                updated = self.form_panel.read_back()
                self.list_widget.update_at(cur_row, updated)
            except Exception:
                pass
        return EditableFlow(
            name=self.name_edit.text().strip(),
            description=self._description,
            inputs=self._original_meta.get("inputs", {}),
            defaults=self._original_meta.get("defaults", {}),
            steps=self.list_widget.steps(),
            editor_meta=self._original_meta.get("editor", {}),
        )

    def _validate_now(self) -> Tuple[str, bool]:
        ef = self._current_flow()
        if not ef.name:
            return "name is required", False
        try:
            parse_flow(to_dict(ef))
            return "valid", True
        except ValidationError as e:
            return str(e), False
        except Exception as e:
            return f"{type(e).__name__}: {e}", False

    def _on_palette_choice(self, step_type: str) -> None:
        existing = self.list_widget.steps()
        prefix = step_type.split(".", 1)[1]
        new_step = EditableStep(
            id=_next_id(existing, prefix),
            type=step_type,
            params={},
        )
        self.list_widget.add(new_step)
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _on_step_selected(self, idx: int, step: EditableStep) -> None:
        if self.form_panel._step is not None and self.list_widget.count() > idx:
            prev_row = self.list_widget.currentRow()
            if prev_row >= 0 and prev_row != idx:
                try:
                    updated = self.form_panel.read_back()
                    self.list_widget.update_at(prev_row, updated)
                except Exception:
                    pass
        self.form_panel.bind(step)

    def _on_validate(self) -> None:
        msg, ok = self._validate_now()
        self.status.showMessage(("valid: " if ok else "error: ") + msg, 6000)

    def _on_save(self) -> None:
        msg, ok = self._validate_now()
        if not ok:
            QMessageBox.critical(self, "Validation failed", msg)
            return
        ef = self._current_flow()
        import yaml as _yaml
        yaml_text = _yaml.safe_dump(to_dict(ef), sort_keys=False, allow_unicode=True)

        s = self._session()
        try:
            now = datetime.utcnow()
            rec = s.query(FlowRecord).filter_by(name=ef.name).first()
            if rec is None:
                rec = FlowRecord(name=ef.name, yaml_text=yaml_text,
                                 schema_version=1, created_at=now, updated_at=now)
                s.add(rec)
            else:
                rec.yaml_text = yaml_text
                rec.updated_at = now
            s.commit()
            self.status.showMessage(f"saved {ef.name!r}", 4000)
        finally:
            s.close()
