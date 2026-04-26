"""Modal editor for nested step bodies (control.if then/else, for_each body, while body).

v1 stub: opens with a placeholder explaining the feature is coming. The
calling button preserves the nested step list across save/cancel.
v1.5 wires in StepListWidget + StepFormPanel for full editing.
"""

from __future__ import annotations
from typing import List

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from .editable_flow import EditableStep


class NestedBodyDialog(QDialog):
    def __init__(self, items: List[EditableStep], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit nested body")
        self._result = list(items)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Nested body has {len(items)} step{'s' if len(items)!=1 else ''}.\n"
            "Full inline editing arrives in v1.5; for now you can save/cancel."
        ))
        row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(ok)
        layout.addLayout(row)

    def result_steps(self) -> List[EditableStep]:
        return self._result
