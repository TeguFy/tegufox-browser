"""Tests for the selector picker UI surface (no real browser launch)."""
import importlib.util

import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)

import tegufox_flow.steps.browser   # noqa  -- registers handlers

from tegufox_gui.widgets.editable_flow import EditableStep
from tegufox_gui.widgets.step_form_panel import StepFormPanel, SelectorPickerLineEdit


def test_picker_line_edit_round_trip(qapp):
    captured = []

    def picker(current: str):
        captured.append(current)
        return "#picked"

    w = SelectorPickerLineEdit(picker, placeholder="#submit")
    assert w.text() == ""
    w.setText("#existing")
    assert w.text() == "#existing"
    w._btn.click()
    assert captured == ["#existing"]
    assert w.text() == "#picked"


def test_picker_returns_none_keeps_existing(qapp):
    w = SelectorPickerLineEdit(picker=lambda _: None, placeholder="")
    w.setText("#stays")
    w._btn.click()
    assert w.text() == "#stays"


def test_panel_uses_picker_widget_for_selector_field(qapp):
    s = EditableStep(id="c", type="browser.click", params={"selector": "#a"})
    panel = StepFormPanel(selector_picker=lambda _: "#picked")
    panel.bind(s)
    selector_widget = panel._widgets["selector"]
    assert isinstance(selector_widget, SelectorPickerLineEdit)


def test_panel_no_picker_no_pick_button(qapp):
    s = EditableStep(id="c", type="browser.click", params={"selector": "#a"})
    panel = StepFormPanel()
    panel.bind(s)
    selector_widget = panel._widgets["selector"]
    assert not isinstance(selector_widget, SelectorPickerLineEdit)


def test_panel_other_string_fields_skip_picker(qapp):
    """The picker only applies to fields named 'selector', not 'text'/'url'."""
    s = EditableStep(id="t", type="browser.type",
                     params={"selector": "#i", "text": "hi"})
    panel = StepFormPanel(selector_picker=lambda _: "#picked")
    panel.bind(s)
    assert isinstance(panel._widgets["selector"], SelectorPickerLineEdit)
    assert not isinstance(panel._widgets["text"], SelectorPickerLineEdit)


def test_panel_round_trip_with_picker(qapp):
    s = EditableStep(id="c", type="browser.click", params={"selector": "#a"})
    panel = StepFormPanel(selector_picker=lambda _: None)
    panel.bind(s)
    out = panel.read_back()
    assert out.params["selector"] == "#a"


def test_dialog_constructs(qapp):
    from tegufox_gui.dialogs.selector_picker_dialog import SelectorPickerDialog
    dlg = SelectorPickerDialog(profile_names=["alice", "bob"],
                                default_url="https://example.com")
    assert dlg.profile_combo.count() == 2
    assert dlg.url_edit.text() == "https://example.com"
    assert dlg.selected_selector() == ""
    assert not dlg.use_btn.isEnabled()
    assert not dlg.test_btn.isEnabled()
    # Picked HTML and paste HTML areas exist for debug + detect.
    assert dlg.picked_html_view.toPlainText() == ""
    assert dlg.paste_html_edit.toPlainText() == ""


def test_typing_selector_enables_use_button(qapp):
    from tegufox_gui.dialogs.selector_picker_dialog import SelectorPickerDialog
    dlg = SelectorPickerDialog(profile_names=["a"])
    dlg.selected_edit.setText("#submit")
    assert dlg.use_btn.isEnabled()
    # Test Click stays disabled until browser is open.
    assert not dlg.test_btn.isEnabled()


def test_detect_button_extracts_selector_from_html(qapp):
    from tegufox_gui.dialogs.selector_picker_dialog import SelectorPickerDialog
    dlg = SelectorPickerDialog(profile_names=["a"])
    dlg.paste_html_edit.setPlainText(
        '<button id="signin" class="btn primary">Sign in</button>'
    )
    dlg.detect_btn.click()
    assert dlg.selected_edit.text() == "#signin"


def test_html_to_selector_priority():
    from tegufox_gui.dialogs.selector_picker_dialog import html_to_selector

    assert html_to_selector('<div id="x"></div>') == "#x"
    assert html_to_selector('<div data-testid="t"></div>') == '[data-testid="t"]'
    assert html_to_selector('<div data-test="t"></div>') == '[data-test="t"]'
    assert html_to_selector('<input name="email">') == 'input[name="email"]'
    assert html_to_selector('<button aria-label="Close">x</button>') == 'button[aria-label="Close"]'
    assert html_to_selector('<button class="btn primary">Hi</button>') == 'button.primary'
    assert html_to_selector('<span></span>') == "span"
    # id wins over class
    assert html_to_selector('<a id="go" class="link" href="/">x</a>') == "#go"


def test_html_to_selector_handles_garbage():
    from tegufox_gui.dialogs.selector_picker_dialog import html_to_selector
    assert html_to_selector("") is None
    assert html_to_selector("   ") is None
    assert html_to_selector("not html") is None


def test_html_to_selector_self_closing_input():
    from tegufox_gui.dialogs.selector_picker_dialog import html_to_selector
    assert html_to_selector('<input name="q" type="text" />') == 'input[name="q"]'
