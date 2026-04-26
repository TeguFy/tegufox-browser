# tests/flow/test_dsl.py
import pytest
from tegufox_flow.dsl import Flow, Step, OnError, Input, parse_flow
from tegufox_flow.errors import ValidationError


def test_minimal_flow_validates():
    flow = parse_flow({
        "schema_version": 1,
        "name": "min",
        "steps": [{"id": "a", "type": "browser.goto", "url": "https://x"}],
    })
    assert flow.name == "min"
    assert flow.schema_version == 1
    assert len(flow.steps) == 1
    assert flow.steps[0].id == "a"
    assert flow.steps[0].type == "browser.goto"
    assert flow.steps[0].params == {"url": "https://x"}


def test_inputs_typed_and_default():
    flow = parse_flow({
        "schema_version": 1,
        "name": "in",
        "inputs": {
            "query": {"type": "string", "required": True},
            "n": {"type": "int", "default": 10},
        },
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    })
    assert flow.inputs["query"].type == "string"
    assert flow.inputs["query"].required is True
    assert flow.inputs["n"].default == 10


def test_defaults_on_error_inherited_into_step_when_missing():
    flow = parse_flow({
        "schema_version": 1,
        "name": "d",
        "defaults": {"on_error": {"action": "retry", "max_attempts": 5, "backoff_ms": 100}},
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
    })
    assert flow.defaults.on_error.action == "retry"
    assert flow.defaults.on_error.max_attempts == 5


def test_unknown_top_level_field_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({"schema_version": 1, "name": "x", "steps": [], "garbage": 1})
    assert "garbage" in str(e.value)


def test_duplicate_step_ids_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [
                {"id": "a", "type": "control.sleep", "ms": 1},
                {"id": "a", "type": "control.sleep", "ms": 2},
            ],
        })
    assert "duplicate" in str(e.value).lower()


def test_unknown_schema_version_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({"schema_version": 99, "name": "x", "steps": []})
    assert "schema_version" in str(e.value)


def test_step_id_must_be_slug():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [{"id": "has space", "type": "control.sleep", "ms": 1}],
        })
    assert "id" in str(e.value).lower()


def test_nested_steps_in_control_if_validate():
    flow = parse_flow({
        "schema_version": 1,
        "name": "x",
        "steps": [{
            "id": "branch",
            "type": "control.if",
            "when": "{{ true }}",
            "then": [{"id": "inner", "type": "control.sleep", "ms": 1}],
            "else": [{"id": "other", "type": "control.sleep", "ms": 2}],
        }],
    })
    assert flow.steps[0].params["then"][0].id == "inner"
    assert flow.steps[0].params["else"][0].id == "other"


def test_duplicate_id_across_nesting_rejected():
    with pytest.raises(ValidationError) as e:
        parse_flow({
            "schema_version": 1,
            "name": "x",
            "steps": [
                {"id": "outer", "type": "control.if", "when": "{{ true }}",
                 "then": [{"id": "outer", "type": "control.sleep", "ms": 1}]},
            ],
        })
    assert "duplicate" in str(e.value).lower()


def test_editor_namespace_preserved_verbatim():
    raw = {
        "schema_version": 1,
        "name": "x",
        "steps": [{"id": "a", "type": "control.sleep", "ms": 1}],
        "editor": {"positions": {"a": {"x": 100, "y": 200}}, "any": "value"},
    }
    flow = parse_flow(raw)
    assert flow.editor == raw["editor"]
