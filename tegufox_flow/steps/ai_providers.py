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
from typing import Callable, Optional


_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "openai_compatible": "gpt-4o-mini",   # alias of openai
    "gemini": "gemini-2.5-flash",
}


def _resolve_provider(explicit: Optional[str] = None) -> str:
    if explicit:
        if explicit == "openai":
            return "openai_compatible"
        return explicit
    env_choice = (os.environ.get("TEGUFOX_AI_PROVIDER") or "").strip().lower()
    if env_choice:
        return "openai_compatible" if env_choice == "openai" else env_choice
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai_compatible"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    raise RuntimeError(
        "No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "or GEMINI_API_KEY (or pass provider=... on the step)."
    )


def _ask_anthropic(system: str, user: str, max_tokens: int,
                   model: Optional[str]) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic SDK not installed") from e
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model or _DEFAULT_MODELS["anthropic"],
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
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai SDK not installed") from e
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model or _DEFAULT_MODELS["openai_compatible"],
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
               or os.environ.get("GOOGLE_API_KEY"))
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
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
        model=model or _DEFAULT_MODELS["gemini"],
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
