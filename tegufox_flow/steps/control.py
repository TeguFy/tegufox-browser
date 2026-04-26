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


@register("control.for_each", required=("items", "var", "body"))
def _for_each(spec: StepSpec, ctx) -> None:
    items = ctx.eval(spec.params["items"]) if isinstance(spec.params["items"], str) else spec.params["items"]
    var = spec.params["var"]
    index_var = spec.params.get("index_var")
    body = spec.params["body"]

    saved = ctx.vars.get(var, _MISSING)
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
