import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.browser  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    return c


# ---------- Task 14: navigation/passive ----------

def test_goto(ctx):
    get_handler("browser.goto")(
        StepSpec(id="g", type="browser.goto",
                 params={"url": "https://x", "wait_until": "load", "timeout_ms": 5000}),
        ctx,
    )
    ctx.page.goto.assert_called_once_with("https://x", wait_until="load", timeout=5000)


def test_wait_for_visible_default(ctx):
    get_handler("browser.wait_for")(
        StepSpec(id="w", type="browser.wait_for",
                 params={"selector": "#x", "timeout_ms": 1000}),
        ctx,
    )
    ctx.page.locator.assert_called_once_with("#x")
    ctx.page.locator.return_value.wait_for.assert_called_once_with(state="visible", timeout=1000)


def test_screenshot_full_page(tmp_path, ctx):
    out = tmp_path / "shot.png"
    get_handler("browser.screenshot")(
        StepSpec(id="s", type="browser.screenshot",
                 params={"path": str(out), "full_page": True}),
        ctx,
    )
    ctx.page.screenshot.assert_called_once_with(path=str(out), full_page=True)


def test_screenshot_element(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.screenshot")(
        StepSpec(id="s", type="browser.screenshot",
                 params={"path": "x.png", "selector": "#card"}),
        ctx,
    )
    ctx.page.locator.assert_called_once_with("#card")
    locator.screenshot.assert_called_once_with(path="x.png")


def test_press_key_global(ctx):
    get_handler("browser.press_key")(
        StepSpec(id="p", type="browser.press_key",
                 params={"key": "Enter"}),
        ctx,
    )
    ctx.page.keyboard.press.assert_called_once_with("Enter")


def test_press_key_focused(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.press_key")(
        StepSpec(id="p", type="browser.press_key",
                 params={"key": "Tab", "selector": "#x"}),
        ctx,
    )
    locator.press.assert_called_once_with("Tab")


def test_scroll_pixels_down(ctx):
    get_handler("browser.scroll")(
        StepSpec(id="s", type="browser.scroll",
                 params={"direction": "down", "pixels": 500}),
        ctx,
    )
    ctx.page.mouse.wheel.assert_called_once_with(0, 500)


def test_scroll_to_bottom(ctx):
    get_handler("browser.scroll")(
        StepSpec(id="s", type="browser.scroll", params={"to": "bottom"}),
        ctx,
    )
    ctx.page.evaluate.assert_called_once()
    arg = ctx.page.evaluate.call_args.args[0]
    assert "scrollHeight" in arg


def test_select_option(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.select_option")(
        StepSpec(id="s", type="browser.select_option",
                 params={"selector": "select", "value": "v"}),
        ctx,
    )
    locator.select_option.assert_called_once_with("v")


# ---------- Task 15: interactive ----------

def test_click_human(ctx):
    ctx._human_mouse = MagicMock()
    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click", params={"selector": "#b"}),
        ctx,
    )
    ctx._human_mouse.click.assert_called_once_with("#b")


def test_click_non_human(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click",
                 params={"selector": "#b", "human": False}),
        ctx,
    )
    locator.click.assert_called_once()


def test_type_human(ctx):
    ctx._human_keyboard = MagicMock()
    get_handler("browser.type")(
        StepSpec(id="t", type="browser.type",
                 params={"selector": "#i", "text": "hi"}),
        ctx,
    )
    ctx._human_keyboard.type_into.assert_called_once_with("#i", "hi")


def test_type_clear_first(ctx):
    locator = MagicMock()
    ctx.page.locator.return_value = locator
    ctx._human_keyboard = MagicMock()
    get_handler("browser.type")(
        StepSpec(id="t", type="browser.type",
                 params={"selector": "#i", "text": "hi", "clear_first": True}),
        ctx,
    )
    locator.fill.assert_called_once_with("")
    ctx._human_keyboard.type_into.assert_called_once_with("#i", "hi")


def test_hover_human(ctx):
    ctx._human_mouse = MagicMock()
    get_handler("browser.hover")(
        StepSpec(id="h", type="browser.hover", params={"selector": "#x"}),
        ctx,
    )
    ctx._human_mouse.move_to.assert_called_once_with("#x")


def test_click_human_falls_back_to_native_on_error():
    """If HumanMouse raises (e.g. Firefox missing windowUtils.sendMouseEvent),
    the step still completes via native page.locator().click()."""
    from unittest.mock import MagicMock
    import logging
    from tegufox_flow.steps import StepSpec, get_handler

    ctx = MagicMock()
    ctx.page = MagicMock()
    ctx.render.side_effect = lambda s: s
    ctx.logger = logging.getLogger("test_fallback")
    ctx._human_mouse = MagicMock()
    ctx._human_mouse.click.side_effect = RuntimeError(
        "Protocol error (Page.dispatchMouseEvent)"
    )
    locator = MagicMock()
    ctx.page.locator.return_value = locator

    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click", params={"selector": "#b"}),
        ctx,
    )
    ctx._human_mouse.click.assert_called_once_with("#b")
    locator.click.assert_called_once()


def test_type_human_falls_back_to_native_on_error():
    from unittest.mock import MagicMock
    import logging
    from tegufox_flow.steps import StepSpec, get_handler

    ctx = MagicMock()
    ctx.page = MagicMock()
    ctx.render.side_effect = lambda s: s
    ctx.logger = logging.getLogger("test_fallback")
    ctx._human_keyboard = MagicMock()
    ctx._human_keyboard.type_into.side_effect = RuntimeError("nope")
    locator = MagicMock()
    ctx.page.locator.return_value = locator

    get_handler("browser.type")(
        StepSpec(id="t", type="browser.type",
                 params={"selector": "#i", "text": "hi"}),
        ctx,
    )
    ctx._human_keyboard.type_into.assert_called_once_with("#i", "hi")
    locator.type.assert_called_once_with("hi", delay=0)


def test_click_human_none_uses_native():
    """When _human_mouse is None (e.g. tegufox_automation import failed at
    runtime), the click still succeeds via native fallback."""
    from unittest.mock import MagicMock
    from tegufox_flow.steps import StepSpec, get_handler

    ctx = MagicMock()
    ctx.page = MagicMock()
    ctx.render.side_effect = lambda s: s
    ctx._human_mouse = None
    locator = MagicMock()
    ctx.page.locator.return_value = locator

    get_handler("browser.click")(
        StepSpec(id="c", type="browser.click", params={"selector": "#b"}),
        ctx,
    )
    locator.click.assert_called_once()
