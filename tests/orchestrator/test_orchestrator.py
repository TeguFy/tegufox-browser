# tests/orchestrator/test_orchestrator.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowBatch, FlowRecord, FlowRun
from tegufox_flow.engine import RunResult
from tegufox_flow.orchestrator import Orchestrator, BatchResult


def _make_db(tmp_path):
    db = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(eng)
    return db


def _ok_result(profile, run_id):
    return RunResult(run_id=run_id, status="succeeded",
                     last_step_id="a", error=None, inputs={})


def _fail_result(profile, run_id):
    return RunResult(run_id=run_id, status="failed",
                     last_step_id="a", error="boom", inputs={})


def test_orchestrator_runs_each_profile(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    calls = []
    def fake(args):
        flow_path, profile, inputs, db_path, batch_id = args
        calls.append(profile)
        return RunResult(run_id=f"r-{profile}", status="succeeded",
                         last_step_id="a", error=None, inputs=inputs)

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1, executor_cls=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor)
        result = orch.run(profiles=["a", "b", "c"], inputs={})

    assert sorted(calls) == ["a", "b", "c"]
    assert result.total == 3
    assert result.succeeded == 3
    assert result.failed == 0


def test_orchestrator_writes_batch_row(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    with patch("tegufox_flow.orchestrator._run_one_subprocess",
               side_effect=lambda args: _ok_result(args[1], f"r-{args[1]}")):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1, executor_cls=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor)
        result = orch.run(profiles=["x"], inputs={})

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    rows = s.query(FlowBatch).all()
    assert len(rows) == 1
    assert rows[0].batch_id == result.batch_id
    assert rows[0].status == "completed"
    assert rows[0].succeeded == 1
    assert rows[0].failed == 0
    assert rows[0].total == 1


def test_orchestrator_aggregates_failures(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    def fake(args):
        _, profile, _, _, _ = args
        return (_ok_result(profile, f"r-{profile}") if profile == "a"
                else _fail_result(profile, f"r-{profile}"))

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1, executor_cls=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor)
        result = orch.run(profiles=["a", "b", "c"], inputs={})
    assert result.succeeded == 1
    assert result.failed == 2


def test_per_profile_inputs_override(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\n"
        "inputs:\n  q:\n    type: string\n    required: true\n"
        "steps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    seen = {}
    def fake(args):
        _, profile, inputs, _, _ = args
        seen[profile] = inputs
        return _ok_result(profile, f"r-{profile}")

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1, executor_cls=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor)
        orch.run(profiles=["a", "b"], inputs={"q": "default"},
                 per_profile_inputs={"a": {"q": "alice"}})

    assert seen["a"]["q"] == "alice"
    assert seen["b"]["q"] == "default"


def test_validates_required_inputs_before_dispatch(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\n"
        "inputs:\n  q:\n    type: string\n    required: true\n"
        "steps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    with patch("tegufox_flow.orchestrator._run_one_subprocess",
               side_effect=AssertionError("should not be called")):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1, executor_cls=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor)
        with pytest.raises(ValueError) as e:
            orch.run(profiles=["a"], inputs={})
        assert "q" in str(e.value)
