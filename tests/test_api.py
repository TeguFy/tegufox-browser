"""Tests for Tegufox REST API."""

import pytest
from fastapi.testclient import TestClient

from tegufox_api import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["rules"] == 8


class TestProfiles:
    def test_list_profiles(self, client):
        r = client.get("/profiles")
        assert r.status_code == 200
        names = r.json()
        assert "chrome-120" in names

    def test_get_profile(self, client):
        r = client.get("/profiles/chrome-120")
        assert r.status_code == 200
        p = r.json()
        assert p["name"] == "chrome-120-windows"
        assert "navigator" in p

    def test_get_missing_profile(self, client):
        r = client.get("/profiles/nonexistent")
        assert r.status_code == 404


class TestScoring:
    def test_score_chrome(self, client):
        r = client.get("/profiles/chrome-120/score")
        assert r.status_code == 200
        data = r.json()
        assert data["score"] >= 0.8
        assert data["passed"]
        assert len(data["rules"]) == 8

    def test_score_inline(self, client):
        profile = {
            "name": "test",
            "navigator": {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120",
                "platform": "Win32",
                "language": "en-US",
            },
        }
        r = client.post("/score", json=profile)
        assert r.status_code == 200
        assert r.json()["score"] >= 0.0

    def test_validate_profile(self, client):
        r = client.get("/profiles/chrome-120/validate?level=strict")
        assert r.status_code == 200
        assert "score" in r.json()


class TestGenerator:
    def test_distributions(self, client):
        r = client.get("/generator/distributions")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 5

    def test_generate_profiles(self, client):
        r = client.post("/generator/sample", json={"count": 3, "seed": 42})
        assert r.status_code == 200
        data = r.json()
        assert data["generated"] == 3
        assert len(data["profiles"]) == 3


class TestSessions:
    def test_create_session_missing_profile(self, client):
        r = client.post("/sessions", json={"profile": "nonexistent"})
        assert r.status_code == 404

    def test_list_sessions_empty(self, client):
        r = client.get("/sessions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_missing_session(self, client):
        r = client.get("/sessions/notreal")
        assert r.status_code == 404

    def test_goto_missing_session(self, client):
        r = client.post("/sessions/notreal/goto", json={"url": "https://example.com"})
        assert r.status_code == 404

    def test_close_missing_session(self, client):
        r = client.delete("/sessions/notreal")
        assert r.status_code == 404


class TestRegistry:
    def test_record_and_stats(self, client):
        r = client.post("/registry/record", json={
            "profile_name": "test-api",
            "domain": "example.com",
            "hash_canvas": "abc123",
        })
        assert r.status_code == 201
        assert "id" in r.json()

        r = client.get("/registry/stats")
        assert r.status_code == 200
        assert r.json()["total_records"] >= 1

    def test_collisions(self, client):
        r = client.get("/registry/collisions/nonexistent")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
