"""Browser step handlers — navigation + passive subset.

Interactive steps (click/type/hover) are added in the next task because
they delegate to HumanMouse / HumanKeyboard from tegufox_automation.
"""

from __future__ import annotations
from . import register, StepSpec


_DEFAULT_TIMEOUT = 30_000


@register("browser.goto", required=("url",))
def _goto(spec: StepSpec, ctx) -> None:
    p = spec.params
    ctx.page.goto(
        ctx.render(p["url"]),
        wait_until=p.get("wait_until", "load"),
        timeout=int(p.get("timeout_ms", _DEFAULT_TIMEOUT)),
    )


@register("browser.wait_for", required=("selector",))
def _wait_for(spec: StepSpec, ctx) -> None:
    p = spec.params
    ctx.page.locator(ctx.render(p["selector"])).wait_for(
        state=p.get("state", "visible"),
        timeout=int(p.get("timeout_ms", _DEFAULT_TIMEOUT)),
    )


@register("browser.screenshot", required=("path",))
def _screenshot(spec: StepSpec, ctx) -> None:
    p = spec.params
    path = ctx.render(p["path"])
    if "selector" in p:
        ctx.page.locator(ctx.render(p["selector"])).screenshot(path=path)
    else:
        ctx.page.screenshot(path=path, full_page=bool(p.get("full_page", False)))


@register("browser.press_key", required=("key",))
def _press_key(spec: StepSpec, ctx) -> None:
    p = spec.params
    if "selector" in p:
        ctx.page.locator(ctx.render(p["selector"])).press(p["key"])
    else:
        ctx.page.keyboard.press(p["key"])


@register("browser.scroll")
def _scroll(spec: StepSpec, ctx) -> None:
    p = spec.params
    if "to" in p:
        target = p["to"]
        if target == "top":
            ctx.page.evaluate("() => window.scrollTo(0, 0)")
        elif target == "bottom":
            ctx.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        else:
            ctx.page.locator(ctx.render(target)).scroll_into_view_if_needed()
        return
    direction = p.get("direction", "down")
    pixels = int(p.get("pixels", 500))
    dy = pixels if direction == "down" else -pixels
    ctx.page.mouse.wheel(0, dy)


@register("browser.select_option", required=("selector", "value"))
def _select_option(spec: StepSpec, ctx) -> None:
    ctx.page.locator(ctx.render(spec.params["selector"])).select_option(
        spec.params["value"]
    )


@register("browser.click", required=("selector",))
def _click(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True):
        ctx._human_mouse.click(sel)
    else:
        ctx.page.locator(sel).click(
            button=p.get("button", "left"),
            click_count=int(p.get("click_count", 1)),
        )


@register("browser.type", required=("selector", "text"))
def _type(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    text = ctx.render(p["text"])
    if p.get("clear_first"):
        ctx.page.locator(sel).fill("")
    if p.get("human", True):
        ctx._human_keyboard.type_into(sel, text)
    else:
        ctx.page.locator(sel).type(text, delay=int(p.get("delay_ms", 0)))


@register("browser.hover", required=("selector",))
def _hover(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True):
        ctx._human_mouse.move_to(sel)
    else:
        ctx.page.locator(sel).hover()
