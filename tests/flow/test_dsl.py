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


import io
from pathlib import Path
from tegufox_flow.dsl import load_flow, dump_flow


def test_load_flow_from_path(tmp_path: Path):
    f = tmp_path / "x.yaml"
    f.write_text(
        "schema_version: 1\n"
        "name: x\n"
        "steps:\n"
        "  - id: a\n"
        "    type: control.sleep\n"
        "    ms: 1\n"
    )
    flow = load_flow(f)
    assert flow.name == "x"


def test_dump_preserves_step_order_and_comments(tmp_path: Path):
    src = (
        "schema_version: 1\n"
        "name: x\n"
        "# top comment\n"
        "steps:\n"
        "  - id: first\n"
        "    type: control.sleep\n"
        "    ms: 1  # inline\n"
        "  - id: second\n"
        "    type: control.sleep\n"
        "    ms: 2\n"
    )
    f = tmp_path / "src.yaml"
    f.write_text(src)
    out = tmp_path / "out.yaml"
    raw = load_flow(f, raw=True)
    dump_flow(raw, out)
    text = out.read_text()
    assert "# top comment" in text
    assert "# inline" in text
    assert text.index("first") < text.index("second")


def test_load_flow_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_flow(tmp_path / "nope.yaml")
