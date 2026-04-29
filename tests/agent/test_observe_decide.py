from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import _observe, _decide, AgentAction, ParseError


def test_observe_returns_url_title_dom():
    page = MagicMock()
    page.url = "https://example.com"
    page.title.return_value = "Example"
    page.content.return_value = "<html><body>X" + "y" * 20000 + "</body></html>"
    obs = _observe(page)
    assert obs["url"] == "https://example.com"
    assert obs["title"] == "Example"
    assert len(obs["dom"]) < 12000
    assert "truncated" in obs["dom"].lower() or len(obs["dom"]) <= 8200


def test_observe_handles_title_failure():
    page = MagicMock()
    page.url = "https://x"
    page.title.side_effect = RuntimeError("no")
    page.content.return_value = "<html></html>"
    obs = _observe(page)
    assert obs["title"] == ""


def test_decide_returns_parsed_action():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    with patch("tegufox_flow.agent.ask_llm",
               return_value='{"verb": "goto", "args": {"url": "https://y"}}'):
        action = _decide(history=[], obs=obs, goal="t",
                         provider=None, model=None)
    assert action.verb == "goto"
    assert action.args["url"] == "https://y"


def test_decide_retries_on_bad_json_then_succeeds():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    responses = iter([
        "not json",
        '{"verb": "ghost"}',
        '{"verb": "done", "args": {"reason": "ok"}}',
    ])
    with patch("tegufox_flow.agent.ask_llm",
               side_effect=lambda **kw: next(responses)):
        action = _decide(history=[], obs=obs, goal="t",
                         provider=None, model=None)
    assert action.verb == "done"


def test_decide_gives_up_after_3_attempts():
    obs = {"url": "https://x", "title": "x", "dom": "<html></html>"}
    with patch("tegufox_flow.agent.ask_llm",
               side_effect=["bad"] * 5):
        with pytest.raises(ParseError):
            _decide(history=[], obs=obs, goal="t",
                    provider=None, model=None)


def test_decide_truncates_history_to_last_10():
    obs = {"url": "x", "title": "x", "dom": ""}
    captured = {}

    def fake(**kw):
        captured["user"] = kw["user"]
        return '{"verb": "done", "args": {"reason": "ok"}}'

    huge_history = [
        {"obs": {"url": f"u{i}", "title": "", "dom": ""},
         "action": {"verb": "goto", "args": {}, "reasoning": ""},
         "result": {"ok": True}}
        for i in range(40)
    ]
    with patch("tegufox_flow.agent.ask_llm", side_effect=fake):
        _decide(history=huge_history, obs=obs, goal="t",
                provider=None, model=None)
    assert "u0" not in captured["user"]
    assert "u39" in captured["user"]
