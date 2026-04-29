#!/usr/bin/env python3
"""
Tegufox Profile Database Module

SQLite database for storing browser profiles with normalized schema.
Replaces legacy file storage with relational database.

Author: Tegufox Browser Toolkit
Date: April 21, 2026
License: MIT
"""

import json as _json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

Base = declarative_base()


# ---------------------------------------------------------------------------
# Schema migrations for SQLite
# ---------------------------------------------------------------------------
# Base.metadata.create_all() only creates *missing* tables; it does NOT
# ALTER existing tables to add new columns. When we add a column to an
# existing model (e.g. flow_runs.batch_id added in sub-project #2) databases
# created before that change have a stale schema. ensure_schema() applies
# additive migrations idempotently: detect missing columns via inspection
# and ALTER TABLE ADD COLUMN. SQLite cannot add FK constraints via ALTER,
# but we don't enforce FKs at runtime so a plain column suffices.

def ensure_schema(engine) -> None:
    """Apply additive schema migrations on top of create_all().

    Safe to call multiple times. Currently handles:
      - flow_runs.batch_id (added by sub-project #2)
      - flow_runs.kind (added by sub-project #7)
      - flow_runs.goal_text (added by sub-project #7)
    """
    from sqlalchemy import inspect

    insp = inspect(engine)
    table_names = set(insp.get_table_names())

    if "flow_runs" in table_names:
        cols = {c["name"] for c in insp.get_columns("flow_runs")}
        if "batch_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE flow_runs ADD COLUMN batch_id VARCHAR(64)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_flow_runs_batch_id "
                    "ON flow_runs(batch_id)"
                ))
        if "kind" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE flow_runs ADD COLUMN kind VARCHAR(16) "
                    "NOT NULL DEFAULT 'flow'"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_flow_runs_kind "
                    "ON flow_runs(kind)"
                ))
        if "goal_text" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE flow_runs ADD COLUMN goal_text TEXT"
                ))


def create_all_and_migrate(engine) -> None:
    """create_all() + ensure_schema() in one call. Use this everywhere."""
    Base.metadata.create_all(engine)
    ensure_schema(engine)


class Profile(Base):
    """Main profile table"""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    created = Column(DateTime, default=datetime.utcnow)
    version = Column(String(50), default="1.0")
    os = Column(String(50), nullable=False, index=True)  # windows, macos, linux
    browser = Column(String(50), index=True)  # firefox, safari, chrome
    timezone = Column(String(100))
    timezone_offset = Column(Integer)

    # Relationships
    screen = relationship("Screen", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    navigator = relationship("Navigator", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    webgl = relationship("WebGL", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    canvas = relationship("Canvas", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    dns_config = relationship("DNSConfig", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    fingerprint = relationship("Fingerprint", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    fonts = relationship("Font", back_populates="profile", cascade="all, delete-orphan")
    firefox_prefs = relationship("FirefoxPreference", back_populates="profile", cascade="all, delete-orphan")
    proxy = relationship("Proxy", back_populates="profile", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to plain Python dict"""
        result = {
            "name": self.name,
            "description": self.description,
            "created": self.created.strftime("%Y-%m-%d") if self.created else None,
            "version": self.version,
            "os": self.os,
            "browser": self.browser,
            "timezone": self.timezone,
            "timezoneOffset": self.timezone_offset,
        }

        if self.screen:
            result["screen"] = self.screen.to_dict()

        if self.navigator:
            result["navigator"] = self.navigator.to_dict()

        if self.webgl:
            result["webgl"] = self.webgl.to_dict()

        if self.canvas:
            result["canvas"] = self.canvas.to_dict()

        if self.dns_config:
            result["dns_config"] = self.dns_config.to_dict()

        if self.fingerprint:
            result["fingerprint"] = self.fingerprint.to_dict()
            result["fingerprints"] = {
                "ja3": self.fingerprint.ja3 or "",
                "ja4": self.fingerprint.ja4 or "",
                "akamai_http2": self.fingerprint.akamai_http2 or "",
                "notes": self.fingerprint.notes or "",
            }

        if self.fonts:
            result["fonts"] = [f.name for f in sorted(self.fonts, key=lambda x: x.name)]

        if self.firefox_prefs:
            result["firefox_preferences"] = {
                pref.key: _json.loads(pref.value) if isinstance(pref.value, str) else pref.value
                for pref in self.firefox_prefs
            }

        if self.proxy:
            result["proxy"] = self.proxy.to_dict()

        return result


class Screen(Base):
    """Screen configuration"""

    __tablename__ = "screens"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    avail_width = Column(Integer, nullable=False)
    avail_height = Column(Integer, nullable=False)
    color_depth = Column(Integer, default=24)
    pixel_depth = Column(Integer, default=24)

    profile = relationship("Profile", back_populates="screen")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "availWidth": self.avail_width,
            "availHeight": self.avail_height,
            "colorDepth": self.color_depth,
            "pixelDepth": self.pixel_depth,
        }


class Navigator(Base):
    """Navigator properties"""

    __tablename__ = "navigators"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    user_agent = Column(Text, nullable=False)
    platform = Column(String(100), nullable=False)
    hardware_concurrency = Column(Integer, default=4)
    device_memory = Column(Integer, default=8)
    max_touch_points = Column(Integer, default=0)
    vendor = Column(String(255), default="")
    language = Column(String(50), default="en-US")
    languages = Column(Text)  # Stored as serialized list

    profile = relationship("Profile", back_populates="navigator")

    def to_dict(self) -> Dict[str, Any]:
        langs = self.languages
        if isinstance(langs, str):
            langs = _json.loads(langs)
        return {
            "userAgent": self.user_agent,
            "platform": self.platform,
            "hardwareConcurrency": self.hardware_concurrency,
            "deviceMemory": self.device_memory,
            "maxTouchPoints": self.max_touch_points,
            "vendor": self.vendor,
            "language": self.language,
            "languages": langs or ["en-US", "en"],
        }


class WebGL(Base):
    """WebGL configuration"""

    __tablename__ = "webgl"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    vendor = Column(String(255))
    renderer = Column(String(255))
    extensions = Column(Text)  # Stored as serialized list
    parameters = Column(Text)  # Stored as serialized dict

    profile = relationship("Profile", back_populates="webgl")

    def to_dict(self) -> Dict[str, Any]:
        exts = self.extensions
        params = self.parameters
        if isinstance(exts, str):
            exts = _json.loads(exts)
        if isinstance(params, str):
            params = _json.loads(params)
        return {
            "vendor": self.vendor or "",
            "renderer": self.renderer or "",
            "extensions": exts or [],
            "parameters": params or {},
        }


class Canvas(Base):
    """Canvas noise configuration"""

    __tablename__ = "canvas"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    noise_seed = Column(Integer)
    noise_intensity = Column(Float)
    noise_magnitude = Column(Integer)
    noise_edge_bias = Column(Float)
    noise_strategy = Column(String(50))
    noise_temporal_variation = Column(Float)
    noise_sparse_probability = Column(Float)

    profile = relationship("Profile", back_populates="canvas")

    def to_dict(self) -> Dict[str, Any]:
        if self.noise_seed is None:
            return {"noise": None}

        return {
            "noise": {
                "seed": self.noise_seed,
                "intensity": self.noise_intensity,
                "magnitude": self.noise_magnitude,
                "edge_bias": self.noise_edge_bias,
                "strategy": self.noise_strategy,
                "temporal_variation": self.noise_temporal_variation,
                "sparse_probability": self.noise_sparse_probability,
            }
        }


class DNSConfig(Base):
    """DNS configuration"""

    __tablename__ = "dns_configs"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    provider = Column(String(100))
    rationale = Column(Text)

    # DoH settings
    doh_uri = Column(String(255))
    doh_bootstrap_address = Column(String(50))
    doh_mode = Column(Integer, default=3)
    doh_strict_fallback = Column(Boolean, default=True)
    doh_disable_ecs = Column(Boolean, default=True)

    # IPv6 settings
    ipv6_enabled = Column(Boolean, default=False)
    ipv6_reason = Column(Text)

    # WebRTC settings
    webrtc_enabled = Column(Boolean, default=False)
    webrtc_reason = Column(Text)

    # Prefetch settings
    dns_prefetch = Column(Boolean, default=False)
    link_prefetch = Column(Boolean, default=False)
    prefetch_reason = Column(Text)

    profile = relationship("Profile", back_populates="dns_config")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "rationale": self.rationale,
            "doh": {
                "uri": self.doh_uri,
                "bootstrap_address": self.doh_bootstrap_address,
                "mode": self.doh_mode,
                "strict_fallback": self.doh_strict_fallback,
                "disable_ecs": self.doh_disable_ecs,
            },
            "ipv6": {
                "enabled": self.ipv6_enabled,
                "reason": self.ipv6_reason,
            },
            "webrtc": {
                "enabled": self.webrtc_enabled,
                "reason": self.webrtc_reason,
            },
            "prefetch": {
                "dns_prefetch": self.dns_prefetch,
                "link_prefetch": self.link_prefetch,
                "reason": self.prefetch_reason,
            },
        }


class Fingerprint(Base):
    """Fingerprint data"""

    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    canvas_seed = Column(Integer)
    audio_seed = Column(Integer)
    ja3 = Column(String(255))
    ja4 = Column(String(255))
    akamai_http2 = Column(String(255))
    notes = Column(Text)

    profile = relationship("Profile", back_populates="fingerprint")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canvas_seed": self.canvas_seed,
            "audio_seed": self.audio_seed,
        }


class Font(Base):
    """Font list"""

    __tablename__ = "fonts"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    name = Column(String(255), nullable=False)

    profile = relationship("Profile", back_populates="fonts")


class FirefoxPreference(Base):
    """Firefox preferences"""

    __tablename__ = "firefox_preferences"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text)  # Stored as serialized value

    profile = relationship("Profile", back_populates="firefox_prefs")


class Proxy(Base):
    """Proxy configuration"""

    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    server = Column(String(255))
    username = Column(String(255))
    password = Column(String(255))
    proxy_name = Column(String(255))

    profile = relationship("Profile", back_populates="proxy")

    def to_dict(self) -> Dict[str, Any]:
        result = {"server": self.server}
        if self.username:
            result["username"] = self.username
        if self.password:
            result["password"] = self.password
        if self.proxy_name:
            result["proxy_name"] = self.proxy_name
        return result


class FlowRecord(Base):
    """Flow definition record"""

    __tablename__ = "flows"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    yaml_text = Column(Text, nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class FlowRun(Base):
    """Flow execution record"""

    __tablename__ = "flow_runs"

    run_id = Column(String(64), primary_key=True)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    profile_name = Column(String(255), nullable=False, index=True)
    inputs_json = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="running", index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    last_step_id = Column(String(255))
    error_text = Column(Text)
    batch_id = Column(String(64), ForeignKey("flow_batches.batch_id"), nullable=True, index=True)
    kind = Column(String(16), nullable=False, default="flow", index=True)
    goal_text = Column(Text)


class FlowCheckpoint(Base):
    """Flow execution checkpoint/state snapshot"""

    __tablename__ = "flow_checkpoints"

    run_id = Column(String(64), primary_key=True)
    seq = Column(Integer, primary_key=True)
    step_id = Column(String(255), nullable=False)
    vars_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False)


class FlowKVState(Base):
    """Flow key-value state storage"""

    __tablename__ = "flow_kv_state"

    flow_name = Column(String(255), primary_key=True)
    key = Column(String(255), primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class FlowBatch(Base):
    __tablename__ = "flow_batches"

    batch_id    = Column(String(64), primary_key=True)
    flow_id     = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    inputs_json = Column(Text, nullable=False, default="{}")
    status      = Column(String(32), nullable=False, default="running", index=True)
    total       = Column(Integer, nullable=False, default=0)
    succeeded   = Column(Integer, nullable=False, default=0)
    failed      = Column(Integer, nullable=False, default=0)
    started_at  = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)


class FlowSchedule(Base):
    """Scheduled flow runs (cron + one-shot).

    cron_expression non-null → recurring on that cron.
    run_at non-null & cron_expression null → one-shot at that time.
    next_run_at is the upcoming firing time the scheduler polls for.
    """
    __tablename__ = "flow_schedules"

    id              = Column(Integer, primary_key=True)
    name            = Column(String(255), nullable=False)
    flow_name       = Column(String(255), nullable=False, index=True)
    profile_name    = Column(String(255), nullable=False)
    proxy_name      = Column(String(255))
    inputs_json     = Column(Text, nullable=False, default="{}")
    cron_expression = Column(String(255))
    run_at          = Column(DateTime)
    enabled         = Column(Boolean, nullable=False, default=True, index=True)
    next_run_at     = Column(DateTime, index=True)
    last_run_id     = Column(String(64))
    last_run_at     = Column(DateTime)
    created_at      = Column(DateTime, nullable=False)
    updated_at      = Column(DateTime, nullable=False)


class ProfileDatabase:
    """Database manager for profiles"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (default: tegufox_core/profiles.db)
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "profiles.db")

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _migrate_schema(self) -> None:
        """In-place ALTER for columns added after initial release."""
        with self.engine.begin() as conn:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(proxies)"))}
            if "proxy_name" not in cols:
                conn.execute(text("ALTER TABLE proxies ADD COLUMN proxy_name VARCHAR(255)"))

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def create_profile_from_dict(self, data: Dict[str, Any]) -> Profile:
        """
        Create profile from plain Python dict

        Args:
            data: Profile data dict

        Returns:
            Profile ORM object
        """
        session = self.get_session()
        try:
            # Create profile
            profile = Profile(
                name=data["name"],
                description=data.get("description"),
                created=datetime.strptime(data.get("created", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"),
                version=data.get("version", "1.0"),
                os=data.get("os", "linux"),
                browser=data.get("browser"),
                timezone=data.get("timezone"),
                timezone_offset=data.get("timezoneOffset"),
            )

            # Screen
            if "screen" in data:
                s = data["screen"]
                profile.screen = Screen(
                    width=s["width"],
                    height=s["height"],
                    avail_width=s.get("availWidth", s["width"]),
                    avail_height=s.get("availHeight", s["height"] - 40),
                    color_depth=s.get("colorDepth", 24),
                    pixel_depth=s.get("pixelDepth", 24),
                )

            # Navigator
            if "navigator" in data:
                n = data["navigator"]
                profile.navigator = Navigator(
                    user_agent=n.get("userAgent", ""),
                    platform=n.get("platform", ""),
                    hardware_concurrency=n.get("hardwareConcurrency", 4),
                    device_memory=n.get("deviceMemory", 8),
                    max_touch_points=n.get("maxTouchPoints", 0),
                    vendor=n.get("vendor", ""),
                    language=n.get("language", "en-US"),
                    languages=_json.dumps(n.get("languages", ["en-US", "en"])),
                )

            # WebGL
            if "webgl" in data:
                w = data["webgl"]
                profile.webgl = WebGL(
                    vendor=w.get("vendor"),
                    renderer=w.get("renderer"),
                    extensions=_json.dumps(w.get("extensions", [])),
                    parameters=_json.dumps(w.get("parameters", {})),
                )

            # Canvas
            if "canvas" in data:
                c = data["canvas"]
                noise = c.get("noise")
                if noise:
                    profile.canvas = Canvas(
                        noise_seed=noise.get("seed"),
                        noise_intensity=noise.get("intensity"),
                        noise_magnitude=noise.get("magnitude"),
                        noise_edge_bias=noise.get("edge_bias"),
                        noise_strategy=noise.get("strategy"),
                        noise_temporal_variation=noise.get("temporal_variation"),
                        noise_sparse_probability=noise.get("sparse_probability"),
                    )
                else:
                    profile.canvas = Canvas()

            # DNS Config
            if "dns_config" in data:
                d = data["dns_config"]
                doh = d.get("doh", {})
                ipv6 = d.get("ipv6", {})
                webrtc = d.get("webrtc", {})
                prefetch = d.get("prefetch", {})

                profile.dns_config = DNSConfig(
                    enabled=d.get("enabled", True),
                    provider=d.get("provider"),
                    rationale=d.get("rationale"),
                    doh_uri=doh.get("uri"),
                    doh_bootstrap_address=doh.get("bootstrap_address"),
                    doh_mode=doh.get("mode", 3),
                    doh_strict_fallback=doh.get("strict_fallback", True),
                    doh_disable_ecs=doh.get("disable_ecs", True),
                    ipv6_enabled=ipv6.get("enabled", False),
                    ipv6_reason=ipv6.get("reason"),
                    webrtc_enabled=webrtc.get("enabled", False),
                    webrtc_reason=webrtc.get("reason"),
                    dns_prefetch=prefetch.get("dns_prefetch", False),
                    link_prefetch=prefetch.get("link_prefetch", False),
                    prefetch_reason=prefetch.get("reason"),
                )

            # Fingerprint
            fp_data = data.get("fingerprint", {})
            fp_meta = data.get("fingerprints", {})
            profile.fingerprint = Fingerprint(
                canvas_seed=fp_data.get("canvas_seed"),
                audio_seed=fp_data.get("audio_seed"),
                ja3=fp_meta.get("ja3"),
                ja4=fp_meta.get("ja4"),
                akamai_http2=fp_meta.get("akamai_http2"),
                notes=fp_meta.get("notes"),
            )

            # Fonts
            if "fonts" in data:
                for font_name in data["fonts"]:
                    profile.fonts.append(Font(name=font_name))

            # Firefox preferences
            if "firefox_preferences" in data:
                for key, value in data["firefox_preferences"].items():
                    profile.firefox_prefs.append(FirefoxPreference(key=key, value=_json.dumps(value)))

            # Proxy
            if "proxy" in data:
                p = data["proxy"]
                profile.proxy = Proxy(
                    server=p.get("server"),
                    username=p.get("username"),
                    password=p.get("password"),
                    proxy_name=p.get("proxy_name"),
                )

            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile by name and return as dict"""
        session = self.get_session()
        try:
            profile = session.query(Profile).filter(Profile.name == name).first()
            if profile:
                return profile.to_dict()
            return None
        finally:
            session.close()

    def get_profile_obj(self, name: str) -> Optional[Profile]:
        """Get profile ORM object (for internal use)"""
        session = self.get_session()
        try:
            return session.query(Profile).filter(Profile.name == name).first()
        finally:
            session.close()

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all profiles as dicts"""
        session = self.get_session()
        try:
            profiles = session.query(Profile).all()
            return [p.to_dict() for p in profiles]
        finally:
            session.close()

    def delete_profile(self, name: str) -> bool:
        """Delete profile by name"""
        session = self.get_session()
        try:
            profile = session.query(Profile).filter(Profile.name == name).first()
            if profile:
                session.delete(profile)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def profile_exists(self, name: str) -> bool:
        """Check if profile exists"""
        session = self.get_session()
        try:
            return session.query(Profile).filter(Profile.name == name).count() > 0
        finally:
            session.close()

    def search_profiles(self, query: str) -> List[Dict[str, Any]]:
        """Search profiles by name or description"""
        session = self.get_session()
        try:
            profiles = (
                session.query(Profile)
                .filter(
                    (Profile.name.like(f"%{query}%")) | (Profile.description.like(f"%{query}%"))
                )
                .all()
            )
            return [p.to_dict() for p in profiles]
        finally:
            session.close()


if __name__ == "__main__":
    # Test database
    db = ProfileDatabase()
    print(f"Database initialized at: {db.db_path}")
    print(f"Total profiles: {len(db.get_all_profiles())}")
