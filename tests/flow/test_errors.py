import pytest
from tegufox_flow.errors import (
    ValidationError, StepError, FlowError,
    BreakSignal, ContinueSignal, GotoSignal,
)


def test_step_error_carries_context():
    cause = RuntimeError("nope")
    err = StepError(step_id="search", step_type="browser.click", cause=cause)
    assert err.step_id == "search"
    assert err.step_type == "browser.click"
    assert err.cause is cause
    assert "search" in str(err)
    assert "browser.click" in str(err)


def test_flow_error_wraps_step_error():
    se = StepError(step_id="x", step_type="browser.goto", cause=ValueError("bad url"))
    fe = FlowError(run_id="run-1", flow_name="amazon-search", cause=se)
    assert fe.run_id == "run-1"
    assert fe.flow_name == "amazon-search"
    assert fe.cause is se


def test_validation_error_collects_problems():
    err = ValidationError(["step 'x' missing required field 'url'", "duplicate id 'y'"])
    assert err.problems == [
        "step 'x' missing required field 'url'",
        "duplicate id 'y'",
    ]
    assert "missing required field 'url'" in str(err)


def test_signals_are_distinct():
    assert not issubclass(BreakSignal, ContinueSignal)
    assert not issubclass(ContinueSignal, BreakSignal)
    g = GotoSignal(target="cleanup")
    assert g.target == "cleanup"
