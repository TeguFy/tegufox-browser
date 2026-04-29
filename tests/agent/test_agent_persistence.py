import json
from unittest.mock import MagicMock, patch
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import (
    Base, ensure_schema, FlowRun, FlowRecord, FlowCheckpoint,
)
from tegufox_flow.agent import AgentRunner


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return str(db_path)


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.page.url = "https://x"
    s.page.title.return_value = "x"
    s.page.content.return_value = ""
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


def test_runner_persists_run_row(db, fake_session):
    actions = iter([
        '{"verb": "done", "args": {"reason": "trivial"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)):
        runner = AgentRunner(goal="hello world", profile_name="p",
                             db_path=db, max_steps=3, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    rows = s.query(FlowRun).filter_by(run_id=result.run_id).all()
    assert len(rows) == 1
    r = rows[0]
    assert r.kind == "agent"
    assert r.goal_text == "hello world"
    assert r.profile_name == "p"
    assert r.status == "done"


def test_runner_persists_checkpoints_per_step(db, fake_session):
    actions = iter([
        '{"verb": "scroll", "args": {"direction": "down"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p", db_path=db,
                             max_steps=5, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    cps = (s.query(FlowCheckpoint)
           .filter_by(run_id=result.run_id)
           .order_by(FlowCheckpoint.seq).all())
    assert len(cps) >= 1
    payload = json.loads(cps[0].vars_json)
    assert payload["action"]["verb"] == "scroll"


def test_runner_persists_failure_status(db, fake_session):
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p", db_path=db,
                             max_steps=3, max_time=60)
        result = runner.run()

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    r = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert r.status == "parse_error"
    assert r.error_text and "malformed" in r.error_text.lower()
