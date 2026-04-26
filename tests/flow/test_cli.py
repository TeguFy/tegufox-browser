import pytest
from pathlib import Path

from tegufox_flow.cli import build_parser, run_cli


def test_validate_ok(tmp_path: Path, capsys):
    f = tmp_path / "x.yaml"
    f.write_text("schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")
    rc = run_cli(["validate", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ok" in out.lower() or "valid" in out.lower()


def test_validate_fails(tmp_path: Path, capsys):
    f = tmp_path / "x.yaml"
    f.write_text("schema_version: 99\nname: x\nsteps: []\n")
    rc = run_cli(["validate", str(f)])
    assert rc != 0
    captured = capsys.readouterr()
    err = captured.err + captured.out
    assert "schema_version" in err


def test_inputs_kv_parsing():
    p = build_parser()
    ns = p.parse_args(["run", "f.yaml", "--profile", "p",
                       "--inputs", "a=1", "b=hi"])
    assert ns.inputs == ["a=1", "b=hi"]
