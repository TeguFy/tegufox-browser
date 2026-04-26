"""High-level entrypoints used by the CLI/REST/GUI."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, ensure_schema

from .dsl import load_flow
from .engine import FlowEngine, RunResult


def _session_factory(db_path: Path):
    eng = create_engine(f"sqlite:///{db_path.resolve()}")
    Base.metadata.create_all(eng)

    ensure_schema(eng)
    return sessionmaker(bind=eng)


def run_flow(
    flow_path: Path,
    *,
    profile_name: str,
    inputs: Dict[str, Any],
    db_path: Path = Path("data/tegufox.db"),
    resume: Optional[str] = None,
    resume_from: Optional[str] = None,
    batch_id: Optional[str] = None,
) -> RunResult:
    flow = load_flow(flow_path)
    Session = _session_factory(db_path)
    engine = FlowEngine(db_session_factory=Session)
    return engine.run(
        flow, inputs=inputs, profile_name=profile_name,
        resume=resume, resume_from=resume_from,
        batch_id=batch_id,
    )
