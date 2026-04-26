import pytest
from tegufox_flow.steps import register, STEP_REGISTRY, get_handler, StepSpec


def test_register_adds_handler():
    @register("test.echo", required=("text",), optional=("upper",))
    def echo(spec: StepSpec, ctx):
        return spec.params["text"]
    assert "test.echo" in STEP_REGISTRY
    assert get_handler("test.echo") is echo
    del STEP_REGISTRY["test.echo"]


def test_get_handler_unknown_raises():
    with pytest.raises(KeyError) as e:
        get_handler("ghost.step")
    assert "ghost.step" in str(e.value)


def test_register_validates_required_params_at_call():
    @register("test.req", required=("must",))
    def fn(spec, ctx):
        return spec.params["must"]
    spec = StepSpec(id="x", type="test.req", params={})
    with pytest.raises(KeyError) as e:
        fn(spec, ctx=None)
    assert "must" in str(e.value)
    del STEP_REGISTRY["test.req"]


def test_register_rejects_duplicate():
    @register("test.dup")
    def a(spec, ctx): pass
    with pytest.raises(ValueError):
        @register("test.dup")
        def b(spec, ctx): pass
    del STEP_REGISTRY["test.dup"]
