# tests/flow/test_steps_state.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.state  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.kv = MagicMock()
    c.eval.side_effect = lambda e: eval(e, {}, {})
    c.render.side_effect = lambda s: s
    return c


def test_save_calls_kv(ctx):
    handler = get_handler("state.save")
    handler(StepSpec(id="s", type="state.save",
                     params={"key": "k", "value": "[1,2]"}), ctx)
    ctx.kv.save.assert_called_once_with("k", [1, 2])


def test_load_with_default(ctx):
    ctx.kv.load.return_value = "default"
    handler = get_handler("state.load")
    handler(StepSpec(id="l", type="state.load",
                     params={"key": "k", "set": "out", "default": "default"}), ctx)
    ctx.kv.load.assert_called_once_with("k", default="default")
    ctx.set_var.assert_called_once_with("out", "default")


def test_delete_calls_kv(ctx):
    handler = get_handler("state.delete")
    handler(StepSpec(id="d", type="state.delete", params={"key": "k"}), ctx)
    ctx.kv.delete.assert_called_once_with("k")
