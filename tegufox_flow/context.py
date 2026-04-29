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
    _human_mouse: Any = None        # HumanMouse, lazily initialised
    _human_keyboard: Any = None     # HumanKeyboard, lazily initialised
    _original_page: Any = None      # set on engine.run; switch_to_main restores it
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
