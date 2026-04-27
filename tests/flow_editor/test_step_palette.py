import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.extract   # noqa
import tegufox_flow.steps.control   # noqa
import tegufox_flow.steps.io        # noqa
import tegufox_flow.steps.state     # noqa

from tegufox_gui.widgets.step_palette import StepPalette


def test_palette_lists_5_categories(qapp):
    p = StepPalette()
    assert p.categories() == ["ai", "browser", "control", "extract", "io", "state"]


def test_palette_has_all_step_types(qapp):
    p = StepPalette()
    types = sum((p.types_in(c) for c in p.categories()), [])
    assert len(types) == 42
    assert "browser.goto" in types
    assert "browser.disable_popups" in types
    assert "browser.save_cookies" in types
    assert "browser.load_cookies" in types
    assert "browser.click_and_wait_popup" in types
    assert "browser.wait_for_popup" in types
    assert "browser.wait_for_url" in types
    assert "browser.switch_to_main" in types
    assert "io.record" in types
    assert "control.for_each" in types
    assert "state.delete" in types


def test_palette_emits_step_added(qapp):
    p = StepPalette()
    seen = []
    p.step_chosen.connect(lambda t: seen.append(t))
    p._emit_choice("browser.click")
    assert seen == ["browser.click"]
