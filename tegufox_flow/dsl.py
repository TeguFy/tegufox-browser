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
    def _check_goto(self) -> OnError:
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
        raw = {k: v for k, v in (self.__pydantic_extra__ or {}).items() if v is not None}
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
