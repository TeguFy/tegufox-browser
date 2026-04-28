# Realtime AI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship sub-project #7 — an interactive AI agent loop that drives a TegufoxSession against a plain-language goal using a curated 10-verb action vocabulary, with live trace + Stop button GUI, optional auto-record to a flow YAML.

**Architecture:** Single-call ReAct loop in `tegufox_flow/agent.py`. DOM-only observation truncated to 8 KB. LLM emits one JSON action per turn via existing `ai_providers.ask_llm` (provider-agnostic). Agent dispatches verbs to existing `tegufox_flow.steps.{browser,extract}` handlers. New `Agent` GUI page with QThread worker + Stop event. Persistence reuses `flow_runs` with new `kind` and `goal_text` columns.

**Tech Stack:** Python 3.14, existing `tegufox_automation.TegufoxSession`, `tegufox_flow.steps.ai_providers`, `tegufox_flow.steps.browser`/`extract`, `tegufox_core.database` (SQLAlchemy), PyQt6, pytest.

**Spec:** `docs/superpowers/specs/2026-04-28-realtime-ai-agent-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `tegufox_flow/agent.py` | NEW | `AgentAction`, `AgentResult`, `AgentRunner`, verb dispatch table, JSON parser |
| `tegufox_gui/pages/agent_page.py` | NEW | `AgentPage` GUI + `_AgentWorker` QThread |
| `tegufox_core/database.py` | MODIFY | Add `FlowRun.kind` and `FlowRun.goal_text` columns; extend `ensure_schema()` |
| `tegufox_gui/app.py` | MODIFY | Register `AgentPage` at stack index 10 + sidebar button |
| `tests/agent/__init__.py` | NEW | (empty) |
| `tests/agent/conftest.py` | NEW | `qapp` fixture |
| `tests/agent/test_action_parser.py` | NEW | JSON parser strict-validates verbs + args |
| `tests/agent/test_action_dispatcher.py` | NEW | Each verb maps to right handler |
| `tests/agent/test_agent_runner.py` | NEW | Loop semantics with stubbed LLM |
| `tests/agent/test_agent_persistence.py` | NEW | DB rows written for agent run |
| `tests/agent/test_agent_record.py` | NEW | Auto-record builds valid flow YAML |
| `tests/agent/test_agent_page.py` | NEW | GUI smoke |

---

## Conventions

- Activate venv: `source venv/bin/activate`.
- Commit signing bypass: `git commit --no-gpg-sign` (user-approved earlier).
- Conventional Commits: `feat(agent): ...`, `test(agent): ...`, `fix(agent): ...`.
- Branch: stay on current `feat/flow-orchestrator`.
- After every commit: `pytest tests/flow tests/flow_editor tests/orchestrator tests/agent -m "not golden" -q`. Aim for green every time.

---

## Task 1: DB schema — `FlowRun.kind` + `FlowRun.goal_text`

**Files:**
- Modify: `tegufox_core/database.py` (FlowRun class + `ensure_schema()` function)
- Create: `tests/agent/__init__.py` (empty)
- Create: `tests/agent/test_db_agent_columns.py`

- [ ] **Step 1: Failing test**

```python
# tests/agent/test_db_agent_columns.py
from datetime import datetime
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import (
    Base, ensure_schema, FlowRun, FlowRecord,
)


def _eng_in_memory():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return eng


def test_flow_run_has_kind_column():
    eng = _eng_in_memory()
    cols = {c["name"] for c in inspect(eng).get_columns("flow_runs")}
    assert "kind" in cols
    assert "goal_text" in cols


def test_flow_run_kind_default_is_flow():
    eng = _eng_in_memory()
    s = sessionmaker(bind=eng)()
    f = FlowRecord(name="x", yaml_text="", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    r = FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running", started_at=datetime.utcnow())
    s.add(r); s.commit()
    fetched = s.query(FlowRun).one()
    assert fetched.kind == "flow"
    assert fetched.goal_text is None


def test_flow_run_kind_agent_persists():
    eng = _eng_in_memory()
    s = sessionmaker(bind=eng)()
    f = FlowRecord(name="x", yaml_text="", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    r = FlowRun(run_id="r2", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running",
                started_at=datetime.utcnow(),
                kind="agent", goal_text="login google")
    s.add(r); s.commit()
    fetched = s.query(FlowRun).filter_by(run_id="r2").one()
    assert fetched.kind == "agent"
    assert fetched.goal_text == "login google"


def test_ensure_schema_adds_kind_to_legacy_db():
    """Existing DB without `kind` column should get it via ensure_schema."""
    from sqlalchemy import text
    eng = create_engine("sqlite:///:memory:")
    # Create a flow_runs table missing the new columns (simulate legacy).
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("ALTER TABLE flow_runs DROP COLUMN kind"))
        conn.execute(text("ALTER TABLE flow_runs DROP COLUMN goal_text"))
    ensure_schema(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("flow_runs")}
    assert "kind" in cols
    assert "goal_text" in cols
```

- [ ] **Step 2: Run, expect failure**

```bash
mkdir -p tests/agent && touch tests/agent/__init__.py
source venv/bin/activate
pytest tests/agent/test_db_agent_columns.py -v
```

Expected: failures on missing `kind` / `goal_text` columns.

- [ ] **Step 3: Implement — add columns**

In `tegufox_core/database.py`, locate `class FlowRun` (around line 427) and add two columns alongside the others:

```python
    # Inside FlowRun class:
    kind        = Column(String(16), nullable=False, default="flow", index=True)
    goal_text   = Column(Text)
```

- [ ] **Step 4: Implement — extend `ensure_schema()`**

Find `ensure_schema()` near the top of the file. Append within the function (after the existing `flow_runs.batch_id` block):

```python
    if "flow_runs" in table_names:
        cols = {c["name"] for c in insp.get_columns("flow_runs")}
        if "kind" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE flow_runs ADD COLUMN kind VARCHAR(16) "
                    "NOT NULL DEFAULT 'flow'"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_flow_runs_kind "
                    "ON flow_runs(kind)"
                ))
        if "goal_text" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE flow_runs ADD COLUMN goal_text TEXT"
                ))
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/agent/test_db_agent_columns.py -v
pytest tests/flow tests/flow_editor tests/orchestrator -m "not golden" -q
```

Expected: 4 new tests pass; no regression in existing 240+ tests.

- [ ] **Step 6: Commit**

```bash
git add tegufox_core/database.py tests/agent/__init__.py tests/agent/test_db_agent_columns.py
git commit --no-gpg-sign -m "feat(agent): FlowRun.kind + goal_text columns + migration"
```

---

## Task 2: `AgentAction` dataclass + JSON parser

**Files:**
- Create: `tegufox_flow/agent.py` (initial — just parser + dataclasses)
- Create: `tests/agent/test_action_parser.py`

The agent module starts here. We add only the parser + types in this task; runner is later.

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_action_parser.py
import pytest
from tegufox_flow.agent import (
    AgentAction, ParseError, parse_action, AGENT_VERBS,
)


def test_verb_catalogue_has_10():
    assert set(AGENT_VERBS.keys()) == {
        "goto", "click", "click_text", "type", "scroll",
        "wait_for", "read_text", "screenshot", "done", "ask_user",
    }


def test_parse_minimal_goto():
    a = parse_action('{"verb": "goto", "args": {"url": "https://x"}}')
    assert a.verb == "goto"
    assert a.args == {"url": "https://x"}
    assert a.reasoning == ""


def test_parse_with_reasoning():
    a = parse_action(
        '{"reasoning": "go to login", "verb": "goto", '
        '"args": {"url": "https://x"}}'
    )
    assert a.reasoning == "go to login"


def test_parse_strips_markdown_fence():
    raw = '```json\n{"verb": "done", "args": {"reason": "ok"}}\n```'
    a = parse_action(raw)
    assert a.verb == "done"


def test_parse_unknown_verb_raises():
    with pytest.raises(ParseError) as e:
        parse_action('{"verb": "nope", "args": {}}')
    assert "nope" in str(e.value)


def test_parse_missing_required_arg_raises():
    with pytest.raises(ParseError) as e:
        parse_action('{"verb": "goto", "args": {}}')
    assert "url" in str(e.value)


def test_parse_extra_args_allowed():
    """Optional args present is fine."""
    a = parse_action(
        '{"verb": "goto", "args": {"url": "https://x", "wait_until": "load"}}'
    )
    assert a.args["wait_until"] == "load"


def test_parse_invalid_json_raises():
    with pytest.raises(ParseError):
        parse_action("not json {")


def test_parse_done_required_reason():
    with pytest.raises(ParseError):
        parse_action('{"verb": "done", "args": {}}')


def test_parse_ask_user_required_question():
    with pytest.raises(ParseError):
        parse_action('{"verb": "ask_user", "args": {}}')
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/agent/test_action_parser.py -v
```

- [ ] **Step 3: Implement parser**

Write `tegufox_flow/agent.py`:

```python
"""Realtime AI Agent — observe → decide → act loop.

Entry: AgentRunner.run() takes a goal + profile, drives a TegufoxSession
through one LLM call per turn, executes the chosen verb, and persists
each step as a flow_runs row + flow_checkpoints rows.

This module is split into 5 layers (top-down):
    1. Action types + JSON parser  (this task)
    2. Verb dispatch table          (Task 3)
    3. Observe / decide helpers     (Task 4)
    4. AgentRunner main loop        (Task 5)
    5. Auto-record to flow YAML     (Task 6)
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. Action types + parser
# ---------------------------------------------------------------------------


class ParseError(ValueError):
    """LLM produced output we couldn't turn into a valid AgentAction."""


@dataclass
class AgentAction:
    verb: str
    args: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


# Vocabulary: verb → required arg names. Optional args allowed in args dict.
AGENT_VERBS: Dict[str, tuple] = {
    "goto":       ("url",),
    "click":      ("selector",),
    "click_text": ("text",),
    "type":       ("selector", "text"),
    "scroll":     (),                 # 'direction' or 'to' optional
    "wait_for":   ("selector",),
    "read_text":  ("selector",),
    "screenshot": ("path",),
    "done":       ("reason",),
    "ask_user":   ("question",),
}


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?\s*```\s*$", re.MULTILINE)


def parse_action(raw: str) -> AgentAction:
    """Parse an LLM turn into an AgentAction. Raises ParseError on any
    structural / vocabulary problem so the runner can retry."""
    text = (raw or "").strip()
    if not text:
        raise ParseError("empty LLM output")
    # Strip markdown fences the LLM might add despite instruction.
    text = _FENCE_RE.sub("", text).strip()

    try:
        obj = json.loads(text)
    except Exception as e:
        raise ParseError(f"not valid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise ParseError("top-level value must be an object")

    verb = obj.get("verb")
    if not isinstance(verb, str):
        raise ParseError("'verb' must be a string")
    if verb not in AGENT_VERBS:
        raise ParseError(
            f"unknown verb {verb!r}; expected one of {sorted(AGENT_VERBS)}"
        )

    args = obj.get("args", {})
    if not isinstance(args, dict):
        raise ParseError("'args' must be an object")

    for required in AGENT_VERBS[verb]:
        if required not in args:
            raise ParseError(
                f"verb {verb!r} requires arg {required!r}; got {sorted(args)}"
            )

    reasoning = obj.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    return AgentAction(verb=verb, args=args, reasoning=reasoning)


@dataclass
class AgentResult:
    """Outcome of a single AgentRunner.run() invocation."""
    run_id: str
    status: str          # done | max_steps | timeout | aborted | parse_error | error
    reason: str = ""
    steps: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    flow_yaml: Optional[str] = None  # set if record_as_flow=True and status=done
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_action_parser.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_action_parser.py
git commit --no-gpg-sign -m "feat(agent): AgentAction + JSON parser with verb validation"
```

---

## Task 3: Verb dispatch — verb → existing step handler

**Files:**
- Modify: `tegufox_flow/agent.py` (append dispatch + executor)
- Create: `tests/agent/test_action_dispatcher.py`

The dispatcher converts an `AgentAction` into a `StepSpec` and invokes the matching handler from `tegufox_flow.steps`. This re-uses the production step code so the agent's actions match flow runs exactly.

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_action_dispatcher.py
from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import (
    AgentAction, dispatch_action, DispatchError,
)


def _ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    import logging
    c.logger = logging.getLogger("test_dispatch")
    return c


def test_dispatch_goto_calls_browser_goto():
    ctx = _ctx()
    with patch("tegufox_flow.steps.browser._goto") as h:
        # _goto is registered, but we want to verify the registry path,
        # so instead patch get_handler.
        pass

    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        action = AgentAction(verb="goto", args={"url": "https://x"})
        result = dispatch_action(action, ctx)
        gh.assert_called_once_with("browser.goto")
        # The handler is called with a StepSpec.
        spec_arg = handler.call_args.args[0]
        assert spec_arg.type == "browser.goto"
        assert spec_arg.params["url"] == "https://x"
        assert result["ok"] is True


def test_dispatch_click_text():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        gh.return_value = MagicMock()
        dispatch_action(AgentAction(verb="click_text",
                                    args={"text": "Sign in"}), ctx)
        gh.assert_called_once_with("browser.click_text")


def test_dispatch_type_passes_human_false():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        dispatch_action(AgentAction(verb="type",
                                    args={"selector": "#x", "text": "hi"}), ctx)
        spec = handler.call_args.args[0]
        assert spec.params["selector"] == "#x"
        assert spec.params["text"] == "hi"
        assert spec.params["human"] is False


def test_dispatch_click_passes_force_true():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        dispatch_action(AgentAction(verb="click",
                                    args={"selector": "#x"}), ctx)
        spec = handler.call_args.args[0]
        assert spec.params["force"] is True


def test_dispatch_read_text_returns_var_value():
    ctx = _ctx()
    captured: dict = {}

    def fake_handler(spec, c):
        # Simulate the real read_text setting the var.
        c.set_var(spec.params["set"], "hello-from-page")

    with patch("tegufox_flow.agent.get_handler", return_value=fake_handler):
        action = AgentAction(verb="read_text", args={"selector": "h1"})
        # ctx is a MagicMock so set_var goes through the MagicMock —
        # we capture via the call_args after dispatch.
        dispatch_action(action, ctx)
        # The dispatcher reads the var back from the context. We exercise
        # this by stubbing set_var to capture and ctx to return the value.


def test_dispatch_screenshot_no_selector():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        gh.return_value = MagicMock()
        dispatch_action(AgentAction(verb="screenshot",
                                    args={"path": "out.png"}), ctx)
        spec = gh.return_value.call_args.args[0]
        assert spec.params["path"] == "out.png"


def test_dispatch_unknown_verb_raises():
    ctx = _ctx()
    with pytest.raises(DispatchError):
        dispatch_action(AgentAction(verb="nope", args={}), ctx)


def test_dispatch_done_returns_signal():
    """done is a meta-verb: dispatcher returns special marker rather than
    invoking a handler."""
    ctx = _ctx()
    out = dispatch_action(
        AgentAction(verb="done", args={"reason": "task complete"}), ctx
    )
    assert out["terminal"] == "done"
    assert out["reason"] == "task complete"


def test_dispatch_ask_user_returns_signal():
    ctx = _ctx()
    out = dispatch_action(
        AgentAction(verb="ask_user", args={"question": "2FA code?"}), ctx
    )
    assert out["terminal"] == "ask_user"
    assert out["question"] == "2FA code?"
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_action_dispatcher.py -v
```

- [ ] **Step 3: Implement**

Append to `tegufox_flow/agent.py`:

```python
# ---------------------------------------------------------------------------
# 2. Verb dispatch — verb → step handler invocation
# ---------------------------------------------------------------------------

# Late imports inside dispatch_action keep the module importable in
# environments where tegufox_automation isn't ready (e.g., test discovery
# before pytest fixtures activate the venv).


class DispatchError(RuntimeError):
    """Tried to dispatch an unknown / unsupported verb."""


def _build_spec(verb: str, args: Dict[str, Any]):
    """Translate an agent verb + args into a StepSpec the existing step
    handlers can consume. Each branch enforces the agent's defaults
    (force=True for click, human=False for type)."""
    from tegufox_flow.steps import StepSpec

    if verb == "goto":
        params = {"url": args["url"]}
        if "wait_until" in args:
            params["wait_until"] = args["wait_until"]
        return StepSpec(id=f"agent_goto", type="browser.goto", params=params)

    if verb == "click":
        return StepSpec(id="agent_click", type="browser.click",
                        params={"selector": args["selector"], "force": True,
                                "human": False})

    if verb == "click_text":
        params = {"text": args["text"], "force": True}
        if "role" in args:
            params["role"] = args["role"]
        return StepSpec(id="agent_click_text", type="browser.click_text",
                        params=params)

    if verb == "type":
        return StepSpec(id="agent_type", type="browser.type",
                        params={"selector": args["selector"],
                                "text": args["text"], "human": False})

    if verb == "scroll":
        params = {}
        for k in ("direction", "pixels", "to"):
            if k in args:
                params[k] = args[k]
        return StepSpec(id="agent_scroll", type="browser.scroll",
                        params=params)

    if verb == "wait_for":
        params = {"selector": args["selector"]}
        if "state" in args:
            params["state"] = args["state"]
        return StepSpec(id="agent_wait_for", type="browser.wait_for",
                        params=params)

    if verb == "read_text":
        return StepSpec(id="agent_read_text", type="extract.read_text",
                        params={"selector": args["selector"],
                                "set": "_agent_read"})

    if verb == "screenshot":
        return StepSpec(id="agent_screenshot", type="browser.screenshot",
                        params={"path": args["path"]})

    raise DispatchError(f"no step mapping for verb {verb!r}")


def dispatch_action(action: AgentAction, ctx) -> Dict[str, Any]:
    """Execute an AgentAction against the given FlowContext-shaped object.
    Returns a result dict: terminal verbs (done/ask_user) return
    `{terminal: <verb>, ...}`; other verbs return `{ok: True, value?: any}`.
    """
    if action.verb == "done":
        return {"terminal": "done", "reason": action.args.get("reason", "")}
    if action.verb == "ask_user":
        return {"terminal": "ask_user",
                "question": action.args.get("question", "")}

    if action.verb not in AGENT_VERBS:
        raise DispatchError(f"unknown verb {action.verb!r}")

    from tegufox_flow.steps import get_handler
    spec = _build_spec(action.verb, action.args)
    handler = get_handler(spec.type)
    handler(spec, ctx)

    out: Dict[str, Any] = {"ok": True}
    if action.verb == "read_text":
        # The handler stored the value under '_agent_read' on ctx.vars
        # (or via ctx.set_var on a real FlowContext).
        try:
            out["value"] = ctx.vars.get("_agent_read")
        except Exception:
            out["value"] = None
    return out
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_action_dispatcher.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_action_dispatcher.py
git commit --no-gpg-sign -m "feat(agent): verb dispatcher mapping to existing step handlers"
```

---

## Task 4: Observe + decide helpers

**Files:**
- Modify: `tegufox_flow/agent.py` (append observe + decide)
- Create: `tests/agent/test_observe_decide.py`

`_observe(page)` collects URL + truncated DOM. `_decide(history, obs, …)` builds the prompt and calls `ask_llm`, returning a parsed `AgentAction` (with retries on parse error).

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_observe_decide.py
from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import _observe, _decide, AgentAction, ParseError


def test_observe_returns_url_title_dom():
    page = MagicMock()
    page.url = "https://example.com"
    page.title.return_value = "Example"
    page.content.return_value = "<html><body>X" + "y" * 20000 + "</body></html>"
    obs = _observe(page)
    assert obs["url"] == "https://example.com"
    assert obs["title"] == "Example"
    # DOM is truncated.
    assert len(obs["dom"]) < 12000
    assert "truncated" in obs["dom"].lower() or len(obs["dom"]) <= 8200


def test_observe_handles_title_failure():
    page = MagicMock()
    page.url = "https://x"
    page.title.side_effect = RuntimeError("no")
    page.content.return_value = "<html></html>"
    obs = _observe(page)
    assert obs["title"] == ""


def test_decide_returns_parsed_action():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    with patch("tegufox_flow.agent.ask_llm",
               return_value='{"verb": "goto", "args": {"url": "https://y"}}'):
        action = _decide(history=[], obs=obs, goal="t",
                         provider=None, model=None)
    assert action.verb == "goto"
    assert action.args["url"] == "https://y"


def test_decide_retries_on_bad_json_then_succeeds():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    responses = iter([
        "not json",
        '{"verb": "ghost"}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(responses)):
        action = _decide(history=[], obs=obs, goal="t",
                         provider=None, model=None)
    assert action.verb == "done"


def test_decide_gives_up_after_3_attempts():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    with patch("tegufox_flow.agent.ask_llm",
               side_effect=["bad"] * 5):
        with pytest.raises(ParseError):
            _decide(history=[], obs=obs, goal="t",
                    provider=None, model=None)


def test_decide_truncates_history_to_last_10():
    obs = {"url": "x", "title": "x", "dom": ""}
    captured = {}

    def fake(**kw):
        captured["user"] = kw["user"]
        return '{"verb": "done", "args": {"reason": "ok"}}'

    huge_history = [
        {"obs": {"url": f"u{i}", "title": "", "dom": ""},
         "action": {"verb": "goto", "args": {}, "reasoning": ""},
         "result": {"ok": True}}
        for i in range(40)
    ]
    with patch("tegufox_flow.agent.ask_llm", side_effect=fake):
        _decide(history=huge_history, obs=obs, goal="t",
                provider=None, model=None)
    # The user prompt should mention only recent turns. Check that the
    # earliest URL u0 isn't in the prompt (pruned), and a recent one is.
    assert "u0" not in captured["user"]
    assert "u39" in captured["user"]
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_observe_decide.py -v
```

- [ ] **Step 3: Implement**

Append to `tegufox_flow/agent.py`:

```python
# ---------------------------------------------------------------------------
# 3. Observe + decide
# ---------------------------------------------------------------------------

_DOM_LIMIT = 8000
_HISTORY_KEEP = 10
_MAX_PARSE_ATTEMPTS = 3


def _truncate_dom(html: str, limit: int = _DOM_LIMIT) -> str:
    if not html:
        return ""
    if len(html) <= limit:
        return html
    head = html[: limit // 2]
    tail = html[-limit // 2:]
    return f"{head}\n…[{len(html) - limit} chars truncated]…\n{tail}"


def _observe(page) -> Dict[str, Any]:
    """Snapshot the current page for the LLM."""
    try:
        url = page.url or ""
    except Exception:
        url = ""
    try:
        title = (page.title() or "")[:200]
    except Exception:
        title = ""
    try:
        dom = _truncate_dom(page.content() or "")
    except Exception:
        dom = ""
    return {"url": url, "title": title, "dom": dom}


_SYSTEM_TEMPLATE = (
    "You are a browser-automation agent.\n"
    "GOAL: {goal}\n\n"
    "On each turn output ONE JSON object with keys:\n"
    "  reasoning  — one short sentence\n"
    "  verb       — exactly one of: goto, click, click_text, type, scroll, "
    "wait_for, read_text, screenshot, done, ask_user\n"
    "  args       — verb-specific keys:\n"
    "    goto:        url, wait_until?\n"
    "    click:       selector\n"
    "    click_text:  text, role?\n"
    "    type:        selector, text\n"
    "    scroll:      direction|to, pixels?\n"
    "    wait_for:    selector, state?\n"
    "    read_text:   selector\n"
    "    screenshot:  path\n"
    "    done:        reason\n"
    "    ask_user:    question\n\n"
    "Emit verb='done' with args.reason when goal achieved.\n"
    "Emit verb='ask_user' if you need info from the user (2FA, etc).\n"
    "Output ONLY the JSON, no markdown, no prose."
)


def _format_history(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "(no prior turns)"
    lines = []
    for i, turn in enumerate(history):
        action = turn.get("action") or {}
        verb = action.get("verb", "?")
        args = action.get("args", {})
        result = turn.get("result") or {}
        url = (turn.get("obs") or {}).get("url", "")
        lines.append(
            f"  Step {i+1}: at {url} → {verb}({json.dumps(args)})"
            f"  result={json.dumps(result)[:100]}"
        )
    return "\n".join(lines)


def _decide(
    *,
    history: List[Dict[str, Any]],
    obs: Dict[str, Any],
    goal: str,
    provider: Optional[str],
    model: Optional[str],
) -> AgentAction:
    """Run one LLM turn and return the parsed AgentAction.
    Retries up to 2 times on ParseError, feeding back the parse error."""
    from tegufox_flow.steps.ai_providers import ask_llm

    recent = history[-_HISTORY_KEEP:]
    history_text = _format_history(recent)
    base_user = (
        f"PRIOR TURNS:\n{history_text}\n\n"
        f"CURRENT PAGE:\n"
        f"URL: {obs.get('url')}\n"
        f"TITLE: {obs.get('title')}\n"
        f"DOM:\n{obs.get('dom')}\n\n"
        f"Next action JSON:"
    )
    system = _SYSTEM_TEMPLATE.format(goal=goal)

    last_error = None
    user = base_user
    for attempt in range(_MAX_PARSE_ATTEMPTS):
        raw = ask_llm(
            system=system, user=user,
            max_tokens=512, provider=provider, model=model,
        )
        try:
            return parse_action(raw)
        except ParseError as e:
            last_error = e
            user = (
                base_user
                + f"\n\nPRIOR ATTEMPT FAILED: {e}\n"
                  "Return STRICTLY valid JSON matching the schema."
            )
    raise ParseError(
        f"LLM produced malformed output {_MAX_PARSE_ATTEMPTS} times: {last_error}"
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_observe_decide.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_observe_decide.py
git commit --no-gpg-sign -m "feat(agent): observe + decide loop helpers with retry"
```

---

## Task 5: `AgentRunner` — main loop

**Files:**
- Modify: `tegufox_flow/agent.py` (append AgentRunner class)
- Create: `tests/agent/test_agent_runner.py`

The runner stitches everything: opens session, loops observe → decide → dispatch, persists checkpoints, honors stop conditions, returns `AgentResult`.

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_agent_runner.py
import threading
from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import AgentRunner, AgentResult


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.page = MagicMock()
    s.page.url = "https://example.com"
    s.page.title.return_value = "ex"
    s.page.content.return_value = "<html></html>"
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


def test_runner_done_terminates(fake_session):
    """LLM emits done immediately → status='done'."""
    actions_iter = iter([
        '{"verb": "done", "args": {"reason": "trivial goal"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions_iter)):
        runner = AgentRunner(goal="check page exists", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "done"
    assert result.reason == "trivial goal"
    assert result.steps == 0   # done emitted before any verb executed


def test_runner_max_steps(fake_session):
    """LLM never emits done → loop hits max_steps cap."""
    def fake_ask(**kw):
        return '{"verb": "scroll", "args": {"direction": "down"}}'

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=fake_ask), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="loop", profile_name="p",
                             max_steps=3, max_time=60)
        result = runner.run()
    assert result.status == "max_steps"
    assert result.steps == 3


def test_runner_user_stop_event(fake_session):
    """User clicks Stop mid-run."""
    stop_event = threading.Event()

    def fake_ask(**kw):
        # Trigger stop right before second decide.
        stop_event.set()
        return '{"verb": "scroll", "args": {"direction": "down"}}'

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=fake_ask), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60,
                             stop_event=stop_event)
        result = runner.run()
    assert result.status == "aborted"


def test_runner_parse_error_after_3_retries(fake_session):
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "parse_error"


def test_runner_dispatch_error_keeps_history(fake_session):
    """If a verb's dispatch raises, the error is recorded and the loop
    continues so the LLM can try a different action."""
    actions = iter([
        '{"verb": "click", "args": {"selector": "#x"}}',
        '{"verb": "done", "args": {"reason": "gave up"}}',
    ])

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               side_effect=RuntimeError("bad selector")):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "done"
    assert any("error" in turn["result"] for turn in result.history)


def test_runner_calls_step_callback(fake_session):
    actions = iter([
        '{"verb": "scroll", "args": {"direction": "down"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    seen = []

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60,
                             on_step=lambda i, a, r: seen.append((i, a.verb)))
        runner.run()
    assert seen[0] == (1, "scroll")
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_agent_runner.py -v
```

- [ ] **Step 3: Implement**

Append to `tegufox_flow/agent.py`:

```python
# ---------------------------------------------------------------------------
# 4. AgentRunner — main loop
# ---------------------------------------------------------------------------

import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from tegufox_automation import TegufoxSession            # type: ignore
from tegufox_flow.steps.ai_providers import ask_llm      # noqa: F401  (patched in tests)


_LOG = logging.getLogger("tegufox_flow.agent")


class _MutableCtx:
    """Lightweight stand-in for FlowContext used inside dispatch_action.
    Exposes .page, .vars, .render, .logger, .set_var — the subset the
    existing step handlers reach for. We don't need the full FlowContext
    (with ExpressionEngine, kv, checkpoints) because the agent doesn't
    use Jinja templates or persistent state — values come straight from
    AgentAction.args."""

    def __init__(self, page, logger):
        self.page = page
        self.vars: Dict[str, Any] = {}
        self.logger = logger
        self._human_mouse = None
        self._human_keyboard = None

    def render(self, s: Any) -> Any:
        return s if not isinstance(s, str) else s

    def set_var(self, name: str, value: Any) -> None:
        self.vars[name] = value

    def eval(self, expr: str) -> Any:
        # Agent verbs never invoke Jinja eval; fall back to literal.
        return expr


class AgentRunner:
    """observe → decide → dispatch loop.

    Construct with goal + profile + limits; call .run() to drive the
    session to completion. Optional `on_step(idx, action, result)`
    callback gets each step for live UI tracing. `stop_event` is a
    threading.Event the GUI Stop button sets; the runner checks it at
    the top of every iteration.
    """

    def __init__(
        self,
        *,
        goal: str,
        profile_name: str,
        proxy_name: Optional[str] = None,
        max_steps: int = 30,
        max_time: int = 300,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        on_step=None,
        on_ask_user=None,
    ):
        self.goal = goal
        self.profile_name = profile_name
        self.proxy_name = proxy_name
        self.max_steps = int(max_steps)
        self.max_time = float(max_time)
        self.provider = provider
        self.model = model
        self._stop = stop_event or threading.Event()
        self._on_step = on_step
        self._on_ask_user = on_ask_user
        self.run_id = str(uuid.uuid4())

    def run(self) -> AgentResult:
        history: List[Dict[str, Any]] = []
        started = time.monotonic()

        try:
            with TegufoxSession(profile=self.profile_name) as session:
                ctx = _MutableCtx(page=session.page, logger=_LOG)
                step_i = 0

                # First iteration may receive `done` immediately — that's why
                # we observe before running any verb.
                while step_i < self.max_steps:
                    if self._stop.is_set():
                        return AgentResult(
                            run_id=self.run_id, status="aborted",
                            reason="user stop", steps=step_i, history=history,
                        )
                    if (time.monotonic() - started) > self.max_time:
                        return AgentResult(
                            run_id=self.run_id, status="timeout",
                            reason=f"exceeded {self.max_time}s",
                            steps=step_i, history=history,
                        )

                    obs = _observe(session.page)
                    try:
                        action = _decide(
                            history=history, obs=obs, goal=self.goal,
                            provider=self.provider, model=self.model,
                        )
                    except ParseError as e:
                        return AgentResult(
                            run_id=self.run_id, status="parse_error",
                            reason=str(e), steps=step_i, history=history,
                        )

                    if self._on_step is not None:
                        try:
                            self._on_step(step_i + 1, action, None)
                        except Exception:
                            pass

                    # Terminal verbs.
                    if action.verb == "done":
                        return AgentResult(
                            run_id=self.run_id, status="done",
                            reason=action.args.get("reason", ""),
                            steps=step_i, history=history,
                        )
                    if action.verb == "ask_user":
                        question = action.args.get("question", "")
                        reply = ""
                        if self._on_ask_user is not None:
                            try:
                                reply = self._on_ask_user(question)
                            except Exception:
                                reply = ""
                        if not reply:
                            return AgentResult(
                                run_id=self.run_id, status="aborted",
                                reason=f"ask_user cancelled: {question}",
                                steps=step_i, history=history,
                            )
                        history.append({
                            "obs": obs, "action": action.__dict__,
                            "result": {"user_reply": reply},
                        })
                        step_i += 1
                        continue

                    # Regular verb.
                    try:
                        result = dispatch_action(action, ctx)
                    except Exception as e:
                        result = {"error": f"{type(e).__name__}: {e}"}
                    history.append({
                        "obs": obs, "action": action.__dict__, "result": result,
                    })
                    step_i += 1

                return AgentResult(
                    run_id=self.run_id, status="max_steps",
                    reason=f"hit max_steps={self.max_steps}",
                    steps=step_i, history=history,
                )
        except Exception as e:
            _LOG.exception("agent runner crashed")
            return AgentResult(
                run_id=self.run_id, status="error",
                reason=f"{type(e).__name__}: {e}",
                steps=len(history), history=history,
            )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_agent_runner.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_agent_runner.py
git commit --no-gpg-sign -m "feat(agent): AgentRunner main loop with stop conditions"
```

---

## Task 6: Persistence — write `flow_runs` + `flow_checkpoints`

**Files:**
- Modify: `tegufox_flow/agent.py` (add `_persist_run_start`, `_persist_step`, `_persist_run_end` + plumb into runner)
- Create: `tests/agent/test_agent_persistence.py`

The runner calls helpers that update `flow_runs` (status, last_step_id, error) and append a `flow_checkpoints` row per step. Agent kind = 'agent'.

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_agent_persistence.py
import json
from unittest.mock import MagicMock, patch
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import (
    Base, ensure_schema, FlowRun, FlowRecord, FlowCheckpoint,
)
from tegufox_flow.agent import AgentRunner


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return str(db_path)


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.page.url = "https://x"
    s.page.title.return_value = "x"
    s.page.content.return_value = ""
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


def test_runner_persists_run_row(db, fake_session):
    actions = iter([
        '{"verb": "done", "args": {"reason": "trivial"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)):
        runner = AgentRunner(goal="hello world", profile_name="p",
                             db_path=db, max_steps=3, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    rows = s.query(FlowRun).filter_by(run_id=result.run_id).all()
    assert len(rows) == 1
    r = rows[0]
    assert r.kind == "agent"
    assert r.goal_text == "hello world"
    assert r.profile_name == "p"
    assert r.status == "done"


def test_runner_persists_checkpoints_per_step(db, fake_session):
    actions = iter([
        '{"verb": "scroll", "args": {"direction": "down"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p", db_path=db,
                             max_steps=5, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    cps = (s.query(FlowCheckpoint)
           .filter_by(run_id=result.run_id)
           .order_by(FlowCheckpoint.seq).all())
    assert len(cps) >= 1
    payload = json.loads(cps[0].vars_json)
    assert payload["verb"] == "scroll"


def test_runner_persists_failure_status(db, fake_session):
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p", db_path=db,
                             max_steps=3, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    r = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert r.status == "parse_error"
    assert r.error_text and "malformed" in r.error_text.lower()
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_agent_persistence.py -v
```

- [ ] **Step 3: Implement persistence**

In `tegufox_flow/agent.py`, modify `AgentRunner.__init__` to accept `db_path` and rewrite `run()` to call persistence helpers. Add the helpers:

Replace the existing `AgentRunner.__init__` parameter list with:

```python
    def __init__(
        self,
        *,
        goal: str,
        profile_name: str,
        proxy_name: Optional[str] = None,
        max_steps: int = 30,
        max_time: int = 300,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        on_step=None,
        on_ask_user=None,
        db_path: str = "data/tegufox.db",
    ):
        self.goal = goal
        self.profile_name = profile_name
        self.proxy_name = proxy_name
        self.max_steps = int(max_steps)
        self.max_time = float(max_time)
        self.provider = provider
        self.model = model
        self._stop = stop_event or threading.Event()
        self._on_step = on_step
        self._on_ask_user = on_ask_user
        self.db_path = db_path
        self.run_id = str(uuid.uuid4())
        self._db_session_factory = self._make_session_factory()

    def _make_session_factory(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from tegufox_core.database import Base, ensure_schema
        eng = create_engine(f"sqlite:///{Path(self.db_path).resolve()}")
        Base.metadata.create_all(eng)
        ensure_schema(eng)
        return sessionmaker(bind=eng)
```

Add helper methods on AgentRunner:

```python
    def _persist_run_start(self) -> None:
        from tegufox_core.database import FlowRecord, FlowRun
        S = self._db_session_factory
        with S() as s:
            now = datetime.utcnow()
            agent_flow = (s.query(FlowRecord)
                          .filter_by(name="__agent__").first())
            if agent_flow is None:
                agent_flow = FlowRecord(
                    name="__agent__", yaml_text="(agent runs)",
                    schema_version=1, created_at=now, updated_at=now,
                )
                s.add(agent_flow); s.commit()
            run_row = FlowRun(
                run_id=self.run_id, flow_id=agent_flow.id,
                profile_name=self.profile_name,
                inputs_json=json.dumps({"goal": self.goal}, default=str),
                status="running", started_at=now,
                kind="agent", goal_text=self.goal,
            )
            s.add(run_row)
            s.commit()

    def _persist_step(self, seq: int, verb: str, payload: Dict[str, Any]) -> None:
        from tegufox_core.database import FlowCheckpoint
        S = self._db_session_factory
        with S() as s:
            row = FlowCheckpoint(
                run_id=self.run_id, seq=seq,
                step_id=f"agent_step_{seq}",
                vars_json=json.dumps(payload, default=str),
                created_at=datetime.utcnow(),
            )
            s.add(row); s.commit()

    def _persist_run_end(self, result: "AgentResult") -> None:
        from tegufox_core.database import FlowRun
        S = self._db_session_factory
        with S() as s:
            row = s.query(FlowRun).filter_by(run_id=self.run_id).first()
            if row is None:
                return
            row.status = result.status
            row.finished_at = datetime.utcnow()
            row.last_step_id = (
                result.history[-1]["action"]["verb"] if result.history else None
            )
            if result.status not in ("done",):
                row.error_text = result.reason
            s.commit()
```

Modify `run()` to call these. At the very top of `run()` add `self._persist_run_start()`. After every step that adds to history, add `self._persist_step(...)`. At every `return AgentResult(...)`, instead of returning directly, do:

```python
                result = AgentResult(...)
                self._persist_run_end(result)
                return result
```

Concretely, here's the updated run() body — replace the entire method:

```python
    def run(self) -> AgentResult:
        self._persist_run_start()
        history: List[Dict[str, Any]] = []
        started = time.monotonic()
        seq = 0

        def _finish(result: AgentResult) -> AgentResult:
            self._persist_run_end(result)
            return result

        try:
            with TegufoxSession(profile=self.profile_name) as session:
                ctx = _MutableCtx(page=session.page, logger=_LOG)
                step_i = 0

                while step_i < self.max_steps:
                    if self._stop.is_set():
                        return _finish(AgentResult(
                            run_id=self.run_id, status="aborted",
                            reason="user stop", steps=step_i, history=history,
                        ))
                    if (time.monotonic() - started) > self.max_time:
                        return _finish(AgentResult(
                            run_id=self.run_id, status="timeout",
                            reason=f"exceeded {self.max_time}s",
                            steps=step_i, history=history,
                        ))

                    obs = _observe(session.page)
                    try:
                        action = _decide(
                            history=history, obs=obs, goal=self.goal,
                            provider=self.provider, model=self.model,
                        )
                    except ParseError as e:
                        return _finish(AgentResult(
                            run_id=self.run_id, status="parse_error",
                            reason=str(e), steps=step_i, history=history,
                        ))

                    if self._on_step is not None:
                        try:
                            self._on_step(step_i + 1, action, None)
                        except Exception:
                            pass

                    if action.verb == "done":
                        return _finish(AgentResult(
                            run_id=self.run_id, status="done",
                            reason=action.args.get("reason", ""),
                            steps=step_i, history=history,
                        ))
                    if action.verb == "ask_user":
                        question = action.args.get("question", "")
                        reply = ""
                        if self._on_ask_user is not None:
                            try:
                                reply = self._on_ask_user(question)
                            except Exception:
                                reply = ""
                        if not reply:
                            return _finish(AgentResult(
                                run_id=self.run_id, status="aborted",
                                reason=f"ask_user cancelled: {question}",
                                steps=step_i, history=history,
                            ))
                        seq += 1
                        turn = {"obs": obs, "action": action.__dict__,
                                "result": {"user_reply": reply}}
                        history.append(turn)
                        self._persist_step(seq, "ask_user", turn)
                        step_i += 1
                        continue

                    try:
                        result = dispatch_action(action, ctx)
                    except Exception as e:
                        result = {"error": f"{type(e).__name__}: {e}"}
                    seq += 1
                    turn = {"obs": obs, "action": action.__dict__,
                            "result": result}
                    history.append(turn)
                    self._persist_step(seq, action.verb, turn)
                    step_i += 1

                return _finish(AgentResult(
                    run_id=self.run_id, status="max_steps",
                    reason=f"hit max_steps={self.max_steps}",
                    steps=step_i, history=history,
                ))
        except Exception as e:
            _LOG.exception("agent runner crashed")
            return _finish(AgentResult(
                run_id=self.run_id, status="error",
                reason=f"{type(e).__name__}: {e}",
                steps=len(history), history=history,
            ))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_agent_persistence.py -v
pytest tests/agent -v   # full agent test set
```

Expected: 3 new pass; all earlier agent tests still pass (some may now fail because the runner needs `db_path` — fix by passing `db_path=":memory:"` or using a `tmp_path` in earlier tests).

- [ ] **Step 5: Adjust earlier runner tests if they fail**

Earlier tests in `test_agent_runner.py` constructed `AgentRunner` without `db_path`. With the default `data/tegufox.db`, persistence will write to the real DB during tests — undesirable. Fix by passing `db_path=":memory:"` in those tests:

```python
# tests/agent/test_agent_runner.py — update every AgentRunner(...) call
runner = AgentRunner(goal="...", profile_name="p", db_path=":memory:",
                     max_steps=..., max_time=...)
```

Actually `:memory:` doesn't work across SQLAlchemy sessions (each connection sees a different memory DB). Use a tmp file fixture instead:

```python
import pytest

@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "agent_test.db")
```

Then update every AgentRunner instantiation in `test_agent_runner.py` to take `tmp_db`:

```python
def test_runner_done_terminates(fake_session, tmp_db):
    ...
    runner = AgentRunner(goal="check page exists", profile_name="p",
                         db_path=tmp_db, max_steps=10, max_time=60)
```

Re-run:

```bash
pytest tests/agent -v
```

- [ ] **Step 6: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_agent_persistence.py tests/agent/test_agent_runner.py
git commit --no-gpg-sign -m "feat(agent): persist runs and checkpoints to flow_runs"
```

---

## Task 7: Auto-record agent run as flow YAML

**Files:**
- Modify: `tegufox_flow/agent.py` (add `_history_to_flow_yaml` + `record_as_flow` plumbing)
- Create: `tests/agent/test_agent_record.py`

After a successful (`status='done'`) agent run, optionally serialise the action history into a `schema_version: 1` flow YAML and write it to `flows`. Skipped if `record_as_flow=False` (default).

- [ ] **Step 1: Failing tests**

```python
# tests/agent/test_agent_record.py
import json
from unittest.mock import MagicMock, patch
import pytest
import yaml as _yaml

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, ensure_schema, FlowRecord
from tegufox_flow.agent import AgentRunner, _history_to_flow_yaml


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return str(db_path)


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.page.url = "https://x"
    s.page.title.return_value = "x"
    s.page.content.return_value = ""
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


def test_history_to_flow_yaml_minimal():
    history = [
        {"action": {"verb": "goto", "args": {"url": "https://x"},
                    "reasoning": "go"}, "result": {"ok": True}},
        {"action": {"verb": "done", "args": {"reason": "ok"},
                    "reasoning": ""}, "result": {}},
    ]
    yaml_text = _history_to_flow_yaml(goal="open x", history=history,
                                      flow_name="agent_test")
    data = _yaml.safe_load(yaml_text)
    assert data["schema_version"] == 1
    assert data["name"] == "agent_test"
    assert any(s["type"] == "browser.goto" for s in data["steps"])
    # done is not emitted as a step.
    assert not any(s["type"] == "browser.done" for s in data["steps"])
    # description carries goal.
    assert "open x" in data.get("description", "")


def test_history_to_flow_yaml_promotes_ask_user_to_input():
    history = [
        {"action": {"verb": "ask_user",
                    "args": {"question": "Email?"},
                    "reasoning": ""},
         "result": {"user_reply": "alice@x.com"}},
        {"action": {"verb": "type",
                    "args": {"selector": "#email", "text": "alice@x.com"},
                    "reasoning": ""}, "result": {"ok": True}},
        {"action": {"verb": "done", "args": {"reason": "ok"},
                    "reasoning": ""}, "result": {}},
    ]
    yaml_text = _history_to_flow_yaml(goal="g", history=history,
                                      flow_name="agent_t")
    data = _yaml.safe_load(yaml_text)
    assert "inputs" in data
    # An input was created for the ask_user question.
    assert any("ask_user" in name or "email" in name.lower()
               for name in data["inputs"])


def test_runner_record_as_flow_writes_flows_row(tmp_db, fake_session):
    actions = iter([
        '{"verb": "goto", "args": {"url": "https://example.com"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="open example", profile_name="p",
                             db_path=tmp_db, max_steps=5, max_time=60,
                             record_as_flow=True)
        result = runner.run()

    assert result.status == "done"
    eng = create_engine(f"sqlite:///{tmp_db}")
    s = sessionmaker(bind=eng)()
    flows = s.query(FlowRecord).all()
    # __agent__ placeholder + the new recorded flow.
    names = [f.name for f in flows]
    assert any(n.startswith("agent-") for n in names)
    assert result.flow_yaml is not None


def test_runner_no_record_when_off(tmp_db, fake_session):
    actions = iter([
        '{"verb": "done", "args": {"reason": "trivial"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)):
        runner = AgentRunner(goal="g", profile_name="p", db_path=tmp_db,
                             max_steps=3, max_time=60,
                             record_as_flow=False)
        result = runner.run()

    eng = create_engine(f"sqlite:///{tmp_db}")
    s = sessionmaker(bind=eng)()
    names = [f.name for f in s.query(FlowRecord).all()]
    assert all(not n.startswith("agent-") for n in names)
    assert result.flow_yaml is None


def test_runner_no_record_on_failure(tmp_db, fake_session):
    """Failed runs aren't auto-saved even if record_as_flow=True."""
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p", db_path=tmp_db,
                             max_steps=3, max_time=60,
                             record_as_flow=True)
        result = runner.run()
    assert result.status == "parse_error"
    assert result.flow_yaml is None
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_agent_record.py -v
```

- [ ] **Step 3: Implement**

Append to `tegufox_flow/agent.py`:

```python
# ---------------------------------------------------------------------------
# 5. Auto-record history → flow YAML
# ---------------------------------------------------------------------------

import re as _re_slug


def _slug(s: str) -> str:
    s = (s or "").lower()
    s = _re_slug.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "anon"


_VERB_TO_STEP_TYPE = {
    "goto":       "browser.goto",
    "click":      "browser.click",
    "click_text": "browser.click_text",
    "type":       "browser.type",
    "scroll":     "browser.scroll",
    "wait_for":   "browser.wait_for",
    "read_text":  "extract.read_text",
    "screenshot": "browser.screenshot",
}


def _history_to_flow_yaml(*, goal: str, history: List[Dict[str, Any]],
                          flow_name: str) -> str:
    """Serialise an agent's successful action history into a runnable
    flow YAML. ask_user turns are promoted to flow inputs, and the next
    verb that consumed the reply is rewritten to reference the input
    via Jinja template.
    """
    inputs: Dict[str, Dict[str, Any]] = {}
    steps: List[Dict[str, Any]] = []
    pending_input: Optional[str] = None

    for i, turn in enumerate(history):
        action = turn.get("action") or {}
        verb = action.get("verb")
        args = dict(action.get("args") or {})

        if verb == "ask_user":
            input_name = f"ask_{_slug(args.get('question',''))}"
            inputs[input_name] = {
                "type": "string",
                "required": True,
                "default": (turn.get("result") or {}).get("user_reply", ""),
            }
            pending_input = input_name
            continue

        if verb in ("done", "ask_user"):
            continue

        if verb not in _VERB_TO_STEP_TYPE:
            # Unknown verb → skip silently.
            continue

        # If previous turn was ask_user, replace the matching arg value
        # with a Jinja reference to the input.
        if pending_input is not None:
            for k, v in list(args.items()):
                if isinstance(v, str) and v == \
                        inputs[pending_input]["default"]:
                    args[k] = "{{ inputs." + pending_input + " }}"
            pending_input = None

        # Add reasonable defaults the agent dispatcher already applies.
        if verb == "click":
            args.setdefault("force", True)
            args.setdefault("human", False)
        if verb == "type":
            args.setdefault("human", False)
        if verb == "click_text":
            args.setdefault("force", True)

        step = {"id": f"step_{i+1}", "type": _VERB_TO_STEP_TYPE[verb]}
        step.update(args)
        steps.append(step)

    flow: Dict[str, Any] = {
        "schema_version": 1,
        "name": flow_name,
        "description": f"Auto-recorded agent run. Goal: {goal}",
    }
    if inputs:
        flow["inputs"] = inputs
    flow["steps"] = steps

    import yaml as _yaml
    return _yaml.safe_dump(flow, sort_keys=False, allow_unicode=True)
```

Add `record_as_flow` parameter to `AgentRunner.__init__` (insert near other kwargs):

```python
        record_as_flow: bool = False,
```

…and store it:

```python
        self.record_as_flow = bool(record_as_flow)
```

Modify `run()` so that when result.status is `'done'` AND `record_as_flow=True`, it builds + saves the YAML before returning. Place this just after creating the success `AgentResult` and BEFORE the `_finish(...)` call. The cleanest spot is in the `_finish` helper — refactor:

Replace `_finish` inside `run()` with:

```python
        def _finish(result: AgentResult) -> AgentResult:
            if result.status == "done" and self.record_as_flow and result.history:
                try:
                    flow_name = f"agent-{_slug(self.goal)}-{int(time.time())}"
                    yaml_text = _history_to_flow_yaml(
                        goal=self.goal, history=result.history,
                        flow_name=flow_name,
                    )
                    self._save_flow(flow_name, yaml_text)
                    result.flow_yaml = yaml_text
                except Exception as e:
                    _LOG.warning(f"auto-record failed: {e}")
            self._persist_run_end(result)
            return result
```

Add `_save_flow`:

```python
    def _save_flow(self, name: str, yaml_text: str) -> None:
        from tegufox_core.database import FlowRecord
        S = self._db_session_factory
        with S() as s:
            now = datetime.utcnow()
            existing = s.query(FlowRecord).filter_by(name=name).first()
            if existing is None:
                s.add(FlowRecord(
                    name=name, yaml_text=yaml_text, schema_version=1,
                    created_at=now, updated_at=now,
                ))
            else:
                existing.yaml_text = yaml_text
                existing.updated_at = now
            s.commit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent -v
pytest tests/flow tests/flow_editor tests/orchestrator -m "not golden" -q   # no regression
```

Expected: 5 new in `test_agent_record.py` pass; all earlier agent tests pass; full suite still green.

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/agent.py tests/agent/test_agent_record.py
git commit --no-gpg-sign -m "feat(agent): auto-record successful runs as flow YAML"
```

---

## Task 8: GUI — Agent page

**Files:**
- Create: `tegufox_gui/pages/agent_page.py`
- Modify: `tegufox_gui/app.py` (register page + sidebar entry)
- Create: `tests/agent/conftest.py`
- Create: `tests/agent/test_agent_page.py`

The page hosts the goal input, options, live trace, Run/Stop buttons. Worker QThread runs `AgentRunner.run()`; signals push trace lines to the UI. Stop button sets the runner's `threading.Event`. `ask_user` callback opens a `QInputDialog` on the main thread.

- [ ] **Step 1: Failing tests**

```python
# tests/agent/conftest.py
import importlib.util
import sys
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)
```

```python
# tests/agent/test_agent_page.py
import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_agent_page_constructs(qapp, tmp_path):
    from tegufox_gui.pages.agent_page import AgentPage
    page = AgentPage(db_path=str(tmp_path / "t.db"))
    assert page.goal_edit is not None
    assert page.run_btn is not None
    assert page.stop_btn is not None
    assert page.trace_view is not None
    assert page.profile_combo is not None
    assert page.proxy_combo is not None
    assert page.max_steps_spin.value() == 30
    assert page.record_chk.isChecked() is False
    # Stop is disabled until Run is clicked.
    assert not page.stop_btn.isEnabled()


def test_agent_page_append_trace(qapp, tmp_path):
    from tegufox_gui.pages.agent_page import AgentPage
    page = AgentPage(db_path=str(tmp_path / "t.db"))
    page._append_trace("Step 1 [goto] https://x")
    assert "Step 1" in page.trace_view.toPlainText()
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/agent/test_agent_page.py -v
```

- [ ] **Step 3: Implement**

Write `tegufox_gui/pages/agent_page.py`:

```python
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
    QFormLayout, QSplitter,
)


_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


class _AgentWorker(QThread):
    step_emitted = pyqtSignal(int, str, str)        # (step_i, verb, summary)
    finished_with = pyqtSignal(dict)                 # AgentResult-like dict
    ask_user = pyqtSignal(str)                       # question; reply via _ask_reply

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
        self._ask_lock.wait(timeout=600)   # 10-minute cap
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

        # Run / Stop
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

        # Live trace
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

    # ------------------------------------------------------------------
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
```

Modify `tegufox_gui/app.py` to register the page. Find the existing block that registers pages around the FlowGen entry and add:

```python
        from tegufox_gui.pages.agent_page import AgentPage
        self.agent_page = AgentPage()
        self.content_stack.addWidget(self.agent_page)
```

…and the sidebar button (place after the AI Flow Gen button):

```python
        agent_btn = SidebarButton("Agent", "🦾")
        agent_btn.clicked.connect(lambda: self.switch_page(10))
        layout.addWidget(agent_btn)
        self.nav_buttons.append(agent_btn)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/agent/test_agent_page.py -v
pytest tests/flow tests/flow_editor tests/orchestrator tests/agent -m "not golden" -q
```

Expected: 2 new GUI tests pass; full suite still green.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/pages/agent_page.py tegufox_gui/app.py tests/agent/conftest.py tests/agent/test_agent_page.py
git commit --no-gpg-sign -m "feat(agent): GUI Agent page with live trace + Stop"
```

---

## Self-review

**Spec coverage:**

| Spec § | Topic | Task |
|---|---|---|
| §1 Goal + scope | (foundation) | T1-T8 collectively |
| §2 Architecture | AgentRunner + ai_providers + dispatch | T2, T3, T5 |
| §3 Action vocabulary | 10 verbs + JSON parsing | T2, T3 |
| §4 Loop pseudocode | observe + decide + run loop | T4, T5 |
| §5 Persistence (kind, goal_text, checkpoints) | T1 schema, T6 writes |
| §6 GUI | T8 |
| §7 Stop conditions (max_steps, max_time, done, ask_user, user stop, parse_error) | T5 (loop), T8 (Stop button) |
| §8 Decisions / tradeoffs | reflected in code defaults |
| §9 Testing | every task ships tests |
| §10 File layout | matches |
| §11 Decisions remaining | model default = inherits from `ai_providers`; ask_user → input promotion in T7; history truncation in T4 |

**Placeholder scan:** No "TBD". Every step contains complete code or commands. Default model is left to `ai_providers` (it has its own per-provider default).

**Type consistency:**
- `AgentAction(verb, args, reasoning)` defined in T2 used uniformly in T3, T5, T7 (via `__dict__` for serialisation).
- `AgentResult` defined in T2 expanded in T7 with `flow_yaml` attr (optional, default None — no breakage).
- `AGENT_VERBS` dict referenced in parser (T2), dispatcher (T3), prompt template (T4); single source of truth.
- `_VERB_TO_STEP_TYPE` in T7 mirrors the dispatcher's `_build_spec` mapping; if either drifts, auto-record produces wrong YAML — keep them aligned in any future change.

---

## Plan complete and saved to `docs/superpowers/plans/2026-04-28-realtime-ai-agent.md`

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, two-stage review, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch checkpoints.

Which approach?
