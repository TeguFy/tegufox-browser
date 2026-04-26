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


def _native_click(ctx, sel: str, p: dict) -> None:
    ctx.page.locator(sel).click(
        button=p.get("button", "left"),
        click_count=int(p.get("click_count", 1)),
    )


def _native_type(ctx, sel: str, text: str, p: dict) -> None:
    ctx.page.locator(sel).type(text, delay=int(p.get("delay_ms", 0)))


def _native_hover(ctx, sel: str) -> None:
    ctx.page.locator(sel).hover()


@register("browser.click", required=("selector",))
def _click(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True) and ctx._human_mouse is not None:
        try:
            ctx._human_mouse.click(sel)
            return
        except Exception as e:
            # HumanMouse uses Firefox internals (windowUtils.sendMouseEvent)
            # that aren't available on every Firefox build / Camoufox patch
            # combination. Falling back to native click keeps the flow
            # functional; user loses anti-detection mouse paths but the
            # step completes.
            ctx.logger.warning(
                f"HumanMouse click failed ({type(e).__name__}: {e}); "
                f"falling back to native click."
            )
    _native_click(ctx, sel, p)


@register("browser.type", required=("selector", "text"))
def _type(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    text = ctx.render(p["text"])
    if p.get("clear_first"):
        ctx.page.locator(sel).fill("")
    if p.get("human", True) and ctx._human_keyboard is not None:
        try:
            ctx._human_keyboard.type_into(sel, text)
            return
        except Exception as e:
            ctx.logger.warning(
                f"HumanKeyboard type failed ({type(e).__name__}: {e}); "
                f"falling back to native type."
            )
    _native_type(ctx, sel, text, p)


@register("browser.wait_for_popup", optional=("url_contains", "timeout_ms"))
def _wait_for_popup(spec: StepSpec, ctx) -> None:
    """Wait until a new page (popup / new tab) opens in the browser context
    and switch ctx.page to it. Common case: site opens 'Login with Google'
    and the rest of the auth flow runs in the popup.

    Optional `url_contains`: a substring filter so we ignore unrelated
    iframes/popups. If multiple popups match, picks the first.
    """
    import time
    p = spec.params
    timeout_ms = int(p.get("timeout_ms", 30_000))
    needle = (p.get("url_contains") or "").strip()

    main = ctx._original_page or ctx.page
    deadline = time.monotonic() + timeout_ms / 1000.0
    seen_initial = set()
    try:
        for pg in main.context.pages:
            seen_initial.add(id(pg))
    except Exception:
        pass

    while time.monotonic() < deadline:
        try:
            for pg in main.context.pages:
                if pg is main:
                    continue
                if id(pg) in seen_initial:
                    continue   # was already open before this step ran
                url = pg.url or ""
                if needle and needle not in url:
                    continue
                ctx.page = pg
                # Re-bind HumanMouse/Keyboard to the popup so subsequent
                # human=True clicks/typing target it.
                try:
                    from tegufox_automation import HumanMouse, HumanKeyboard
                    if HumanMouse: ctx._human_mouse = HumanMouse(pg)
                    if HumanKeyboard: ctx._human_keyboard = HumanKeyboard(pg)
                except Exception:
                    pass
                ctx.logger.info(f"switched to popup: {url}")
                return
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError(
        f"no popup opened within {timeout_ms}ms"
        + (f" matching {needle!r}" if needle else "")
    )


@register("browser.switch_to_main")
def _switch_to_main(spec: StepSpec, ctx) -> None:
    """Switch ctx.page back to the original page (the one opened first).
    Use after browser.wait_for_popup when the popup-side flow is done."""
    if ctx._original_page is None:
        raise RuntimeError("no original page recorded; engine.run did not bind it")
    ctx.page = ctx._original_page
    try:
        from tegufox_automation import HumanMouse, HumanKeyboard
        if HumanMouse: ctx._human_mouse = HumanMouse(ctx._original_page)
        if HumanKeyboard: ctx._human_keyboard = HumanKeyboard(ctx._original_page)
    except Exception:
        pass


@register("browser.hover", required=("selector",))
def _hover(spec: StepSpec, ctx) -> None:
    p = spec.params
    sel = ctx.render(p["selector"])
    if p.get("human", True) and ctx._human_mouse is not None:
        try:
            ctx._human_mouse.move_to(sel)
            return
        except Exception as e:
            ctx.logger.warning(
                f"HumanMouse hover failed ({type(e).__name__}: {e}); "
                f"falling back to native hover."
            )
    _native_hover(ctx, sel)
