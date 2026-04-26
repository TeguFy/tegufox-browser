# Flow Editor (Visual) — Design Spec

**Sub-project:** #3 of 6 (depends on #1)
**Date:** 2026-04-26
**Status:** Draft
**Owner:** lugondev

## 1. Goal

Provide a non-YAML way to create and edit flows inside the Tegufox GUI. Users pick step types from a palette, edit params via auto-generated forms, reorder steps with drag, save → valid YAML to DB. The flow file remains the same `schema_version=1` YAML produced by sub-project #1 — the editor is a pure consumer of that contract.

In scope (v1):

- Form-based step editor for all 29 step types declared in #1.
- Step list with drag-to-reorder + add/remove.
- Step palette (left sidebar) grouped by category (browser/extract/control/io/state).
- Param panel (right) auto-generated from a per-step schema.
- Nested body editing for `control.if`, `control.for_each`, `control.while` via recursive sub-dialog.
- Save → validates via `parse_flow()` → writes to `FlowRecord` table.
- Load → renders existing flow's YAML into the editor.
- Run button (calls existing `runtime.run_flow` like Flows page).

Out of scope (defer):

- Free-form node graph with connection edges
- Live YAML preview pane
- Inline validation error markers
- Drag-drop from palette to specific position (v1 always appends)
- Auto-layout / auto-complete in code fields
- Undo/redo
- Template library
- Live execution highlighting (mark current step yellow during run)

## 2. Architecture

```
tegufox_gui/
├── pages/
│   ├── flow_editor_page.py         NEW — full-screen QSplitter layout
│   └── flows_page.py               MODIFY — add "Edit" / "New Flow" buttons
└── widgets/
    ├── __init__.py                 NEW (or augment)
    ├── step_form_schema.py         NEW — data-only schema for 29 step types
    ├── step_form_panel.py          NEW — renders QFormLayout from schema
    ├── step_list_widget.py         NEW — QListWidget with drag-reorder
    ├── step_palette.py             NEW — left sidebar palette
    └── nested_body_dialog.py       NEW — recursive editor for control bodies
```

Layout:

```
┌─ FlowEditorPage ──────────────────────────────────────────────┐
│ [Name: ____] [Description: ______]   [Validate] [Save] [Run]  │
├─────────────┬──────────────────────────┬──────────────────────┤
│  Palette    │  Step List               │  Param Editor         │
│             │                          │                       │
│  ▾ Browser  │  ☰ 1. open   browser.goto│  url:  https://...    │
│   • goto    │  ☰ 2. type   browser.type│  wait: load     ▾     │
│   • click   │  ☰ 3. click  browser.cl..│                       │
│   • ...     │  ☰ 4. read   extract.tex.│                       │
│             │  + Add step              │                       │
│  ▾ Extract  │                          │                       │
│   • ...     │                          │                       │
│  ▾ Control  │                          │                       │
│   • if      │                          │                       │
│   • for_each│                          │                       │
│  ▾ I/O      │                          │                       │
│  ▾ State    │                          │                       │
└─────────────┴──────────────────────────┴──────────────────────┘
```

Selecting a step in the middle pane populates the right pane.
Double-clicking a `control.if`/`for_each`/`while` step opens a nested dialog showing the same UI for `then`/`else`/`body` lists.

## 3. Step form schema

A pure-data declaration of which params each step type accepts and what widget to use. Defined in `tegufox_gui/widgets/step_form_schema.py`:

```python
@dataclass
class Field:
    name: str
    kind: str     # "string" | "int" | "bool" | "select" | "code" | "steps"
    label: str = ""
    required: bool = False
    default: Any = None
    placeholder: str = ""
    choices: list = field(default_factory=list)   # for "select"
    multiline: bool = False                       # for "string"
    help: str = ""

STEP_FORM: dict[str, list[Field]] = {
    "browser.goto": [
        Field("url", "string", required=True, placeholder="https://example.com"),
        Field("wait_until", "select",
              choices=["load", "domcontentloaded", "networkidle"],
              default="load"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.click": [
        Field("selector", "string", required=True, placeholder="#button or .class"),
        Field("human", "bool", default=True, help="Use HumanMouse"),
        Field("button", "select", choices=["left", "right", "middle"], default="left"),
        Field("click_count", "int", default=1),
    ],
    # ... 27 more entries, one per step type ...
    "control.if": [
        Field("when", "string", required=True, placeholder="{{ vars.x > 0 }}"),
        Field("then", "steps", required=True, label="Then body"),
        Field("else", "steps", label="Else body"),
    ],
    "control.for_each": [
        Field("items", "string", required=True, placeholder="{{ vars.list }}"),
        Field("var", "string", required=True, placeholder="item"),
        Field("body", "steps", required=True),
        Field("index_var", "string"),
    ],
    # ...
}
```

Widget mapping:

| kind | widget |
|---|---|
| string | `QLineEdit` (or `QPlainTextEdit` if `multiline=True`) |
| int | `QSpinBox` (range 0..2³¹) |
| bool | `QCheckBox` |
| select | `QComboBox` |
| code | `QPlainTextEdit` with monospace font, ~6 visible lines, used for `script`, `value`, `body content`, Jinja templates |
| steps | a button "Edit N steps…" opening `NestedBodyDialog` |

Common across-step fields (always available, not in the per-type list):

- `id` (slug, auto-generated `step_<n>` if blank)
- `when` inline guard
- `on_error` collapsed sub-form (action / max_attempts / backoff_ms / goto_step)

These are rendered in a fixed "Step settings" group above the type-specific fields.

## 4. Editor data model

Internal mutable state in `FlowEditorPage`:

```python
@dataclass
class EditableStep:
    id: str
    type: str
    params: dict       # type-specific params (url, selector, body=[...nested EditableStep])
    when: str | None
    on_error: dict | None

@dataclass
class EditableFlow:
    name: str
    description: str
    inputs: dict       # not edited in v1; preserved on round-trip
    defaults: dict
    steps: list[EditableStep]
    editor_meta: dict  # preserved verbatim across load/save (ruamel `editor:` block)
```

Conversion:

- **Load**: `parse_flow(YAML)` → walk pydantic Step → produce `EditableStep`. Nested `then`/`else`/`body` are recursive.
- **Save**: walk `EditableStep` → produce dict matching schema → `parse_flow(dict)` to validate → write `yaml.dump(dict)` (round-trip-safe via ruamel) into `FlowRecord.yaml_text`.

Round-trip preservation:

- `inputs`, `defaults`, `description`, `editor:` namespace are **passed through unchanged** even though v1 doesn't expose UI for them. The `inputs:` field becomes editable in #3.5 / future.

## 5. Run integration

Toolbar **Run** button:

- If flow has unsaved changes → prompt to save first.
- Open small dialog: pick a profile from `ProfileManager.list()`.
- Spawn `_RunWorker` (same QThread pattern from `flows_page.py`) calling `runtime.run_flow(...)`.
- On result: append to a status bar at the bottom: `Run <run_id> finished: succeeded` (or error).

No live highlighting during run (deferred).

## 6. Validation UX

- **Validate** button → calls `parse_flow(serialise(state))` and:
  - Success → green status bar "valid".
  - Failure → red status bar with first 3 problems; click expands to dialog with full list.

Per-step validation while typing is OUT of scope. Only on demand via the button or implicitly on Save.

## 7. Persistence

- Same `FlowRecord` table as #1. `name` is the unique key.
- Save creates the record on first save; subsequent saves update `yaml_text` and `updated_at`.
- "New Flow" button → empty editor with `name=""` placeholder; Save fails until name is provided.

No editor-specific tables.

## 8. Out of scope decisions and why

| Considered | Decision | Why |
|---|---|---|
| Free-form QGraphicsView with edges | Out | Flow is a list, not a graph. Edges add complexity for no semantic gain. |
| Web-based (React Flow / Drawflow in QWebEngine) | Out | Adds JS+HTML stack to a pure-Python project. PyQt6 native is sufficient for a list-of-steps UI. |
| Live YAML preview pane | Out | Useful but doubles widget count. Add in #3.5. |
| Templates library | Out | Most users will copy from `tests/flow/flows/*.yaml` for now. |
| Drag from palette to specific list position | Out | Append-only. Re-order with QListWidget drag is enough. |
| Inline error markers per-step | Out | Validate-on-demand is enough for v1. |
| Live execution progress | Out | Defer to #6 dashboard. |

## 9. Testing strategy

- **Unit (`tests/flow_editor/test_step_form_schema.py`)**: every step in `STEP_REGISTRY` has a corresponding entry in `STEP_FORM`. Field names match handler `required` + `optional`.
- **Unit (`tests/flow_editor/test_step_form_panel.py`)**: rendering + reading back produces correct dict for each kind.
- **Unit (`tests/flow_editor/test_editable_flow.py`)**: round-trip — parse_flow YAML → EditableFlow → serialise → parse_flow again equals original.
- **GUI smoke (`tests/flow_editor/test_flow_editor_page.py`)**: page constructs, palette has 5 categories, list starts empty, adding a step from palette extends list, selecting a step shows its params.

All tests skip if PyQt6 unavailable. No `golden`-style e2e for the editor — that's manual QA.

## 10. File layout (after impl)

```
tegufox_gui/
├── pages/
│   ├── flow_editor_page.py
│   └── flows_page.py            (modified)
└── widgets/
    ├── __init__.py
    ├── step_form_schema.py      (29 step entries + Field dataclass + helpers)
    ├── step_form_panel.py
    ├── step_list_widget.py
    ├── step_palette.py
    └── nested_body_dialog.py

tests/flow_editor/
├── __init__.py
├── conftest.py
├── test_step_form_schema.py
├── test_step_form_panel.py
├── test_editable_flow.py
└── test_flow_editor_page.py
```

## 11. Roadmap context

- After #3 ships, `editor:` namespace in YAML can carry positional metadata for a future free-form layout (#3.5).
- #4 (AI Copilot) plugs in as a "Generate step here" button that calls an LLM and produces an `EditableStep` to insert.
- #5 (AI Flow Generator) produces the `EditableFlow` for the editor to render. Same data model.
- #6 (Run dashboard) reuses `runtime.run_flow` results stored in `flow_runs`.

The editor's `EditableStep` dataclass is the lingua franca for #4/#5 to interoperate with #3.

## 12. Open questions (resolve in plan)

- Exact monospace font selection (use `QFont.StyleHint.Monospace`).
- QSpinBox max for `int` fields (use 2³¹-1; spec doesn't impose max).
- Save vs "Save As" semantics (v1: Save = upsert by name; renaming = creates new record).
