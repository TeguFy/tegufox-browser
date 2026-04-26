import pytest


def test_flows_page_has_new_flow_button(qapp, tmp_path):
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage(db_path=str(tmp_path / "t.db"))
    assert hasattr(page, "new_btn"), "FlowsPage should expose a 'new_btn' attribute"
    assert page.new_btn is not None
