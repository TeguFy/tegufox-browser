"""Tests for the SQLite-backed fingerprint registry."""

from __future__ import annotations

import ast

import pytest

from fingerprint_registry import FingerprintRegistry


@pytest.fixture
def registry(tmp_path):
    db = tmp_path / "fingerprints.db"
    reg = FingerprintRegistry(db_path=db)
    yield reg
    reg.close()


def test_record_and_count(registry):
    registry.record("profile-a", "example.com", hash_canvas="abc", hash_webgl="def")
    registry.record("profile-a", "example.com", hash_canvas="abc", hash_webgl="def")
    assert registry.count() == 2


def test_no_collision_for_unique_hashes(registry):
    registry.record("profile-a", "example.com", hash_canvas="hash-a")
    collisions = registry.find_collisions("profile-b", hash_canvas="hash-b")
    assert collisions == []


def test_collision_detected_across_profiles(registry):
    registry.record("profile-a", "example.com", hash_canvas="shared-canvas")
    registry.record("profile-b", "example.com", hash_canvas="shared-canvas")
    collisions = registry.find_collisions("profile-c", hash_canvas="shared-canvas")
    assert set(collisions) == {"profile-a", "profile-b"}


def test_same_profile_doesnt_collide_with_itself(registry):
    registry.record("profile-a", "example.com", hash_canvas="hash1")
    collisions = registry.find_collisions("profile-a", hash_canvas="hash1")
    assert collisions == []


def test_collision_on_any_hash_field(registry):
    registry.record("profile-a", None, hash_tls_ja3="ja3-x")
    collisions = registry.find_collisions(
        "profile-b", hash_canvas="doesnt-match", hash_tls_ja3="ja3-x"
    )
    assert collisions == ["profile-a"]


def test_find_collisions_for_profile(registry):
    registry.record("profile-a", "example.com", hash_canvas="canv-1", hash_webgl="gl-1")
    profile = {
        "name": "profile-b",
        "fingerprints": {"canvas": "canv-1", "webgl": "other"},
    }
    collisions = registry.find_collisions_for_profile(profile)
    assert collisions == ["profile-a"]


def test_list_for_profile_orders_desc(registry):
    registry.record("profile-a", "site1.com", hash_canvas="c1")
    registry.record("profile-a", "site2.com", hash_canvas="c2")
    rows = registry.list_for_profile("profile-a")
    assert len(rows) == 2
    assert rows[0]["domain"] == "site2.com"


def test_export_records_roundtrip(registry, tmp_path):
    registry.record("profile-a", "example.com", hash_canvas="c1")
    registry.record("profile-b", "example.com", hash_canvas="c2")

    out = tmp_path / "export.txt"
    n = registry.export_records(out)
    assert n == 2

    data = ast.literal_eval(out.read_text())
    assert len(data) == 2
    assert {row["profile_name"] for row in data} == {"profile-a", "profile-b"}


def test_clear(registry):
    registry.record("profile-a", None, hash_canvas="c1")
    assert registry.count() == 1
    registry.clear()
    assert registry.count() == 0
