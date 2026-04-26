# tests/orchestrator/test_batch_dialog.py
import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_batch_dialog_constructs(qapp, tmp_path):
    from tegufox_gui.dialogs.batch_run_dialog import BatchRunDialog
    dlg = BatchRunDialog(
        flow_name="x",
        flow_yaml="schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n",
        profile_names=["alice", "bob"],
        db_path=str(tmp_path / "t.db"),
    )
    assert dlg.profile_list.count() == 2
    assert dlg.max_concurrent_spin.value() == 3


def test_flows_page_has_batch_button(qapp, tmp_path):
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage(db_path=str(tmp_path / "t.db"))
    assert hasattr(page, "batch_btn")
    assert page.batch_btn is not None
