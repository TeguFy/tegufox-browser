import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowCheckpoint, FlowKVState
from tegufox_flow.checkpoints import CheckpointStore, KVStore


@pytest.fixture
def session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    s = Session()
    yield s
    s.close()


def test_checkpoint_save_increments_seq(session):
    store = CheckpointStore(session)
    store.save("run-1", "step-a", {"x": 1})
    store.save("run-1", "step-b", {"x": 2})
    rows = session.query(FlowCheckpoint).filter_by(run_id="run-1").order_by(FlowCheckpoint.seq).all()
    assert [(r.seq, r.step_id) for r in rows] == [(1, "step-a"), (2, "step-b")]
    assert json.loads(rows[1].vars_json) == {"x": 2}


def test_checkpoint_last_returns_latest(session):
    store = CheckpointStore(session)
    store.save("run-1", "a", {"i": 0})
    store.save("run-1", "b", {"i": 1})
    store.save("run-1", "c", {"i": 2})
    cp = store.last("run-1")
    assert cp is not None
    assert cp.step_id == "c"
    assert cp.vars == {"i": 2}


def test_checkpoint_last_none_for_unknown_run(session):
    store = CheckpointStore(session)
    assert store.last("ghost") is None


def test_kv_save_then_load(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", {"a": 1})
    assert kv.load("k") == {"a": 1}


def test_kv_load_default_when_missing(session):
    kv = KVStore(session, flow_name="f")
    assert kv.load("nope", default="x") == "x"


def test_kv_save_overwrites_and_updates_timestamp(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", "v1")
    t1 = session.query(FlowKVState).one().updated_at
    kv.save("k", "v2")
    rows = session.query(FlowKVState).filter_by(flow_name="f", key="k").all()
    assert len(rows) == 1
    assert rows[0].value_json == '"v2"'
    assert rows[0].updated_at >= t1


def test_kv_delete(session):
    kv = KVStore(session, flow_name="f")
    kv.save("k", 1)
    kv.delete("k")
    assert kv.load("k", default=None) is None


def test_kv_isolated_per_flow(session):
    a = KVStore(session, flow_name="a")
    b = KVStore(session, flow_name="b")
    a.save("k", 1)
    b.save("k", 2)
    assert a.load("k") == 1
    assert b.load("k") == 2
