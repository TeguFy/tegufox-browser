"""Control-flow step handlers.

This module's import side-effect registers handlers in STEP_REGISTRY.
Engine sets ctx.engine before invoking nested steps so handlers can call
ctx.engine.execute_steps(...) for then/else/body lists.
"""

from __future__ import annotations
import time
from typing import List

from . import register, StepSpec
from ..errors import BreakSignal, ContinueSignal, GotoSignal


_MISSING = object()


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
