"""Tests for tegufox_core.runtime_settings — global settings reader."""
from pathlib import Path
import pprint


def test_get_setting_default_when_file_missing(tmp_path, monkeypatch):
    from tegufox_core import runtime_settings as rs
    monkeypatch.setattr(rs, "SETTINGS_PATH", tmp_path / "missing.conf")
    assert rs.get_setting("disable_popups", True) is True
    assert rs.get_setting("missing_key", 42) == 42


def test_get_setting_reads_from_file(tmp_path, monkeypatch):
    from tegufox_core import runtime_settings as rs
    p = tmp_path / "settings.conf"
    p.write_text(pprint.pformat({"disable_popups": False, "api_port": 9000}))
    monkeypatch.setattr(rs, "SETTINGS_PATH", p)
    assert rs.get_setting("disable_popups", True) is False
    assert rs.get_setting("api_port", 8420) == 9000


def test_set_setting_writes_back(tmp_path, monkeypatch):
    from tegufox_core import runtime_settings as rs
    p = tmp_path / "settings.conf"
    monkeypatch.setattr(rs, "SETTINGS_PATH", p)
    rs.set_setting("disable_popups", False)
    assert rs.get_setting("disable_popups", True) is False
    # round-trip preserves other keys
    rs.set_setting("api_port", 8888)
    assert rs.get_setting("api_port", 0) == 8888
    assert rs.get_setting("disable_popups", True) is False


def test_load_settings_returns_empty_on_garbage(tmp_path, monkeypatch):
    from tegufox_core import runtime_settings as rs
    p = tmp_path / "x.conf"
    p.write_text("not a python literal { { (")
    monkeypatch.setattr(rs, "SETTINGS_PATH", p)
    assert rs.load_settings() == {}


def test_load_settings_returns_empty_when_not_dict(tmp_path, monkeypatch):
    from tegufox_core import runtime_settings as rs
    p = tmp_path / "x.conf"
    p.write_text("[1, 2, 3]")
    monkeypatch.setattr(rs, "SETTINGS_PATH", p)
    assert rs.load_settings() == {}
