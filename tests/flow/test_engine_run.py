# tests/flow/test_engine_run.py
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowRecord, FlowRun
from tegufox_flow.engine import FlowEngine, RunResult
from tegufox_flow.dsl import parse_flow
from tegufox_flow.steps import register, STEP_REGISTRY


@pytest.fixture(autouse=True)
def _iso():
    snap = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snap)


@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    yield Session
    eng.dispose()


@pytest.fixture
def flow_record(db):
    s = db()
    f = FlowRecord(name="t", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f)
    s.commit()
    fid = f.id
    s.close()
    return fid


def test_run_succeeds_and_records_status(db, flow_record):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    assert isinstance(result, RunResult)
    assert result.status == "succeeded"
    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.status == "succeeded"
    assert row.profile_name == "p"


def test_run_failure_marks_failed(db, flow_record):
    @register("t.bad")
    def _(spec, ctx):
        raise RuntimeError("boom")

    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "steps": [{"id": "a", "type": "t.bad"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    assert result.status == "failed"
    assert "boom" in (result.error or "")


def test_run_validates_required_inputs(db, flow_record):
    flow = parse_flow({
        "schema_version": 1, "name": "t",
        "inputs": {"q": {"type": "string", "required": True}},
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    eng = FlowEngine(db_session_factory=db)
    with pytest.raises(ValueError) as e:
        eng.run(flow, inputs={}, profile_name="p")
    assert "q" in str(e.value)
