"""AI Copilot steps — call Claude / OpenAI to bridge selectors and intent.

Three step types, all share an LLM-call helper that:

  * Reads ANTHROPIC_API_KEY from env (or set_pref equivalent, future).
  * Sends a small prompt with truncated page DOM + the user's intent.
  * Returns a single short answer (selector / extracted value / yes-no).

Cost is a real concern — only reach for ai.* steps when classical CSS
selectors keep breaking. Each call costs ~1-3¢ depending on page size
(we truncate outerHTML to 8 KB).
"""

from __future__ import annotations
import os
from typing import Optional

from . import register, StepSpec


_DEFAULT_MODEL = os.environ.get("TEGUFOX_AI_MODEL", "claude-sonnet-4-6")
_MAX_HTML_BYTES = 8000
_DEFAULT_MAX_TOKENS = 256


def _get_anthropic_client():
    """Return an anthropic.Anthropic instance or raise a clear error."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it in your shell or add to "
            "settings before using ai.* steps."
        )
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK not installed. Run: pip install anthropic"
        ) from e
    return anthropic.Anthropic(api_key=api_key)


def _truncate_dom(html: str, limit: int = _MAX_HTML_BYTES) -> str:
    if len(html) <= limit:
        return html
    head = html[: limit // 2]
    tail = html[-limit // 2:]
    return f"{head}\n…[{len(html) - limit} chars truncated]…\n{tail}"


def _ask_llm(
    *,
    system: str,
    user: str,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    model: Optional[str] = None,
) -> str:
    client = _get_anthropic_client()
    msg = client.messages.create(
        model=model or _DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text
    return text.strip()


# ---------------------------------------------------------------------------
# ai.click — given an English/Vietnamese description, AI picks a selector
# and the step clicks it.
# ---------------------------------------------------------------------------

@register("ai.click", required=("description",))
def _ai_click(spec: StepSpec, ctx) -> None:
    p = spec.params
    description = ctx.render(p["description"])
    model = p.get("model")
    force = bool(p.get("force", True))
    timeout_ms = int(p.get("timeout_ms", 15_000))

    html = ctx.page.content()
    truncated = _truncate_dom(html)

    system = (
        "You are an HTML selector expert helping a Playwright automation. "
        "Given an HTML page and a description of an element to click, "
        "return ONLY a single CSS selector that uniquely identifies the "
        "intended element. No explanation, no markdown, no quotes — just "
        "the selector. Prefer stable selectors: data-testid > id > "
        "aria-label > role+text > tag.class. If no element matches, "
        "respond with the literal string NOT_FOUND."
    )
    user = (
        f"DESCRIPTION: {description}\n\nHTML (current page):\n{truncated}"
    )
    selector = _ask_llm(system=system, user=user, max_tokens=200, model=model)

    if selector == "NOT_FOUND" or not selector:
        raise RuntimeError(f"ai.click: AI could not match {description!r}")

    ctx.logger.info(f"ai.click: AI suggested selector={selector!r} for {description!r}")
    ctx.page.locator(selector).first.click(force=force, timeout=timeout_ms)


# ---------------------------------------------------------------------------
# ai.fix_selector — try `selector` first; if it doesn't match, ask AI for
# a replacement that targets the same intent.
# ---------------------------------------------------------------------------

@register("ai.fix_selector", required=("selector", "description", "set"))
def _ai_fix_selector(spec: StepSpec, ctx) -> None:
    """Self-healing selector. If `selector` matches → store it in `set`
    var. If not, ask AI for a new selector based on `description` and
    store the AI's suggestion. Useful at the top of a flow that's
    about to operate on a brittle element."""
    p = spec.params
    initial = ctx.render(p["selector"])
    description = ctx.render(p["description"])
    out_var = p["set"]
    model = p.get("model")

    try:
        count = ctx.page.locator(initial).count()
    except Exception:
        count = 0

    if count > 0:
        ctx.logger.info(f"ai.fix_selector: {initial!r} matched {count}; keeping")
        ctx.set_var(out_var, initial)
        return

    html = ctx.page.content()
    system = (
        "You are an HTML selector repair tool. The user's CSS selector "
        "matches NOTHING on the current page. Suggest a new CSS selector "
        "that finds the element described. Return ONLY the selector — no "
        "explanation, no quotes, no markdown."
    )
    user = (
        f"OLD SELECTOR (now missing): {initial}\n"
        f"DESCRIPTION: {description}\n\nHTML:\n{_truncate_dom(html)}"
    )
    new_sel = _ask_llm(system=system, user=user, max_tokens=200, model=model)
    if not new_sel or new_sel == "NOT_FOUND":
        raise RuntimeError(
            f"ai.fix_selector: AI could not heal selector for {description!r}"
        )
    ctx.logger.info(f"ai.fix_selector: {initial!r} → {new_sel!r}")
    ctx.set_var(out_var, new_sel)


# ---------------------------------------------------------------------------
# ai.extract — given a description, AI extracts a value from the page.
# Useful when scraped data has no stable selector but is identifiable by
# context (e.g. "the order total on the receipt").
# ---------------------------------------------------------------------------

@register("ai.extract", required=("description", "set"))
def _ai_extract(spec: StepSpec, ctx) -> None:
    p = spec.params
    description = ctx.render(p["description"])
    out_var = p["set"]
    model = p.get("model")
    max_tokens = int(p.get("max_tokens", 256))

    html = ctx.page.content()
    system = (
        "You are an HTML data extraction assistant. Given a page and a "
        "description of what to extract, return ONLY the extracted value. "
        "No labels, no quotes (unless they're part of the value), no "
        "explanations. If the data isn't on the page, return NOT_FOUND."
    )
    user = f"DESCRIPTION: {description}\n\nHTML:\n{_truncate_dom(html)}"
    value = _ask_llm(system=system, user=user, max_tokens=max_tokens, model=model)

    if value == "NOT_FOUND":
        raise RuntimeError(f"ai.extract: AI could not find {description!r}")
    ctx.logger.info(f"ai.extract: {description!r} → {value[:80]!r}")
    ctx.set_var(out_var, value)


# ---------------------------------------------------------------------------
# ai.ask — generic Q&A. Sends DOM + question, stores answer.
# ---------------------------------------------------------------------------

@register("ai.ask", required=("question", "set"))
def _ai_ask(spec: StepSpec, ctx) -> None:
    p = spec.params
    question = ctx.render(p["question"])
    out_var = p["set"]
    include_dom = bool(p.get("include_dom", True))
    model = p.get("model")
    max_tokens = int(p.get("max_tokens", 512))

    if include_dom:
        html = ctx.page.content()
        user = f"QUESTION: {question}\n\nHTML:\n{_truncate_dom(html)}"
    else:
        user = question

    system = (
        "You are a helpful page-analysis assistant. Answer concisely. "
        "If the answer can be a single word or short phrase, just return that."
    )
    answer = _ask_llm(system=system, user=user, max_tokens=max_tokens, model=model)
    ctx.set_var(out_var, answer)
    ctx.logger.info(f"ai.ask: {question[:60]!r} → {answer[:80]!r}")
