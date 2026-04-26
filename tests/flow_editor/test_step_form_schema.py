import pytest
from tegufox_gui.widgets.step_form_schema import STEP_FORM, Field, fields_for

# Make sure the registered step types are imported, so STEP_REGISTRY is populated.
import tegufox_flow.steps.browser  # noqa
import tegufox_flow.steps.extract  # noqa
import tegufox_flow.steps.control  # noqa
import tegufox_flow.steps.io       # noqa
import tegufox_flow.steps.state    # noqa

from tegufox_flow.steps import STEP_REGISTRY


def test_every_registered_step_has_form_schema():
    missing = sorted(set(STEP_REGISTRY) - set(STEP_FORM))
    assert missing == [], f"step types missing from STEP_FORM: {missing}"


def test_form_schema_required_fields_match_handler_required():
    for step_type, handler in STEP_REGISTRY.items():
        required_fields = {f.name for f in STEP_FORM[step_type] if f.required}
        handler_required = set(getattr(handler, "required", ()))
        assert handler_required.issubset(required_fields), (
            f"{step_type}: handler requires {handler_required - required_fields} "
            f"but STEP_FORM does not mark them required"
        )


def test_fields_for_unknown_returns_empty():
    assert fields_for("ghost.step") == []


def test_field_kinds_are_in_expected_set():
    valid = {"string", "int", "bool", "select", "code", "steps"}
    for step_type, fields in STEP_FORM.items():
        for f in fields:
            assert f.kind in valid, f"{step_type}.{f.name} has invalid kind {f.kind!r}"
