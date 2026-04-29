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
