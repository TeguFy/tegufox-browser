# tests/flow/test_steps_extract.py
import pytest
from unittest.mock import MagicMock

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.extract  # noqa


@pytest.fixture
def ctx():
    c = MagicMock()
    c.page = MagicMock()
    c.render.side_effect = lambda s: s
    return c


def test_read_text(ctx):
    locator = MagicMock()
    locator.inner_text.return_value = "hello"
    ctx.page.locator.return_value = locator
    handler = get_handler("extract.read_text")
    handler(StepSpec(id="e", type="extract.read_text",
                     params={"selector": "h1", "set": "out"}), ctx)
    ctx.page.locator.assert_called_once_with("h1")
    ctx.set_var.assert_called_once_with("out", "hello")


def test_read_attr(ctx):
    locator = MagicMock()
    locator.get_attribute.return_value = "/x"
    ctx.page.locator.return_value = locator
    handler = get_handler("extract.read_attr")
    handler(StepSpec(id="e", type="extract.read_attr",
                     params={"selector": "a", "attr": "href", "set": "h"}), ctx)
    locator.get_attribute.assert_called_once_with("href")
    ctx.set_var.assert_called_once_with("h", "/x")


def test_eval_js(ctx):
    ctx.page.evaluate.return_value = [1, 2, 3]
    handler = get_handler("extract.eval_js")
    handler(StepSpec(id="e", type="extract.eval_js",
                     params={"script": "() => [1,2,3]", "set": "arr"}), ctx)
    ctx.page.evaluate.assert_called_once_with("() => [1,2,3]")
    ctx.set_var.assert_called_once_with("arr", [1, 2, 3])


def test_url(ctx):
    ctx.page.url = "https://x"
    handler = get_handler("extract.url")
    handler(StepSpec(id="e", type="extract.url", params={"set": "u"}), ctx)
    ctx.set_var.assert_called_once_with("u", "https://x")


def test_title(ctx):
    ctx.page.title.return_value = "T"
    handler = get_handler("extract.title")
    handler(StepSpec(id="e", type="extract.title", params={"set": "t"}), ctx)
    ctx.set_var.assert_called_once_with("t", "T")
