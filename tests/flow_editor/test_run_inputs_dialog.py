"""Tests for RunInputsDialog (used by Flows page Run button)."""
import importlib.util

import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)

from tegufox_flow.dsl import Input
from tegufox_gui.dialogs.run_inputs_dialog import RunInputsDialog


def test_no_inputs_dialog(qapp):
    dlg = RunInputsDialog("flow_x", {})
    assert dlg.values() == {}


def test_string_input_required_default(qapp):
    decl = {"q": Input(type="string", required=True)}
    dlg = RunInputsDialog("flow_x", decl)
    dlg._widgets["q"].setText("laptop")
    assert dlg.values() == {"q": "laptop"}


def test_password_input_uses_password_echo(qapp):
    from PyQt6.QtWidgets import QLineEdit
    decl = {"password": Input(type="string", required=True)}
    dlg = RunInputsDialog("login", decl)
    assert dlg._widgets["password"].echoMode() == QLineEdit.EchoMode.Password


def test_token_input_uses_password_echo(qapp):
    from PyQt6.QtWidgets import QLineEdit
    decl = {"api_token": Input(type="string", required=True)}
    dlg = RunInputsDialog("api", decl)
    assert dlg._widgets["api_token"].echoMode() == QLineEdit.EchoMode.Password


def test_int_input_default(qapp):
    decl = {"n": Input(type="int", default=10)}
    dlg = RunInputsDialog("x", decl)
    assert dlg.values() == {"n": 10}


def test_bool_input(qapp):
    decl = {"verbose": Input(type="bool", default=True)}
    dlg = RunInputsDialog("x", decl)
    assert dlg.values() == {"verbose": True}


def test_list_input_json(qapp):
    decl = {"items": Input(type="list", required=True)}
    dlg = RunInputsDialog("x", decl)
    dlg._widgets["items"].setPlainText('["a","b","c"]')
    assert dlg.values() == {"items": ["a", "b", "c"]}


def test_list_input_csv_fallback(qapp):
    decl = {"items": Input(type="list", required=True)}
    dlg = RunInputsDialog("x", decl)
    dlg._widgets["items"].setPlainText("a, b, c")
    assert dlg.values() == {"items": ["a", "b", "c"]}


def test_optional_string_skipped_when_empty(qapp):
    decl = {"opt": Input(type="string")}
    dlg = RunInputsDialog("x", decl)
    # Leave empty; optional → not in values()
    assert dlg.values() == {}


def test_run_button_blocks_on_missing_required(qapp):
    decl = {"email": Input(type="string", required=True)}
    dlg = RunInputsDialog("x", decl)
    # Simulate clicking Run with empty email
    dlg._on_run()
    assert "email" in dlg._missing_label.text()
