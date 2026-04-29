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
        ctx.page.locator(ctx.render(p["selector"])).first.screenshot(path=path)
    else:
        ctx.page.screenshot(path=path, full_page=bool(p.get("full_page", False)))


@register("browser.press_key", required=("key",))
def _press_key(spec: StepSpec, ctx) -> None:
    p = spec.params
    if "selector" in p:
        ctx.page.locator(ctx.render(p["selector"])).first.press(p["key"])
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
    ctx.page.locator(ctx.render(spec.params["selector"])).first.select_option(
        spec.params["value"]
    )


def _native_click(ctx, sel: str, p: dict) -> None:
    # `.first` — selector lists matching multiple elements would otherwise
    # raise strict-mode violation. Always click the first match.
    ctx.page.locator(sel).first.click(
        button=p.get("button", "left"),
        click_count=int(p.get("click_count", 1)),
        force=bool(p.get("force", False)),
    )


def _native_type(ctx, sel: str, text: str, p: dict) -> None:
    ctx.page.locator(sel).first.type(text, delay=int(p.get("delay_ms", 0)))


def _native_hover(ctx, sel: str) -> None:
    ctx.page.locator(sel).first.hover()


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
        ctx.page.locator(sel).first.fill("")
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


@register("browser.fill_form_by_labels", required=("fields",))
def _fill_form_by_labels(spec: StepSpec, ctx) -> None:
    """Fill multiple form inputs by their visible label text.

    `fields` is a dict {label_text: value_to_type}. For each entry the
    step finds the matching <input>/<textarea>/<select> on the page and
    fills it. Matching priority:
      1. <label for="..."> with that text → input by id
      2. <input> with placeholder matching the text
      3. <input> with aria-label matching the text
      4. <input> sibling/descendant of an element with that text
      5. AI fallback (if `use_ai=true` and ANTHROPIC/OPENAI/GEMINI key set)
    """
    p = spec.params
    fields = p.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields must be a {label: value} dict")
    use_ai = bool(p.get("use_ai", False))
    human = bool(p.get("human", False))
    timeout_ms = int(p.get("timeout_ms", 5_000))

    # Render values (Jinja-aware) and labels (in case user uses {{ }}).
    fields_r = {}
    for k, v in fields.items():
        rk = ctx.render(k) if isinstance(k, str) else k
        rv = ctx.render(v) if isinstance(v, str) else v
        fields_r[rk] = rv

    js_resolve = """
    (label) => {
      const t = label.toLowerCase();
      function visible(el) {
        if (!el) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      }
      function tag(id) {
        return document.querySelector(
          `input[data-tegu-fill="${id}"], textarea[data-tegu-fill="${id}"], select[data-tegu-fill="${id}"]`
        );
      }
      const id = '__tegu-fill-' + Date.now() + '-' + Math.floor(Math.random()*1e6);
      // 1. <label for="...">
      const labels = Array.from(document.querySelectorAll('label'));
      const lab = labels.find(l => visible(l) && l.textContent.toLowerCase().includes(t));
      if (lab) {
        const fid = lab.getAttribute('for');
        const el = fid ? document.getElementById(fid)
                       : lab.querySelector('input, textarea, select');
        if (el && visible(el)) { el.setAttribute('data-tegu-fill', id); return id; }
      }
      // 2. placeholder match
      const ph = Array.from(document.querySelectorAll('input[placeholder], textarea[placeholder]'))
                       .find(el => visible(el) &&
                             (el.placeholder || '').toLowerCase().includes(t));
      if (ph) { ph.setAttribute('data-tegu-fill', id); return id; }
      // 3. aria-label
      const aria = Array.from(document.querySelectorAll('input[aria-label], textarea[aria-label], select[aria-label]'))
                         .find(el => visible(el) &&
                               (el.getAttribute('aria-label') || '').toLowerCase().includes(t));
      if (aria) { aria.setAttribute('data-tegu-fill', id); return id; }
      // 4. text-near-input heuristic
      const all = Array.from(document.querySelectorAll('*')).filter(visible);
      for (const el of all) {
        if ((el.textContent || '').toLowerCase().trim() === t) {
          const inp = el.parentElement?.querySelector('input, textarea, select')
                    || el.querySelector('input, textarea, select')
                    || el.nextElementSibling?.querySelector?.('input, textarea, select');
          if (inp && visible(inp)) { inp.setAttribute('data-tegu-fill', id); return id; }
        }
      }
      return null;
    }
    """

    filled = 0
    for label, value in fields_r.items():
        token = None
        try:
            token = ctx.page.evaluate(js_resolve, label)
        except Exception:
            token = None

        if not token and use_ai:
            try:
                from .ai_providers import ask_llm
                html = ctx.page.content()[:8000]
                sel = ask_llm(
                    system=(
                        "You match a form field by its visible label. Return "
                        "ONLY a CSS selector for the matching <input>/"
                        "<textarea>/<select>. NOT_FOUND if absent."
                    ),
                    user=f"LABEL: {label}\nHTML:\n{html}",
                    max_tokens=120,
                    provider=p.get("provider"),
                ).strip()
                if sel and sel != "NOT_FOUND":
                    ctx.page.locator(sel).first.fill(str(value))
                    filled += 1
                    continue
            except Exception as e:
                ctx.logger.warning(f"fill_form: AI fallback failed for {label!r}: {e}")

        if not token:
            ctx.logger.warning(f"fill_form: no field for label {label!r}")
            continue

        sel = f'[data-tegu-fill="{token}"]'
        if human and ctx._human_keyboard is not None:
            try:
                ctx._human_keyboard.type_into(sel, str(value))
            except Exception:
                ctx.page.locator(sel).first.fill(str(value))
        else:
            ctx.page.locator(sel).first.fill(str(value))
        try:
            ctx.page.evaluate(
                "(s) => document.querySelector(s)?.removeAttribute('data-tegu-fill')",
                sel,
            )
        except Exception:
            pass
        filled += 1

    ctx.logger.info(f"fill_form_by_labels: filled {filled}/{len(fields_r)} fields")


@register("browser.click_text", required=("text",))
def _click_text(spec: StepSpec, ctx) -> None:
    """Smart click by visible text. Walks every interactive element on the
    page and clicks the first one whose visible text contains the target.

    Bypasses fragile CSS selector lists — works even when class names /
    data-testids change. Considers `<button>`, `<a>`, `[role=button]`,
    `[role=link]`, and `<div>`/`<span>` with `tabindex` (Twitter-style
    custom buttons).

    Optional:
      exact: bool — require equals (default False = substring contains)
      role: filter ('button' | 'link' | None for any)
      timeout_ms: how long to keep retrying as page renders
    """
    import time as _time
    p = spec.params
    target = ctx.render(p["text"]).strip()
    role = p.get("role")
    exact = bool(p.get("exact", False))
    timeout_ms = int(p.get("timeout_ms", 15_000))
    force = bool(p.get("force", True))

    js_find = """
    (args) => {
      const {target, role, exact} = args;
      const t = target.toLowerCase();
      // Candidate selectors widest-to-narrowest; we filter by text below.
      const sels = role === 'button'
        ? '[role=button], button, [tabindex]'
        : role === 'link'
          ? '[role=link], a[href], [tabindex]'
          : 'button, a[href], [role=button], [role=link], [tabindex], [onclick]';
      const all = Array.from(document.querySelectorAll(sels));
      function visible(el) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return false;
        const cs = getComputedStyle(el);
        return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0;
      }
      function txt(el) {
        const aria = el.getAttribute('aria-label') || '';
        const inner = (el.textContent || '').trim();
        return (aria + ' ' + inner).toLowerCase();
      }
      const match = all.find(el => {
        if (!visible(el)) return false;
        const s = txt(el);
        return exact ? s === t : s.includes(t);
      });
      if (!match) return null;
      // Mark for click via a unique attribute so the Playwright side can
      // re-locate it without re-running the heuristic.
      const id = '__tegu-click-' + Date.now() + '-' + Math.floor(Math.random()*1e6);
      match.setAttribute('data-tegu-click', id);
      return id;
    }
    """

    deadline = _time.monotonic() + timeout_ms / 1000.0
    found_id = None
    while _time.monotonic() < deadline:
        try:
            found_id = ctx.page.evaluate(
                js_find, {"target": target, "role": role, "exact": exact}
            )
        except Exception:
            found_id = None
        if found_id:
            break
        _time.sleep(0.3)

    if not found_id:
        raise RuntimeError(
            f"click_text: no visible element matched {target!r}"
            + (f" (role={role!r})" if role else "")
        )

    sel = f'[data-tegu-click="{found_id}"]'
    ctx.page.locator(sel).first.click(force=force, timeout=timeout_ms)
    try:
        ctx.page.evaluate(
            "(s) => { document.querySelector(s)?.removeAttribute('data-tegu-click'); }",
            sel,
        )
    except Exception:
        pass
    ctx.logger.info(f"click_text: clicked element matching {target!r}")


@register("browser.save_cookies", required=("path",))
def _save_cookies(spec: StepSpec, ctx) -> None:
    """Export browser-context cookies to a JSON file. Useful at the end of
    a successful login flow so the same session can be replayed without
    re-typing credentials.

    Optional `domain_contains` filters by cookie.domain substring (e.g.
    'google.com' to skip unrelated trackers).
    """
    import json as _json
    from pathlib import Path as _Path
    p = spec.params
    path = _Path(ctx.render(p["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    needle = (p.get("domain_contains") or "").strip()
    cookies = ctx.page.context.cookies()
    if needle:
        cookies = [c for c in cookies if needle in (c.get("domain") or "")]
    with path.open("w", encoding="utf-8") as f:
        _json.dump(cookies, f, indent=2, ensure_ascii=False)
    ctx.logger.info(f"saved {len(cookies)} cookies to {path}")


@register("browser.load_cookies", required=("path",))
def _load_cookies(spec: StepSpec, ctx) -> None:
    """Pre-populate the browser context with cookies from a JSON file
    written by browser.save_cookies. Call BEFORE the first browser.goto
    against the cookie's domain."""
    import json as _json
    from pathlib import Path as _Path
    path = _Path(ctx.render(spec.params["path"]))
    with path.open("r", encoding="utf-8") as f:
        cookies = _json.load(f)
    ctx.page.context.add_cookies(cookies)
    ctx.logger.info(f"loaded {len(cookies)} cookies from {path}")


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
