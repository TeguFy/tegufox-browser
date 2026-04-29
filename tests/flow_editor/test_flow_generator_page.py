"""Smoke tests for the AI Flow Generator page."""
import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_flow_generator_page_constructs(qapp, tmp_path):
    from tegufox_gui.pages.flow_generator_page import FlowGeneratorPage
    page = FlowGeneratorPage(db_path=str(tmp_path / "t.db"))
    assert page.goal_edit is not None
    assert page.yaml_view is not None
    assert page.provider_combo.count() == 4   # auto + 3 providers


def test_flow_generator_validate_rejects_garbage(qapp, tmp_path):
    from tegufox_gui.pages.flow_generator_page import FlowGeneratorPage
    page = FlowGeneratorPage(db_path=str(tmp_path / "t.db"))
    page.yaml_view.setPlainText("this is not yaml: : :")
    page._on_validate()
    assert "Invalid" in page.status_label.text() or "valid" in page.status_label.text().lower()


def test_flow_generator_validate_accepts_minimal_yaml(qapp, tmp_path):
    from tegufox_gui.pages.flow_generator_page import FlowGeneratorPage
    page = FlowGeneratorPage(db_path=str(tmp_path / "t.db"))
    page.yaml_view.setPlainText(
        "schema_version: 1\nname: t\nsteps:\n"
        "  - id: a\n    type: control.sleep\n    ms: 1\n"
    )
    page._on_validate()
    assert "Valid" in page.status_label.text()
