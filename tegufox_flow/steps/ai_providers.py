"""LLM provider abstraction for ai.* steps.

Three providers are supported. Each exposes the same `ask(system, user,
max_tokens, model)` callable so step handlers don't care which one is in
use.

  • anthropic         — Claude (default, model = claude-sonnet-4-6)
  • openai_compatible — OpenAI / Groq / Together / Fireworks / vLLM /
                        any service that speaks the OpenAI Chat
                        Completions API. Uses OPENAI_BASE_URL if set
                        (lets users point at any compatible endpoint).
  • gemini            — Google (model = gemini-2.5-flash)

Provider selection priority:
  1. explicit `provider` parameter on the step
  2. TEGUFOX_AI_PROVIDER env var
  3. first provider whose API key is set in env (anthropic > openai > gemini)
"""

from __future__ import annotations
import os
from typing import Callable, List, Optional


_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "openai_compatible": "gpt-4o-mini",   # alias of openai
    "gemini": "gemini-2.5-flash",
}


# ---------------------------------------------------------------------------
# Settings-aware credential / model lookup
# ---------------------------------------------------------------------------
# Env vars always win over settings.conf so power users can override per
# shell session, but GUI-only users can store keys in settings.conf via
# the Settings page.

def _settings_ai() -> dict:
    """Read the `ai` block from settings.conf; empty dict if absent."""
    try:
        from tegufox_core.runtime_settings import get_setting
        block = get_setting("ai", {}) or {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _provider_creds(name: str) -> dict:
    """Return the per-provider settings sub-dict (api_key / model / base_url)."""
    block = _settings_ai().get(name) or {}
    return block if isinstance(block, dict) else {}


def _api_key_for(provider: str, env_var: str) -> Optional[str]:
    return os.environ.get(env_var) or _provider_creds(provider).get("api_key") or None


def _model_for(provider: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    cfg = _provider_creds(provider).get("model")
    if cfg:
        return cfg
    return _DEFAULT_MODELS[provider]


def list_configured_providers() -> List[str]:
    """Return the providers that have an API key (via env OR settings)."""
    out: List[str] = []
    if _api_key_for("anthropic", "ANTHROPIC_API_KEY"):
        out.append("anthropic")
    if _api_key_for("openai", "OPENAI_API_KEY") or \
            _api_key_for("openai_compatible", "OPENAI_API_KEY"):
        out.append("openai")
    if (os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or _provider_creds("gemini").get("api_key")):
        out.append("gemini")
    return out


def _settings_default_provider() -> Optional[str]:
    val = (_settings_ai().get("default_provider") or "").strip().lower()
    return val or None


def _resolve_provider(explicit: Optional[str] = None) -> str:
    if explicit:
        if explicit == "openai":
            return "openai_compatible"
        return explicit
    env_choice = (os.environ.get("TEGUFOX_AI_PROVIDER") or "").strip().lower()
    if env_choice:
        return "openai_compatible" if env_choice == "openai" else env_choice
    settings_default = _settings_default_provider()
    if settings_default:
        return "openai_compatible" if settings_default == "openai" else settings_default
    if _api_key_for("anthropic", "ANTHROPIC_API_KEY"):
        return "anthropic"
    if _api_key_for("openai", "OPENAI_API_KEY"):
        return "openai_compatible"
    if (os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or _provider_creds("gemini").get("api_key")):
        return "gemini"
    raise RuntimeError(
        "No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "or GEMINI_API_KEY in your shell, OR add an API key via Settings → "
        "AI Providers."
    )


def _ask_anthropic(system: str, user: str, max_tokens: int,
                   model: Optional[str]) -> str:
    api_key = _api_key_for("anthropic", "ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Anthropic API key not set (env ANTHROPIC_API_KEY or "
            "Settings → AI Providers → Anthropic)."
        )
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic SDK not installed") from e
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=_model_for("anthropic", model),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    out = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            out += block.text
    return out.strip()


def _ask_openai_compatible(system: str, user: str, max_tokens: int,
                           model: Optional[str]) -> str:
    api_key = (_api_key_for("openai", "OPENAI_API_KEY")
               or _api_key_for("openai_compatible", "OPENAI_API_KEY"))
    if not api_key:
        raise RuntimeError(
            "OpenAI API key not set (env OPENAI_API_KEY or "
            "Settings → AI Providers → OpenAI)."
        )
    base_url = (os.environ.get("OPENAI_BASE_URL")
                or _provider_creds("openai").get("base_url")
                or None)
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai SDK not installed") from e
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=_model_for("openai_compatible", model),
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def _ask_gemini(system: str, user: str, max_tokens: int,
                model: Optional[str]) -> str:
    api_key = (os.environ.get("GEMINI_API_KEY")
               or os.environ.get("GOOGLE_API_KEY")
               or _provider_creds("gemini").get("api_key"))
    if not api_key:
        raise RuntimeError(
            "Gemini API key not set (env GEMINI_API_KEY/GOOGLE_API_KEY or "
            "Settings → AI Providers → Gemini)."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("google-genai SDK not installed") from e
    client = genai.Client(api_key=api_key)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
    )
    resp = client.models.generate_content(
        model=_model_for("gemini", model),
        contents=user,
        config=cfg,
    )
    text = getattr(resp, "text", "") or ""
    return text.strip()


_DISPATCH: dict = {
    "anthropic": _ask_anthropic,
    "openai_compatible": _ask_openai_compatible,
    "openai": _ask_openai_compatible,           # alias
    "gemini": _ask_gemini,
}


def ask_llm(
    *,
    system: str,
    user: str,
    max_tokens: int = 256,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """Dispatch to the resolved provider's `_ask_*` function."""
    name = _resolve_provider(provider)
    fn: Callable = _DISPATCH.get(name)
    if fn is None:
        raise RuntimeError(f"unknown AI provider: {name!r}")
    return fn(system, user, max_tokens, model)
