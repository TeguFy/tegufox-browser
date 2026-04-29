# tests/orchestrator/test_api_batch.py
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_post_batch_invokes_orchestrator(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    from tegufox_flow.orchestrator import BatchResult

    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/flows", json={"name": "f", "yaml":
        "schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"})

    fake = BatchResult(batch_id="b1", flow_name="f", total=2,
                       succeeded=2, failed=0, status="completed", runs=[])

    with patch("tegufox_cli.api.Orchestrator") as O:
        O.return_value.run.return_value = fake
        r = client.post("/flows/f/batches", json={
            "profiles": ["a", "b"], "inputs": {}, "max_concurrent": 1,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["batch_id"] == "b1"
        assert body["succeeded"] == 2


def test_post_batch_404_unknown_flow(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    r = client.post("/flows/ghost/batches", json={"profiles": ["a"], "inputs": {}})
    assert r.status_code == 404
