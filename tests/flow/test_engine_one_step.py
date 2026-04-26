# tests/flow/test_engine_one_step.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.engine import FlowEngine
from tegufox_flow.dsl import OnError
from tegufox_flow.steps import StepSpec, register, STEP_REGISTRY
from tegufox_flow.errors import StepError, GotoSignal


@pytest.fixture(autouse=True)
def _registry_isolation():
    snapshot = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snapshot)


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {"v": 1}
    c.run_id = "r"
    c.checkpoints = MagicMock()
    return c


def test_step_runs_and_checkpoints(ctx):
    calls = []

    @register("t.ok")
    def _h(spec, c):
        calls.append(spec.id)

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(StepSpec(id="a", type="t.ok"), ctx)
    assert calls == ["a"]
    ctx.checkpoints.save.assert_called_once_with("r", "a", {"v": 1})


def test_when_false_skips(ctx):
    @register("t.never")
    def _h(spec, c):
        raise AssertionError("should not run")

    ctx.eval.return_value = False
    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(StepSpec(id="a", type="t.never", when="false"), ctx)
    ctx.checkpoints.save.assert_not_called()


def test_retry_then_succeed(ctx):
    attempts = {"n": 0}

    @register("t.flaky")
    def _h(spec, c):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(
        StepSpec(id="a", type="t.flaky",
                 on_error=OnError(action="retry", max_attempts=5, backoff_ms=0)),
        ctx,
    )
    assert attempts["n"] == 3


def test_retry_exhausted_raises(ctx):
    @register("t.always")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    with pytest.raises(StepError):
        eng._execute_one(
            StepSpec(id="a", type="t.always",
                     on_error=OnError(action="retry", max_attempts=2, backoff_ms=0)),
            ctx,
        )


def test_skip_swallows_error(ctx):
    @register("t.bad")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    eng._execute_one(
        StepSpec(id="a", type="t.bad", on_error=OnError(action="skip")),
        ctx,
    )  # no raise


def test_goto_raises_signal(ctx):
    @register("t.fail")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="abort")
    with pytest.raises(GotoSignal) as e:
        eng._execute_one(
            StepSpec(id="a", type="t.fail",
                     on_error=OnError(action="goto", goto_step="cleanup")),
            ctx,
        )
    assert e.value.target == "cleanup"


def test_default_on_error_inherited(ctx):
    @register("t.fail2")
    def _h(spec, c):
        raise RuntimeError("nope")

    eng = FlowEngine.__new__(FlowEngine)
    eng._default_on_error = OnError(action="skip")
    eng._execute_one(StepSpec(id="a", type="t.fail2"), ctx)
