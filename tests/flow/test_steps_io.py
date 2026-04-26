# tests/flow/test_steps_io.py
import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tegufox_flow.steps import StepSpec, get_handler
import tegufox_flow.steps.io  # noqa: F401


@pytest.fixture
def ctx():
    c = MagicMock()
    c.vars = {}
    c.render.side_effect = lambda s: s
    c.eval.side_effect = lambda e: eval(e, {}, {})
    c.logger = logging.getLogger("test")
    return c


def test_log_emits_at_level(ctx, caplog):
    caplog.set_level(logging.WARNING, logger="test")
    handler = get_handler("io.log")
    handler(StepSpec(id="l", type="io.log",
                     params={"message": "warn me", "level": "warning"}), ctx)
    assert any("warn me" in r.message for r in caplog.records)


def test_write_file_creates_dirs(tmp_path, ctx):
    target = tmp_path / "sub" / "out.txt"
    handler = get_handler("io.write_file")
    handler(StepSpec(id="w", type="io.write_file",
                     params={"path": str(target), "content": "hi"}), ctx)
    assert target.read_text() == "hi"


def test_write_file_append(tmp_path, ctx):
    target = tmp_path / "log.txt"
    target.write_text("a")
    handler = get_handler("io.write_file")
    handler(StepSpec(id="w", type="io.write_file",
                     params={"path": str(target), "content": "b", "append": True}), ctx)
    assert target.read_text() == "ab"


def test_read_file_text(tmp_path, ctx):
    f = tmp_path / "x.txt"
    f.write_text("hello")
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "set": "out"}), ctx)
    ctx.set_var.assert_called_once_with("out", "hello")


def test_read_file_json(tmp_path, ctx):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"a": 1}))
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "format": "json", "set": "out"}), ctx)
    ctx.set_var.assert_called_once_with("out", {"a": 1})


def test_read_file_csv(tmp_path, ctx):
    f = tmp_path / "x.csv"
    f.write_text("a,b\n1,2\n3,4\n")
    handler = get_handler("io.read_file")
    handler(StepSpec(id="r", type="io.read_file",
                     params={"path": str(f), "format": "csv", "set": "rows"}), ctx)
    ctx.set_var.assert_called_once_with("rows", [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])


def test_http_request_get(ctx):
    fake_resp = MagicMock(status_code=200, text="ok", headers={"X": "Y"})
    fake_resp.json.return_value = {"k": "v"}
    with patch("tegufox_flow.steps.io.requests.request", return_value=fake_resp) as p:
        handler = get_handler("io.http_request")
        handler(
            StepSpec(id="h", type="io.http_request",
                     params={"method": "GET", "url": "https://api/x", "set": "resp"}),
            ctx,
        )
        p.assert_called_once()
        call = p.call_args
        assert call.kwargs["method"] == "GET"
        assert call.kwargs["url"] == "https://api/x"
    ctx.set_var.assert_called_once()
    saved = ctx.set_var.call_args.args[1]
    assert saved["status"] == 200
    assert saved["body"] == "ok"
    assert saved["json"] == {"k": "v"}
