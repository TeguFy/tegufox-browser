"""Realtime AI Agent — observe → decide → act loop.

Entry: AgentRunner.run() takes a goal + profile, drives a TegufoxSession
through one LLM call per turn, executes the chosen verb, and persists
each step as a flow_runs row + flow_checkpoints rows.

This module is split into 5 layers (top-down):
    1. Action types + JSON parser  (this task)
    2. Verb dispatch table          (Task 3)
    3. Observe / decide helpers     (Task 4)
    4. AgentRunner main loop        (Task 5)
    5. Auto-record to flow YAML     (Task 6/7)
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from tegufox_flow.steps import StepSpec, get_handler


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
    "scroll":     (),
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
    flow_yaml: Optional[str] = None


# ---------------------------------------------------------------------------
# 2. Verb dispatch — verb → step handler invocation
# ---------------------------------------------------------------------------


class DispatchError(RuntimeError):
    """Tried to dispatch an unknown / unsupported verb."""


def _build_spec(verb: str, args: Dict[str, Any]):
    """Translate an agent verb + args into a StepSpec the existing step
    handlers can consume. Each branch enforces the agent's defaults
    (force=True for click, human=False for type)."""
    if verb == "goto":
        params = {"url": args["url"]}
        if "wait_until" in args:
            params["wait_until"] = args["wait_until"]
        return StepSpec(id="agent_goto", type="browser.goto", params=params)

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

    spec = _build_spec(action.verb, action.args)
    handler = get_handler(spec.type)
    handler(spec, ctx)

    out: Dict[str, Any] = {"ok": True}
    if action.verb == "read_text":
        try:
            out["value"] = ctx.vars.get("_agent_read")
        except Exception:
            out["value"] = None
    return out


# ---------------------------------------------------------------------------
# 3. Observe + decide
# ---------------------------------------------------------------------------

# Module-level alias so tests can patch it.
from tegufox_flow.steps.ai_providers import ask_llm  # noqa: F401

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


# ---------------------------------------------------------------------------
# 4. AgentRunner — main loop
# ---------------------------------------------------------------------------

import logging
import threading
import time
import uuid

# Import as module-level so tests can monkeypatch.
from tegufox_automation import TegufoxSession            # type: ignore  # noqa: F401


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
        db_path: str = "data/tegufox.db",
        record_as_flow: bool = False,
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
        self.record_as_flow = bool(record_as_flow)
        self.run_id = str(uuid.uuid4())
        self._db_session_factory = self._make_session_factory()

    def _make_session_factory(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from pathlib import Path
        from tegufox_core.database import Base, ensure_schema
        eng = create_engine(f"sqlite:///{Path(self.db_path).resolve()}")
        Base.metadata.create_all(eng)
        ensure_schema(eng)
        return sessionmaker(bind=eng)

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

    def _persist_run_end(self, result) -> None:
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
            if result.status != "done":
                row.error_text = result.reason
            s.commit()

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

    def run(self) -> AgentResult:
        self._persist_run_start()
        history: List[Dict[str, Any]] = []
        started = time.monotonic()
        seq = 0

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
            input_name = f"ask_{_slug(args.get('question', ''))}"
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
            continue

        if pending_input is not None:
            for k, v in list(args.items()):
                if isinstance(v, str) and v == \
                        inputs[pending_input]["default"]:
                    args[k] = "{{ inputs." + pending_input + " }}"
            pending_input = None

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
