import pytest

import tegufox_flow.steps.browser  # noqa
import tegufox_flow.steps.control  # noqa

from tegufox_flow.dsl import parse_flow
from tegufox_gui.widgets.editable_flow import (
    EditableFlow, EditableStep, from_pydantic, to_dict,
)


def test_round_trip_minimal():
    src = {
        "schema_version": 1,
        "name": "minimal",
        "steps": [{"id": "a", "type": "browser.goto", "url": "https://x"}],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    flow2 = parse_flow(out)
    assert flow2.name == "minimal"
    assert flow2.steps[0].params["url"] == "https://x"


def test_round_trip_nested_if():
    src = {
        "schema_version": 1,
        "name": "x",
        "steps": [{
            "id": "br",
            "type": "control.if",
            "when": "{{ true }}",
            "then": [{"id": "a", "type": "control.sleep", "ms": 1}],
            "else": [{"id": "b", "type": "control.sleep", "ms": 2}],
        }],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    flow2 = parse_flow(out)
    assert flow2.steps[0].type == "control.if"
    then_body = flow2.steps[0].params["then"]
    assert then_body[0].id == "a"


def test_editor_meta_passes_through():
    src = {
        "schema_version": 1,
        "name": "x",
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
        "editor": {"positions": {"a": {"x": 1, "y": 2}}, "anything": "preserved"},
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    assert ef.editor_meta == src["editor"]
    out = to_dict(ef)
    assert out["editor"] == src["editor"]


def test_inputs_pass_through():
    src = {
        "schema_version": 1,
        "name": "x",
        "inputs": {"q": {"type": "string", "required": True}},
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    }
    flow = parse_flow(src)
    ef = from_pydantic(flow)
    out = to_dict(ef)
    parse_flow(out)  # still valid


def test_validate_step_params_catches_missing_required():
    from tegufox_gui.widgets.editable_flow import validate_step_params

    flow_dict = {
        "schema_version": 1,
        "name": "x",
        "steps": [
            {"id": "click_1", "type": "browser.click", "selector": ""},
            {"id": "type_1", "type": "browser.type", "selector": "#x"},
        ],
    }
    problems = validate_step_params(flow_dict)
    assert any("click_1" in p and "selector" in p for p in problems)
    assert any("type_1" in p and "text" in p for p in problems)


def test_validate_step_params_clean_when_filled():
    from tegufox_gui.widgets.editable_flow import validate_step_params

    flow_dict = {
        "schema_version": 1,
        "name": "x",
        "steps": [
            {"id": "g", "type": "browser.goto", "url": "https://x"},
            {"id": "c", "type": "browser.click", "selector": "#a"},
        ],
    }
    assert validate_step_params(flow_dict) == []


def test_validate_step_params_recurses_nested():
    from tegufox_gui.widgets.editable_flow import validate_step_params

    flow_dict = {
        "schema_version": 1,
        "name": "x",
        "steps": [{
            "id": "if_1", "type": "control.if", "when": "{{ true }}",
            "then": [{"id": "inner", "type": "browser.click", "selector": ""}],
        }],
    }
    problems = validate_step_params(flow_dict)
    assert any("inner" in p and "selector" in p for p in problems)
