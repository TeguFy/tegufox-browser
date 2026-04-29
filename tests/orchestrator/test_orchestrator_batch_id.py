# tests/orchestrator/test_orchestrator_batch_id.py
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowRecord, FlowRun, FlowBatch
from tegufox_flow.engine import FlowEngine
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


def test_run_writes_batch_id_when_provided(db):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "x",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    # Pre-create the batch row so the FK is satisfied.
    s = db()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit(); fid = f.id
    s.add(FlowBatch(batch_id="b1", flow_id=fid, inputs_json="{}",
                    status="running", total=1,
                    started_at=datetime.utcnow()))
    s.commit(); s.close()

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p", batch_id="b1")
    assert result.status == "succeeded"

    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.batch_id == "b1"


def test_run_default_batch_id_is_none(db):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "x",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.batch_id is None
