import importlib.util
import sys
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PyQt6") is None,
    reason="PyQt6 not available",
)


def test_flows_page_constructs(tmp_path):
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage(db_path=str(tmp_path / "t.db"))
    assert page is not None
    # The page should have the basic widgets we expect.
    assert page.list_widget is not None
    assert page.profile_combo is not None
    assert page.run_btn is not None
    assert page.upload_btn is not None
