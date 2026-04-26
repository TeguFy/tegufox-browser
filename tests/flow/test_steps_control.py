import time
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
from tegufox_flow.errors import BreakSignal, ContinueSignal, GotoSignal
import tegufox_flow.steps.control  # noqa: F401  -- registers handlers


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.eval.side_effect = lambda expr: eval(expr, {}, {})  # cheap eval for tests
    c.render.side_effect = lambda s: s
    return c


# ---------- Task 9: set, sleep, if ----------

def test_control_set_assigns_var(ctx):
    handler = get_handler("control.set")
    spec = StepSpec(id="s", type="control.set", params={"var": "x", "value": "1+2"})
    handler(spec, ctx)
    ctx.set_var.assert_called_once_with("x", 3)


def test_control_sleep_sleeps(monkeypatch, ctx):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    handler = get_handler("control.sleep")
    handler(StepSpec(id="s", type="control.sleep", params={"ms": 250}), ctx)
    assert slept == [0.25]


def test_control_if_runs_then_when_true(ctx):
    ctx.eval.side_effect = lambda expr: True
    inner_called = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: inner_called.append(steps))
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    spec = StepSpec(
        id="c", type="control.if",
        params={"when": "true", "then": ["A"], "else": ["B"]},
    )
    handler(spec, ctx)
    assert inner_called == [["A"]]


def test_control_if_runs_else_when_false(ctx):
    ctx.eval.side_effect = lambda expr: False
    inner_called = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: inner_called.append(steps))
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    spec = StepSpec(
        id="c", type="control.if",
        params={"when": "false", "then": ["A"], "else": ["B"]},
    )
    handler(spec, ctx)
    assert inner_called == [["B"]]


def test_control_if_no_else_when_false_does_nothing(ctx):
    ctx.eval.side_effect = lambda expr: False
    fake_engine = MagicMock()
    ctx.engine = fake_engine
    handler = get_handler("control.if")
    handler(
        StepSpec(id="c", type="control.if", params={"when": "false", "then": ["A"]}),
        ctx,
    )
    fake_engine.execute_steps.assert_not_called()


# ---------- Task 10: loops, signals, goto ----------

def test_for_each_iterates_and_sets_var(ctx):
    seen = []
    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=lambda steps, c: seen.append(c.vars["item"]))
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2, 3]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2,3]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert seen == [1, 2, 3]


def test_for_each_break_exits_early(ctx):
    iterations = []

    def body(steps, c):
        iterations.append(c.vars["item"])
        if c.vars["item"] == 2:
            raise BreakSignal("break")

    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=body)
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2, 3]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2,3]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert iterations == [1, 2]


def test_for_each_continue_skips_remainder(ctx):
    iterations = []

    def body(steps, c):
        iterations.append(c.vars["item"])
        raise ContinueSignal("continue")

    fake_engine = MagicMock()
    fake_engine.execute_steps = MagicMock(side_effect=body)
    ctx.engine = fake_engine
    ctx.eval.side_effect = lambda expr: [1, 2]
    handler = get_handler("control.for_each")
    spec = StepSpec(id="loop", type="control.for_each",
                    params={"items": "[1,2]", "var": "item",
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert iterations == [1, 2]


def test_while_respects_max_iterations(ctx):
    ctx.eval.side_effect = lambda expr: True  # always true
    fake_engine = MagicMock()
    ctx.engine = fake_engine
    handler = get_handler("control.while")
    spec = StepSpec(id="w", type="control.while",
                    params={"when": "true", "max_iterations": 3,
                            "body": [StepSpec(id="b", type="x", params={})]})
    handler(spec, ctx)
    assert fake_engine.execute_steps.call_count == 3


def test_break_outside_loop_propagates(ctx):
    handler = get_handler("control.break")
    with pytest.raises(BreakSignal):
        handler(StepSpec(id="b", type="control.break", params={}), ctx)


def test_continue_outside_loop_propagates(ctx):
    handler = get_handler("control.continue")
    with pytest.raises(ContinueSignal):
        handler(StepSpec(id="c", type="control.continue", params={}), ctx)


def test_goto_raises_signal(ctx):
    handler = get_handler("control.goto")
    with pytest.raises(GotoSignal) as e:
        handler(StepSpec(id="g", type="control.goto", params={"step_id": "cleanup"}), ctx)
    assert e.value.target == "cleanup"
