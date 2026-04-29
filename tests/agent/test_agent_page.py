import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_agent_page_constructs(qapp, tmp_path):
    from tegufox_gui.pages.agent_page import AgentPage
    page = AgentPage(db_path=str(tmp_path / "t.db"))
    assert page.goal_edit is not None
    assert page.run_btn is not None
    assert page.stop_btn is not None
    assert page.trace_view is not None
    assert page.profile_combo is not None
    assert page.proxy_combo is not None
    assert page.max_steps_spin.value() == 30
    assert page.record_chk.isChecked() is False
    assert not page.stop_btn.isEnabled()


def test_agent_page_append_trace(qapp, tmp_path):
    from tegufox_gui.pages.agent_page import AgentPage
    page = AgentPage(db_path=str(tmp_path / "t.db"))
    page._append_trace("Step 1 [goto] https://x")
    assert "Step 1" in page.trace_view.toPlainText()
