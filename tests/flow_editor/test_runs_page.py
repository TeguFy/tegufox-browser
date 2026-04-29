"""Smoke test for the Runs dashboard page."""
import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_runs_page_constructs(qapp, tmp_path):
    from tegufox_gui.pages.runs_page import RunsPage
    page = RunsPage(db_path=str(tmp_path / "t.db"))
    assert page.runs_table is not None
    assert page.batches_table is not None
    assert page.flow_filter.count() >= 1   # at least the "(all flows)" entry
    # Buttons start disabled (nothing selected).
    assert not page.replay_btn.isEnabled()
    assert not page.delete_btn.isEnabled()
