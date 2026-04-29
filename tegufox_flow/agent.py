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
