from unittest.mock import MagicMock, patch
import pytest

from tegufox_flow.agent import (
    AgentAction, dispatch_action, DispatchError,
)


def _ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    import logging
    c.logger = logging.getLogger("test_dispatch")
    return c


def test_dispatch_goto_calls_browser_goto():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        action = AgentAction(verb="goto", args={"url": "https://x"})
        result = dispatch_action(action, ctx)
        gh.assert_called_once_with("browser.goto")
        spec_arg = handler.call_args.args[0]
        assert spec_arg.type == "browser.goto"
        assert spec_arg.params["url"] == "https://x"
        assert result["ok"] is True


def test_dispatch_click_text():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        gh.return_value = MagicMock()
        dispatch_action(AgentAction(verb="click_text",
                                    args={"text": "Sign in"}), ctx)
        gh.assert_called_once_with("browser.click_text")


def test_dispatch_type_passes_human_false():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        dispatch_action(AgentAction(verb="type",
                                    args={"selector": "#x", "text": "hi"}), ctx)
        spec = handler.call_args.args[0]
        assert spec.params["selector"] == "#x"
        assert spec.params["text"] == "hi"
        assert spec.params["human"] is False


def test_dispatch_click_passes_force_true():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        handler = MagicMock()
        gh.return_value = handler
        dispatch_action(AgentAction(verb="click",
                                    args={"selector": "#x"}), ctx)
        spec = handler.call_args.args[0]
        assert spec.params["force"] is True


def test_dispatch_screenshot_no_selector():
    ctx = _ctx()
    with patch("tegufox_flow.agent.get_handler") as gh:
        gh.return_value = MagicMock()
        dispatch_action(AgentAction(verb="screenshot",
                                    args={"path": "out.png"}), ctx)
        spec = gh.return_value.call_args.args[0]
        assert spec.params["path"] == "out.png"


def test_dispatch_unknown_verb_raises():
    ctx = _ctx()
    with pytest.raises(DispatchError):
        dispatch_action(AgentAction(verb="nope", args={}), ctx)


def test_dispatch_done_returns_signal():
    ctx = _ctx()
    out = dispatch_action(
        AgentAction(verb="done", args={"reason": "task complete"}), ctx
    )
    assert out["terminal"] == "done"
    assert out["reason"] == "task complete"


def test_dispatch_ask_user_returns_signal():
    ctx = _ctx()
    out = dispatch_action(
        AgentAction(verb="ask_user", args={"question": "2FA code?"}), ctx
    )
    assert out["terminal"] == "ask_user"
    assert out["question"] == "2FA code?"
