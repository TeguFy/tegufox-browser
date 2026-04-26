"""Left-pane step palette — categorised tree of step types."""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, List

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from .step_form_schema import STEP_FORM


class StepPalette(QTreeWidget):
    step_chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self._cat_to_types: Dict[str, List[str]] = defaultdict(list)
        for step_type in sorted(STEP_FORM):
            cat = step_type.split(".", 1)[0]
            self._cat_to_types[cat].append(step_type)

        for cat in self.categories():
            cat_item = QTreeWidgetItem([cat])
            self.addTopLevelItem(cat_item)
            for st in self._cat_to_types[cat]:
                child = QTreeWidgetItem([st.split(".", 1)[1]])
                child.setData(0, 0x100, st)
                cat_item.addChild(child)
            cat_item.setExpanded(True)

        self.itemDoubleClicked.connect(self._on_double)

    def categories(self) -> List[str]:
        return sorted(self._cat_to_types)

    def types_in(self, category: str) -> List[str]:
        return list(self._cat_to_types.get(category, []))

    def _on_double(self, item: QTreeWidgetItem, _col: int):
        step_type = item.data(0, 0x100)
        if isinstance(step_type, str) and "." in step_type:
            self._emit_choice(step_type)

    def _emit_choice(self, step_type: str) -> None:
        self.step_chosen.emit(step_type)
