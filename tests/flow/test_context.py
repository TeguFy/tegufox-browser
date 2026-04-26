import pytest
from unittest.mock import MagicMock

from tegufox_flow.context import FlowContext
from tegufox_flow.expressions import ExpressionEngine
from tegufox_flow.checkpoints import CheckpointStore, KVStore


@pytest.fixture
def ctx():
    return FlowContext(
        session=MagicMock(),
        page=MagicMock(),
        flow_name="f",
        run_id="r",
        inputs={"q": "laptop"},
        vars={"i": 0},
        kv=MagicMock(spec=KVStore),
        checkpoints=MagicMock(spec=CheckpointStore),
        expressions=ExpressionEngine(),
        env_allowlist={"HOME"},
    )


def test_render_uses_inputs_namespace(ctx):
    assert ctx.render("q={{ inputs.q }}") == "q=laptop"


def test_render_uses_vars_namespace(ctx):
    assert ctx.render("i={{ vars.i }}") == "i=0"


def test_eval_returns_native(ctx):
    assert ctx.eval("vars.i + 1") == 1


def test_set_var_updates_vars(ctx):
    ctx.set_var("i", 7)
    assert ctx.vars["i"] == 7


def test_set_var_rejects_inputs_collision(ctx):
    with pytest.raises(ValueError):
        ctx.set_var("inputs", "x")


def test_state_lookup_hits_kv(ctx):
    ctx.kv.load.return_value = "stored"
    assert ctx.eval("state.foo") == "stored"
    ctx.kv.load.assert_called_once_with("foo")


def test_env_allowlist_enforced(ctx, monkeypatch):
    monkeypatch.setenv("HOME", "/tmp")
    monkeypatch.setenv("SECRET", "x")
    assert ctx.eval("env.HOME") == "/tmp"
    with pytest.raises(Exception):
        ctx.eval("env.SECRET")


def test_snapshot_is_json_serialisable(ctx):
    import json
    ctx.set_var("nested", {"a": [1, 2, 3]})
    json.dumps(ctx.snapshot())  # no error


def test_logger_namespaced(ctx):
    assert ctx.logger.name.startswith("tegufox_flow")
