"""I/O step handlers: log, read_file, write_file, http_request."""

from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any, Dict

import requests

from . import register, StepSpec


_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


@register("io.log", required=("message",))
def _log(spec: StepSpec, ctx) -> None:
    level = _LEVELS[spec.params.get("level", "info")]
    msg = ctx.render(spec.params["message"])
    ctx.logger.log(level, msg)


@register("io.write_file", required=("path", "content"))
def _write_file(spec: StepSpec, ctx) -> None:
    path = Path(ctx.render(spec.params["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ctx.render(spec.params["content"]) if isinstance(spec.params["content"], str) else json.dumps(spec.params["content"])
    mode = "a" if spec.params.get("append") else "w"
    encoding = spec.params.get("encoding", "utf-8")
    with path.open(mode, encoding=encoding) as f:
        f.write(content)


@register("io.read_file", required=("path", "set"))
def _read_file(spec: StepSpec, ctx) -> None:
    path = Path(ctx.render(spec.params["path"]))
    encoding = spec.params.get("encoding", "utf-8")
    fmt = spec.params.get("format", "text")
    with path.open("r", encoding=encoding) as f:
        text = f.read()
    if fmt == "text":
        out: Any = text
    elif fmt == "json":
        out = json.loads(text)
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        out = list(reader)
    else:
        raise ValueError(f"unknown format {fmt!r}")
    ctx.set_var(spec.params["set"], out)


@register("io.http_request", required=("method", "url"))
def _http_request(spec: StepSpec, ctx) -> None:
    p = spec.params
    kwargs: Dict[str, Any] = {
        "method": p["method"].upper(),
        "url": ctx.render(p["url"]),
        "timeout": p.get("timeout_ms", 30_000) / 1000.0,
    }
    if "headers" in p:
        kwargs["headers"] = {k: ctx.render(v) for k, v in p["headers"].items()}
    if "body" in p:
        body = p["body"]
        if isinstance(body, str):
            kwargs["data"] = ctx.render(body)
        else:
            kwargs["json"] = body

    resp = requests.request(**kwargs)
    payload: Dict[str, Any] = {
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text,
    }
    try:
        payload["json"] = resp.json()
    except Exception:
        payload["json"] = None

    if "set" in p:
        ctx.set_var(p["set"], payload)
