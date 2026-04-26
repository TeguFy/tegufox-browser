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
