import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.control   # noqa

from tegufox_gui.widgets.editable_flow import EditableStep
from tegufox_gui.widgets.step_form_panel import StepFormPanel


def test_panel_renders_browser_goto(qapp):
    s = EditableStep(id="open", type="browser.goto",
                     params={"url": "https://x", "wait_until": "load", "timeout_ms": 5000})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert out.id == "open"
    assert out.type == "browser.goto"
    assert out.params["url"] == "https://x"
    assert out.params["wait_until"] == "load"
    assert out.params["timeout_ms"] == 5000


def test_panel_round_trip_bool(qapp):
    s = EditableStep(id="c", type="browser.click",
                     params={"selector": "#b", "human": False})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert out.params["human"] is False


def test_panel_steps_kind_uses_button(qapp):
    s = EditableStep(id="i", type="control.if",
                     params={"when": "{{ true }}", "then": [
                         EditableStep(id="x", type="control.sleep", params={"ms": 1})
                     ]})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert len(out.params["then"]) == 1
    assert out.params["then"][0].type == "control.sleep"


def test_panel_handles_unknown_type_gracefully(qapp):
    s = EditableStep(id="x", type="ghost.unknown", params={"foo": "bar"})
    panel = StepFormPanel()
    panel.bind(s)
    out = panel.read_back()
    assert out.params == {"foo": "bar"}
