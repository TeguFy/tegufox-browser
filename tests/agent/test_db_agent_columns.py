from datetime import datetime
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import (
    Base, ensure_schema, FlowRun, FlowRecord,
)


def _eng_in_memory():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return eng


def test_flow_run_has_kind_column():
    eng = _eng_in_memory()
    cols = {c["name"] for c in inspect(eng).get_columns("flow_runs")}
    assert "kind" in cols
    assert "goal_text" in cols


def test_flow_run_kind_default_is_flow():
    eng = _eng_in_memory()
    s = sessionmaker(bind=eng)()
    f = FlowRecord(name="x", yaml_text="", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    r = FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running", started_at=datetime.utcnow())
    s.add(r); s.commit()
    fetched = s.query(FlowRun).one()
    assert fetched.kind == "flow"
    assert fetched.goal_text is None


def test_flow_run_kind_agent_persists():
    eng = _eng_in_memory()
    s = sessionmaker(bind=eng)()
    f = FlowRecord(name="x", yaml_text="", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    r = FlowRun(run_id="r2", flow_id=f.id, profile_name="p",
                inputs_json="{}", status="running",
                started_at=datetime.utcnow(),
                kind="agent", goal_text="login google")
    s.add(r); s.commit()
    fetched = s.query(FlowRun).filter_by(run_id="r2").one()
    assert fetched.kind == "agent"
    assert fetched.goal_text == "login google"


def test_ensure_schema_adds_kind_to_legacy_db():
    """Existing DB without `kind` column should get it via ensure_schema."""
    from sqlalchemy import text
    eng = create_engine("sqlite:///:memory:")
    # Create a flow_runs table missing the new columns (simulate legacy).
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        # SQLite requires dropping indexes before dropping columns
        conn.execute(text("DROP INDEX IF EXISTS ix_flow_runs_kind"))
        conn.execute(text("ALTER TABLE flow_runs DROP COLUMN kind"))
        conn.execute(text("ALTER TABLE flow_runs DROP COLUMN goal_text"))
    ensure_schema(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("flow_runs")}
    assert "kind" in cols
    assert "goal_text" in cols
