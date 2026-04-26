from fastapi.testclient import TestClient


def test_flow_lifecycle(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)

    yaml = (
        "schema_version: 1\n"
        "name: api_t\n"
        "steps:\n"
        "  - id: a\n"
        "    type: control.sleep\n"
        "    ms: 1\n"
    )
    r = client.post("/flows", json={"name": "api_t", "yaml": yaml})
    assert r.status_code == 200, r.text

    r = client.get("/flows")
    assert any(f["name"] == "api_t" for f in r.json())

    r = client.get("/flows/api_t")
    assert "schema_version: 1" in r.json()["yaml"]


def test_post_run_requires_profile(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/flows", json={"name": "x", "yaml":
        "schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"})
    r = client.post("/flows/x/runs", json={"inputs": {}})
    assert r.status_code == 422
