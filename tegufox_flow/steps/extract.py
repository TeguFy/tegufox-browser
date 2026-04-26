"""Extract data from the current page into vars."""

from . import register, StepSpec


@register("extract.read_text", required=("selector", "set"))
def _read_text(spec, ctx) -> None:
    sel = ctx.render(spec.params["selector"])
    text = ctx.page.locator(sel).first.inner_text()
    ctx.set_var(spec.params["set"], text)


@register("extract.read_attr", required=("selector", "attr", "set"))
def _read_attr(spec, ctx) -> None:
    sel = ctx.render(spec.params["selector"])
    attr = spec.params["attr"]
    val = ctx.page.locator(sel).first.get_attribute(attr)
    ctx.set_var(spec.params["set"], val)


@register("extract.eval_js", required=("script", "set"))
def _eval_js(spec, ctx) -> None:
    script = ctx.render(spec.params["script"])
    val = ctx.page.evaluate(script)
    ctx.set_var(spec.params["set"], val)


@register("extract.url", required=("set",))
def _url(spec, ctx) -> None:
    ctx.set_var(spec.params["set"], ctx.page.url)


@register("extract.title", required=("set",))
def _title(spec, ctx) -> None:
    ctx.set_var(spec.params["set"], ctx.page.title())
