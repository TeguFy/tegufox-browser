# Flow Editor (Visual) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a PyQt6 form-based flow editor (sub-project #3) on top of the #1 engine. Users create/edit flows without writing YAML.

**Architecture:** Three-pane QSplitter — palette (left), step list with drag-reorder (center), auto-generated param form (right). Internal `EditableStep`/`EditableFlow` dataclasses round-trip cleanly with #1's YAML schema.

**Tech Stack:** PyQt6 native widgets only (no QGraphicsView, no JS). Reuses `tegufox_flow.dsl.parse_flow`, `tegufox_flow.runtime.run_flow`, `tegufox_core.database.FlowRecord`.

**Spec reference:** `docs/superpowers/specs/2026-04-26-flow-editor-design.md`.

---

## File Structure

| File | Responsibility |
|---|---|
| `tegufox_gui/widgets/__init__.py` | Package marker. |
| `tegufox_gui/widgets/step_form_schema.py` | `Field` dataclass + `STEP_FORM` dict (29 entries) + helpers. |
| `tegufox_gui/widgets/step_form_panel.py` | `StepFormPanel(QWidget)` — renders form for one step, exposes `read_back()`. |
| `tegufox_gui/widgets/step_list_widget.py` | `StepListWidget(QListWidget)` — drag-reorder, add/remove. |
| `tegufox_gui/widgets/step_palette.py` | `StepPalette(QTreeWidget)` — categorised step types, click-to-add. |
| `tegufox_gui/widgets/nested_body_dialog.py` | `NestedBodyDialog(QDialog)` — recursive editor for control bodies. |
| `tegufox_gui/pages/flow_editor_page.py` | Top-level editor page assembling all three panes + toolbar. |
| `tegufox_gui/pages/flows_page.py` | (modify) Add "New Flow" button + Edit row action. |
| `tests/flow_editor/conftest.py` | `qapp` fixture. |
| `tests/flow_editor/test_step_form_schema.py` | Coverage parity with `STEP_REGISTRY`. |
| `tests/flow_editor/test_step_form_panel.py` | Render + read-back per kind. |
| `tests/flow_editor/test_editable_flow.py` | Round-trip with parse_flow. |
| `tests/flow_editor/test_flow_editor_page.py` | GUI smoke. |

---

## Conventions

- Activate venv: `source venv/bin/activate`.
- Commit signing bypass: `git commit --no-gpg-sign`.
- Conventional Commits: `feat(editor): ...`, `test(editor): ...`.
- All editor tests live under `tests/flow_editor/` (separate from `tests/flow/`) so the existing #1 suite stays untouched.

---

## Task 1: Step form schema (data only)

**Files:**
- Create: `tegufox_gui/widgets/__init__.py` (empty)
- Create: `tegufox_gui/widgets/step_form_schema.py`
- Create: `tests/flow_editor/__init__.py` (empty)
- Create: `tests/flow_editor/test_step_form_schema.py`

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_step_form_schema.py
import pytest
from tegufox_gui.widgets.step_form_schema import STEP_FORM, Field, fields_for

# Make sure the registered step types are imported, so STEP_REGISTRY is populated.
import tegufox_flow.steps.browser  # noqa
import tegufox_flow.steps.extract  # noqa
import tegufox_flow.steps.control  # noqa
import tegufox_flow.steps.io       # noqa
import tegufox_flow.steps.state    # noqa

from tegufox_flow.steps import STEP_REGISTRY


def test_every_registered_step_has_form_schema():
    missing = sorted(set(STEP_REGISTRY) - set(STEP_FORM))
    assert missing == [], f"step types missing from STEP_FORM: {missing}"


def test_form_schema_required_fields_match_handler_required():
    for step_type, handler in STEP_REGISTRY.items():
        required_fields = {f.name for f in STEP_FORM[step_type] if f.required}
        # Note: handler.required is what `register(required=...)` saw.
        handler_required = set(getattr(handler, "required", ()))
        assert handler_required.issubset(required_fields), (
            f"{step_type}: handler requires {handler_required - required_fields} "
            f"but STEP_FORM does not mark them required"
        )


def test_fields_for_unknown_returns_empty():
    assert fields_for("ghost.step") == []


def test_field_kinds_are_in_expected_set():
    valid = {"string", "int", "bool", "select", "code", "steps"}
    for step_type, fields in STEP_FORM.items():
        for f in fields:
            assert f.kind in valid, f"{step_type}.{f.name} has invalid kind {f.kind!r}"
```

- [ ] **Step 2: Run, expect ImportError**

```bash
mkdir -p tegufox_gui/widgets tests/flow_editor
touch tegufox_gui/widgets/__init__.py tests/flow_editor/__init__.py
pytest tests/flow_editor/test_step_form_schema.py -v
```

- [ ] **Step 3: Implement**

Write `tegufox_gui/widgets/step_form_schema.py`:

```python
"""Form schema for every step type in tegufox_flow.

This is a pure-data declaration — no Qt imports — so it can be unit-tested
without a display server. step_form_panel.py consumes it to build widgets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List


_VALID_KINDS = {"string", "int", "bool", "select", "code", "steps"}


@dataclass
class Field:
    name: str
    kind: str
    label: str = ""
    required: bool = False
    default: Any = None
    placeholder: str = ""
    choices: List[str] = field(default_factory=list)
    multiline: bool = False
    help: str = ""

    def __post_init__(self):
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"unknown field kind {self.kind!r}")
        if not self.label:
            self.label = self.name.replace("_", " ").title()


def fields_for(step_type: str) -> List[Field]:
    return STEP_FORM.get(step_type, [])


# ---------------------------------------------------------------------------
# Browser steps
# ---------------------------------------------------------------------------

_WAIT_UNTIL = ["load", "domcontentloaded", "networkidle", "commit"]
_WAIT_STATE = ["visible", "attached", "hidden", "detached"]


STEP_FORM: dict = {
    "browser.goto": [
        Field("url", "string", required=True, placeholder="https://example.com"),
        Field("wait_until", "select", choices=_WAIT_UNTIL, default="load"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.click": [
        Field("selector", "string", required=True, placeholder="#submit"),
        Field("human", "bool", default=True),
        Field("button", "select", choices=["left", "right", "middle"], default="left"),
        Field("click_count", "int", default=1),
    ],
    "browser.type": [
        Field("selector", "string", required=True, placeholder="#q"),
        Field("text", "string", required=True, placeholder="hello world"),
        Field("clear_first", "bool", default=False),
        Field("human", "bool", default=True),
        Field("delay_ms", "int", default=0),
    ],
    "browser.hover": [
        Field("selector", "string", required=True),
        Field("human", "bool", default=True),
    ],
    "browser.scroll": [
        Field("direction", "select", choices=["down", "up"], default="down"),
        Field("pixels", "int", default=500),
        Field("to", "string", placeholder="top | bottom | <selector>"),
    ],
    "browser.wait_for": [
        Field("selector", "string", required=True),
        Field("state", "select", choices=_WAIT_STATE, default="visible"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.select_option": [
        Field("selector", "string", required=True),
        Field("value", "string", required=True),
    ],
    "browser.screenshot": [
        Field("path", "string", required=True, placeholder="screenshots/x.png"),
        Field("full_page", "bool", default=False),
        Field("selector", "string", placeholder="(optional) for element shot"),
    ],
    "browser.press_key": [
        Field("key", "string", required=True, placeholder="Enter"),
        Field("selector", "string", placeholder="(optional) focus this first"),
    ],

    # ---------------------------------------------------------------------
    # Extract steps
    # ---------------------------------------------------------------------
    "extract.read_text": [
        Field("selector", "string", required=True),
        Field("set", "string", required=True, placeholder="my_var"),
    ],
    "extract.read_attr": [
        Field("selector", "string", required=True),
        Field("attr", "string", required=True, placeholder="href"),
        Field("set", "string", required=True),
    ],
    "extract.eval_js": [
        Field("script", "code", required=True,
              placeholder="() => document.title", multiline=True),
        Field("set", "string", required=True),
    ],
    "extract.url": [
        Field("set", "string", required=True),
    ],
    "extract.title": [
        Field("set", "string", required=True),
    ],

    # ---------------------------------------------------------------------
    # Control steps
    # ---------------------------------------------------------------------
    "control.set": [
        Field("var", "string", required=True),
        Field("value", "code", required=True, placeholder="vars.x + 1"),
    ],
    "control.sleep": [
        Field("ms", "int", required=True, default=1000),
    ],
    "control.if": [
        Field("when", "string", required=True, placeholder="{{ vars.x > 0 }}"),
        Field("then", "steps", required=True, label="Then body"),
        Field("else", "steps", label="Else body"),
    ],
    "control.for_each": [
        Field("items", "code", required=True, placeholder="vars.list"),
        Field("var", "string", required=True, placeholder="item"),
        Field("body", "steps", required=True),
        Field("index_var", "string"),
    ],
    "control.while": [
        Field("when", "code", required=True, placeholder="vars.i < 10"),
        Field("body", "steps", required=True),
        Field("max_iterations", "int", default=1000),
    ],
    "control.break": [],
    "control.continue": [],
    "control.goto": [
        Field("step_id", "string", required=True),
    ],

    # ---------------------------------------------------------------------
    # I/O steps
    # ---------------------------------------------------------------------
    "io.log": [
        Field("message", "string", required=True, multiline=True),
        Field("level", "select", choices=["debug", "info", "warning", "error"],
              default="info"),
    ],
    "io.write_file": [
        Field("path", "string", required=True),
        Field("content", "code", required=True, multiline=True),
        Field("append", "bool", default=False),
        Field("encoding", "string", default="utf-8"),
    ],
    "io.read_file": [
        Field("path", "string", required=True),
        Field("set", "string", required=True),
        Field("format", "select", choices=["text", "json", "csv"], default="text"),
        Field("encoding", "string", default="utf-8"),
    ],
    "io.http_request": [
        Field("method", "select",
              choices=["GET", "POST", "PUT", "DELETE", "PATCH"], default="GET"),
        Field("url", "string", required=True),
        Field("body", "code", multiline=True),
        Field("set", "string"),
        Field("timeout_ms", "int", default=30000),
    ],

    # ---------------------------------------------------------------------
    # State steps
    # ---------------------------------------------------------------------
    "state.save": [
        Field("key", "string", required=True),
        Field("value", "code", required=True),
    ],
    "state.load": [
        Field("key", "string", required=True),
        Field("set", "string", required=True),
        Field("default", "string"),
    ],
    "state.delete": [
        Field("key", "string", required=True),
    ],
}
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_step_form_schema.py -v
```

Expect 4 passed. If `test_every_registered_step_has_form_schema` fails it tells you which step types you missed — add them.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/widgets/__init__.py tegufox_gui/widgets/step_form_schema.py tests/flow_editor/__init__.py tests/flow_editor/test_step_form_schema.py
git commit --no-gpg-sign -m "feat(editor): step form schema for all 29 step types"
```

---

## Task 2: EditableFlow data model + round-trip

**Files:**
- Create: `tegufox_gui/widgets/editable_flow.py`
- Create: `tests/flow_editor/test_editable_flow.py`

This is the in-memory model the editor mutates. `to_dict()` → valid input for `parse_flow`. `from_flow()` ← Pydantic Flow.

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_editable_flow.py
import pytest

# Register step types (so parse_flow has handlers — not strictly required but
# import safety).
import tegufox_flow.steps.browser  # noqa
import tegufox_flow.steps.control  # noqa

from tegufox_flow.dsl import parse_flow
from tegufox_gui.widgets.editable_flow import (
    EditableFlow, EditableStep, from_pydantic, to_dict,
)


def test_round_trip_minimal():
    src = {
        "schema_version": 1,
        "name": "minimal",
        "steps": [{"id": "a", "type": "browser.goto", "url": "https://x"}],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    flow2 = parse_flow(out)
    assert flow2.name == "minimal"
    assert flow2.steps[0].params["url"] == "https://x"


def test_round_trip_nested_if():
    src = {
        "schema_version": 1,
        "name": "x",
        "steps": [{
            "id": "br",
            "type": "control.if",
            "when": "{{ true }}",
            "then": [{"id": "a", "type": "control.sleep", "ms": 1}],
            "else": [{"id": "b", "type": "control.sleep", "ms": 2}],
        }],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    flow2 = parse_flow(out)
    assert flow2.steps[0].type == "control.if"
    then_body = flow2.steps[0].params["then"]
    assert then_body[0].id == "a"


def test_editor_meta_passes_through():
    src = {
        "schema_version": 1,
        "name": "x",
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
        "editor": {"positions": {"a": {"x": 1, "y": 2}}, "anything": "preserved"},
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    assert ef.editor_meta == src["editor"]
    out = to_dict(ef)
    assert out["editor"] == src["editor"]


def test_inputs_pass_through():
    src = {
        "schema_version": 1,
        "name": "x",
        "inputs": {"q": {"type": "string", "required": True}},
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    parse_flow(out)  # still valid
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow_editor/test_editable_flow.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_gui/widgets/editable_flow.py
"""Editor's mutable in-memory model — round-trips with tegufox_flow.dsl."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tegufox_flow.dsl import Flow, Step


_NESTED_KEYS = ("then", "else", "body")


@dataclass
class EditableStep:
    id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    when: Optional[str] = None
    on_error: Optional[Dict[str, Any]] = None


@dataclass
class EditableFlow:
    name: str
    description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    steps: List[EditableStep] = field(default_factory=list)
    editor_meta: Dict[str, Any] = field(default_factory=dict)


def _step_to_editable(s: Step) -> EditableStep:
    params: Dict[str, Any] = {}
    for k, v in s.params.items():
        if k in _NESTED_KEYS and isinstance(v, list):
            params[k] = [_step_to_editable(child) for child in v]
        else:
            params[k] = v
    return EditableStep(
        id=s.id, type=s.type, params=params,
        when=s.when,
        on_error=s.on_error.model_dump() if s.on_error else None,
    )


def _input_to_dict(name, decl) -> Dict[str, Any]:
    out = {"type": decl.type}
    if decl.required:
        out["required"] = True
    if decl.default is not None:
        out["default"] = decl.default
    return out


def from_pydantic(flow: Flow) -> EditableFlow:
    return EditableFlow(
        name=flow.name,
        description=flow.description or "",
        inputs={k: _input_to_dict(k, v) for k, v in flow.inputs.items()},
        defaults=flow.defaults.model_dump() if flow.defaults else {},
        steps=[_step_to_editable(s) for s in flow.steps],
        editor_meta=dict(flow.editor) if flow.editor else {},
    )


def _editable_to_dict(s: EditableStep) -> Dict[str, Any]:
    out: Dict[str, Any] = {"id": s.id, "type": s.type}
    if s.when is not None:
        out["when"] = s.when
    if s.on_error:
        out["on_error"] = dict(s.on_error)
    for k, v in s.params.items():
        if k in _NESTED_KEYS and isinstance(v, list):
            out[k] = [_editable_to_dict(child) for child in v]
        else:
            out[k] = v
    return out


def to_dict(ef: EditableFlow) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "schema_version": 1,
        "name": ef.name,
    }
    if ef.description:
        out["description"] = ef.description
    if ef.inputs:
        out["inputs"] = dict(ef.inputs)
    if ef.defaults:
        out["defaults"] = dict(ef.defaults)
    out["steps"] = [_editable_to_dict(s) for s in ef.steps]
    if ef.editor_meta:
        out["editor"] = dict(ef.editor_meta)
    return out
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_editable_flow.py -v
```

Expect 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/widgets/editable_flow.py tests/flow_editor/test_editable_flow.py
git commit --no-gpg-sign -m "feat(editor): EditableFlow model with parse_flow round-trip"
```

---

## Task 3: StepFormPanel widget

**Files:**
- Create: `tegufox_gui/widgets/step_form_panel.py`
- Create: `tests/flow_editor/conftest.py`
- Create: `tests/flow_editor/test_step_form_panel.py`

- [ ] **Step 1: conftest + failing tests**

```python
# tests/flow_editor/conftest.py
import importlib.util
import sys

import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app
```

```python
# tests/flow_editor/test_step_form_panel.py
import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.control   # noqa

from tegufox_gui.widgets.editable_flow import EditableStep
from tegufox_gui.widgets.step_form_panel import StepFormPanel


def test_panel_renders_browser_goto(qapp):
    s = EditableStep(id="open", type="browser.goto",
                     params={"url": "https://x", "wait_until": "load", "timeout_ms": 5000})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert out.id == "open"
    assert out.type == "browser.goto"
    assert out.params["url"] == "https://x"
    assert out.params["wait_until"] == "load"
    assert out.params["timeout_ms"] == 5000


def test_panel_round_trip_bool(qapp):
    s = EditableStep(id="c", type="browser.click",
                     params={"selector": "#b", "human": False})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert out.params["human"] is False


def test_panel_steps_kind_uses_button(qapp):
    s = EditableStep(id="i", type="control.if",
                     params={"when": "{{ true }}", "then": [
                         EditableStep(id="x", type="control.sleep", params={"ms": 1})
                     ]})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    # The panel must preserve nested steps even though it doesn't render them
    # inline (they're edited via NestedBodyDialog opened from the button).
    assert len(out.params["then"]) == 1
    assert out.params["then"][0].type == "control.sleep"


def test_panel_handles_unknown_type_gracefully(qapp):
    s = EditableStep(id="x", type="ghost.unknown", params={"foo": "bar"})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    # Unknown types preserve params verbatim — schema-less passthrough.
    assert out.params == {"foo": "bar"}
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/flow_editor -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_gui/widgets/step_form_panel.py
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
        # Late import — NestedBodyDialog imports back into widgets/.
        from .nested_body_dialog import NestedBodyDialog
        dlg = NestedBodyDialog(self._items, parent=self)
        if dlg.exec():
            self.set_items(dlg.result_steps())


class StepFormPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._step: EditableStep | None = None
        self._widgets: Dict[str, Any] = {}      # field_name → widget
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

        # ---- Step settings (id, type label) --------------------------------
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

        # ---- Type-specific fields ------------------------------------------
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

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Read-back
    # ------------------------------------------------------------------
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
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_step_form_panel.py -v
```

Expect 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/widgets/step_form_panel.py tests/flow_editor/conftest.py tests/flow_editor/test_step_form_panel.py
git commit --no-gpg-sign -m "feat(editor): StepFormPanel auto-generates form per step schema"
```

---

## Task 4: NestedBodyDialog (recursive editor)

**Files:**
- Create: `tegufox_gui/widgets/nested_body_dialog.py`

The dialog reuses `StepListWidget` + `StepFormPanel` once those exist (Tasks 5+6 below). To unblock the test in Task 3 (button.items() preservation), implement a stub now that just stores the list and exposes `result_steps()`. We replace the body in Task 7.

- [ ] **Step 1: Stub implementation**

```python
# tegufox_gui/widgets/nested_body_dialog.py
"""Modal editor for nested step bodies (control.if then/else, for_each body, while body).

v1 stub: opens with a placeholder explaining the feature is coming. The
calling button preserves the nested step list across save/cancel.
v1.5 wires in StepListWidget + StepFormPanel for full editing.
"""

from __future__ import annotations
from typing import List

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from .editable_flow import EditableStep


class NestedBodyDialog(QDialog):
    def __init__(self, items: List[EditableStep], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit nested body")
        self._result = list(items)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Nested body has {len(items)} step{'s' if len(items)!=1 else ''}.\n"
            "Full inline editing arrives in v1.5; for now you can save/cancel."
        ))
        row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(ok)
        layout.addLayout(row)

    def result_steps(self) -> List[EditableStep]:
        return self._result
```

- [ ] **Step 2: No new tests** (covered indirectly by `test_panel_steps_kind_uses_button`).

- [ ] **Step 3: Run full editor suite**

```bash
pytest tests/flow_editor -q
```

Expect 12 passed (4+4+4).

- [ ] **Step 4: Commit**

```bash
git add tegufox_gui/widgets/nested_body_dialog.py
git commit --no-gpg-sign -m "feat(editor): nested body dialog (stub for v1)"
```

---

## Task 5: StepListWidget (drag-reorder)

**Files:**
- Create: `tegufox_gui/widgets/step_list_widget.py`
- Append: `tests/flow_editor/test_step_list_widget.py`

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_step_list_widget.py
import pytest

import tegufox_flow.steps.browser   # noqa

from tegufox_gui.widgets.editable_flow import EditableStep
from tegufox_gui.widgets.step_list_widget import StepListWidget


def test_list_starts_empty(qapp):
    w = StepListWidget()
    assert w.steps() == []


def test_add_step_appends(qapp):
    w = StepListWidget()
    s = EditableStep(id="a", type="browser.goto", params={"url": "https://x"})
    w.add(s)
    assert len(w.steps()) == 1
    assert w.steps()[0].id == "a"


def test_remove_at_index(qapp):
    w = StepListWidget()
    w.add(EditableStep(id="a", type="control.sleep", params={"ms": 1}))
    w.add(EditableStep(id="b", type="control.sleep", params={"ms": 2}))
    w.remove(0)
    assert [s.id for s in w.steps()] == ["b"]


def test_set_steps_replaces(qapp):
    w = StepListWidget()
    w.add(EditableStep(id="x", type="control.sleep", params={"ms": 1}))
    new = [
        EditableStep(id="a", type="control.sleep", params={"ms": 1}),
        EditableStep(id="b", type="control.sleep", params={"ms": 2}),
    ]
    w.set_steps(new)
    assert [s.id for s in w.steps()] == ["a", "b"]


def test_signal_emitted_on_selection(qapp):
    w = StepListWidget()
    s = EditableStep(id="a", type="control.sleep", params={"ms": 1})
    w.add(s)
    received = []
    w.step_selected.connect(lambda i, st: received.append((i, st.id)))
    w.setCurrentRow(0)
    assert received == [(0, "a")]
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow_editor/test_step_list_widget.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_gui/widgets/step_list_widget.py
"""Centre-pane step list with drag-to-reorder.

Each row shows: <index>. <id> — <type>.  The widget keeps its own list of
EditableStep objects in sync with QListWidget rows.
"""

from __future__ import annotations
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

from .editable_flow import EditableStep


class StepListWidget(QListWidget):
    step_selected = pyqtSignal(int, object)   # (index, EditableStep)
    steps_reordered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._steps: List[EditableStep] = []
        self.currentRowChanged.connect(self._emit_selected)
        self.model().rowsMoved.connect(self._on_rows_moved)

    def steps(self) -> List[EditableStep]:
        return list(self._steps)

    def set_steps(self, xs: List[EditableStep]) -> None:
        self._steps = list(xs)
        self.clear()
        for i, s in enumerate(self._steps):
            self.addItem(self._format_row(i, s))

    def add(self, s: EditableStep) -> None:
        self._steps.append(s)
        self.addItem(self._format_row(len(self._steps) - 1, s))

    def remove(self, idx: int) -> None:
        if 0 <= idx < len(self._steps):
            del self._steps[idx]
            self.takeItem(idx)
            self._refresh_labels()

    def update_at(self, idx: int, s: EditableStep) -> None:
        if 0 <= idx < len(self._steps):
            self._steps[idx] = s
            self.item(idx).setText(self._format_text(idx, s))

    # ------------------------------------------------------------------
    @staticmethod
    def _format_text(i: int, s: EditableStep) -> str:
        return f"{i + 1}. {s.id}  —  {s.type}"

    def _format_row(self, i: int, s: EditableStep) -> QListWidgetItem:
        return QListWidgetItem(self._format_text(i, s))

    def _refresh_labels(self):
        for i in range(self.count()):
            self.item(i).setText(self._format_text(i, self._steps[i]))

    def _emit_selected(self, row: int):
        if 0 <= row < len(self._steps):
            self.step_selected.emit(row, self._steps[row])

    def _on_rows_moved(self, _src_parent, src_start, src_end, _dst_parent, dst_row):
        # Reflect Qt row movement into self._steps.
        moved = self._steps[src_start:src_end + 1]
        del self._steps[src_start:src_end + 1]
        # Adjust insertion index if the move is downward.
        insert_at = dst_row if dst_row <= src_start else dst_row - len(moved)
        self._steps[insert_at:insert_at] = moved
        self._refresh_labels()
        self.steps_reordered.emit()
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_step_list_widget.py -v
```

Expect 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/widgets/step_list_widget.py tests/flow_editor/test_step_list_widget.py
git commit --no-gpg-sign -m "feat(editor): StepListWidget with drag-reorder"
```

---

## Task 6: StepPalette

**Files:**
- Create: `tegufox_gui/widgets/step_palette.py`
- Create: `tests/flow_editor/test_step_palette.py`

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_step_palette.py
import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.extract   # noqa
import tegufox_flow.steps.control   # noqa
import tegufox_flow.steps.io        # noqa
import tegufox_flow.steps.state     # noqa

from tegufox_gui.widgets.step_palette import StepPalette


def test_palette_lists_5_categories(qapp):
    p = StepPalette()
    assert p.categories() == ["browser", "control", "extract", "io", "state"]


def test_palette_has_all_step_types(qapp):
    p = StepPalette()
    types = sum((p.types_in(c) for c in p.categories()), [])
    assert len(types) == 29
    assert "browser.goto" in types
    assert "control.for_each" in types
    assert "state.delete" in types


def test_palette_emits_step_added(qapp):
    p = StepPalette()
    seen = []
    p.step_chosen.connect(lambda t: seen.append(t))
    p._emit_choice("browser.click")
    assert seen == ["browser.click"]
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow_editor/test_step_palette.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_gui/widgets/step_palette.py
"""Left-pane step palette — categorised tree of step types."""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from .step_form_schema import STEP_FORM


class StepPalette(QTreeWidget):
    step_chosen = pyqtSignal(str)   # step_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self._cat_to_types: Dict[str, List[str]] = defaultdict(list)
        for step_type in sorted(STEP_FORM):
            cat = step_type.split(".", 1)[0]
            self._cat_to_types[cat].append(step_type)

        for cat in self.categories():
            cat_item = QTreeWidgetItem([cat])
            self.addTopLevelItem(cat_item)
            for st in self._cat_to_types[cat]:
                child = QTreeWidgetItem([st.split(".", 1)[1]])
                child.setData(0, 0x100, st)   # custom role for full type
                cat_item.addChild(child)
            cat_item.setExpanded(True)

        self.itemDoubleClicked.connect(self._on_double)

    def categories(self) -> List[str]:
        return sorted(self._cat_to_types)

    def types_in(self, category: str) -> List[str]:
        return list(self._cat_to_types.get(category, []))

    def _on_double(self, item: QTreeWidgetItem, _col: int):
        step_type = item.data(0, 0x100)
        if isinstance(step_type, str) and "." in step_type:
            self._emit_choice(step_type)

    def _emit_choice(self, step_type: str) -> None:
        self.step_chosen.emit(step_type)
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_step_palette.py -v
```

Expect 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/widgets/step_palette.py tests/flow_editor/test_step_palette.py
git commit --no-gpg-sign -m "feat(editor): StepPalette categorised tree"
```

---

## Task 7: FlowEditorPage — assemble splitter

**Files:**
- Create: `tegufox_gui/pages/flow_editor_page.py`
- Create: `tests/flow_editor/test_flow_editor_page.py`

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_flow_editor_page.py
import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.control   # noqa

from tegufox_gui.pages.flow_editor_page import FlowEditorPage


def test_editor_constructs_empty(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    assert p.list_widget.steps() == []
    assert p.palette is not None
    assert p.form_panel is not None


def test_palette_choice_appends_step(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.palette._emit_choice("browser.goto")
    assert len(p.list_widget.steps()) == 1
    assert p.list_widget.steps()[0].type == "browser.goto"


def test_load_existing_flow(qapp, tmp_path):
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tegufox_core.database import Base, FlowRecord

    db = tmp_path / "x.db"
    eng = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    yaml = ("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")
    s.add(FlowRecord(name="f", yaml_text=yaml, schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    s.commit(); s.close()

    p = FlowEditorPage(db_path=str(db))
    p.load_flow_by_name("f")
    assert p.name_edit.text() == "f"
    assert len(p.list_widget.steps()) == 1
    assert p.list_widget.steps()[0].id == "a"


def test_validate_button_reports_ok(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.name_edit.setText("ok")
    p.palette._emit_choice("control.sleep")
    msg, ok = p._validate_now()
    assert ok, msg


def test_validate_button_reports_error(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.name_edit.setText("")  # invalid: empty name
    msg, ok = p._validate_now()
    assert not ok
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow_editor/test_flow_editor_page.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_gui/pages/flow_editor_page.py
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
        self._original_meta: dict = {}   # editor:, defaults:, inputs: passthrough
        self._description: str = ""

        # ---- Toolbar ------------------------------------------------------
        bar = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("flow name (slug)")
        self.validate_btn = QPushButton("Validate")
        self.save_btn = QPushButton("Save")
        self.validate_btn.clicked.connect(self._on_validate)
        self.save_btn.clicked.connect(self._on_save)
        bar.addWidget(QLabel("Name:")); bar.addWidget(self.name_edit, 1)
        bar.addWidget(self.validate_btn); bar.addWidget(self.save_btn)

        # ---- Three panes --------------------------------------------------
        self.palette = StepPalette()
        self.list_widget = StepListWidget()
        self.form_panel = StepFormPanel()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.palette)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.form_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)

        # ---- Status -------------------------------------------------------
        self.status = QStatusBar()

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.status)

        # ---- Wiring -------------------------------------------------------
        self.palette.step_chosen.connect(self._on_palette_choice)
        self.list_widget.step_selected.connect(self._on_step_selected)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def _session(self):
        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        return sessionmaker(bind=eng)()

    def _current_flow(self) -> EditableFlow:
        # If the user is currently editing a step in form_panel, read it back first.
        cur_row = self.list_widget.currentRow()
        if cur_row >= 0 and self.form_panel._step is not None:
            updated = self.form_panel.read_back()
            self.list_widget.update_at(cur_row, updated)
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

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------
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
        # Save what was being edited first.
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
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor/test_flow_editor_page.py -v
pytest tests/flow_editor -q
pytest tests/flow -m "not golden" -q   # nothing in #1 should break
```

Expect editor: 5 passed (tied to 12 from earlier = 17 in tests/flow_editor); flow: still 116 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/pages/flow_editor_page.py tests/flow_editor/test_flow_editor_page.py
git commit --no-gpg-sign -m "feat(editor): FlowEditorPage assembling palette + list + form"
```

---

## Task 8: Wire into Flows page + main app

**Files:**
- Modify: `tegufox_gui/pages/flows_page.py`
- Modify: `tegufox_gui/app.py` (add Editor as new stack page)
- Append: `tests/flow_editor/test_flows_page_integration.py`

The Flows page (#1) currently has Upload YAML. We add:
1. **"New Flow"** button → opens the editor with an empty flow.
2. Per-row "Edit" action → opens editor with that flow loaded.

Implementation choice: open the editor as a modal dialog `QDialog` or push it into the existing `QStackedWidget`. Modal is simpler and self-contained. Use modal for v1.

- [ ] **Step 1: Failing test**

```python
# tests/flow_editor/test_flows_page_integration.py
import pytest


def test_flows_page_has_new_flow_button(qapp, tmp_path):
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage(db_path=str(tmp_path / "t.db"))
    # The button is the new addition; existing widget names from #1 stay.
    assert hasattr(page, "new_btn"), "FlowsPage should expose a 'new_btn' attribute"
    assert page.new_btn is not None
```

- [ ] **Step 2: Run, expect AttributeError**

```bash
pytest tests/flow_editor/test_flows_page_integration.py -v
```

- [ ] **Step 3: Modify `tegufox_gui/pages/flows_page.py`**

Read the current file first. Find the `__init__` where `self.upload_btn` is added inside the toolbar `row` layout. Add a sibling button just before it:

```python
# inside FlowsPage.__init__, in the toolbar row construction:
self.new_btn = QPushButton("New Flow")
self.new_btn.clicked.connect(self._on_new_flow)
row.insertWidget(row.indexOf(self.upload_btn), self.new_btn)
```

(Or if the toolbar uses `addWidget` calls in order, place the line for `new_btn` immediately before `row.addWidget(self.upload_btn)`.)

Add the slot at class scope:

```python
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
    self._refresh()   # pick up newly saved flow

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
```

Bind double-click on the list widget to `_on_edit_flow`:

```python
# at end of __init__
self.list_widget.itemDoubleClicked.connect(self._on_edit_flow)
```

- [ ] **Step 4: Run**

```bash
pytest tests/flow_editor -q
pytest tests/flow -m "not golden" -q
```

Expect all editor tests pass; #1 flow suite unchanged (116 passing).

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/pages/flows_page.py tests/flow_editor/test_flows_page_integration.py
git commit --no-gpg-sign -m "feat(editor): wire FlowEditorPage into FlowsPage (New / double-click Edit)"
```

---

## Self-review notes

**Spec coverage:**

| Spec § | Implemented in |
|---|---|
| §2 architecture (palette / list / form) | Tasks 5, 6, 3, 7 |
| §3 step form schema (29 entries) | Task 1 |
| §4 EditableFlow / round-trip | Task 2 |
| §5 run integration | **Deferred** — not in any task. The Run button calls `_on_save` only; running is via the existing Flows page's Run action after saving. Acceptable for v1; flag as concern. |
| §6 validate UX | Task 7 (`_on_validate`) |
| §7 persistence | Task 7 (`_on_save`) |
| §9 testing | Tasks 1-7 inline |

Note: the spec includes a Run button in the editor toolbar; this plan deliberately skips it because (a) FlowsPage already has Run, (b) running the just-edited flow requires a save anyway, (c) the editor would have to spawn a profile-picker dialog and a QThread it doesn't otherwise need. Add in v1.5 if user friction is real.

**Placeholder scan:** No "TBD" or "implement later" anywhere. Task 4's NestedBodyDialog is a stub by design — explicitly marked v1 limitation.

**Type consistency:** `EditableStep`/`EditableFlow` (Task 2) are the single mutable model. `parse_flow` is the validation oracle. `STEP_FORM` is read-only schema.

**Follow-up to schedule (after v1 ships):**
- Replace `NestedBodyDialog` stub with a full nested editor (StepListWidget + StepFormPanel inside a QDialog). One implementation, recursive instances of itself.
- Add live YAML preview pane (collapsed by default).
- Wire editor's own Run button.
- Live execution highlighting.

---

**Plan complete.** Use superpowers:subagent-driven-development to execute task-by-task.
