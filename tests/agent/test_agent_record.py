import json
from unittest.mock import MagicMock, patch
import pytest
import yaml as _yaml

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, ensure_schema, FlowRecord
from tegufox_flow.agent import AgentRunner, _history_to_flow_yaml


@pytest.fixture
def tmp_db(tmp_path):
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


def test_history_to_flow_yaml_minimal():
    history = [
        {"action": {"verb": "goto", "args": {"url": "https://x"},
                    "reasoning": "go"}, "result": {"ok": True}},
        {"action": {"verb": "done", "args": {"reason": "ok"},
                    "reasoning": ""}, "result": {}},
    ]
    yaml_text = _history_to_flow_yaml(goal="open x", history=history,
                                      flow_name="agent_test")
    data = _yaml.safe_load(yaml_text)
    assert data["schema_version"] == 1
    assert data["name"] == "agent_test"
    assert any(s["type"] == "browser.goto" for s in data["steps"])
    # done is not emitted as a step.
    assert not any(s["type"] == "browser.done" for s in data["steps"])
    assert "open x" in data.get("description", "")


def test_history_to_flow_yaml_promotes_ask_user_to_input():
    history = [
        {"action": {"verb": "ask_user",
                    "args": {"question": "Email?"},
                    "reasoning": ""},
         "result": {"user_reply": "alice@x.com"}},
        {"action": {"verb": "type",
                    "args": {"selector": "#email", "text": "alice@x.com"},
                    "reasoning": ""}, "result": {"ok": True}},
        {"action": {"verb": "done", "args": {"reason": "ok"},
                    "reasoning": ""}, "result": {}},
    ]
    yaml_text = _history_to_flow_yaml(goal="g", history=history,
                                      flow_name="agent_t")
    data = _yaml.safe_load(yaml_text)
    assert "inputs" in data
    assert any("ask_user" in name or "email" in name.lower()
               for name in data["inputs"])


def test_runner_record_as_flow_writes_flows_row(tmp_db, fake_session):
    actions = iter([
        '{"verb": "goto", "args": {"url": "https://example.com"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="open example", profile_name="p",
                             db_path=tmp_db, max_steps=5, max_time=60,
                             record_as_flow=True)
        result = runner.run()

    assert result.status == "done"
    eng = create_engine(f"sqlite:///{tmp_db}")
    s = sessionmaker(bind=eng)()
    flows = s.query(FlowRecord).all()
    names = [f.name for f in flows]
    assert any(n.startswith("agent-") for n in names)
    assert result.flow_yaml is not None


def test_runner_no_record_when_off(tmp_db, fake_session):
    actions = iter([
        '{"verb": "done", "args": {"reason": "trivial"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)):
        runner = AgentRunner(goal="g", profile_name="p", db_path=tmp_db,
                             max_steps=3, max_time=60,
                             record_as_flow=False)
        result = runner.run()

    eng = create_engine(f"sqlite:///{tmp_db}")
    s = sessionmaker(bind=eng)()
    names = [f.name for f in s.query(FlowRecord).all()]
    assert all(not n.startswith("agent-") for n in names)
    assert result.flow_yaml is None


def test_runner_no_record_on_failure(tmp_db, fake_session):
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p", db_path=tmp_db,
                             max_steps=3, max_time=60,
                             record_as_flow=True)
        result = runner.run()
    assert result.status == "parse_error"
    assert result.flow_yaml is None
