"""ai.* steps — verify registration + the API-key error path.
Real LLM calls aren't tested here (network + cost); we mock the
helper that wraps Anthropic.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.ai  # noqa  -- registers


def _ctx_with_page(html: str = "<html><body><button>OK</button></body></html>"):
    ctx = MagicMock()
    ctx.page = MagicMock()
    ctx.page.content.return_value = html
    ctx.render.side_effect = lambda s: s
    import logging
    ctx.logger = logging.getLogger("test_ai")
    return ctx


def test_ai_click_registered():
    handler = get_handler("ai.click")
    assert handler is not None
    assert "description" in getattr(handler, "required", ())


def test_ai_fix_selector_registered():
    handler = get_handler("ai.fix_selector")
    assert handler is not None


def test_ai_extract_registered():
    handler = get_handler("ai.extract")
    assert handler is not None


def test_ai_ask_registered():
    handler = get_handler("ai.ask")
    assert handler is not None


def test_ai_click_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ctx = _ctx_with_page()
    with pytest.raises(RuntimeError) as e:
        get_handler("ai.click")(
            StepSpec(id="c", type="ai.click", params={"description": "OK button"}),
            ctx,
        )
    assert "ANTHROPIC_API_KEY" in str(e.value)


def test_ai_click_uses_returned_selector(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    locator = MagicMock()
    ctx.page.locator.return_value = locator

    with patch("tegufox_flow.steps.ai._ask_llm", return_value="#submit"):
        get_handler("ai.click")(
            StepSpec(id="c", type="ai.click",
                     params={"description": "the submit button"}),
            ctx,
        )
    ctx.page.locator.assert_called_once_with("#submit")
    locator.first.click.assert_called_once()


def test_ai_click_raises_on_not_found(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    with patch("tegufox_flow.steps.ai._ask_llm", return_value="NOT_FOUND"):
        with pytest.raises(RuntimeError) as e:
            get_handler("ai.click")(
                StepSpec(id="c", type="ai.click",
                         params={"description": "ghost"}),
                ctx,
            )
        assert "ghost" in str(e.value)


def test_ai_fix_selector_keeps_working_selector(monkeypatch):
    """If the original selector matches, AI is NOT called."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    locator = MagicMock(); locator.count.return_value = 1
    ctx.page.locator.return_value = locator

    with patch("tegufox_flow.steps.ai._ask_llm",
               side_effect=AssertionError("AI shouldn't be called")):
        get_handler("ai.fix_selector")(
            StepSpec(id="f", type="ai.fix_selector",
                     params={"selector": "#x", "description": "x button",
                             "set": "out"}),
            ctx,
        )
    ctx.set_var.assert_called_once_with("out", "#x")


def test_ai_fix_selector_calls_ai_when_selector_misses(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    locator = MagicMock(); locator.count.return_value = 0
    ctx.page.locator.return_value = locator

    with patch("tegufox_flow.steps.ai._ask_llm", return_value="[data-testid='x']"):
        get_handler("ai.fix_selector")(
            StepSpec(id="f", type="ai.fix_selector",
                     params={"selector": "#x", "description": "x button",
                             "set": "out"}),
            ctx,
        )
    ctx.set_var.assert_called_once_with("out", "[data-testid='x']")


def test_ai_extract_stores_value(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    with patch("tegufox_flow.steps.ai._ask_llm", return_value="$42.99"):
        get_handler("ai.extract")(
            StepSpec(id="e", type="ai.extract",
                     params={"description": "order total", "set": "total"}),
            ctx,
        )
    ctx.set_var.assert_called_once_with("total", "$42.99")


def test_ai_ask_stores_answer(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    ctx = _ctx_with_page()
    with patch("tegufox_flow.steps.ai._ask_llm", return_value="yes"):
        get_handler("ai.ask")(
            StepSpec(id="a", type="ai.ask",
                     params={"question": "is logged in?", "set": "ans"}),
            ctx,
        )
    ctx.set_var.assert_called_once_with("ans", "yes")


# --- Provider resolution -----------------------------------------------------

def test_resolve_provider_explicit(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    assert _resolve_provider("anthropic") == "anthropic"
    assert _resolve_provider("openai") == "openai_compatible"
    assert _resolve_provider("gemini") == "gemini"


def test_resolve_provider_env_var(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("TEGUFOX_AI_PROVIDER", "gemini")
    assert _resolve_provider() == "gemini"


def test_resolve_provider_auto_anthropic_first(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    monkeypatch.delenv("TEGUFOX_AI_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    assert _resolve_provider() == "anthropic"


def test_resolve_provider_auto_falls_back_to_openai(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    monkeypatch.delenv("TEGUFOX_AI_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert _resolve_provider() == "openai_compatible"


def test_resolve_provider_auto_falls_back_to_gemini(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    monkeypatch.delenv("TEGUFOX_AI_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "z")
    assert _resolve_provider() == "gemini"


def test_resolve_provider_no_keys_raises(monkeypatch):
    from tegufox_flow.steps.ai_providers import _resolve_provider
    for v in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
              "GOOGLE_API_KEY", "TEGUFOX_AI_PROVIDER"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError) as e:
        _resolve_provider()
    assert "ANTHROPIC_API_KEY" in str(e.value)


def test_ai_click_uses_explicit_provider(monkeypatch):
    """Step's `provider` param flows down to ask_llm()."""
    from unittest.mock import patch as _patch
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    ctx = _ctx_with_page()
    locator = MagicMock()
    ctx.page.locator.return_value = locator

    captured = {}
    def fake_ask(*args, **kwargs):
        captured.update(kwargs)
        return "#x"

    with _patch("tegufox_flow.steps.ai._ask_llm", side_effect=fake_ask):
        get_handler("ai.click")(
            StepSpec(id="c", type="ai.click",
                     params={"description": "x", "provider": "openai"}),
            ctx,
        )
    assert captured.get("provider") == "openai"
