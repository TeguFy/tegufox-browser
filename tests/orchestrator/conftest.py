# tests/orchestrator/conftest.py
import importlib.util
import sys

import pytest


@pytest.fixture(scope="session")
def qapp():
    if importlib.util.find_spec("PyQt6") is None:
        pytest.skip("PyQt6 not available", allow_module_level=False)
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)
