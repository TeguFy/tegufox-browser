"""Tegufox REST API

FastAPI server for profile management, consistency scoring,
fleet generation, and fingerprint anti-correlation.

Run:
    uvicorn tegufox_api:app --reload --port 8420

Docs:
    http://localhost:8420/docs (Swagger UI)
    http://localhost:8420/redoc (ReDoc)
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from consistency_engine import ConsistencyEngine, default_rules
from fingerprint_registry import FingerprintRegistry
from generator_v2 import generate_profile, generate_fleet, sample_browser_os, MARKET_DISTRIBUTIONS
from profile_manager import ProfileManager, ValidationLevel

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tegufox API",
    description="Deep browser fingerprint engine u2014 profile management, consistency scoring, fleet generation",
    version="0.1.0",
)

PROFILES_DIR = "profiles"
_manager = ProfileManager(PROFILES_DIR)
_engine = ConsistencyEngine(default_rules())
_registry = FingerprintRegistry()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProfileSummary(BaseModel):
    name: str
    description: str = ""
    browser: str = ""


class ScoreResult(BaseModel):
    score: float
    passed: bool
    rules: list
    collisions: List[str] = []


class GenerateRequest(BaseModel):
    count: int = Field(1, ge=1, le=100)
    save: bool = False
    seed: Optional[int] = None


class RecordRequest(BaseModel):
    profile_name: str
    domain: Optional[str] = None
    hash_canvas: Optional[str] = None
    hash_webgl: Optional[str] = None
    hash_tls_ja3: Optional[str] = None


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------


@app.get("/profiles", response_model=List[str], tags=["profiles"])
def list_profiles(pattern: Optional[str] = None):
    """List all profile names."""
    return _manager.list(pattern)


@app.get("/profiles/{name}", tags=["profiles"])
def get_profile(name: str):
    """Get full profile JSON."""
    try:
        return _manager.load(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Profile not found: {name}")


@app.post("/profiles/{name}", tags=["profiles"], status_code=201)
def create_profile(name: str, profile: dict):
    """Create or overwrite a profile."""
    profile["name"] = name
    path = _manager.save(profile, name)
    return {"name": name, "path": str(path)}


@app.delete("/profiles/{name}", tags=["profiles"])
def delete_profile(name: str):
    """Delete a profile."""
    if not _manager.delete(name):
        raise HTTPException(404, f"Profile not found: {name}")
    return {"deleted": name}


@app.post("/profiles/{name}/clone", tags=["profiles"], status_code=201)
def clone_profile(name: str, destination: str = Query(...)):
    """Clone a profile."""
    try:
        profile = _manager.clone(name, destination)
        return {"name": destination, "cloned_from": name}
    except FileNotFoundError:
        raise HTTPException(404, f"Profile not found: {name}")


# ---------------------------------------------------------------------------
# Scoring endpoints
# ---------------------------------------------------------------------------


@app.get("/profiles/{name}/score", response_model=ScoreResult, tags=["scoring"])
def score_profile(name: str, with_collisions: bool = True):
    """Evaluate cross-layer consistency for a profile."""
    try:
        profile = _manager.load(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Profile not found: {name}")

    registry = _registry if with_collisions else None
    engine = ConsistencyEngine(default_rules(), registry=registry)
    report = engine.evaluate(profile)
    return ScoreResult(**report.to_dict())


@app.get("/profiles/{name}/validate", tags=["scoring"])
def validate_profile(
    name: str,
    level: str = Query("standard", enum=["basic", "standard", "strict"]),
):
    """Legacy 3-level validation."""
    try:
        profile = _manager.load(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Profile not found: {name}")

    level_map = {"basic": ValidationLevel.BASIC, "standard": ValidationLevel.STANDARD, "strict": ValidationLevel.STRICT}
    result = _manager.validate(profile, level_map[level])
    return result.to_dict()


@app.post("/score", response_model=ScoreResult, tags=["scoring"])
def score_inline(profile: dict):
    """Score an inline profile (not saved)."""
    report = _engine.evaluate(profile)
    return ScoreResult(**report.to_dict())


# ---------------------------------------------------------------------------
# Generator endpoints
# ---------------------------------------------------------------------------


@app.get("/generator/distributions", tags=["generator"])
def get_distributions():
    """Current market distribution weights."""
    return {f"{b}/{o}": w for (b, o), w in MARKET_DISTRIBUTIONS.items()}


@app.post("/generator/sample", tags=["generator"])
def generate_profiles(req: GenerateRequest):
    """Generate profiles sampled from market distribution."""
    rng = random.Random(req.seed) if req.seed is not None else random.Random()
    fleet = generate_fleet(_manager, count=req.count, rng=rng)

    if req.save:
        saved = []
        for p in fleet:
            path = _manager.save(p, p["name"])
            saved.append({"name": p["name"], "path": str(path)})
        return {"generated": len(fleet), "saved": saved}

    return {"generated": len(fleet), "profiles": fleet}


# ---------------------------------------------------------------------------
# Fingerprint registry endpoints
# ---------------------------------------------------------------------------


@app.post("/registry/record", tags=["registry"], status_code=201)
def record_fingerprint(req: RecordRequest):
    """Record a fingerprint observation."""
    row_id = _registry.record(
        profile_name=req.profile_name,
        domain=req.domain,
        hash_canvas=req.hash_canvas,
        hash_webgl=req.hash_webgl,
        hash_tls_ja3=req.hash_tls_ja3,
    )
    return {"id": row_id}


@app.get("/registry/collisions/{profile_name}", tags=["registry"])
def find_collisions(
    profile_name: str,
    hash_canvas: Optional[str] = None,
    hash_webgl: Optional[str] = None,
    hash_tls_ja3: Optional[str] = None,
):
    """Find profiles with colliding fingerprints."""
    return _registry.find_collisions(profile_name, hash_canvas, hash_webgl, hash_tls_ja3)


@app.get("/registry/stats", tags=["registry"])
def registry_stats():
    """Registry statistics."""
    return {"total_records": _registry.count()}


# ---------------------------------------------------------------------------
# Session control endpoints
# ---------------------------------------------------------------------------

import asyncio
import base64
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

_sessions: dict[str, dict] = {}  # session_id -> {session, profile, created_at, ...}
_session_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4)


class SessionCreateRequest(BaseModel):
    profile: str = Field(..., description="Profile name from /profiles")
    headless: bool = True
    url: Optional[str] = None


class SessionActionRequest(BaseModel):
    selector: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    wpm: Optional[float] = None
    distance: Optional[int] = None
    direction: str = "down"


def _launch_session(session_id: str, profile_name: str, headless: bool, url: Optional[str]):
    """Launch browser in background thread (blocking Playwright calls)."""
    from tegufox_automation import TegufoxSession
    try:
        session = TegufoxSession(profile=profile_name, headless=headless)
        session.start()
        with _session_lock:
            _sessions[session_id]["session"] = session
            _sessions[session_id]["status"] = "running"
        if url:
            session.goto(url)
    except Exception as e:
        with _session_lock:
            _sessions[session_id]["status"] = "error"
            _sessions[session_id]["error"] = str(e)


@app.post("/sessions", tags=["sessions"], status_code=201)
def create_session(req: SessionCreateRequest):
    """Launch a new browser session with a profile."""
    if not _manager.exists(req.profile):
        raise HTTPException(404, f"Profile not found: {req.profile}")

    session_id = str(uuid.uuid4())[:8]
    with _session_lock:
        _sessions[session_id] = {
            "session": None,
            "profile": req.profile,
            "status": "starting",
            "created_at": time.time(),
            "error": None,
        }

    _executor.submit(_launch_session, session_id, req.profile, req.headless, req.url)
    return {"session_id": session_id, "status": "starting", "profile": req.profile}


@app.get("/sessions", tags=["sessions"])
def list_sessions():
    """List all active sessions."""
    with _session_lock:
        return [
            {
                "session_id": sid,
                "profile": info["profile"],
                "status": info["status"],
                "created_at": info["created_at"],
            }
            for sid, info in _sessions.items()
        ]


@app.get("/sessions/{session_id}", tags=["sessions"])
def get_session(session_id: str):
    """Get session status."""
    with _session_lock:
        info = _sessions.get(session_id)
    if not info:
        raise HTTPException(404, f"Session not found: {session_id}")
    return {
        "session_id": session_id,
        "profile": info["profile"],
        "status": info["status"],
        "error": info["error"],
    }


def _get_running_session(session_id: str):
    with _session_lock:
        info = _sessions.get(session_id)
    if not info:
        raise HTTPException(404, f"Session not found: {session_id}")
    if info["status"] != "running":
        raise HTTPException(409, f"Session {session_id} is {info['status']}, not running")
    return info["session"]


@app.post("/sessions/{session_id}/goto", tags=["sessions"])
def session_goto(session_id: str, req: SessionActionRequest):
    """Navigate session to a URL."""
    if not req.url:
        raise HTTPException(400, "url is required")
    session = _get_running_session(session_id)
    session.goto(req.url)
    return {"navigated": req.url}


@app.post("/sessions/{session_id}/type", tags=["sessions"])
def session_type(session_id: str, req: SessionActionRequest):
    """Type text into an element."""
    if not req.selector or not req.text:
        raise HTTPException(400, "selector and text are required")
    session = _get_running_session(session_id)
    session.human_type(req.selector, req.text, wpm=req.wpm)
    return {"typed": len(req.text), "selector": req.selector}


@app.post("/sessions/{session_id}/click", tags=["sessions"])
def session_click(session_id: str, req: SessionActionRequest):
    """Click an element."""
    if not req.selector:
        raise HTTPException(400, "selector is required")
    session = _get_running_session(session_id)
    session.human_click(req.selector)
    return {"clicked": req.selector}


@app.post("/sessions/{session_id}/scroll", tags=["sessions"])
def session_scroll(session_id: str, req: SessionActionRequest):
    """Scroll the page."""
    session = _get_running_session(session_id)
    session.human_scroll(distance=req.distance or 500, direction=req.direction)
    return {"scrolled": req.distance or 500, "direction": req.direction}


@app.get("/sessions/{session_id}/screenshot", tags=["sessions"])
def session_screenshot(session_id: str):
    """Take a screenshot (returns base64 PNG)."""
    session = _get_running_session(session_id)
    raw = session.page.screenshot()
    b64 = base64.b64encode(raw).decode()
    return {"format": "png", "base64": b64}


@app.get("/sessions/{session_id}/evaluate", tags=["sessions"])
def session_evaluate(session_id: str, expression: str = Query(...)):
    """Evaluate JavaScript in the page."""
    session = _get_running_session(session_id)
    result = session.page.evaluate(expression)
    return {"result": result}


@app.delete("/sessions/{session_id}", tags=["sessions"])
def close_session(session_id: str):
    """Close and clean up a session."""
    with _session_lock:
        info = _sessions.pop(session_id, None)
    if not info:
        raise HTTPException(404, f"Session not found: {session_id}")
    if info["session"]:
        try:
            info["session"].stop()
        except Exception:
            pass
    return {"closed": session_id}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "profiles": len(_manager.list()),
        "rules": len(default_rules()),
        "registry_records": _registry.count(),
    }
