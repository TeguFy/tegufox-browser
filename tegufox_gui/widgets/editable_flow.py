"""Editor's mutable in-memory model — round-trips with tegufox_flow.dsl."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tegufox_flow.dsl import Flow, Step


_NESTED_KEYS = ("then", "else", "body")


@dataclass
class EditableStep:
    id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    when: Optional[str] = None
    on_error: Optional[Dict[str, Any]] = None


@dataclass
class EditableFlow:
    name: str
    description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    steps: List[EditableStep] = field(default_factory=list)
    editor_meta: Dict[str, Any] = field(default_factory=dict)


def _step_to_editable(s: Step) -> EditableStep:
    params: Dict[str, Any] = {}
    for k, v in s.params.items():
        if k in _NESTED_KEYS and isinstance(v, list):
            params[k] = [_step_to_editable(child) for child in v]
        else:
            params[k] = v
    return EditableStep(
        id=s.id, type=s.type, params=params,
        when=s.when,
        on_error=s.on_error.model_dump() if s.on_error else None,
    )


def _input_to_dict(name, decl) -> Dict[str, Any]:
    out = {"type": decl.type}
    if decl.required:
        out["required"] = True
    if decl.default is not None:
        out["default"] = decl.default
    return out


def from_pydantic(flow: Flow) -> EditableFlow:
    return EditableFlow(
        name=flow.name,
        description=flow.description or "",
        inputs={k: _input_to_dict(k, v) for k, v in flow.inputs.items()},
        defaults=flow.defaults.model_dump() if flow.defaults else {},
        steps=[_step_to_editable(s) for s in flow.steps],
        editor_meta=dict(flow.editor) if flow.editor else {},
    )


def _editable_to_dict(s: EditableStep) -> Dict[str, Any]:
    out: Dict[str, Any] = {"id": s.id, "type": s.type}
    if s.when is not None:
        out["when"] = s.when
    if s.on_error:
        out["on_error"] = dict(s.on_error)
    for k, v in s.params.items():
        if k in _NESTED_KEYS and isinstance(v, list):
            out[k] = [_editable_to_dict(child) for child in v]
        else:
            out[k] = v
    return out


def to_dict(ef: EditableFlow) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "schema_version": 1,
        "name": ef.name,
    }
    if ef.description:
        out["description"] = ef.description
    if ef.inputs:
        out["inputs"] = dict(ef.inputs)
    if ef.defaults:
        out["defaults"] = dict(ef.defaults)
    out["steps"] = [_editable_to_dict(s) for s in ef.steps]
    if ef.editor_meta:
        out["editor"] = dict(ef.editor_meta)
    return out


def validate_step_params(flow_dict: Dict[str, Any]) -> List[str]:
    """Walk every step (incl. nested then/else/body) and check required
    params per STEP_FORM schema. Returns a list of human-readable problems
    (empty list = OK). parse_flow only validates structure, not per-type
    params; this fills the gap so the editor's Save / Validate buttons
    catch missing selectors etc. before the runtime does.
    """
    from tegufox_gui.widgets.step_form_schema import STEP_FORM

    problems: List[str] = []

    def _check(steps: List[Dict[str, Any]], path: str = "") -> None:
        for s in steps:
            sid = s.get("id", "?")
            stype = s.get("type", "?")
            full = f"{path}/{sid}" if path else sid
            fields = STEP_FORM.get(stype, [])
            for f in fields:
                if not f.required:
                    continue
                val = s.get(f.name)
                if val is None or (isinstance(val, str) and not val.strip()) \
                        or (isinstance(val, list) and not val):
                    problems.append(
                        f"step {full!r} ({stype}): missing required param {f.name!r}"
                    )
            for nested_key in ("then", "else", "body"):
                nested = s.get(nested_key)
                if isinstance(nested, list):
                    _check(nested, full)

    _check(flow_dict.get("steps", []))
    return problems
