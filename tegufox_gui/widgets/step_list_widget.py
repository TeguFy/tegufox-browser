"""Centre-pane step list with drag-to-reorder.

Each row shows: <index>. <id> — <type>.  The widget keeps its own list of
EditableStep objects in sync with QListWidget rows.
"""

from __future__ import annotations
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

from .editable_flow import EditableStep


class StepListWidget(QListWidget):
    step_selected = pyqtSignal(int, object)
    steps_reordered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._steps: List[EditableStep] = []
        self.currentRowChanged.connect(self._emit_selected)
        self.model().rowsMoved.connect(self._on_rows_moved)

    def steps(self) -> List[EditableStep]:
        return list(self._steps)

    def set_steps(self, xs: List[EditableStep]) -> None:
        self._steps = list(xs)
        self.clear()
        for i, s in enumerate(self._steps):
            self.addItem(self._format_row(i, s))

    def add(self, s: EditableStep) -> None:
        self._steps.append(s)
        self.addItem(self._format_row(len(self._steps) - 1, s))

    def remove(self, idx: int) -> None:
        if 0 <= idx < len(self._steps):
            del self._steps[idx]
            self.takeItem(idx)
            self._refresh_labels()

    def update_at(self, idx: int, s: EditableStep) -> None:
        if 0 <= idx < len(self._steps):
            self._steps[idx] = s
            self.item(idx).setText(self._format_text(idx, s))

    @staticmethod
    def _format_text(i: int, s: EditableStep) -> str:
        return f"{i + 1}. {s.id}  —  {s.type}"

    def _format_row(self, i: int, s: EditableStep) -> QListWidgetItem:
        return QListWidgetItem(self._format_text(i, s))

    def _refresh_labels(self):
        for i in range(self.count()):
            self.item(i).setText(self._format_text(i, self._steps[i]))

    def _emit_selected(self, row: int):
        if 0 <= row < len(self._steps):
            self.step_selected.emit(row, self._steps[row])

    def _on_rows_moved(self, _src_parent, src_start, src_end, _dst_parent, dst_row):
        moved = self._steps[src_start:src_end + 1]
        del self._steps[src_start:src_end + 1]
        insert_at = dst_row if dst_row <= src_start else dst_row - len(moved)
        self._steps[insert_at:insert_at] = moved
        self._refresh_labels()
        self.steps_reordered.emit()
