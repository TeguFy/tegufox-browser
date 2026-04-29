from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import (
    Base, FlowRecord, FlowRun, FlowCheckpoint, FlowKVState,
)


def _session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_flow_record_unique_name():
    s = _session()
    s.add(FlowRecord(name="a", yaml_text="x", schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    s.commit()
    s.add(FlowRecord(name="a", yaml_text="y", schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        s.commit()


def test_flow_run_status_default_running():
    s = _session()
    f = FlowRecord(name="a", yaml_text="x", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f)
    s.commit()
    r = FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running", started_at=datetime.utcnow())
    s.add(r)
    s.commit()
    assert s.query(FlowRun).first().status == "running"


def test_checkpoint_pk_is_run_seq():
    s = _session()
    s.add(FlowCheckpoint(run_id="r1", step_id="s", seq=1,
                         vars_json="{}", created_at=datetime.utcnow()))
    s.add(FlowCheckpoint(run_id="r1", step_id="t", seq=2,
                         vars_json="{}", created_at=datetime.utcnow()))
    s.commit()
    rows = s.query(FlowCheckpoint).order_by(FlowCheckpoint.seq).all()
    assert [r.step_id for r in rows] == ["s", "t"]


def test_kv_state_pk_is_flow_key():
    s = _session()
    s.add(FlowKVState(flow_name="f", key="k", value_json='"v"', updated_at=datetime.utcnow()))
    s.commit()
    row = s.query(FlowKVState).filter_by(flow_name="f", key="k").one()
    assert row.value_json == '"v"'
