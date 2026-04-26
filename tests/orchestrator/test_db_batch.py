# tests/orchestrator/test_db_batch.py
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowBatch, FlowRun, FlowRecord


def _session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_flow_batch_table_exists():
    s = _session()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    b = FlowBatch(batch_id="b1", flow_id=f.id,
                  inputs_json="{}", status="running",
                  total=2, started_at=datetime.utcnow())
    s.add(b); s.commit()
    assert s.query(FlowBatch).first().batch_id == "b1"


def test_flow_run_has_optional_batch_id():
    s = _session()
    r = FlowRun(run_id="r1", flow_id=1, profile_name="p", inputs_json="{}",
                status="running", started_at=datetime.utcnow(), batch_id=None)
    s.add(r); s.commit()
    assert s.query(FlowRun).one().batch_id is None


def test_flow_run_batch_id_persists():
    s = _session()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    s.add(FlowBatch(batch_id="b1", flow_id=f.id,
                    inputs_json="{}", status="running",
                    total=1, started_at=datetime.utcnow()))
    s.commit()
    s.add(FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                  inputs_json="{}", status="running",
                  started_at=datetime.utcnow(), batch_id="b1"))
    s.commit()
    assert s.query(FlowRun).filter_by(run_id="r1").one().batch_id == "b1"
