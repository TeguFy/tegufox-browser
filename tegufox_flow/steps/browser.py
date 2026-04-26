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
    # `.first` avoids strict-mode violations and ensures we wait for the
    # first match (rather than getting stuck on a hidden duplicate).
    ctx.page.locator(ctx.render(p["selector"])).first.wait_for(
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
        force=bool(p.get("force", False)),
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


def _all_pages_across_contexts(main_page) -> list:
    """Return every Page across every BrowserContext of the underlying
    browser. Camoufox/Firefox sometimes opens OAuth in a fresh window
    that lives in a *separate* context (not just a new page in the
    current context), so iterating only `main.context.pages` misses it.
    """
    pages: list = []
    seen: set = set()
    try:
        ctx0 = main_page.context
        pages_list = list(ctx0.pages)
        for p in pages_list:
            if id(p) not in seen:
                seen.add(id(p)); pages.append(p)
        # Walk sibling contexts via the shared Browser object.
        try:
            browser = ctx0.browser
            if browser is not None:
                for c in browser.contexts:
                    for p in c.pages:
                        if id(p) not in seen:
                            seen.add(id(p)); pages.append(p)
        except Exception:
            pass
    except Exception:
        pages = [main_page]
    return pages


@register("browser.disable_popups")
def _disable_popups(spec: StepSpec, ctx) -> None:
    """Override window.open so popups become same-tab redirects.

    Useful when Camoufox isolates popup windows in a browser process
    Playwright can't reach. Once disabled, any window.open(url) call
    navigates the CURRENT page to that URL instead of opening a new
    window — which Playwright tracks naturally.

    Trade-off: the original tab's content is lost when redirected.
    For OAuth flows this is fine because the auth provider redirects
    back to the originating site after success, restoring the user
    on the original origin (different page, but same browser tab).

    Applied via context.add_init_script() so it persists across all
    navigations and any new pages opened in this context. Also
    applied immediately to ctx.page via evaluate() so it takes
    effect on the page that's already loaded.
    """
    js = """
    (() => {
      if (window.__teguPopupsDisabled) return;
      window.__teguPopupsDisabled = true;
      const origOpen = window.open;
      window.open = function(url, name, features) {
        if (typeof url === 'string' && url.length > 0) {
          window.location.href = url;
        }
        return window;
      };
    })();
    """
    try:
        ctx.page.context.add_init_script(js)
    except Exception as e:
        ctx.logger.warning(f"add_init_script failed: {e}")
    try:
        ctx.page.evaluate(js)
    except Exception as e:
        ctx.logger.warning(f"page.evaluate failed: {e}")
    ctx.logger.info("popups disabled — window.open now redirects current tab")


@register("browser.click_and_wait_popup", required=("selector",))
def _click_and_wait_popup(spec: StepSpec, ctx) -> None:
    """Atomic click + popup capture.

    The canonical Playwright pattern: register a popup-event listener on
    the current page BEFORE triggering the click, then perform the click,
    then read the captured popup. Catches popups even when Camoufox
    isolates them into a fresh top-level window that page.context.pages
    polling never sees, because the page-level "popup" event fires the
    instant window.open() is called.
    """
    p = spec.params
    sel = ctx.render(p["selector"])
    timeout_ms = int(p.get("timeout_ms", 30_000))
    force = bool(p.get("force", False))

    page = ctx.page
    with page.expect_popup(timeout=timeout_ms) as popup_info:
        page.locator(sel).first.click(force=force, timeout=timeout_ms)
    popup = popup_info.value
    try:
        popup.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except Exception:
        pass

    ctx.page = popup
    try:
        from tegufox_automation import HumanMouse, HumanKeyboard
        if HumanMouse: ctx._human_mouse = HumanMouse(popup)
        if HumanKeyboard: ctx._human_keyboard = HumanKeyboard(popup)
    except Exception:
        pass
    try:
        ctx.logger.info(f"clicked, switched to popup: {popup.url}")
    except Exception:
        pass


@register("browser.wait_for_popup", optional=("url_contains", "timeout_ms"))
def _wait_for_popup(spec: StepSpec, ctx) -> None:
    """Wait until a new page (popup / tab / window) opens and switch ctx.page
    to it. Scans pages across all browser contexts, so it catches OAuth
    flows that open a separate Firefox window with its own context.
    """
    import time
    p = spec.params
    timeout_ms = int(p.get("timeout_ms", 30_000))
    needle = (p.get("url_contains") or "").strip()

    main = ctx._original_page or ctx.page
    deadline = time.monotonic() + timeout_ms / 1000.0
    seen_initial = {id(pg) for pg in _all_pages_across_contexts(main)}

    while time.monotonic() < deadline:
        for pg in _all_pages_across_contexts(main):
            if pg is main or id(pg) in seen_initial:
                continue
            try:
                url = pg.url or ""
            except Exception:
                continue
            if needle and needle not in url:
                continue
            ctx.page = pg
            try:
                from tegufox_automation import HumanMouse, HumanKeyboard
                if HumanMouse: ctx._human_mouse = HumanMouse(pg)
                if HumanKeyboard: ctx._human_keyboard = HumanKeyboard(pg)
            except Exception:
                pass
            ctx.logger.info(f"switched to popup/window: {url}")
            return
        time.sleep(0.2)

    raise RuntimeError(
        f"no popup/window opened within {timeout_ms}ms"
        + (f" matching {needle!r}" if needle else "")
    )


@register("browser.wait_for_url", optional=("url_contains", "timeout_ms"))
def _wait_for_url(spec: StepSpec, ctx) -> None:
    """Wait until any page (across ALL browser contexts) has a URL matching
    `url_contains` and switch ctx.page to it. Handles same-tab redirect,
    popups, and Camoufox-style separate-context windows.
    """
    import time
    p = spec.params
    timeout_ms = int(p.get("timeout_ms", 30_000))
    needle = (p.get("url_contains") or "").strip()

    main = ctx._original_page or ctx.page
    deadline = time.monotonic() + timeout_ms / 1000.0

    while time.monotonic() < deadline:
        for pg in _all_pages_across_contexts(main):
            try:
                url = pg.url or ""
            except Exception:
                continue
            if needle and needle not in url:
                continue
            if not needle and not url:
                continue
            if pg is not ctx.page:
                ctx.page = pg
                try:
                    from tegufox_automation import HumanMouse, HumanKeyboard
                    if HumanMouse: ctx._human_mouse = HumanMouse(pg)
                    if HumanKeyboard: ctx._human_keyboard = HumanKeyboard(pg)
                except Exception:
                    pass
                ctx.logger.info(f"switched to page: {url}")
            else:
                ctx.logger.info(f"already on matching page: {url}")
            return
        time.sleep(0.2)

    raise RuntimeError(
        f"no page matched URL"
        + (f" containing {needle!r}" if needle else "")
        + f" within {timeout_ms}ms"
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
