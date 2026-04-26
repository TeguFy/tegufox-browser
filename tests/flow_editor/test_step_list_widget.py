import pytest

import tegufox_flow.steps.browser   # noqa

from tegufox_gui.widgets.editable_flow import EditableStep
from tegufox_gui.widgets.step_list_widget import StepListWidget


def test_list_starts_empty(qapp):
    w = StepListWidget()
    assert w.steps() == []


def test_add_step_appends(qapp):
    w = StepListWidget()
    s = EditableStep(id="a", type="browser.goto", params={"url": "https://x"})
    w.add(s)
    assert len(w.steps()) == 1
    assert w.steps()[0].id == "a"


def test_remove_at_index(qapp):
    w = StepListWidget()
    w.add(EditableStep(id="a", type="control.sleep", params={"ms": 1}))
    w.add(EditableStep(id="b", type="control.sleep", params={"ms": 2}))
    w.remove(0)
    assert [s.id for s in w.steps()] == ["b"]


def test_set_steps_replaces(qapp):
    w = StepListWidget()
    w.add(EditableStep(id="x", type="control.sleep", params={"ms": 1}))
    new = [
        EditableStep(id="a", type="control.sleep", params={"ms": 1}),
        EditableStep(id="b", type="control.sleep", params={"ms": 2}),
    ]
    w.set_steps(new)
    assert [s.id for s in w.steps()] == ["a", "b"]


def test_signal_emitted_on_selection(qapp):
    w = StepListWidget()
    s = EditableStep(id="a", type="control.sleep", params={"ms": 1})
    w.add(s)
    received = []
    w.step_selected.connect(lambda i, st: received.append((i, st.id)))
    w.setCurrentRow(0)
    assert received == [(0, "a")]
