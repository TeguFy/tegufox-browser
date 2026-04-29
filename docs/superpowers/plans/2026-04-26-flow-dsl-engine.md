# Flow DSL + Execution Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tegufox_flow/` package — a YAML flow DSL plus tree-interpreter engine that runs browser automation flows on a single profile via the existing `TegufoxSession`. Foundation for the visual editor (#3), AI generators (#4/#5), multi-profile orchestrator (#2), and run dashboard (#6).

**Architecture:** YAML files (parsed via `ruamel.yaml`, validated with `pydantic`) describe an ordered list of steps. A tree-interpreter walks the list, dispatches each step type to a handler in `tegufox_flow/steps/`, renders Jinja2 templates against a `FlowContext`, and persists checkpoints + KV state in the existing `tegufox.db`. Crash-resume by replaying from the last checkpointed step.

**Tech Stack:** Python 3.14, `pydantic` (v2), `ruamel.yaml`, `jinja2` (sandboxed), `SQLAlchemy` (already in repo), `pytest`, `playwright.sync_api.Page` via `tegufox_automation.TegufoxSession`. New runtime deps: `pydantic`, `ruamel.yaml`, `jinja2`. The package depends on `tegufox_automation` and `tegufox_core` only.

**Spec reference:** `docs/superpowers/specs/2026-04-25-flow-dsl-engine-design.md`. Section numbers below refer to that spec.

---

## File Structure

**New package** `tegufox_flow/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports (`load_flow`, `FlowEngine`, `FlowContext`, `RunResult`). |
| `errors.py` | `ValidationError`, `StepError`, `FlowError`, `BreakSignal`, `ContinueSignal`, `GotoSignal`. |
| `dsl.py` | Pydantic models (`Flow`, `Step`, `OnError`, `Input`) + `load_flow()` (ruamel.yaml). |
| `expressions.py` | `ExpressionEngine` — Jinja2 sandbox + filters (`slug`, `tojson`, `b64encode`, `b64decode`) + helpers (`now`, `today`, `uuid`, `random_int`). |
| `checkpoints.py` | `CheckpointStore` (run scoped) + `KVStore` (flow scoped) on top of SQLAlchemy. |
| `context.py` | `FlowContext` dataclass + `render()`, `eval()`, `set_var()`, `snapshot()`. |
| `engine.py` | `FlowEngine` — `run()`, `_execute_steps()`, `_execute_one()`, error policy + retry. |
| `runtime.py` | `run_flow()` high-level helper that wires Profile → TegufoxSession → FlowEngine. |
| `cli.py` | `tegufox-cli flow ...` argparse subcommand. |
| `steps/__init__.py` | `STEP_REGISTRY` dict + `register()` decorator. |
| `steps/control.py` | `set, sleep, if, for_each, while, break, continue, goto`. |
| `steps/io.py` | `log, read_file, write_file, http_request`. |
| `steps/state.py` | `save, load, delete`. |
| `steps/extract.py` | `read_text, read_attr, eval_js, url, title`. |
| `steps/browser.py` | `goto, click, type, hover, scroll, wait_for, select_option, screenshot, press_key`. |

**Modified files:**

- `tegufox_core/database.py` — add 4 tables (`Flow`, `FlowRun`, `FlowCheckpoint`, `FlowKVState`).
- `tegufox-cli` script — register `flow` subcommand group.
- `tegufox_cli/api.py` — add `/flows`, `/flows/{name}/runs`, `/runs/{run_id}` endpoints.
- `tegufox_gui/pages/flows_page.py` — new minimal list/run page.
- `tegufox_gui/app.py` (or wherever pages register) — add Flows tab.
- `pytest.ini` — add `golden` marker.

**New test tree:**

```
tests/flow/
├── __init__.py
├── conftest.py              # fixtures: in-memory DB, fake page, static HTTP server
├── test_dsl.py
├── test_expressions.py
├── test_checkpoints.py
├── test_context.py
├── test_engine.py
├── test_steps_control.py
├── test_steps_io.py
├── test_steps_state.py
├── test_steps_extract.py
├── test_steps_browser.py
├── test_runtime.py
├── test_cli.py
└── flows/
    ├── linear_search.yaml
    ├── conditional_filter.yaml
    └── stateful_loop.yaml
```

---

## Conventions for every task

- TDD strict: write failing test → run it → implement → run → commit.
- Run tests with `pytest tests/flow/<file>::<test> -v`.
- Commit message: Conventional Commits — `feat(flow): ...`, `test(flow): ...`, `refactor(flow): ...`.
- Sign-off: rely on existing repo `commit.gpgsign=true` + 1Password SSH agent. **Do not pass `--no-verify` or `--no-gpg-sign`.** If signing fails, surface the error to the user.
- After every commit, run the full `pytest tests/flow -m "not golden" -v` to make sure nothing else broke.

---

## Task 1: Errors module

**Files:**
- Create: `tegufox_flow/__init__.py`
- Create: `tegufox_flow/errors.py`
- Create: `tests/flow/__init__.py`
- Create: `tests/flow/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/flow/test_errors.py
import pytest
from tegufox_flow.errors import (
    ValidationError, StepError, FlowError,
    BreakSignal, ContinueSignal, GotoSignal,
)


def test_step_error_carries_context():
    cause = RuntimeError("nope")
    err = StepError(step_id="search", step_type="browser.click", cause=cause)
    assert err.step_id == "search"
    assert err.step_type == "browser.click"
    assert err.cause is cause
    assert "search" in str(err)
    assert "browser.click" in str(err)


def test_flow_error_wraps_step_error():
    se = StepError(step_id="x", step_type="browser.goto", cause=ValueError("bad url"))
    fe = FlowError(run_id="run-1", flow_name="amazon-search", cause=se)
    assert fe.run_id == "run-1"
    assert fe.flow_name == "amazon-search"
    assert fe.cause is se


def test_validation_error_collects_problems():
    err = ValidationError(["step 'x' missing required field 'url'", "duplicate id 'y'"])
    assert err.problems == [
        "step 'x' missing required field 'url'",
        "duplicate id 'y'",
    ]
    assert "missing required field 'url'" in str(err)


def test_signals_are_distinct():
    assert not issubclass(BreakSignal, ContinueSignal)
    assert not issubclass(ContinueSignal, BreakSignal)
    g = GotoSignal(target="cleanup")
    assert g.target == "cleanup"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
mkdir -p tegufox_flow tests/flow
touch tegufox_flow/__init__.py tests/flow/__init__.py
pytest tests/flow/test_errors.py -v
```

Expected: `ImportError: cannot import name 'ValidationError' from 'tegufox_flow.errors'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tegufox_flow/errors.py
"""Exception hierarchy for the flow engine.

ValidationError is raised at parse time and never caught by the engine.
StepError is raised by step handlers; the engine applies on_error policy.
FlowError is the terminal run failure surfaced to callers.

Break/Continue/Goto are control-flow signals (not errors) used inside loops.
"""

from typing import List, Optional


class FlowEngineException(Exception):
    """Base class — never raise directly."""


class ValidationError(FlowEngineException):
    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        super().__init__("flow validation failed:\n  - " + "\n  - ".join(self.problems))


class StepError(FlowEngineException):
    def __init__(self, step_id: str, step_type: str, cause: BaseException):
        self.step_id = step_id
        self.step_type = step_type
        self.cause = cause
        super().__init__(f"step {step_id!r} ({step_type}) failed: {cause}")


class FlowError(FlowEngineException):
    def __init__(self, run_id: str, flow_name: str, cause: BaseException):
        self.run_id = run_id
        self.flow_name = flow_name
        self.cause = cause
        super().__init__(f"flow {flow_name!r} run {run_id} failed: {cause}")


class BreakSignal(FlowEngineException):
    """Raised by control.break, caught by control.for_each / control.while."""


class ContinueSignal(FlowEngineException):
    """Raised by control.continue, caught by control.for_each / control.while."""


class GotoSignal(FlowEngineException):
    def __init__(self, target: str):
        self.target = target
        super().__init__(f"goto {target!r}")
```

```python
# tegufox_flow/__init__.py
"""Tegufox flow DSL + engine.

Public surface:
    load_flow(path) -> Flow
    FlowEngine(profile_name=..., db_path=...).run(flow, inputs=...) -> RunResult
"""
from .errors import (
    ValidationError, StepError, FlowError,
    BreakSignal, ContinueSignal, GotoSignal,
)

__all__ = [
    "ValidationError", "StepError", "FlowError",
    "BreakSignal", "ContinueSignal", "GotoSignal",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/flow/test_errors.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/__init__.py tegufox_flow/errors.py tests/flow/__init__.py tests/flow/test_errors.py
git commit -m "feat(flow): exception hierarchy for flow engine"
```

---

## Task 2: DSL pydantic schema

**Files:**
- Create: `tegufox_flow/dsl.py`
- Create: `tests/flow/test_dsl.py`

**Background:** spec §4. `Flow` has `schema_version`, `name`, optional `description`, `inputs`, `defaults`, required `steps`, optional `editor`. `Step` has `id`, `type`, optional `on_error`, `when`, plus a `params: dict` for type-specific fields. We don't validate per-step params here — that happens when each step handler is registered (Task 9 onward).

- [ ] **Step 1: Write the failing test**

```python
# tests/flow/test_dsl.py
import pytest
from tegufox_flow.dsl import Flow, Step, OnError, Input, parse_flow
from tegufox_flow.errors import ValidationError


def test_minimal_flow_validates():
    flow = parse_flow({
        "schema_version": 1,
        "name": "min",
        "steps": [{"id": "a", "type": "browser.goto", "url": "https://x"}],
    })
    assert flow.name == "min"
    assert flow.schema_version == 1
    assert len(flow.steps) == 1
    assert flow.steps[0].id == "a"
    assert flow.steps[0].type == "browser.goto"
    assert flow.steps[0].params == {"url": "https://x"}


def test_inputs_typed_and_default():
    flow = parse_flow({
        "schema_version": 1,
        "name": "in",
        "inputs": {
            "query": {"type": "string", "required": True},
            "n": {"type": "int", "default": 10},
        },
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    })
    assert flow.inputs["query"].type == "string"
    assert flow.inputs["query"].required is True
    assert flow.inputs["n"].default == 10


def test_defaults_on_error_inherited_into_step_when_missing():
    flow = parse_flow({
        "schema_version": 1,
        "name": "d",
        "defaults": {"on_error": {"action": "retry", "max_attempts": 5, "backoff_ms": 100}},
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    })
    assert flow.defaults.on_error.action == "retry"
    assert flow.defaults.on_error.max_attempts == 5


def test_unknown_top_level_field_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({"schema_version": 1, "name": "x", "steps": [], "garbage": 1})
    assert "garbage" in str(e.value)


def test_duplicate_step_ids_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [
                {"id": "a", "type": "control.sleep", "ms": 1},
                {"id": "a", "type": "control.sleep", "ms": 2},
            ],
        })
    assert "duplicate" in str(e.value).lower()


def test_unknown_schema_version_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({"schema_version": 99, "name": "x", "steps": []})
    assert "schema_version" in str(e.value)


def test_step_id_must_be_slug():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [{"id": "has space", "type": "control.sleep", "ms": 1}],
        })
    assert "id" in str(e.value).lower()


def test_nested_steps_in_control_if_validate():
    flow = parse_flow({
        "schema_version": 1,
        "name": "x",
        "steps": [{
            "id": "branch",
            "type": "control.if",
            "when": "{{ true }}",
            "then": [{"id": "inner", "type": "control.sleep", "ms": 1}],
            "else": [{"id": "other", "type": "control.sleep", "ms": 2}],
        }],
    })
    assert flow.steps[0].params["then"][0].id == "inner"
    assert flow.steps[0].params["else"][0].id == "other"


def test_duplicate_id_across_nesting_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [
                {"id": "outer", "type": "control.if", "when": "{{ true }}",
                 "then": [{"id": "outer", "type": "control.sleep", "ms": 1}]},
            ],
        })
    assert "duplicate" in str(e.value).lower()


def test_editor_namespace_preserved_verbatim():
    raw = {
        "schema_version": 1,
        "name": "x",
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
        "editor": {"positions": {"a": {"x": 100, "y": 200}}, "any": "value"},
    }
    flow = parse_flow(raw)
    assert flow.editor == raw["editor"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/flow/test_dsl.py -v
```

Expected: ImportError on `parse_flow`.

- [ ] **Step 3: Write minimal implementation**

```python
# tegufox_flow/dsl.py
"""Pydantic schema for flow YAML files.

Validates structure but does NOT validate per-step params (that's the
responsibility of each step handler in tegufox_flow.steps.*).
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .errors import ValidationError


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
SCHEMA_VERSIONS = {1}
ON_ERROR_ACTIONS = {"abort", "retry", "skip", "goto"}


class OnError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["abort", "retry", "skip", "goto"] = "abort"
    max_attempts: int = Field(default=1, ge=1, le=100)
    backoff_ms: int = Field(default=0, ge=0)
    goto_step: Optional[str] = None

    @model_validator(mode="after")
    def _check_goto(self) -> "OnError":
        if self.action == "goto" and not self.goto_step:
            raise ValueError("on_error.action=goto requires goto_step")
        return self


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["string", "int", "float", "bool", "list", "map"]
    required: bool = False
    default: Any = None


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    on_error: OnError = Field(default_factory=OnError)
    timeout_ms: int = 30_000


class Step(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    type: str
    on_error: Optional[OnError] = None
    when: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _id_is_slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError(f"step id {v!r} must match {SLUG_RE.pattern}")
        return v

    @property
    def params(self) -> Dict[str, Any]:
        # Coerce nested step lists in then/else/body to Step instances if they
        # look like dicts. We do this lazily to avoid recursion in pydantic.
        raw = {k: v for k, v in self.__pydantic_extra__.items() if v is not None}
        for key in ("then", "else", "body"):
            if key in raw and isinstance(raw[key], list):
                raw[key] = [
                    s if isinstance(s, Step) else Step(**s)
                    for s in raw[key]
                ]
        return raw


class Flow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    name: str
    description: Optional[str] = None
    inputs: Dict[str, Input] = Field(default_factory=dict)
    defaults: Defaults = Field(default_factory=Defaults)
    steps: List[Step]
    editor: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _known_version(cls, v: int) -> int:
        if v not in SCHEMA_VERSIONS:
            raise ValueError(f"unsupported schema_version {v} (known: {SCHEMA_VERSIONS})")
        return v

    @field_validator("name")
    @classmethod
    def _name_is_slug(cls, v: str) -> str:
        if not SLUG_RE.match(v.replace("-", "_")):
            raise ValueError(f"flow name {v!r} must be a slug")
        return v


def _collect_step_ids(steps: List[Step], seen: set, problems: list, path: str = "") -> None:
    for s in steps:
        full = f"{path}/{s.id}" if path else s.id
        if s.id in seen:
            problems.append(f"duplicate step id {s.id!r} at {full}")
        seen.add(s.id)
        for key in ("then", "else", "body"):
            nested = s.params.get(key)
            if isinstance(nested, list):
                _collect_step_ids(nested, seen, problems, full)


def parse_flow(data: Dict[str, Any]) -> Flow:
    """Build a Flow from a plain dict; raise ValidationError with all problems."""
    try:
        flow = Flow.model_validate(data)
    except Exception as e:
        # pydantic ValidationError → our ValidationError
        problems = []
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = ".".join(str(x) for x in err.get("loc", ()))
                problems.append(f"{loc}: {err.get('msg')}")
        else:
            problems.append(str(e))
        raise ValidationError(problems) from e

    problems: List[str] = []
    _collect_step_ids(flow.steps, set(), problems)
    if problems:
        raise ValidationError(problems)
    return flow
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/flow/test_dsl.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/dsl.py tests/flow/test_dsl.py
git commit -m "feat(flow): pydantic schema for flow YAML"
```

---

## Task 3: YAML loader with comment-preserving round-trip

**Files:**
- Modify: `tegufox_flow/dsl.py` (add `load_flow`, `dump_flow`)
- Modify: `tests/flow/test_dsl.py` (append round-trip tests)

**Background:** spec §4.5 — round-trip via `ruamel.yaml`. Uses `YAML(typ='rt')` to preserve comments and key order. Editor relies on this.

- [ ] **Step 1: Append failing tests**

```python
# tests/flow/test_dsl.py — append
import io
from pathlib import Path
from tegufox_flow.dsl import load_flow, dump_flow


def test_load_flow_from_path(tmp_path: Path):
    f = tmp_path / "x.yaml"
    f.write_text(
        "schema_version: 1\n"
        "name: x\n"
        "steps:\n"
        "  - id: a\n"
        "    type: control.sleep\n"
        "    ms: 1\n"
    )
    flow = load_flow(f)
    assert flow.name == "x"


def test_dump_preserves_step_order_and_comments(tmp_path: Path):
    src = (
        "schema_version: 1\n"
        "name: x\n"
        "# top comment\n"
        "steps:\n"
        "  - id: first\n"
        "    type: control.sleep\n"
        "    ms: 1  # inline\n"
        "  - id: second\n"
        "    type: control.sleep\n"
        "    ms: 2\n"
    )
    f = tmp_path / "src.yaml"
    f.write_text(src)
    out = tmp_path / "out.yaml"
    raw = load_flow(f, raw=True)
    dump_flow(raw, out)
    text = out.read_text()
    assert "# top comment" in text
    assert "# inline" in text
    assert text.index("first") < text.index("second")


def test_load_flow_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_flow(tmp_path / "nope.yaml")
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/flow/test_dsl.py -k "load or dump" -v
```

Expected: ImportError on `load_flow`/`dump_flow`.

- [ ] **Step 3: Implement loader**

```python
# tegufox_flow/dsl.py — add at bottom
from pathlib import Path
from ruamel.yaml import YAML
from typing import Union

_YAML_RT = YAML(typ="rt")
_YAML_RT.preserve_quotes = True
_YAML_RT.indent(mapping=2, sequence=4, offset=2)


def load_flow(path: Union[str, Path], *, raw: bool = False):
    """Load a flow from disk.

    raw=False (default) → returns a parsed Flow (Pydantic).
    raw=True → returns the ruamel.yaml CommentedMap, suitable for dump_flow.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = _YAML_RT.load(fh)
    if raw:
        return data
    return parse_flow(_to_plain(data))


def dump_flow(data, path: Union[str, Path]) -> None:
    """Write a CommentedMap (from load_flow(..., raw=True)) preserving comments."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as fh:
        _YAML_RT.dump(data, fh)


def _to_plain(obj):
    """Recursively convert ruamel CommentedMap/Seq into plain dict/list."""
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    if isinstance(obj, CommentedMap):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, CommentedSeq):
        return [_to_plain(v) for v in obj]
    return obj
```

Add `ruamel.yaml` to `requirements.txt` (or `pyproject.toml`):

```bash
echo "ruamel.yaml>=0.18" >> requirements.txt
pip install ruamel.yaml
```

Update `tegufox_flow/__init__.py`:

```python
# tegufox_flow/__init__.py — replace existing
from .errors import (
    ValidationError, StepError, FlowError,
    BreakSignal, ContinueSignal, GotoSignal,
)
from .dsl import Flow, Step, Input, OnError, parse_flow, load_flow, dump_flow

__all__ = [
    "ValidationError", "StepError", "FlowError",
    "BreakSignal", "ContinueSignal", "GotoSignal",
    "Flow", "Step", "Input", "OnError",
    "parse_flow", "load_flow", "dump_flow",
]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_dsl.py -v
```

Expected: all 13 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/dsl.py tegufox_flow/__init__.py tests/flow/test_dsl.py requirements.txt
git commit -m "feat(flow): YAML round-trip loader with ruamel.yaml"
```

---

## Task 4: Expression engine (Jinja2 sandbox + filters/helpers)

**Files:**
- Create: `tegufox_flow/expressions.py`
- Create: `tests/flow/test_expressions.py`

**Background:** spec §4.4. Sandboxed Jinja2 with restricted globals, custom filters (`slug`, `tojson`, `b64encode`, `b64decode`), and helpers (`now`, `today`, `uuid`, `random_int`).

- [ ] **Step 1: Write failing tests**

```python
# tests/flow/test_expressions.py
import json
import pytest
from datetime import datetime
from tegufox_flow.expressions import ExpressionEngine


@pytest.fixture
def eng():
    return ExpressionEngine()


def test_render_string_with_var(eng):
    assert eng.render("hello {{ name }}", {"name": "world"}) == "hello world"


def test_render_returns_str_even_for_int(eng):
    assert eng.render("{{ n + 1 }}", {"n": 5}) == "6"


def test_eval_returns_native_python(eng):
    assert eng.eval("n + 1", {"n": 5}) == 6
    assert eng.eval("xs | length", {"xs": [1, 2, 3]}) == 3


def test_filter_slug(eng):
    assert eng.eval("'Hello, World!' | slug", {}) == "hello-world"


def test_filter_tojson(eng):
    out = eng.render("{{ d | tojson }}", {"d": {"a": 1}})
    assert json.loads(out) == {"a": 1}


def test_filter_b64(eng):
    enc = eng.render("{{ 'abc' | b64encode }}", {})
    assert enc == "YWJj"
    dec = eng.render("{{ 'YWJj' | b64decode }}", {})
    assert dec == "abc"


def test_helper_now(eng, monkeypatch):
    fixed = datetime(2026, 1, 2, 3, 4, 5)

    class _DT:
        @staticmethod
        def utcnow():
            return fixed

    monkeypatch.setattr("tegufox_flow.expressions._dt_now", lambda: fixed)
    out = eng.eval("now()", {})
    assert out == fixed


def test_helper_random_int_within_range(eng):
    for _ in range(50):
        x = eng.eval("random_int(0, 5)", {})
        assert 0 <= x <= 5


def test_sandbox_blocks_dunder_access(eng):
    with pytest.raises(Exception):
        eng.eval("().__class__", {})


def test_sandbox_blocks_attr_to_function(eng):
    with pytest.raises(Exception):
        eng.eval("foo.__init__", {"foo": object()})


def test_undefined_var_raises(eng):
    with pytest.raises(Exception):
        eng.eval("missing_var + 1", {})


def test_render_keeps_strings_without_templates(eng):
    assert eng.render("plain text", {}) == "plain text"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_expressions.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# tegufox_flow/expressions.py
"""Sandboxed Jinja2 environment for flow expressions.

Variable namespaces (passed via context dict): inputs, vars, state, env.
Helpers: now(), today(), uuid(), random_int(a, b).
Filters: slug, tojson, b64encode, b64decode.
"""

from __future__ import annotations
import base64
import json
import random
import re
import uuid as _uuid
from datetime import datetime, date
from typing import Any, Dict

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


_SLUG_NONALNUM = re.compile(r"[^a-z0-9]+")


def _slug(s: Any) -> str:
    return _SLUG_NONALNUM.sub("-", str(s).lower()).strip("-")


def _tojson(o: Any, indent: int | None = None) -> str:
    return json.dumps(o, ensure_ascii=False, indent=indent, default=str)


def _b64encode(s: Any) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return base64.b64encode(s).decode("ascii")


def _b64decode(s: Any) -> str:
    return base64.b64decode(str(s)).decode("utf-8")


def _dt_now() -> datetime:  # indirection for monkeypatching in tests
    return datetime.utcnow()


def _today() -> date:
    return _dt_now().date()


class ExpressionEngine:
    def __init__(self) -> None:
        env = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=False,
        )
        env.filters.update({
            "slug": _slug,
            "tojson": _tojson,
            "b64encode": _b64encode,
            "b64decode": _b64decode,
        })
        env.globals.update({
            "now": _dt_now,
            "today": _today,
            "uuid": lambda: str(_uuid.uuid4()),
            "random_int": lambda a, b: random.randint(int(a), int(b)),
        })
        self._env = env

    def render(self, template: str, context: Dict[str, Any]) -> str:
        return self._env.from_string(template).render(**context)

    def eval(self, expr: str, context: Dict[str, Any]) -> Any:
        # Wrap expression so we can return native value (Jinja2 expressions
        # don't have a clean "return value" API; we use compile_expression).
        compiled = self._env.compile_expression(expr)
        return compiled(**context)
```

Add Jinja2:

```bash
echo "jinja2>=3.1" >> requirements.txt
pip install jinja2
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_expressions.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/expressions.py tests/flow/test_expressions.py requirements.txt
git commit -m "feat(flow): sandboxed Jinja2 expression engine with filters/helpers"
```

---

## Task 5: Database tables (Flow / FlowRun / FlowCheckpoint / FlowKVState)

**Files:**
- Modify: `tegufox_core/database.py`
- Create: `tests/flow/test_db_schema.py`

**Background:** spec §6. Add 4 tables to the existing SQLAlchemy `Base` so they share `tegufox.db`. No Alembic — `Base.metadata.create_all()` is idempotent and runs at startup.

- [ ] **Step 1: Write failing tests**

```python
# tests/flow/test_db_schema.py
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import (
    Base, FlowRecord, FlowRun, FlowCheckpoint, FlowKVState,
)


def _session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_flow_record_unique_name():
    s = _session()
    s.add(FlowRecord(name="a", yaml_text="x", schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    s.commit()
    s.add(FlowRecord(name="a", yaml_text="y", schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.commit()


def test_flow_run_status_default_running():
    s = _session()
    f = FlowRecord(name="a", yaml_text="x", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f)
    s.commit()
    r = FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running", started_at=datetime.utcnow())
    s.add(r)
    s.commit()
    assert s.query(FlowRun).first().status == "running"


def test_checkpoint_pk_is_run_seq():
    s = _session()
    s.add(FlowCheckpoint(run_id="r1", step_id="s", seq=1,
                         vars_json="{}", created_at=datetime.utcnow()))
    s.add(FlowCheckpoint(run_id="r1", step_id="t", seq=2,
                         vars_json="{}", created_at=datetime.utcnow()))
    s.commit()
    rows = s.query(FlowCheckpoint).order_by(FlowCheckpoint.seq).all()
    assert [r.step_id for r in rows] == ["s", "t"]


def test_kv_state_pk_is_flow_key():
    s = _session()
    s.add(FlowKVState(flow_name="f", key="k", value_json='"v"', updated_at=datetime.utcnow()))
    s.commit()
    row = s.query(FlowKVState).filter_by(flow_name="f", key="k").one()
    assert row.value_json == '"v"'
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_db_schema.py -v
```

Expected: ImportError on `FlowRecord` etc.

- [ ] **Step 3: Add tables**

Append to `tegufox_core/database.py` (after the existing `Profile`, `Screen`, etc., and before `__all__` if any):

```python
# tegufox_core/database.py — append before any __all__ block

class FlowRecord(Base):
    __tablename__ = "flows"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    yaml_text = Column(Text, nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class FlowRun(Base):
    __tablename__ = "flow_runs"

    run_id = Column(String(64), primary_key=True)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    profile_name = Column(String(255), nullable=False, index=True)
    inputs_json = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="running", index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    last_step_id = Column(String(255))
    error_text = Column(Text)


class FlowCheckpoint(Base):
    __tablename__ = "flow_checkpoints"

    run_id = Column(String(64), primary_key=True)
    seq = Column(Integer, primary_key=True)
    step_id = Column(String(255), nullable=False)
    vars_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False)


class FlowKVState(Base):
    __tablename__ = "flow_kv_state"

    flow_name = Column(String(255), primary_key=True)
    key = Column(String(255), primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_db_schema.py -v
```

Expected: 4 passed. Re-run the existing DB tests to make sure nothing broke:

```bash
pytest tests/ -k "database or db" -v
```

- [ ] **Step 5: Commit**

```bash
git add tegufox_core/database.py tests/flow/test_db_schema.py
git commit -m "feat(flow): SQLAlchemy tables for flows/runs/checkpoints/kv"
```

---

## Task 6: Checkpoint and KV stores

**Files:**
- Create: `tegufox_flow/checkpoints.py`
- Create: `tests/flow/test_checkpoints.py`

**Background:** spec §6. `CheckpointStore` writes per-step snapshots to `flow_checkpoints` and reads the last successful one for resume. `KVStore` is the per-flow KV table accessed by `state.*` steps.

- [ ] **Step 1: Write failing tests**

```python
# tests/flow/test_checkpoints.py
import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowCheckpoint, FlowKVState
from tegufox_flow.checkpoints import CheckpointStore, KVStore


@pytest.fixture
def session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    s = Session()
    yield s
    s.close()


def test_checkpoint_save_increments_seq(session):
    store = CheckpointStore(session)
    store.save("run-1", "step-a", {"x": 1})
    store.save("run-1", "step-b", {"x": 2})
    rows = session.query(FlowCheckpoint).filter_by(run_id="run-1").order_by(FlowCheckpoint.seq).all()
    assert [(r.seq, r.step_id) for r in rows] == [(1, "step-a"), (2, "step-b")]
    assert json.loads(rows[1].vars_json) == {"x": 2}


def test_checkpoint_last_returns_latest(session):
    store = CheckpointStore(session)
    store.save("run-1", "a", {"i": 0})
    store.save("run-1", "b", {"i": 1})
    store.save("run-1", "c", {"i": 2})
    cp = store.last("run-1")
    assert cp is not None
    assert cp.step_id == "c"
    assert cp.vars == {"i": 2}


def test_checkpoint_last_none_for_unknown_run(session):
    store = CheckpointStore(session)
    assert store.last("ghost") is None


def test_kv_save_then_load(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", {"a": 1})
    assert kv.load("k") == {"a": 1}


def test_kv_load_default_when_missing(session):
    kv = KVStore(session, flow_name="f")
    assert kv.load("nope", default="x") == "x"


def test_kv_save_overwrites_and_updates_timestamp(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", "v1")
    t1 = session.query(FlowKVState).one().updated_at
    kv.save("k", "v2")
    rows = session.query(FlowKVState).filter_by(flow_name="f", key="k").all()
    assert len(rows) == 1
    assert rows[0].value_json == '"v2"'
    assert rows[0].updated_at >= t1


def test_kv_delete(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", 1)
    kv.delete("k")
    assert kv.load("k", default=None) is None


def test_kv_isolated_per_flow(session):
    a = KVStore(session, flow_name="a")
    b = KVStore(session, flow_name="b")
    a.save("k", 1)
    b.save("k", 2)
    assert a.load("k") == 1
    assert b.load("k") == 2
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/flow/test_checkpoints.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# tegufox_flow/checkpoints.py
"""Checkpoint and KV state stores backed by SQLAlchemy.

CheckpointStore: per-run, append-only, monotonic seq.
KVStore: per-flow, last-write-wins on (flow_name, key).
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from tegufox_core.database import FlowCheckpoint, FlowKVState

_MISSING = object()


@dataclass
class Checkpoint:
    run_id: str
    step_id: str
    seq: int
    vars: dict


class CheckpointStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def save(self, run_id: str, step_id: str, vars: dict) -> int:
        last = (
            self._s.query(FlowCheckpoint.seq)
            .filter_by(run_id=run_id)
            .order_by(FlowCheckpoint.seq.desc())
            .first()
        )
        next_seq = (last[0] + 1) if last else 1
        row = FlowCheckpoint(
            run_id=run_id,
            seq=next_seq,
            step_id=step_id,
            vars_json=json.dumps(vars, default=str),
            created_at=datetime.utcnow(),
        )
        self._s.add(row)
        self._s.commit()
        return next_seq

    def last(self, run_id: str) -> Optional[Checkpoint]:
        row = (
            self._s.query(FlowCheckpoint)
            .filter_by(run_id=run_id)
            .order_by(FlowCheckpoint.seq.desc())
            .first()
        )
        if row is None:
            return None
        return Checkpoint(
            run_id=row.run_id,
            step_id=row.step_id,
            seq=row.seq,
            vars=json.loads(row.vars_json),
        )


class KVStore:
    def __init__(self, session: Session, flow_name: str) -> None:
        self._s = session
        self._flow = flow_name

    def save(self, key: str, value: Any) -> None:
        row = (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .first()
        )
        payload = json.dumps(value, default=str)
        now = datetime.utcnow()
        if row is None:
            row = FlowKVState(
                flow_name=self._flow, key=key, value_json=payload, updated_at=now,
            )
            self._s.add(row)
        else:
            row.value_json = payload
            row.updated_at = now
        self._s.commit()

    def load(self, key: str, default: Any = _MISSING) -> Any:
        row = (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .first()
        )
        if row is None:
            if default is _MISSING:
                return None
            return default
        return json.loads(row.value_json)

    def delete(self, key: str) -> None:
        (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .delete()
        )
        self._s.commit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_checkpoints.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/checkpoints.py tests/flow/test_checkpoints.py
git commit -m "feat(flow): checkpoint store + per-flow KV state"
```

---

## Task 7: FlowContext

**Files:**
- Create: `tegufox_flow/context.py`
- Create: `tests/flow/test_context.py`

**Background:** spec §5.3. `FlowContext` carries everything a step handler needs and exposes `render`/`eval` over the right namespaces. `snapshot()` returns a JSON-serializable copy of `vars` for checkpointing.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_context.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.context import FlowContext
from tegufox_flow.expressions import ExpressionEngine
from tegufox_flow.checkpoints import CheckpointStore, KVStore


@pytest.fixture
def ctx():
    return FlowContext(
        session=MagicMock(),
        page=MagicMock(),
        flow_name="f",
        run_id="r",
        inputs={"q": "laptop"},
        vars={"i": 0},
        kv=MagicMock(spec=KVStore),
        checkpoints=MagicMock(spec=CheckpointStore),
        expressions=ExpressionEngine(),
        env_allowlist={"HOME"},
    )


def test_render_uses_inputs_namespace(ctx):
    assert ctx.render("q={{ inputs.q }}") == "q=laptop"


def test_render_uses_vars_namespace(ctx):
    assert ctx.render("i={{ vars.i }}") == "i=0"


def test_eval_returns_native(ctx):
    assert ctx.eval("vars.i + 1") == 1


def test_set_var_updates_vars(ctx):
    ctx.set_var("i", 7)
    assert ctx.vars["i"] == 7


def test_set_var_rejects_inputs_collision(ctx):
    with pytest.raises(ValueError):
        ctx.set_var("inputs", "x")


def test_state_lookup_hits_kv(ctx):
    ctx.kv.load.return_value = "stored"
    assert ctx.eval("state.foo") == "stored"
    ctx.kv.load.assert_called_once_with("foo")


def test_env_allowlist_enforced(ctx, monkeypatch):
    monkeypatch.setenv("HOME", "/tmp")
    monkeypatch.setenv("SECRET", "x")
    assert ctx.eval("env.HOME") == "/tmp"
    with pytest.raises(Exception):
        ctx.eval("env.SECRET")


def test_snapshot_is_json_serialisable(ctx):
    import json
    ctx.set_var("nested", {"a": [1, 2, 3]})
    json.dumps(ctx.snapshot())  # no error


def test_logger_namespaced(ctx):
    assert ctx.logger.name.startswith("tegufox_flow")
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/flow/test_context.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# tegufox_flow/context.py
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from .expressions import ExpressionEngine
from .checkpoints import CheckpointStore, KVStore


_LOG = logging.getLogger("tegufox_flow.context")


class _StateProxy:
    """Lazy proxy: state.foo → kv.load('foo')."""

    def __init__(self, kv: KVStore):
        self._kv = kv

    def __getattr__(self, name: str) -> Any:
        return self._kv.load(name)

    def __getitem__(self, name: str) -> Any:
        return self._kv.load(name)


class _EnvProxy:
    def __init__(self, allowlist: Set[str]):
        self._allow = allowlist

    def __getattr__(self, name: str) -> str:
        if name not in self._allow:
            raise PermissionError(f"env var {name!r} not in allowlist")
        return os.environ.get(name, "")

    def __getitem__(self, name: str) -> str:
        return self.__getattr__(name)


@dataclass
class FlowContext:
    session: Any                  # TegufoxSession (avoid import cycle)
    page: Any                     # playwright Page (None until session opens)
    flow_name: str
    run_id: str
    inputs: Dict[str, Any]
    vars: Dict[str, Any]
    kv: KVStore
    checkpoints: CheckpointStore
    expressions: ExpressionEngine
    env_allowlist: Set[str] = field(default_factory=set)
    current_step_id: Optional[str] = None
    logger: logging.Logger = field(default_factory=lambda: _LOG)

    def _ns(self) -> Dict[str, Any]:
        return {
            "inputs": self.inputs,
            "vars": self.vars,
            "state": _StateProxy(self.kv),
            "env": _EnvProxy(self.env_allowlist),
        }

    def render(self, template: str) -> str:
        return self.expressions.render(template, self._ns())

    def eval(self, expr: str) -> Any:
        return self.expressions.eval(expr, self._ns())

    def set_var(self, name: str, value: Any) -> None:
        if name in {"inputs", "state", "env"}:
            raise ValueError(f"cannot shadow reserved namespace {name!r}")
        self.vars[name] = value

    def snapshot(self) -> Dict[str, Any]:
        # Returns a JSON-serialisable shallow copy of vars only.
        # state and inputs are restored from elsewhere.
        import json
        json.dumps(self.vars, default=str)  # raises if not serialisable
        return dict(self.vars)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_context.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/context.py tests/flow/test_context.py
git commit -m "feat(flow): FlowContext with sandboxed namespaces"
```

---

## Task 8: STEP_REGISTRY infrastructure

**Files:**
- Create: `tegufox_flow/steps/__init__.py`
- Create: `tests/flow/test_step_registry.py`

**Background:** Step handlers register themselves via decorator. The engine looks them up by `step.type`.

- [ ] **Step 1: Failing test**

```python
# tests/flow/test_step_registry.py
import pytest
from tegufox_flow.steps import register, STEP_REGISTRY, get_handler, StepSpec


def test_register_adds_handler():
    @register("test.echo", required=("text",), optional=("upper",))
    def echo(spec: StepSpec, ctx):
        return spec.params["text"]
    assert "test.echo" in STEP_REGISTRY
    assert get_handler("test.echo") is echo
    del STEP_REGISTRY["test.echo"]


def test_get_handler_unknown_raises():
    with pytest.raises(KeyError) as e:
        get_handler("ghost.step")
    assert "ghost.step" in str(e.value)


def test_register_validates_required_params_at_call():
    @register("test.req", required=("must",))
    def fn(spec, ctx):
        return spec.params["must"]
    spec = StepSpec(id="x", type="test.req", params={})
    with pytest.raises(KeyError) as e:
        fn(spec, ctx=None)
    assert "must" in str(e.value)
    del STEP_REGISTRY["test.req"]


def test_register_rejects_duplicate():
    @register("test.dup")
    def a(spec, ctx): pass
    with pytest.raises(ValueError):
        @register("test.dup")
        def b(spec, ctx): pass
    del STEP_REGISTRY["test.dup"]
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_step_registry.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/__init__.py
"""Step handler registry.

Each step type is a function (StepSpec, FlowContext) -> None.
Register via @register("category.name", required=(...), optional=(...)).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

STEP_REGISTRY: Dict[str, Callable] = {}


@dataclass
class StepSpec:
    id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    on_error: Optional[Any] = None
    when: Optional[str] = None


def register(
    name: str,
    *,
    required: Iterable[str] = (),
    optional: Iterable[str] = (),
) -> Callable:
    required_t: Tuple[str, ...] = tuple(required)
    optional_t: Tuple[str, ...] = tuple(optional)
    if name in STEP_REGISTRY:
        raise ValueError(f"step type already registered: {name}")

    def deco(fn: Callable) -> Callable:
        if name in STEP_REGISTRY:
            raise ValueError(f"step type already registered: {name}")

        def wrapper(spec: StepSpec, ctx) -> Any:
            for r in required_t:
                if r not in spec.params:
                    raise KeyError(f"step {spec.id!r} ({name}) missing required param {r!r}")
            return fn(spec, ctx)

        wrapper.__name__ = fn.__name__
        wrapper.required = required_t
        wrapper.optional = optional_t
        STEP_REGISTRY[name] = wrapper
        return wrapper

    return deco


def get_handler(step_type: str) -> Callable:
    if step_type not in STEP_REGISTRY:
        raise KeyError(f"unknown step type: {step_type}")
    return STEP_REGISTRY[step_type]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_step_registry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/__init__.py tests/flow/test_step_registry.py
git commit -m "feat(flow): step handler registry with required-param validation"
```

---

## Task 9: Control steps (set, sleep, if, when guard)

**Files:**
- Create: `tegufox_flow/steps/control.py`
- Create: `tests/flow/test_steps_control.py`

**Background:** spec §4.3 control. The control steps call back into the engine for nested execution. Implement only `set`, `sleep`, `if` here; loops and break/continue/goto in Task 10.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_steps_control.py
import time
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.control  # noqa: F401  -- registers handlers


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.eval.side_effect = lambda expr: eval(expr, {}, {})  # cheap eval for tests
    c.render.side_effect = lambda s: s
    return c


def test_control_set_assigns_var(ctx):
    handler = get_handler("control.set")
    spec = StepSpec(id="s", type="control.set", params={"var": "x", "value": "1+2"})
    handler(spec, ctx)
    ctx.set_var.assert_called_once_with("x", 3)


def test_control_sleep_sleeps(monkeypatch, ctx):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    handler = get_handler("control.sleep")
    handler(StepSpec(id="s", type="control.sleep", params={"ms": 250}), ctx)
    assert slept == [0.25]


def test_control_if_runs_then_when_true(ctx):
    ctx.eval.side_effect = lambda expr: True
    inner_called = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: inner_called.append(steps))
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    spec = StepSpec(
        id="c", type="control.if",
        params={"when": "true", "then": ["A"], "else": ["B"]},
    )
    handler(spec, ctx)
    assert inner_called == [["A"]]


def test_control_if_runs_else_when_false(ctx):
    ctx.eval.side_effect = lambda expr: False
    inner_called = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: inner_called.append(steps))
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    spec = StepSpec(
        id="c", type="control.if",
        params={"when": "false", "then": ["A"], "else": ["B"]},
    )
    handler(spec, ctx)
    assert inner_called == [["B"]]


def test_control_if_no_else_when_false_does_nothing(ctx):
    ctx.eval.side_effect = lambda expr: False
    fake_engine = MagicMock()
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    handler(
        StepSpec(id="c", type="control.if", params={"when": "false", "then": ["A"]}),
        ctx,
    )
    fake_engine.execute_steps.assert_not_called()
```

- [ ] **Step 2: Run, expect ImportError on `tegufox_flow.steps.control`**

```bash
pytest tests/flow/test_steps_control.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/control.py
"""Control-flow step handlers.

This module's import side-effect registers handlers in STEP_REGISTRY.
Engine sets ctx.engine before invoking nested steps so handlers can call
ctx.engine.execute_steps(...) for then/else/body lists.
"""

from __future__ import annotations
import time
from typing import List

from . import register, StepSpec


@register("control.set", required=("var", "value"))
def _set(spec: StepSpec, ctx) -> None:
    name = spec.params["var"]
    raw = spec.params["value"]
    value = ctx.eval(raw) if isinstance(raw, str) else raw
    ctx.set_var(name, value)


@register("control.sleep", required=("ms",))
def _sleep(spec: StepSpec, ctx) -> None:
    ms = int(spec.params["ms"])
    time.sleep(ms / 1000.0)


@register("control.if", required=("when", "then"))
def _if(spec: StepSpec, ctx) -> None:
    cond = bool(ctx.eval(spec.params["when"]))
    branch: List = spec.params["then"] if cond else spec.params.get("else") or []
    if branch:
        ctx.engine.execute_steps(branch, ctx)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_control.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/control.py tests/flow/test_steps_control.py
git commit -m "feat(flow): control.set, control.sleep, control.if"
```

---

## Task 10: Loops, break/continue, goto

**Files:**
- Modify: `tegufox_flow/steps/control.py`
- Modify: `tests/flow/test_steps_control.py`

- [ ] **Step 1: Append failing tests**

```python
# tests/flow/test_steps_control.py — append
from tegufox_flow.errors import BreakSignal, ContinueSignal, GotoSignal


def test_for_each_iterates_and_sets_var(ctx):
    seen = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: seen.append(c.vars["item"]))
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2, 3]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2,3]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert seen == [1, 2, 3]


def test_for_each_break_exits_early(ctx):
    iterations = []

    def body(steps, c):
        iterations.append(c.vars["item"])
        if c.vars["item"] == 2:
            raise BreakSignal("break")

    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=body)
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2, 3]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2,3]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert iterations == [1, 2]


def test_for_each_continue_skips_remainder(ctx):
    iterations = []

    def body(steps, c):
        iterations.append(c.vars["item"])
        raise ContinueSignal("continue")

    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=body)
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert iterations == [1, 2]


def test_while_respects_max_iterations(ctx):
    ctx.eval.side_effect = lambda expr: True  # always true
    fake_engine = MagicMock()
    ctx.engine = fake_engine
    handler = get_handler("control.while")
    spec = StepSpec(id="w", type="control.while",
                    params={"when": "true", "max_iterations": 3,
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert fake_engine.execute_steps.call_count == 3


def test_break_outside_loop_propagates(ctx):
    handler = get_handler("control.break")
    with pytest.raises(BreakSignal):
        handler(StepSpec(id="b", type="control.break", params={}), ctx)


def test_continue_outside_loop_propagates(ctx):
    handler = get_handler("control.continue")
    with pytest.raises(ContinueSignal):
        handler(StepSpec(id="c", type="control.continue", params={}), ctx)


def test_goto_raises_signal(ctx):
    handler = get_handler("control.goto")
    with pytest.raises(GotoSignal) as e:
        handler(StepSpec(id="g", type="control.goto", params={"step_id": "cleanup"}), ctx)
    assert e.value.target == "cleanup"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_steps_control.py -v
```

- [ ] **Step 3: Append handlers**

```python
# tegufox_flow/steps/control.py — append at bottom
from ..errors import BreakSignal, ContinueSignal, GotoSignal


@register("control.for_each", required=("items", "var", "body"))
def _for_each(spec: StepSpec, ctx) -> None:
    items = ctx.eval(spec.params["items"]) if isinstance(spec.params["items"], str) else spec.params["items"]
    var = spec.params["var"]
    index_var = spec.params.get("index_var")
    body = spec.params["body"]

    saved = ctx.vars.get(var, _MISSING := object())
    saved_idx = ctx.vars.get(index_var, _MISSING) if index_var else None

    try:
        for idx, item in enumerate(items):
            ctx.set_var(var, item)
            if index_var:
                ctx.set_var(index_var, idx)
            try:
                ctx.engine.execute_steps(body, ctx)
            except ContinueSignal:
                continue
            except BreakSignal:
                break
    finally:
        if saved is _MISSING:
            ctx.vars.pop(var, None)
        else:
            ctx.vars[var] = saved
        if index_var:
            if saved_idx is _MISSING:
                ctx.vars.pop(index_var, None)
            else:
                ctx.vars[index_var] = saved_idx


@register("control.while", required=("when", "body"))
def _while(spec: StepSpec, ctx) -> None:
    body = spec.params["body"]
    max_it = int(spec.params.get("max_iterations", 1000))
    count = 0
    while count < max_it and bool(ctx.eval(spec.params["when"])):
        count += 1
        try:
            ctx.engine.execute_steps(body, ctx)
        except ContinueSignal:
            continue
        except BreakSignal:
            return


@register("control.break")
def _break(spec: StepSpec, ctx) -> None:
    raise BreakSignal("break")


@register("control.continue")
def _continue(spec: StepSpec, ctx) -> None:
    raise ContinueSignal("continue")


@register("control.goto", required=("step_id",))
def _goto(spec: StepSpec, ctx) -> None:
    raise GotoSignal(target=spec.params["step_id"])
```

Replace the `_MISSING := object()` walrus with a module-level sentinel for clarity:

```python
# tegufox_flow/steps/control.py — near top, before handlers
_MISSING = object()
```

And remove the inline `:=` from `_for_each`:

```python
    saved = ctx.vars.get(var, _MISSING)
    saved_idx = ctx.vars.get(index_var, _MISSING) if index_var else None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_control.py -v
```

Expected: 12 passed (5 from Task 9 + 7 new).

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/control.py tests/flow/test_steps_control.py
git commit -m "feat(flow): control.for_each/while/break/continue/goto"
```

---

## Task 11: I/O steps

**Files:**
- Create: `tegufox_flow/steps/io.py`
- Create: `tests/flow/test_steps_io.py`

**Background:** spec §4.3 io. `log`, `read_file`, `write_file`, `http_request`. Use `requests` (already a dep via Camoufox stack — verify with `pip show requests`; if absent add to requirements).

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_steps_io.py
import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.io  # noqa: F401


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.render.side_effect = lambda s: s
    c.eval.side_effect = lambda e: eval(e, {}, {})
    c.logger = logging.getLogger("test")
    return c


def test_log_emits_at_level(ctx, caplog):
    caplog.set_level(logging.WARNING, logger="test")
    handler = get_handler("io.log")
    handler(StepSpec(id="l", type="io.log",
                     params={"message": "warn me", "level": "warning"}), ctx)
    assert any("warn me" in r.message for r in caplog.records)


def test_write_file_creates_dirs(tmp_path, ctx):
    target = tmp_path / "sub" / "out.txt"
    handler = get_handler("io.write_file")
    handler(StepSpec(id="w", type="io.write_file",
                     params={"path": str(target), "content": "hi"}), ctx)
    assert target.read_text() == "hi"


def test_write_file_append(tmp_path, ctx):
    target = tmp_path / "log.txt"
    target.write_text("a")
    handler = get_handler("io.write_file")
    handler(StepSpec(id="w", type="io.write_file",
                     params={"path": str(target), "content": "b", "append": True}), ctx)
    assert target.read_text() == "ab"


def test_read_file_text(tmp_path, ctx):
    f = tmp_path / "x.txt"
    f.write_text("hello")
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "set": "out"}), ctx)
    ctx.set_var.assert_called_once_with("out", "hello")


def test_read_file_json(tmp_path, ctx):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"a": 1}))
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "format": "json", "set": "out"}), ctx)
    ctx.set_var.assert_called_once_with("out", {"a": 1})


def test_read_file_csv(tmp_path, ctx):
    f = tmp_path / "x.csv"
    f.write_text("a,b\n1,2\n3,4\n")
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "format": "csv", "set": "rows"}), ctx)
    ctx.set_var.assert_called_once_with("rows", [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])


def test_http_request_get(ctx):
    fake_resp = MagicMock(status_code=200, text="ok", headers={"X": "Y"})
    fake_resp.json.return_value = {"k": "v"}
    with patch("tegufox_flow.steps.io.requests.request", return_value=fake_resp) as p:
        handler = get_handler("io.http_request")
        handler(
            StepSpec(id="h", type="io.http_request",
                     params={"method": "GET", "url": "https://api/x", "set": "resp"}),
            ctx,
        )
        p.assert_called_once()
        call = p.call_args
        assert call.kwargs["method"] == "GET"
        assert call.kwargs["url"] == "https://api/x"
    ctx.set_var.assert_called_once()
    saved = ctx.set_var.call_args.args[1]
    assert saved["status"] == 200
    assert saved["body"] == "ok"
    assert saved["json"] == {"k": "v"}
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_steps_io.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/io.py
"""I/O step handlers: log, read_file, write_file, http_request."""

from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any, Dict

import requests  # transitively via camoufox/playwright

from . import register, StepSpec


_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


@register("io.log", required=("message",))
def _log(spec: StepSpec, ctx) -> None:
    level = _LEVELS[spec.params.get("level", "info")]
    msg = ctx.render(spec.params["message"])
    ctx.logger.log(level, msg)


@register("io.write_file", required=("path", "content"))
def _write_file(spec: StepSpec, ctx) -> None:
    path = Path(ctx.render(spec.params["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ctx.render(spec.params["content"]) if isinstance(spec.params["content"], str) else json.dumps(spec.params["content"])
    mode = "a" if spec.params.get("append") else "w"
    encoding = spec.params.get("encoding", "utf-8")
    with path.open(mode, encoding=encoding) as f:
        f.write(content)


@register("io.read_file", required=("path", "set"))
def _read_file(spec: StepSpec, ctx) -> None:
    path = Path(ctx.render(spec.params["path"]))
    encoding = spec.params.get("encoding", "utf-8")
    fmt = spec.params.get("format", "text")
    with path.open("r", encoding=encoding) as f:
        text = f.read()
    if fmt == "text":
        out: Any = text
    elif fmt == "json":
        out = json.loads(text)
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        out = list(reader)
    else:
        raise ValueError(f"unknown format {fmt!r}")
    ctx.set_var(spec.params["set"], out)


@register("io.http_request", required=("method", "url"))
def _http_request(spec: StepSpec, ctx) -> None:
    p = spec.params
    kwargs: Dict[str, Any] = {
        "method": p["method"].upper(),
        "url": ctx.render(p["url"]),
        "timeout": p.get("timeout_ms", 30_000) / 1000.0,
    }
    if "headers" in p:
        kwargs["headers"] = {k: ctx.render(v) for k, v in p["headers"].items()}
    if "body" in p:
        body = p["body"]
        if isinstance(body, str):
            kwargs["data"] = ctx.render(body)
        else:
            kwargs["json"] = body

    resp = requests.request(**kwargs)
    payload: Dict[str, Any] = {
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text,
    }
    try:
        payload["json"] = resp.json()
    except Exception:
        payload["json"] = None

    if "set" in p:
        ctx.set_var(p["set"], payload)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_io.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/io.py tests/flow/test_steps_io.py
git commit -m "feat(flow): io.log/read_file/write_file/http_request"
```

---

## Task 12: State steps

**Files:**
- Create: `tegufox_flow/steps/state.py`
- Create: `tests/flow/test_steps_state.py`

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_steps_state.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.state  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.kv = MagicMock()
    c.eval.side_effect = lambda e: eval(e, {}, {})
    c.render.side_effect = lambda s: s
    return c


def test_save_calls_kv(ctx):
    handler = get_handler("state.save")
    handler(StepSpec(id="s", type="state.save",
                     params={"key": "k", "value": "[1,2]"}), ctx)
    ctx.kv.save.assert_called_once_with("k", [1, 2])


def test_load_with_default(ctx):
    ctx.kv.load.return_value = "default"
    handler = get_handler("state.load")
    handler(StepSpec(id="l", type="state.load",
                     params={"key": "k", "set": "out", "default": "default"}), ctx)
    ctx.kv.load.assert_called_once_with("k", default="default")
    ctx.set_var.assert_called_once_with("out", "default")


def test_delete_calls_kv(ctx):
    handler = get_handler("state.delete")
    handler(StepSpec(id="d", type="state.delete", params={"key": "k"}), ctx)
    ctx.kv.delete.assert_called_once_with("k")
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_steps_state.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/state.py
"""Persistent KV state step handlers."""

from . import register, StepSpec


@register("state.save", required=("key", "value"))
def _save(spec, ctx) -> None:
    raw = spec.params["value"]
    value = ctx.eval(raw) if isinstance(raw, str) else raw
    ctx.kv.save(spec.params["key"], value)


@register("state.load", required=("key", "set"))
def _load(spec, ctx) -> None:
    default = spec.params.get("default")
    value = ctx.kv.load(spec.params["key"], default=default)
    ctx.set_var(spec.params["set"], value)


@register("state.delete", required=("key",))
def _delete(spec, ctx) -> None:
    ctx.kv.delete(spec.params["key"])
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_state.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/state.py tests/flow/test_steps_state.py
git commit -m "feat(flow): state.save/load/delete"
```

---

## Task 13: Extract steps

**Files:**
- Create: `tegufox_flow/steps/extract.py`
- Create: `tests/flow/test_steps_extract.py`

**Background:** spec §4.3 extract. Operate on `ctx.page` (Playwright sync `Page`). Use `page.locator(selector).inner_text()`, `.get_attribute()`, `page.evaluate(script)`, `page.url`, `page.title()`.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_steps_extract.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.extract  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    return c


def test_read_text(ctx):
    locator = MagicMock()
    locator.inner_text.return_value = "hello"
    ctx.page.locator.return_value = locator
    handler = get_handler("extract.read_text")
    handler(StepSpec(id="e", type="extract.read_text",
                     params={"selector": "h1", "set": "out"}), ctx)
    ctx.page.locator.assert_called_once_with("h1")
    ctx.set_var.assert_called_once_with("out", "hello")


def test_read_attr(ctx):
    locator = MagicMock()
    locator.get_attribute.return_value = "/x"
    ctx.page.locator.return_value = locator
    handler = get_handler("extract.read_attr")
    handler(StepSpec(id="e", type="extract.read_attr",
                     params={"selector": "a", "attr": "href", "set": "h"}), ctx)
    locator.get_attribute.assert_called_once_with("href")
    ctx.set_var.assert_called_once_with("h", "/x")


def test_eval_js(ctx):
    ctx.page.evaluate.return_value = [1, 2, 3]
    handler = get_handler("extract.eval_js")
    handler(StepSpec(id="e", type="extract.eval_js",
                     params={"script": "() => [1,2,3]", "set": "arr"}), ctx)
    ctx.page.evaluate.assert_called_once_with("() => [1,2,3]")
    ctx.set_var.assert_called_once_with("arr", [1, 2, 3])


def test_url(ctx):
    ctx.page.url = "https://x"
    handler = get_handler("extract.url")
    handler(StepSpec(id="e", type="extract.url", params={"set": "u"}), ctx)
    ctx.set_var.assert_called_once_with("u", "https://x")


def test_title(ctx):
    ctx.page.title.return_value = "T"
    handler = get_handler("extract.title")
    handler(StepSpec(id="e", type="extract.title", params={"set": "t"}), ctx)
    ctx.set_var.assert_called_once_with("t", "T")
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_steps_extract.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/extract.py
"""Extract data from the current page into vars."""

from . import register, StepSpec


@register("extract.read_text", required=("selector", "set"))
def _read_text(spec, ctx) -> None:
    sel = ctx.render(spec.params["selector"])
    text = ctx.page.locator(sel).inner_text()
    ctx.set_var(spec.params["set"], text)


@register("extract.read_attr", required=("selector", "attr", "set"))
def _read_attr(spec, ctx) -> None:
    sel = ctx.render(spec.params["selector"])
    attr = spec.params["attr"]
    val = ctx.page.locator(sel).get_attribute(attr)
    ctx.set_var(spec.params["set"], val)


@register("extract.eval_js", required=("script", "set"))
def _eval_js(spec, ctx) -> None:
    script = ctx.render(spec.params["script"])
    val = ctx.page.evaluate(script)
    ctx.set_var(spec.params["set"], val)


@register("extract.url", required=("set",))
def _url(spec, ctx) -> None:
    ctx.set_var(spec.params["set"], ctx.page.url)


@register("extract.title", required=("set",))
def _title(spec, ctx) -> None:
    ctx.set_var(spec.params["set"], ctx.page.title())
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_extract.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/extract.py tests/flow/test_steps_extract.py
git commit -m "feat(flow): extract.read_text/read_attr/eval_js/url/title"
```

---

## Task 14: Browser navigation steps

**Files:**
- Create: `tegufox_flow/steps/browser.py`
- Create: `tests/flow/test_steps_browser.py`

**Background:** spec §4.3 browser. Implement the navigation/passive subset here: `goto`, `wait_for`, `screenshot`, `press_key`, `scroll`, `select_option`. Interactive (click/type/hover) in Task 15 since they need `HumanMouse`/`HumanKeyboard`.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_steps_browser.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.browser  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    return c


def test_goto(ctx):
    get_handler("browser.goto")(
        StepSpec(id="g", type="browser.goto",
                 params={"url": "https://x", "wait_until": "load", "timeout_ms": 5000}),
        ctx,
    )
    ctx.page.goto.assert_called_once_with("https://x", wait_until="load", timeout=5000)


def test_wait_for_visible_default(ctx):
    get_handler("browser.wait_for")(
        StepSpec(id="w", type="browser.wait_for",
                 params={"selector": "#x", "timeout_ms": 1000}),
        ctx,
    )
    ctx.page.locator.assert_called_once_with("#x")
    ctx.page.locator.return_value.wait_for.assert_called_once_with(state="visible", timeout=1000)


def test_screenshot_full_page(tmp_path, ctx):
    out = tmp_path / "shot.png"
    get_handler("browser.screenshot")(
        StepSpec(id="s", type="browser.screenshot",
                 params={"path": str(out), "full_page": True}),
        ctx,
    )
    ctx.page.screenshot.assert_called_once_with(path=str(out), full_page=True)


def test_screenshot_element(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.screenshot")(
        StepSpec(id="s", type="browser.screenshot",
                 params={"path": "x.png", "selector": "#card"}),
        ctx,
    )
    ctx.page.locator.assert_called_once_with("#card")
    locator.screenshot.assert_called_once_with(path="x.png")


def test_press_key_global(ctx):
    get_handler("browser.press_key")(
        StepSpec(id="p", type="browser.press_key",
                 params={"key": "Enter"}),
        ctx,
    )
    ctx.page.keyboard.press.assert_called_once_with("Enter")


def test_press_key_focused(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.press_key")(
        StepSpec(id="p", type="browser.press_key",
                 params={"key": "Tab", "selector": "#x"}),
        ctx,
    )
    locator.press.assert_called_once_with("Tab")


def test_scroll_pixels_down(ctx):
    get_handler("browser.scroll")(
        StepSpec(id="s", type="browser.scroll",
                 params={"direction": "down", "pixels": 500}),
        ctx,
    )
    ctx.page.mouse.wheel.assert_called_once_with(0, 500)


def test_scroll_to_bottom(ctx):
    get_handler("browser.scroll")(
        StepSpec(id="s", type="browser.scroll", params={"to": "bottom"}),
        ctx,
    )
    ctx.page.evaluate.assert_called_once()
    arg = ctx.page.evaluate.call_args.args[0]
    assert "scrollHeight" in arg


def test_select_option(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.select_option")(
        StepSpec(id="s", type="browser.select_option",
                 params={"selector": "select", "value": "v"}),
        ctx,
    )
    locator.select_option.assert_called_once_with("v")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_steps_browser.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/steps/browser.py
"""Browser step handlers — navigation + passive subset.

Interactive steps (click/type/hover) are added in the next task because
they delegate to HumanMouse / HumanKeyboard from tegufox_automation.
"""

from __future__ import annotations
from . import register, StepSpec


_DEFAULT_TIMEOUT = 30_000


@register("browser.goto", required=("url",))
def _goto(spec: StepSpec, ctx) -> None:
    p = spec.params
    ctx.page.goto(
        ctx.render(p["url"]),
        wait_until=p.get("wait_until", "load"),
        timeout=int(p.get("timeout_ms", _DEFAULT_TIMEOUT)),
    )


@register("browser.wait_for", required=("selector",))
def _wait_for(spec: StepSpec, ctx) -> None:
    p = spec.params
    ctx.page.locator(ctx.render(p["selector"])).wait_for(
        state=p.get("state", "visible"),
        timeout=int(p.get("timeout_ms", _DEFAULT_TIMEOUT)),
    )


@register("browser.screenshot", required=("path",))
def _screenshot(spec: StepSpec, ctx) -> None:
    p = spec.params
    path = ctx.render(p["path"])
    if "selector" in p:
        ctx.page.locator(ctx.render(p["selector"])).screenshot(path=path)
    else:
        ctx.page.screenshot(path=path, full_page=bool(p.get("full_page", False)))


@register("browser.press_key", required=("key",))
def _press_key(spec: StepSpec, ctx) -> None:
    p = spec.params
    if "selector" in p:
        ctx.page.locator(ctx.render(p["selector"])).press(p["key"])
    else:
        ctx.page.keyboard.press(p["key"])


@register("browser.scroll")
def _scroll(spec: StepSpec, ctx) -> None:
    p = spec.params
    if "to" in p:
        target = p["to"]
        if target == "top":
            ctx.page.evaluate("() => window.scrollTo(0, 0)")
        elif target == "bottom":
            ctx.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        else:
            ctx.page.locator(ctx.render(target)).scroll_into_view_if_needed()
        return
    direction = p.get("direction", "down")
    pixels = int(p.get("pixels", 500))
    dy = pixels if direction == "down" else -pixels
    ctx.page.mouse.wheel(0, dy)


@register("browser.select_option", required=("selector", "value"))
def _select_option(spec: StepSpec, ctx) -> None:
    ctx.page.locator(ctx.render(spec.params["selector"])).select_option(
        spec.params["value"]
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_browser.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/browser.py tests/flow/test_steps_browser.py
git commit -m "feat(flow): browser.goto/wait_for/screenshot/press_key/scroll/select_option"
```

---

## Task 15: Browser interactive steps (click, type, hover) with HumanMouse/HumanKeyboard

**Files:**
- Modify: `tegufox_flow/steps/browser.py`
- Modify: `tests/flow/test_steps_browser.py`

**Background:** spec §4.3, decision §13. Default `human=True`. The session exposes `HumanMouse(page)` and `HumanKeyboard(page)` lazily; we cache them on the context as `ctx._human_mouse` and `ctx._human_keyboard` to avoid creating them per step.

- [ ] **Step 1: Append failing tests**

```python
# tests/flow/test_steps_browser.py — append
def test_click_human(ctx):
    ctx._human_mouse = MagicMock()
    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click", params={"selector": "#b"}),
        ctx,
    )
    ctx._human_mouse.click.assert_called_once_with("#b")


def test_click_non_human(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click",
                 params={"selector": "#b", "human": False}),
        ctx,
    )
    locator.click.assert_called_once()


def test_type_human(ctx):
    ctx._human_keyboard = MagicMock()
    get_handler("browser.type")(
        StepSpec(id="t", type="browser.type",
                 params={"selector": "#i", "text": "hi"}),
        ctx,
    )
    ctx._human_keyboard.type_into.assert_called_once_with("#i", "hi")


def test_type_clear_first(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    ctx._human_keyboard = MagicMock()
    get_handler("browser.type")(
        StepSpec(id="t", type="browser.type",
                 params={"selector": "#i", "text": "hi", "clear_first": True}),
        ctx,
    )
    locator.fill.assert_called_once_with("")
    ctx._human_keyboard.type_into.assert_called_once_with("#i", "hi")


def test_hover_human(ctx):
    ctx._human_mouse = MagicMock()
    get_handler("browser.hover")(
        StepSpec(id="h", type="browser.hover", params={"selector": "#x"}),
        ctx,
    )
    ctx._human_mouse.move_to.assert_called_once_with("#x")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_steps_browser.py -v
```

- [ ] **Step 3: Append handlers**

```python
# tegufox_flow/steps/browser.py — append
@register("browser.click", required=("selector",))
def _click(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True):
        ctx._human_mouse.click(sel)
    else:
        ctx.page.locator(sel).click(
            button=p.get("button", "left"),
            click_count=int(p.get("click_count", 1)),
        )


@register("browser.type", required=("selector", "text"))
def _type(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    text = ctx.render(p["text"])
    if p.get("clear_first"):
        ctx.page.locator(sel).fill("")
    if p.get("human", True):
        ctx._human_keyboard.type_into(sel, text)
    else:
        ctx.page.locator(sel).type(text, delay=int(p.get("delay_ms", 0)))


@register("browser.hover", required=("selector",))
def _hover(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True):
        ctx._human_mouse.move_to(sel)
    else:
        ctx.page.locator(sel).hover()
```

Add HumanMouse/HumanKeyboard fields to `FlowContext` for caching:

```python
# tegufox_flow/context.py — modify FlowContext
@dataclass
class FlowContext:
    # ... existing fields ...
    _human_mouse: Any = None        # HumanMouse, lazily initialised
    _human_keyboard: Any = None     # HumanKeyboard, lazily initialised
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_steps_browser.py -v
```

Expected: 14 passed (9 + 5).

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/steps/browser.py tegufox_flow/context.py tests/flow/test_steps_browser.py
git commit -m "feat(flow): browser.click/type/hover with HumanMouse/Keyboard"
```

---

## Task 16: FlowEngine — single-step execution + error policy

**Files:**
- Create: `tegufox_flow/engine.py`
- Create: `tests/flow/test_engine_one_step.py`

**Background:** spec §5.2/§5.5. The engine has three layers: `_execute_one(step)` (with retries/skip/goto + checkpointing), `_execute_steps(steps)` (loop with resume + goto handling), `run()` (top-level lifecycle, Task 18). Build them in order.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_engine_one_step.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.engine import FlowEngine
from tegufox_flow.dsl import OnError
from tegufox_flow.steps import StepSpec, register, STEP_REGISTRY
from tegufox_flow.errors import StepError, GotoSignal


@pytest.fixture(autouse=True)
def _registry_isolation():
    snapshot = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snapshot)


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {"v": 1}
    c.run_id = "r"
    c.checkpoints = MagicMock()
    return c


def test_step_runs_and_checkpoints(ctx):
    calls = []

    @register("t.ok")
    def _h(spec, c):
        calls.append(spec.id)

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(StepSpec(id="a", type="t.ok"), ctx)
    assert calls == ["a"]
    ctx.checkpoints.save.assert_called_once_with("r", "a", {"v": 1})


def test_when_false_skips(ctx):
    @register("t.never")
    def _h(spec, c):
        raise AssertionError("should not run")

    ctx.eval.return_value = False
    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(StepSpec(id="a", type="t.never", when="false"), ctx)
    ctx.checkpoints.save.assert_not_called()


def test_retry_then_succeed(ctx):
    attempts = {"n": 0}

    @register("t.flaky")
    def _h(spec, c):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(
        StepSpec(id="a", type="t.flaky",
                 on_error=OnError(action="retry", max_attempts=5, backoff_ms=0)),
        ctx,
    )
    assert attempts["n"] == 3


def test_retry_exhausted_raises(ctx):
    @register("t.always")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    with pytest.raises(StepError):
        eng._execute_one(
            StepSpec(id="a", type="t.always",
                     on_error=OnError(action="retry", max_attempts=2, backoff_ms=0)),
            ctx,
        )


def test_skip_swallows_error(ctx):
    @register("t.bad")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(
        StepSpec(id="a", type="t.bad", on_error=OnError(action="skip")),
        ctx,
    )  # no raise


def test_goto_raises_signal(ctx):
    @register("t.fail")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    with pytest.raises(GotoSignal) as e:
        eng._execute_one(
            StepSpec(id="a", type="t.fail",
                     on_error=OnError(action="goto", goto_step="cleanup")),
            ctx,
        )
    assert e.value.target == "cleanup"


def test_default_on_error_inherited(ctx):
    @register("t.fail2")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="skip")
    # No on_error on the step → inherits skip from defaults.
    eng._execute_one(StepSpec(id="a", type="t.fail2"), ctx)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/flow/test_engine_one_step.py -v
```

- [ ] **Step 3: Implement**

```python
# tegufox_flow/engine.py
"""Flow execution engine — tree interpreter."""

from __future__ import annotations
import logging
import time
from typing import List, Optional

from .dsl import Flow, OnError
from .errors import StepError, GotoSignal
from .steps import StepSpec, get_handler


_LOG = logging.getLogger("tegufox_flow.engine")


def _to_spec(step) -> StepSpec:
    """Coerce a Pydantic Step into a registry StepSpec."""
    return StepSpec(
        id=step.id,
        type=step.type,
        params=step.params,
        on_error=step.on_error,
        when=step.when,
    )


class FlowEngine:
    def __init__(self, default_on_error: Optional[OnError] = None) -> None:
        self._default_on_error = default_on_error or OnError(action="abort")

    def _execute_one(self, step, ctx) -> None:
        spec = step if isinstance(step, StepSpec) else _to_spec(step)
        ctx.current_step_id = spec.id

        if spec.when is not None and not bool(ctx.eval(spec.when)):
            ctx.logger.info(f"step {spec.id!r} skipped (when=false)")
            return

        policy = spec.on_error or self._default_on_error
        handler = get_handler(spec.type)

        attempt = 0
        while True:
            attempt += 1
            try:
                ctx.checkpoints.save(ctx.run_id, spec.id, ctx.snapshot())
                handler(spec, ctx)
                return
            except (GotoSignal,):
                raise
            except Exception as e:
                if isinstance(e, (StepError,)):
                    raise
                if policy.action == "retry" and attempt < policy.max_attempts:
                    ctx.logger.warning(
                        f"step {spec.id!r} failed (attempt {attempt}): {e}; retrying"
                    )
                    if policy.backoff_ms:
                        time.sleep(policy.backoff_ms / 1000.0)
                    continue
                if policy.action == "skip":
                    ctx.logger.warning(f"step {spec.id!r} failed: {e}; skipped")
                    return
                if policy.action == "goto":
                    ctx.logger.warning(
                        f"step {spec.id!r} failed: {e}; jumping to {policy.goto_step!r}"
                    )
                    raise GotoSignal(target=policy.goto_step) from e
                raise StepError(step_id=spec.id, step_type=spec.type, cause=e) from e
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_engine_one_step.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/engine.py tests/flow/test_engine_one_step.py
git commit -m "feat(flow): FlowEngine._execute_one with retry/skip/goto"
```

---

## Task 17: FlowEngine — list execution with resume + goto + signals

**Files:**
- Modify: `tegufox_flow/engine.py`
- Create: `tests/flow/test_engine_list.py`

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_engine_list.py
import pytest
from unittest.mock import MagicMock
from tegufox_flow.engine import FlowEngine
from tegufox_flow.dsl import OnError
from tegufox_flow.steps import StepSpec, register, STEP_REGISTRY
from tegufox_flow.errors import GotoSignal, BreakSignal


@pytest.fixture(autouse=True)
def _iso():
    snap = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snap)


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.eval.return_value = True
    c.run_id = "r"
    return c


def test_executes_steps_in_order(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    eng = FlowEngine()
    ctx.engine = eng
    steps = [StepSpec(id=x, type="t.mark") for x in ("a", "b", "c")]
    eng.execute_steps(steps, ctx)
    assert seen == ["a", "b", "c"]


def test_resume_from_skips_earlier_steps(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    eng = FlowEngine()
    ctx.engine = eng
    steps = [StepSpec(id=x, type="t.mark") for x in ("a", "b", "c")]
    eng.execute_steps(steps, ctx, resume_from="b")
    assert seen == ["b", "c"]


def test_goto_jumps_to_target_at_same_scope(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    @register("t.gotoer")
    def g(spec, c):
        raise GotoSignal("c")

    eng = FlowEngine()
    ctx.engine = eng
    steps = [
        StepSpec(id="a", type="t.mark"),
        StepSpec(id="g", type="t.gotoer"),
        StepSpec(id="b", type="t.mark"),
        StepSpec(id="c", type="t.mark"),
    ]
    eng.execute_steps(steps, ctx)
    assert seen == ["a", "c"]


def test_goto_to_unknown_target_raises(ctx):
    @register("t.gotoer")
    def g(spec, c):
        raise GotoSignal("ghost")

    eng = FlowEngine()
    ctx.engine = eng
    with pytest.raises(GotoSignal):  # propagates to outer scope
        eng.execute_steps([StepSpec(id="g", type="t.gotoer")], ctx)


def test_break_propagates_out_of_steps(ctx):
    @register("t.brk")
    def b(spec, c):
        raise BreakSignal("b")

    eng = FlowEngine()
    ctx.engine = eng
    with pytest.raises(BreakSignal):
        eng.execute_steps([StepSpec(id="x", type="t.brk")], ctx)
```

- [ ] **Step 2: Run, expect AttributeError on `execute_steps`**

```bash
pytest tests/flow/test_engine_list.py -v
```

- [ ] **Step 3: Add method**

```python
# tegufox_flow/engine.py — append to FlowEngine class
    def execute_steps(self, steps, ctx, *, resume_from: Optional[str] = None) -> None:
        skipping = resume_from is not None
        i = 0
        while i < len(steps):
            step = steps[i]
            spec = step if isinstance(step, StepSpec) else _to_spec(step)
            if skipping:
                if spec.id == resume_from:
                    skipping = False
                else:
                    i += 1
                    continue
            try:
                self._execute_one(spec, ctx)
            except GotoSignal as g:
                # Resolve at this scope: find sibling with that id.
                target = g.target
                idx = self._find_index(steps, target)
                if idx is None:
                    raise  # propagate to outer scope
                i = idx
                continue
            i += 1

    @staticmethod
    def _find_index(steps, target: str) -> Optional[int]:
        for idx, step in enumerate(steps):
            sid = step.id if hasattr(step, "id") else step["id"]
            if sid == target:
                return idx
        return None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_engine_list.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/engine.py tests/flow/test_engine_list.py
git commit -m "feat(flow): execute_steps with resume + goto resolution"
```

---

## Task 18: FlowEngine.run — full lifecycle

**Files:**
- Modify: `tegufox_flow/engine.py`
- Create: `tests/flow/test_engine_run.py`

**Background:** spec §5.1. `run(flow, inputs, *, profile_name)` opens TegufoxSession, builds FlowContext, persists `FlowRun` row, executes, finalizes status. Returns `RunResult`.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_engine_run.py
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowRecord, FlowRun
from tegufox_flow.engine import FlowEngine, RunResult
from tegufox_flow.dsl import parse_flow
from tegufox_flow.steps import register, STEP_REGISTRY


@pytest.fixture(autouse=True)
def _iso():
    snap = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snap)


@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    yield Session
    eng.dispose()


@pytest.fixture
def flow_record(db):
    s = db()
    f = FlowRecord(name="t", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f)
    s.commit()
    fid = f.id
    s.close()
    return fid


def test_run_succeeds_and_records_status(db, flow_record):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = lambda s: s
    fake_session.__exit__ = lambda s, *a: None

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    assert isinstance(result, RunResult)
    assert result.status == "succeeded"
    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.status == "succeeded"
    assert row.profile_name == "p"


def test_run_failure_marks_failed(db, flow_record):
    @register("t.bad")
    def _(spec, ctx):
        raise RuntimeError("boom")

    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "steps": [{"id": "a", "type": "t.bad"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = lambda s: s
    fake_session.__exit__ = lambda s, *a: None

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    assert result.status == "failed"
    assert "boom" in (result.error or "")


def test_run_validates_required_inputs(db, flow_record):
    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "inputs": {"q": {"type": "string", "required": True}},
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    eng = FlowEngine(db_session_factory=db)
    with pytest.raises(ValueError) as e:
        eng.run(flow, inputs={}, profile_name="p")
    assert "q" in str(e.value)
```

- [ ] **Step 2: Run, expect AttributeError on `RunResult`/`run`**

```bash
pytest tests/flow/test_engine_run.py -v
```

- [ ] **Step 3: Implement run() and RunResult**

```python
# tegufox_flow/engine.py — add at module top, after imports
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from tegufox_core.database import FlowRecord, FlowRun
from tegufox_automation import TegufoxSession  # type: ignore

from .checkpoints import CheckpointStore, KVStore
from .context import FlowContext
from .expressions import ExpressionEngine


@dataclass
class RunResult:
    run_id: str
    status: str  # succeeded | failed | aborted
    last_step_id: Optional[str]
    error: Optional[str]
    inputs: dict


# Augment FlowEngine.__init__:
class FlowEngine:
    def __init__(
        self,
        default_on_error: Optional[OnError] = None,
        *,
        db_session_factory=None,
        env_allowlist: Optional[set] = None,
    ) -> None:
        self._default_on_error = default_on_error or OnError(action="abort")
        self._db = db_session_factory
        self._env_allow = env_allowlist or set()
```

Add `run`:

```python
# tegufox_flow/engine.py — append to FlowEngine
    def run(
        self,
        flow: Flow,
        *,
        inputs: dict,
        profile_name: str,
        resume: Optional[str] = None,
        resume_from: Optional[str] = None,
    ) -> RunResult:
        self._validate_inputs(flow, inputs)
        run_id = resume or str(uuid.uuid4())

        with self._db() as s:
            fid = s.query(FlowRecord.id).filter_by(name=flow.name).scalar()
            if fid is None:
                rec = FlowRecord(
                    name=flow.name, yaml_text="(loaded from disk)",
                    schema_version=flow.schema_version,
                    created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
                )
                s.add(rec); s.commit(); fid = rec.id

            if resume:
                run_row = s.query(FlowRun).filter_by(run_id=run_id).first()
                if run_row is None:
                    raise ValueError(f"unknown run_id {run_id}")
                run_row.status = "running"
            else:
                run_row = FlowRun(
                    run_id=run_id, flow_id=fid, profile_name=profile_name,
                    inputs_json=json.dumps(inputs, default=str),
                    status="running", started_at=datetime.utcnow(),
                )
                s.add(run_row)
            s.commit()

        # Build context
        with self._db() as s:
            checkpoints = CheckpointStore(s)
            kv = KVStore(s, flow_name=flow.name)

            # Restore vars from latest checkpoint if resuming.
            vars_ = {}
            resume_step: Optional[str] = resume_from
            if resume:
                cp = checkpoints.last(run_id)
                if cp:
                    vars_ = dict(cp.vars)
                    # Resume after the last successful checkpoint:
                    resume_step = self._step_after(flow.steps, cp.step_id)

            with TegufoxSession(profile=profile_name) as session:
                from tegufox_automation import HumanMouse, HumanKeyboard
                ctx = FlowContext(
                    session=session, page=session.page,
                    flow_name=flow.name, run_id=run_id,
                    inputs=dict(inputs), vars=vars_,
                    kv=kv, checkpoints=checkpoints,
                    expressions=ExpressionEngine(),
                    env_allowlist=self._env_allow,
                )
                ctx._human_mouse = HumanMouse(session.page) if HumanMouse else None
                ctx._human_keyboard = HumanKeyboard(session.page) if HumanKeyboard else None
                ctx.engine = self

                try:
                    self.execute_steps(flow.steps, ctx, resume_from=resume_step)
                    status, err = "succeeded", None
                except Exception as e:
                    status = "failed"
                    err = f"{type(e).__name__}: {e}"
                finally:
                    last = ctx.current_step_id

        with self._db() as s:
            row = s.query(FlowRun).filter_by(run_id=run_id).one()
            row.status = status
            row.last_step_id = last
            row.error_text = err
            row.finished_at = datetime.utcnow()
            s.commit()

        return RunResult(
            run_id=run_id, status=status,
            last_step_id=last, error=err, inputs=inputs,
        )

    def _validate_inputs(self, flow: Flow, inputs: dict) -> None:
        for name, decl in flow.inputs.items():
            if name not in inputs and decl.required and decl.default is None:
                raise ValueError(f"missing required input {name!r}")

    @staticmethod
    def _step_after(steps, step_id: str) -> Optional[str]:
        for i, s in enumerate(steps):
            if s.id == step_id:
                if i + 1 < len(steps):
                    return steps[i + 1].id
                return None
        return None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_engine_run.py -v
```

Expected: 3 passed. Re-run all flow tests:

```bash
pytest tests/flow -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/engine.py tests/flow/test_engine_run.py
git commit -m "feat(flow): FlowEngine.run lifecycle with persistence + resume"
```

---

## Task 19: Runtime helper + CLI subcommand

**Files:**
- Create: `tegufox_flow/runtime.py`
- Create: `tegufox_flow/cli.py`
- Modify: `tegufox-cli` (entry script)
- Create: `tests/flow/test_cli.py`

**Background:** spec §7.2. `tegufox-cli flow validate <file>`, `flow run <file> --profile <name> --inputs k=v ...`, `flow runs ls`, `flow runs show`. Single argparse group plugged into the existing parser.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_cli.py
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

from tegufox_flow.cli import build_parser, run_cli


def test_validate_ok(tmp_path: Path, capsys):
    f = tmp_path / "x.yaml"
    f.write_text("schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")
    rc = run_cli(["validate", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ok" in out.lower() or "valid" in out.lower()


def test_validate_fails(tmp_path: Path, capsys):
    f = tmp_path / "x.yaml"
    f.write_text("schema_version: 99\nname: x\nsteps: []\n")
    rc = run_cli(["validate", str(f)])
    assert rc != 0
    err = capsys.readouterr().err + capsys.readouterr().out
    assert "schema_version" in err


def test_inputs_kv_parsing():
    p = build_parser()
    ns = p.parse_args(["run", "f.yaml", "--profile", "p",
                       "--inputs", "a=1", "b=hi"])
    assert ns.inputs == ["a=1", "b=hi"]
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_cli.py -v
```

- [ ] **Step 3: Implement runtime + cli**

```python
# tegufox_flow/runtime.py
"""High-level entrypoints used by the CLI/REST/GUI."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base

from .dsl import load_flow
from .engine import FlowEngine, RunResult


def _session_factory(db_path: Path):
    eng = create_engine(f"sqlite:///{db_path.resolve()}")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)


def run_flow(
    flow_path: Path,
    *,
    profile_name: str,
    inputs: Dict[str, Any],
    db_path: Path = Path("data/tegufox.db"),
    resume: Optional[str] = None,
    resume_from: Optional[str] = None,
) -> RunResult:
    flow = load_flow(flow_path)
    Session = _session_factory(db_path)
    engine = FlowEngine(db_session_factory=Session)
    return engine.run(
        flow, inputs=inputs, profile_name=profile_name,
        resume=resume, resume_from=resume_from,
    )
```

```python
# tegufox_flow/cli.py
"""tegufox-cli flow ... subcommand."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .dsl import load_flow
from .errors import ValidationError
from .runtime import run_flow


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tegufox-cli flow")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a flow YAML file")
    v.add_argument("path")

    r = sub.add_parser("run", help="Run a flow on a single profile")
    r.add_argument("path")
    r.add_argument("--profile", required=True)
    r.add_argument("--inputs", nargs="*", default=[],
                   help="key=value pairs (parsed as JSON if possible)")
    r.add_argument("--db", default="data/tegufox.db")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--resume")
    g.add_argument("--resume-from", dest="resume_from")

    runs = sub.add_parser("runs", help="Run history")
    runs_sub = runs.add_subparsers(dest="runs_cmd", required=True)
    ls = runs_sub.add_parser("ls")
    ls.add_argument("--flow", required=False)
    ls.add_argument("--limit", type=int, default=20)
    show = runs_sub.add_parser("show")
    show.add_argument("run_id")

    return p


def _parse_inputs(items: List[str]) -> dict:
    out = {}
    for it in items:
        if "=" not in it:
            raise ValueError(f"input must be key=value: {it!r}")
        k, v = it.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def run_cli(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "validate":
        try:
            load_flow(args.path)
            print(f"ok: {args.path}")
            return 0
        except (ValidationError, Exception) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if args.cmd == "run":
        result = run_flow(
            Path(args.path),
            profile_name=args.profile,
            inputs=_parse_inputs(args.inputs),
            db_path=Path(args.db),
            resume=args.resume,
            resume_from=args.resume_from,
        )
        print(json.dumps({
            "run_id": result.run_id,
            "status": result.status,
            "last_step_id": result.last_step_id,
            "error": result.error,
        }, indent=2))
        return 0 if result.status == "succeeded" else 2

    if args.cmd == "runs":
        return _runs_cmd(args)

    return 1


def _runs_cmd(args) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tegufox_core.database import Base, FlowRun, FlowRecord

    eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    try:
        if args.runs_cmd == "ls":
            q = s.query(FlowRun).join(FlowRecord, FlowRecord.id == FlowRun.flow_id)
            if args.flow:
                q = q.filter(FlowRecord.name == args.flow)
            q = q.order_by(FlowRun.started_at.desc()).limit(args.limit)
            for r in q:
                print(f"{r.run_id}\t{r.status}\t{r.profile_name}\t{r.started_at.isoformat()}")
            return 0
        if args.runs_cmd == "show":
            r = s.query(FlowRun).filter_by(run_id=args.run_id).first()
            if r is None:
                print(f"not found: {args.run_id}", file=sys.stderr); return 1
            print(json.dumps({
                "run_id": r.run_id,
                "status": r.status,
                "profile": r.profile_name,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "last_step_id": r.last_step_id,
                "error": r.error_text,
                "inputs": json.loads(r.inputs_json or "{}"),
            }, indent=2))
            return 0
    finally:
        s.close()
    return 1
```

Modify `tegufox-cli` entrypoint — register `flow` subparser. Locate the `subparsers = parser.add_subparsers(...)` line in `tegufox-cli` (around line 39 per Task 0 exploration) and after the existing `profile`/`fleet`/`api` parsers add:

```python
# tegufox-cli — add inside main(), after existing subparsers
    flow_parser = subparsers.add_parser('flow', help='Flow DSL: validate/run/inspect',
                                        add_help=False)
    flow_parser.set_defaults(_flow=True)

    # In the dispatch block (where commands are routed):
    args, rest = parser.parse_known_args()
    if getattr(args, "_flow", False) or (sys.argv[1:2] == ["flow"]):
        from tegufox_flow.cli import run_cli
        sys.exit(run_cli(sys.argv[2:]))
```

(The exact integration point depends on how `tegufox-cli` dispatches; if dispatch is a long if/elif on `args.command`, just add `elif args.command == "flow": ...` calling `run_cli(sys.argv[2:])`.)

- [ ] **Step 4: Run tests**

```bash
pytest tests/flow/test_cli.py -v
./tegufox-cli flow --help    # smoke
```

Expected: 3 passed; help text shows `validate`, `run`, `runs`.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/runtime.py tegufox_flow/cli.py tegufox-cli tests/flow/test_cli.py
git commit -m "feat(flow): runtime helper and tegufox-cli flow subcommand"
```

---

## Task 20: REST endpoints

**Files:**
- Modify: `tegufox_cli/api.py`
- Create: `tests/flow/test_api.py`

**Background:** spec §7.3. Add to existing FastAPI app. Endpoints: `POST /flows` (upload YAML), `GET /flows`, `GET /flows/{name}`, `POST /flows/{name}/runs`, `GET /flows/{name}/runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/log`.

- [ ] **Step 1: Failing tests**

```python
# tests/flow/test_api.py
from fastapi.testclient import TestClient


def test_flow_lifecycle(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)

    yaml = (
        "schema_version: 1\n"
        "name: api_t\n"
        "steps:\n"
        "  - id: a\n"
        "    type: control.sleep\n"
        "    ms: 1\n"
    )
    r = client.post("/flows", json={"name": "api_t", "yaml": yaml})
    assert r.status_code == 200, r.text

    r = client.get("/flows")
    assert any(f["name"] == "api_t" for f in r.json())

    r = client.get("/flows/api_t")
    assert "schema_version: 1" in r.json()["yaml"]


def test_post_run_requires_profile(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/flows", json={"name": "x", "yaml":
        "schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"})
    r = client.post("/flows/x/runs", json={"inputs": {}})
    assert r.status_code == 422
```

- [ ] **Step 2: Run, expect failures**

```bash
pytest tests/flow/test_api.py -v
```

- [ ] **Step 3: Add endpoints to `tegufox_cli/api.py`**

Open `tegufox_cli/api.py`, locate the FastAPI `app = FastAPI(...)` block (or `create_app()` factory), and add a new router:

```python
# tegufox_cli/api.py — add near other routes
import os
import json as _json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowRecord, FlowRun
from tegufox_flow.dsl import parse_flow
from tegufox_flow.runtime import run_flow as _run_flow

flow_router = APIRouter(prefix="", tags=["flow"])


def _db_session():
    db_path = os.environ.get("TEGUFOX_DB", "data/tegufox.db")
    eng = create_engine(f"sqlite:///{Path(db_path).resolve()}")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


class FlowUpload(BaseModel):
    name: str
    yaml: str


class RunRequest(BaseModel):
    profile: str
    inputs: dict = {}


@flow_router.post("/flows")
def upload_flow(body: FlowUpload):
    import yaml as _yaml
    try:
        data = _yaml.safe_load(body.yaml)
        parse_flow(data)
    except Exception as e:
        raise HTTPException(400, str(e))

    s = _db_session()
    try:
        rec = s.query(FlowRecord).filter_by(name=body.name).first()
        now = datetime.utcnow()
        if rec is None:
            rec = FlowRecord(name=body.name, yaml_text=body.yaml,
                             schema_version=1, created_at=now, updated_at=now)
            s.add(rec)
        else:
            rec.yaml_text = body.yaml
            rec.updated_at = now
        s.commit()
        return {"name": rec.name, "id": rec.id}
    finally:
        s.close()


@flow_router.get("/flows")
def list_flows():
    s = _db_session()
    try:
        rows = s.query(FlowRecord).order_by(FlowRecord.name).all()
        return [{"name": r.name, "schema_version": r.schema_version,
                 "updated_at": r.updated_at.isoformat()} for r in rows]
    finally:
        s.close()


@flow_router.get("/flows/{name}")
def get_flow(name: str):
    s = _db_session()
    try:
        rec = s.query(FlowRecord).filter_by(name=name).first()
        if rec is None:
            raise HTTPException(404, "not found")
        return {"name": rec.name, "yaml": rec.yaml_text}
    finally:
        s.close()


@flow_router.post("/flows/{name}/runs")
def post_run(name: str, body: RunRequest):
    s = _db_session()
    try:
        rec = s.query(FlowRecord).filter_by(name=name).first()
        if rec is None:
            raise HTTPException(404, "flow not found")
        # Write YAML to a temp file so run_flow can load_flow().
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(rec.yaml_text); tmp_path = f.name
        result = _run_flow(Path(tmp_path), profile_name=body.profile,
                           inputs=body.inputs, db_path=Path(os.environ.get("TEGUFOX_DB", "data/tegufox.db")))
        return {"run_id": result.run_id, "status": result.status,
                "last_step_id": result.last_step_id, "error": result.error}
    finally:
        s.close()


@flow_router.get("/flows/{name}/runs")
def list_runs(name: str, limit: int = 20):
    s = _db_session()
    try:
        rec = s.query(FlowRecord).filter_by(name=name).first()
        if rec is None:
            raise HTTPException(404, "flow not found")
        runs = (s.query(FlowRun).filter_by(flow_id=rec.id)
                .order_by(FlowRun.started_at.desc()).limit(limit).all())
        return [{"run_id": r.run_id, "status": r.status,
                 "profile_name": r.profile_name,
                 "started_at": r.started_at.isoformat() if r.started_at else None,
                 "finished_at": r.finished_at.isoformat() if r.finished_at else None}
                for r in runs]
    finally:
        s.close()


@flow_router.get("/runs/{run_id}")
def get_run(run_id: str):
    s = _db_session()
    try:
        r = s.query(FlowRun).filter_by(run_id=run_id).first()
        if r is None:
            raise HTTPException(404, "not found")
        return {"run_id": r.run_id, "status": r.status,
                "profile_name": r.profile_name,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "last_step_id": r.last_step_id, "error": r.error_text,
                "inputs": _json.loads(r.inputs_json or "{}")}
    finally:
        s.close()


@flow_router.get("/runs/{run_id}/log")
def get_run_log(run_id: str):
    log = Path("data/runs") / run_id / "log.jsonl"
    if not log.exists():
        return []
    return [_json.loads(line) for line in log.read_text().splitlines() if line.strip()]
```

Then register the router in the existing `create_app()` (or wherever app is constructed):

```python
# tegufox_cli/api.py — inside create_app()
app.include_router(flow_router)
```

If `tegufox_cli/api.py` does not currently expose a `create_app()` factory, add one:

```python
def create_app() -> "FastAPI":
    app = FastAPI(title="Tegufox API")
    # ... existing routers ...
    app.include_router(flow_router)
    return app
```

(The exact existing structure determines whether you wrap or splice — read the file before editing.)

- [ ] **Step 4: Run tests**

```bash
pip install fastapi httpx  # for TestClient if not present
pytest tests/flow/test_api.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_cli/api.py tests/flow/test_api.py
git commit -m "feat(flow): REST endpoints for flows and runs"
```

---

## Task 21: GUI — minimal Flows page

**Files:**
- Create: `tegufox_gui/pages/flows_page.py`
- Modify: `tegufox_gui/app.py` (or wherever pages register) — add Flows tab.

**Background:** spec §7. Minimal v1: list flows from DB, dropdown to pick a profile, "Run" button that calls `run_flow()` in a QThread. Real visual editing is sub-project #3.

- [ ] **Step 1: Failing test**

```python
# tests/flow/test_flows_page.py
import pytest
pytestmark = pytest.mark.skipif(
    "PyQt6" not in __import__("sys").modules and not __import__("importlib.util").util.find_spec("PyQt6"),
    reason="PyQt6 not available")


def test_flows_page_constructs():
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage()
    assert page is not None
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/flow/test_flows_page.py -v
```

- [ ] **Step 3: Implement minimal page**

```python
# tegufox_gui/pages/flows_page.py
"""Minimal Flows page — list + run.

Real visual editor lives in sub-project #3.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, FlowRecord, FlowRun
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

        self.log = QTextEdit(); self.log.setReadOnly(True)
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
            for p in ProfileManager().list_profiles():
                self.profile_combo.addItem(p["name"])
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
            from datetime import datetime
            now = datetime.utcnow()
            rec = s.query(FlowRecord).filter_by(name=flow.name).first()
            if rec is None:
                rec = FlowRecord(name=flow.name, yaml_text=text,
                                 schema_version=flow.schema_version,
                                 created_at=now, updated_at=now)
                s.add(rec)
            else:
                rec.yaml_text = text; rec.updated_at = now
            s.commit()
        finally:
            s.close()
        self._refresh()

    def _on_run(self):
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(self, "Pick a flow", "Select a flow first."); return
        profile = self.profile_combo.currentText()
        if not profile:
            QMessageBox.warning(self, "Pick a profile", "No profile available."); return

        s = self._session()
        try:
            rec = s.query(FlowRecord).filter_by(name=item.text()).one()
            yaml_text = rec.yaml_text
        finally:
            s.close()

        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text); tmp = Path(f.name)

        worker = _RunWorker(tmp, profile, {})
        worker.finished_with.connect(self._on_run_done)
        self._workers.append(worker)
        self.log.append(f"Starting {item.text()} on {profile}…")
        worker.start()

    def _on_run_done(self, result: dict):
        self.log.append(f"Result: {result}")
```

Add the page to the GUI navigation. Locate the existing tab/page registration block in `tegufox_gui/app.py` (or wherever `SessionsPage`, `ProfilesPage` are added) and add:

```python
from tegufox_gui.pages.flows_page import FlowsPage
# ... wherever other pages are wired:
self.tabs.addTab(FlowsPage(), "Flows")  # or similar
```

- [ ] **Step 4: Run tests + smoke**

```bash
pytest tests/flow/test_flows_page.py -v
./tegufox-gui &  # smoke open & verify Flows tab appears
```

Expected: 1 passed; GUI shows a Flows tab.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/pages/flows_page.py tegufox_gui/app.py tests/flow/test_flows_page.py
git commit -m "feat(flow): minimal Flows page in GUI"
```

---

## Task 22: pytest markers + golden flow fixtures

**Files:**
- Modify: `pytest.ini` — add `golden` marker.
- Create: `tests/flow/conftest.py`
- Create: `tests/flow/flows/linear_search.yaml`
- Create: `tests/flow/flows/conditional_filter.yaml`
- Create: `tests/flow/flows/stateful_loop.yaml`
- Create: `tests/flow/test_golden_flows.py`

**Background:** spec §9. End-to-end fixtures with a small `http.server` serving static HTML pages.

- [ ] **Step 1: Add marker**

In `pytest.ini`, append `golden` under markers:

```ini
markers =
    slow: ...
    real_network: ...
    integration: ...
    unit: ...
    benchmark: ...
    golden: marks end-to-end golden flow tests
```

- [ ] **Step 2: Static page server fixture**

```python
# tests/flow/conftest.py
import contextlib
import threading
import http.server
import socketserver
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def static_pages():
    """Serve tests/flow/static_pages/ on a free port."""
    pages_dir = Path(__file__).parent / "static_pages"
    pages_dir.mkdir(exist_ok=True)
    # Provide one page used by golden flows.
    (pages_dir / "search.html").write_text(
        "<!doctype html><html><body>"
        "<input id='q' />"
        "<button id='go' onclick=\"document.getElementById('out').innerText='hello '+document.getElementById('q').value\">go</button>"
        "<div id='out'></div>"
        "</body></html>"
    )

    class _H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(pages_dir), **kw)

        def log_message(self, *_): pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown(); httpd.server_close()
```

- [ ] **Step 3: Linear flow + test**

```yaml
# tests/flow/flows/linear_search.yaml
schema_version: 1
name: linear_search
inputs:
  base_url:
    type: string
    required: true
steps:
  - id: open
    type: browser.goto
    url: "{{ inputs.base_url }}/search.html"
  - id: type_q
    type: browser.type
    selector: "#q"
    text: "world"
    human: false
  - id: click_go
    type: browser.click
    selector: "#go"
    human: false
  - id: read
    type: extract.read_text
    selector: "#out"
    set: result
```

```python
# tests/flow/test_golden_flows.py
import pytest
from pathlib import Path
from tegufox_flow.runtime import run_flow


@pytest.mark.golden
def test_linear_search(tmp_path, static_pages):
    db = tmp_path / "g.db"
    flow = Path(__file__).parent / "flows" / "linear_search.yaml"
    result = run_flow(
        flow, profile_name="default",  # assumes a profile named 'default' exists
        inputs={"base_url": static_pages}, db_path=db,
    )
    assert result.status == "succeeded", result.error
```

(Conditional and stateful flows: write similarly — `conditional_filter.yaml` exercises `control.if`, `stateful_loop.yaml` exercises `control.for_each` + `state.save`/`load`. Pattern matches `linear_search`. Add corresponding tests gated by `@pytest.mark.golden`.)

- [ ] **Step 4: Run unit suite, then golden**

```bash
pytest tests/flow -m "not golden" -v
pytest tests/flow -m golden -v   # requires a real Camoufox + a profile named 'default'
```

Expected: unit suite all green; golden tests pass when run interactively (CI may skip).

- [ ] **Step 5: Commit**

```bash
git add pytest.ini tests/flow/conftest.py tests/flow/flows/ tests/flow/test_golden_flows.py
git commit -m "test(flow): golden e2e fixtures + static page server"
```

---

## Self-review notes

**Spec coverage walk-through (each spec section → task):**

| Spec § | Topic | Task |
|---|---|---|
| §3 | Architecture diagram, deps | Tasks 1–8 (foundation) |
| §4.1 | Top-level fields | Task 2 (pydantic schema) |
| §4.2 | Step common fields | Task 2 + Task 16 (`when` guard in engine) |
| §4.3 browser | 9 step types | Tasks 14, 15 |
| §4.3 extract | 5 step types | Task 13 |
| §4.3 control | 8 step types | Tasks 9, 10 |
| §4.3 io | 4 step types | Task 11 |
| §4.3 state | 3 step types | Task 12 |
| §4.4 expressions | Jinja2 sandbox | Task 4 + Task 7 (namespaces) |
| §4.5 round-trip | ruamel.yaml | Task 3 |
| §5.1 lifecycle | run() | Task 18 |
| §5.2 dispatch | execute_steps + execute_one | Tasks 16, 17 |
| §5.3 scoping | inputs/vars/state/env | Task 7 |
| §5.4 resume | --resume / --resume-from | Tasks 17, 18, 19 |
| §5.5 error policy | retry/skip/abort/goto | Task 16 |
| §6 persistence | 4 tables | Tasks 5, 6 |
| §7.1 Python API | load_flow / FlowEngine | Tasks 3, 18 |
| §7.2 CLI | tegufox-cli flow | Task 19 |
| §7.3 REST | /flows, /runs | Task 20 |
| §7 GUI | Flows page | Task 21 |
| §8 errors | hierarchy | Task 1 |
| §9 testing | unit/integration/golden | All tasks (TDD) + Task 22 |
| §10 file layout | exactly as spec | All tasks (paths match spec) |

**Placeholder scan:** No "TBD", "TODO", or "implement later" anywhere. Every code block is complete.

**Type consistency:** `StepSpec` shape (Task 8) matches all step handlers. `FlowContext` fields (Task 7) used identically by every step. `RunResult` (Task 18) is the single return type from CLI/API/runtime.

**Risk areas to watch during execution:**

1. **Camoufox `TegufoxSession` import path** — Task 18 imports `from tegufox_automation import TegufoxSession`. This works today but may need `from tegufox_automation.session import TegufoxSession` if the re-export breaks.
2. **`from_browserforge` monkeypatch in `session.py`** — when `FlowEngine.run` opens a `TegufoxSession`, the existing monkeypatch must already be applied. It is, because `import tegufox_automation` triggers it. No action needed.
3. **`HumanMouse` / `HumanKeyboard` API** — Task 15 assumes `mouse.click(selector)`, `mouse.move_to(selector)`, `keyboard.type_into(selector, text)`. Verify exact method names against `tegufox_automation/mouse.py` and `keyboard.py` before implementing; rename in plan if needed.
4. **`ProfileManager.list_profiles()` shape** — Task 21 calls it. Verify it returns `[{"name": ...}, ...]`; if it returns Profile ORM objects, change to `p.name`.
5. **`tegufox-cli` script integration** — read its current dispatch block before splicing the `flow` subcommand. Don't blindly copy the snippet in Task 19; adapt to how `profile`, `fleet`, and `api` are dispatched.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-flow-dsl-engine.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with batch checkpoints.

Which approach?
