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
