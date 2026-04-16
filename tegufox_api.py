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
