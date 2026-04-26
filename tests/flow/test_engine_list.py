# tests/flow/test_engine_list.py
import pytest
from unittest.mock import MagicMock
from tegufox_flow.engine import FlowEngine
from tegufox_flow.dsl import OnError
from tegufox_flow.steps import StepSpec, register, STEP_REGISTRY
from tegufox_flow.errors import GotoSignal, BreakSignal


@pytest.fixture(autouse=True)
def _iso():
    snap = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snap)


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.eval.return_value = True
    c.run_id = "r"
    return c


def test_executes_steps_in_order(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    eng = FlowEngine()
    ctx.engine = eng
    steps = [StepSpec(id=x, type="t.mark") for x in ("a", "b", "c")]
    eng.execute_steps(steps, ctx)
    assert seen == ["a", "b", "c"]


def test_resume_from_skips_earlier_steps(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    eng = FlowEngine()
    ctx.engine = eng
    steps = [StepSpec(id=x, type="t.mark") for x in ("a", "b", "c")]
    eng.execute_steps(steps, ctx, resume_from="b")
    assert seen == ["b", "c"]


def test_goto_jumps_to_target_at_same_scope(ctx):
    seen = []

    @register("t.mark")
    def h(spec, c):
        seen.append(spec.id)

    @register("t.gotoer")
    def g(spec, c):
        raise GotoSignal("c")

    eng = FlowEngine()
    ctx.engine = eng
    steps = [
        StepSpec(id="a", type="t.mark"),
        StepSpec(id="g", type="t.gotoer"),
        StepSpec(id="b", type="t.mark"),
        StepSpec(id="c", type="t.mark"),
    ]
    eng.execute_steps(steps, ctx)
    assert seen == ["a", "c"]


def test_goto_to_unknown_target_raises(ctx):
    @register("t.gotoer")
    def g(spec, c):
        raise GotoSignal("ghost")

    eng = FlowEngine()
    ctx.engine = eng
    with pytest.raises(GotoSignal):  # propagates to outer scope
        eng.execute_steps([StepSpec(id="g", type="t.gotoer")], ctx)


def test_break_propagates_out_of_steps(ctx):
    @register("t.brk")
    def b(spec, c):
        raise BreakSignal("b")

    eng = FlowEngine()
    ctx.engine = eng
    with pytest.raises(BreakSignal):
        eng.execute_steps([StepSpec(id="x", type="t.brk")], ctx)
