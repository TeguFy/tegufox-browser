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


# Side-effect imports: each submodule registers its handlers on import.
# Tests do this explicitly per-file; production callers (runtime, GUI, REST)
# only import tegufox_flow.engine which transitively imports this module.
from . import browser, control, extract, io, state  # noqa: F401, E402
