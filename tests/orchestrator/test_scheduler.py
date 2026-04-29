"""Unit tests for the flow scheduler (CRUD + cron resolution).

We don't spin up the daemon thread — that's e2e. We exercise the pure
DB CRUD functions and the croniter integration.
"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def db(tmp_path):
    from sqlalchemy import create_engine
    from tegufox_core.database import Base, ensure_schema
    db = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return str(db)


def test_add_cron_schedule_sets_next_run(db):
    from tegufox_flow.scheduler import add_schedule, list_schedules
    sid = add_schedule(db, name="daily", flow_name="x",
                       profile_name="p", cron_expression="0 3 * * *")
    rows = list_schedules(db)
    assert any(r["id"] == sid for r in rows)
    sched = next(r for r in rows if r["id"] == sid)
    assert sched["cron_expression"] == "0 3 * * *"
    assert sched["next_run_at"] is not None


def test_add_one_shot_schedule(db):
    from tegufox_flow.scheduler import add_schedule, list_schedules
    when = datetime.utcnow() + timedelta(hours=1)
    sid = add_schedule(db, name="once", flow_name="x",
                       profile_name="p", run_at=when)
    rows = list_schedules(db)
    sched = next(r for r in rows if r["id"] == sid)
    assert sched["run_at"] is not None
    assert sched["cron_expression"] is None


def test_add_rejects_both_cron_and_run_at(db):
    from tegufox_flow.scheduler import add_schedule
    with pytest.raises(ValueError):
        add_schedule(db, name="x", flow_name="f", profile_name="p",
                     cron_expression="* * * * *",
                     run_at=datetime.utcnow())


def test_add_rejects_neither(db):
    from tegufox_flow.scheduler import add_schedule
    with pytest.raises(ValueError):
        add_schedule(db, name="x", flow_name="f", profile_name="p")


def test_set_enabled_toggles_and_resets_next_run(db):
    from tegufox_flow.scheduler import add_schedule, list_schedules, set_enabled
    sid = add_schedule(db, name="x", flow_name="f", profile_name="p",
                       cron_expression="* * * * *", enabled=True)
    set_enabled(db, sid, False)
    rows = list_schedules(db)
    assert next(r for r in rows if r["id"] == sid)["enabled"] is False
    set_enabled(db, sid, True)
    sched = next(r for r in list_schedules(db) if r["id"] == sid)
    assert sched["enabled"] is True
    assert sched["next_run_at"] is not None


def test_delete_schedule(db):
    from tegufox_flow.scheduler import add_schedule, delete_schedule, list_schedules
    sid = add_schedule(db, name="x", flow_name="f", profile_name="p",
                       cron_expression="* * * * *")
    delete_schedule(db, sid)
    assert all(r["id"] != sid for r in list_schedules(db))


def test_next_cron_is_in_future():
    from tegufox_flow.scheduler import _next_cron
    base = datetime(2026, 4, 28, 1, 30)
    nxt = _next_cron("0 3 * * *", base)
    assert nxt > base
    assert nxt.hour == 3 and nxt.minute == 0
