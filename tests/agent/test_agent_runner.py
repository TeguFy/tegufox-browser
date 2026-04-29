import threading
from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import AgentRunner, AgentResult


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.page = MagicMock()
    s.page.url = "https://example.com"
    s.page.title.return_value = "ex"
    s.page.content.return_value = "<html></html>"
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


def test_runner_done_terminates(fake_session):
    actions_iter = iter([
        '{"verb": "done", "args": {"reason": "trivial goal"}}',
    ])
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions_iter)):
        runner = AgentRunner(goal="check page exists", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "done"
    assert result.reason == "trivial goal"
    assert result.steps == 0


def test_runner_max_steps(fake_session):
    def fake_ask(**kw):
        return '{"verb": "scroll", "args": {"direction": "down"}}'

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=fake_ask), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="loop", profile_name="p",
                             max_steps=3, max_time=60)
        result = runner.run()
    assert result.status == "max_steps"
    assert result.steps == 3


def test_runner_user_stop_event(fake_session):
    stop_event = threading.Event()

    def fake_ask(**kw):
        stop_event.set()
        return '{"verb": "scroll", "args": {"direction": "down"}}'

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=fake_ask), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60,
                             stop_event=stop_event)
        result = runner.run()
    assert result.status == "aborted"


def test_runner_parse_error_after_3_retries(fake_session):
    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm", side_effect=["bad"] * 10):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "parse_error"


def test_runner_dispatch_error_keeps_history(fake_session):
    actions = iter([
        '{"verb": "click", "args": {"selector": "#x"}}',
        '{"verb": "done", "args": {"reason": "gave up"}}',
    ])

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               side_effect=RuntimeError("bad selector")):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60)
        result = runner.run()
    assert result.status == "done"
    assert any("error" in turn["result"] for turn in result.history)


def test_runner_calls_step_callback(fake_session):
    actions = iter([
        '{"verb": "scroll", "args": {"direction": "down"}}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    seen = []

    with patch("tegufox_flow.agent.TegufoxSession", return_value=fake_session), \
         patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(actions)), \
         patch("tegufox_flow.agent.dispatch_action",
               return_value={"ok": True}):
        runner = AgentRunner(goal="g", profile_name="p",
                             max_steps=10, max_time=60,
                             on_step=lambda i, a, r: seen.append((i, a.verb)))
        runner.run()
    assert seen[0] == (1, "scroll")
