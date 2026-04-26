import json
import pytest
from datetime import datetime
from tegufox_flow.expressions import ExpressionEngine


@pytest.fixture
def eng():
    return ExpressionEngine()


def test_render_string_with_var(eng):
    assert eng.render("hello {{ name }}", {"name": "world"}) == "hello world"


def test_render_returns_str_even_for_int(eng):
    assert eng.render("{{ n + 1 }}", {"n": 5}) == "6"


def test_eval_returns_native_python(eng):
    assert eng.eval("n + 1", {"n": 5}) == 6
    assert eng.eval("xs | length", {"xs": [1, 2, 3]}) == 3


def test_filter_slug(eng):
    assert eng.eval("'Hello, World!' | slug", {}) == "hello-world"


def test_filter_tojson(eng):
    out = eng.render("{{ d | tojson }}", {"d": {"a": 1}})
    assert json.loads(out) == {"a": 1}


def test_filter_b64(eng):
    enc = eng.render("{{ 'abc' | b64encode }}", {})
    assert enc == "YWJj"
    dec = eng.render("{{ 'YWJj' | b64decode }}", {})
    assert dec == "abc"


def test_helper_now(eng, monkeypatch):
    fixed = datetime(2026, 1, 2, 3, 4, 5)
    monkeypatch.setattr("tegufox_flow.expressions._dt_now", lambda: fixed)
    out = eng.eval("now()", {})
    assert out == fixed


def test_helper_random_int_within_range(eng):
    for _ in range(50):
        x = eng.eval("random_int(0, 5)", {})
        assert 0 <= x <= 5


def test_sandbox_blocks_dunder_access(eng):
    with pytest.raises(Exception):
        eng.eval("().__class__", {})


def test_sandbox_blocks_attr_to_function(eng):
    with pytest.raises(Exception):
        eng.eval("foo.__init__", {"foo": object()})


def test_undefined_var_raises(eng):
    with pytest.raises(Exception):
        eng.eval("missing_var + 1", {})


def test_render_keeps_strings_without_templates(eng):
    assert eng.render("plain text", {}) == "plain text"
