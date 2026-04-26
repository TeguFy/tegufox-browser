# tests/orchestrator/test_cli_batch.py
import pytest
from pathlib import Path
from unittest.mock import patch

from tegufox_flow.cli import build_parser, run_cli
from tegufox_flow.orchestrator import BatchResult


def test_batch_run_parses_profiles_csv():
    p = build_parser()
    ns = p.parse_args([
        "batch", "run", "f.yaml",
        "--profiles", "a,b,c",
        "--inputs", "q=hello",
        "--max-concurrent", "2",
    ])
    assert ns.cmd == "batch"
    assert ns.batch_cmd == "run"
    assert ns.profiles == "a,b,c"
    assert ns.max_concurrent == 2


def test_batch_run_invokes_orchestrator(tmp_path):
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    fake_result = BatchResult(
        batch_id="b1", flow_name="f", total=2,
        succeeded=2, failed=0, status="completed", runs=[],
    )
    with patch("tegufox_flow.cli._run_batch", return_value=fake_result) as p:
        rc = run_cli([
            "batch", "run", str(flow_yaml),
            "--profiles", "a,b",
            "--max-concurrent", "1",
            "--db", str(tmp_path / "t.db"),
        ])
        assert rc == 0
        p.assert_called_once()
