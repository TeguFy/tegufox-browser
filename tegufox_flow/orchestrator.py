"""Multi-profile orchestrator: run one flow on N profiles with bounded concurrency."""

from __future__ import annotations
import json
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowBatch, FlowRecord
from .dsl import load_flow
from .engine import RunResult
from .runtime import run_flow


_RunArgs = Tuple[Path, str, Dict[str, Any], Path, str]


@dataclass
class BatchResult:
    batch_id: str
    flow_name: str
    total: int
    succeeded: int
    failed: int
    status: str   # completed | aborted
    runs: List[RunResult] = field(default_factory=list)


def _run_one_subprocess(args: _RunArgs) -> RunResult:
    """Top-level (picklable) entry point dispatched into worker processes."""
    flow_path, profile, inputs, db_path, batch_id = args
    return run_flow(
        flow_path,
        profile_name=profile,
        inputs=inputs,
        db_path=db_path,
        batch_id=batch_id,
    )


class Orchestrator:
    def __init__(
        self,
        flow_path: Path,
        db_path: Path,
        *,
        max_concurrent: int = 3,
        fail_fast: bool = False,
    ):
        self._flow_path = Path(flow_path)
        self._db_path = Path(db_path)
        self._max = max(1, int(max_concurrent))
        self._fail_fast = bool(fail_fast)

    def run(
        self,
        profiles: List[str],
        *,
        inputs: Optional[Dict[str, Any]] = None,
        per_profile_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> BatchResult:
        if not profiles:
            raise ValueError("profiles list cannot be empty")

        inputs = inputs or {}
        per_profile_inputs = per_profile_inputs or {}

        # Pre-validate: all required inputs must resolve for every profile.
        flow = load_flow(self._flow_path)
        per_profile_merged = {}
        for p in profiles:
            merged = {**inputs, **per_profile_inputs.get(p, {})}
            for name, decl in flow.inputs.items():
                if (name not in merged
                        and decl.required
                        and decl.default is None):
                    raise ValueError(
                        f"profile {p!r}: missing required input {name!r}")
            per_profile_merged[p] = merged

        batch_id = str(uuid.uuid4())
        Session = sessionmaker(
            bind=create_engine(f"sqlite:///{self._db_path.resolve()}"))

        # Ensure FlowRecord and FlowBatch exist before any subprocess writes
        # FlowRun referencing the batch_id.
        with Session() as s:
            Base.metadata.create_all(s.get_bind())
            fid = s.query(FlowRecord.id).filter_by(name=flow.name).scalar()
            if fid is None:
                rec = FlowRecord(
                    name=flow.name, yaml_text="(loaded from disk)",
                    schema_version=flow.schema_version,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                s.add(rec); s.commit(); fid = rec.id

            s.add(FlowBatch(
                batch_id=batch_id, flow_id=fid,
                inputs_json=json.dumps(inputs, default=str),
                status="running", total=len(profiles),
                started_at=datetime.utcnow(),
            ))
            s.commit()

        # Dispatch
        runs: List[RunResult] = []
        succeeded = 0
        failed = 0
        aborted = False

        args_per_profile: List[_RunArgs] = [
            (self._flow_path, p, per_profile_merged[p], self._db_path, batch_id)
            for p in profiles
        ]

        with ThreadPoolExecutor(max_workers=self._max) as ex:
            future_to_profile = {
                ex.submit(_run_one_subprocess, args): args[1]
                for args in args_per_profile
            }
            try:
                for fut in as_completed(future_to_profile):
                    profile = future_to_profile[fut]
                    try:
                        result = fut.result()
                    except Exception as exc:  # subprocess crash, etc.
                        result = RunResult(
                            run_id=f"crashed-{profile}",
                            status="failed",
                            last_step_id=None,
                            error=f"{type(exc).__name__}: {exc}",
                            inputs=per_profile_merged[profile],
                        )
                    runs.append(result)

                    if result.status == "succeeded":
                        succeeded += 1
                    else:
                        failed += 1

                    self._increment(Session, batch_id,
                                    succeeded_delta=1 if result.status == "succeeded" else 0,
                                    failed_delta=1 if result.status != "succeeded" else 0)

                    if self._fail_fast and result.status != "succeeded":
                        ex.shutdown(wait=False, cancel_futures=True)
                        aborted = True
                        break
            finally:
                pass

        status = "aborted" if aborted else "completed"
        with Session() as s:
            row = s.query(FlowBatch).filter_by(batch_id=batch_id).one()
            row.status = status
            row.finished_at = datetime.utcnow()
            s.commit()

        return BatchResult(
            batch_id=batch_id, flow_name=flow.name,
            total=len(profiles), succeeded=succeeded, failed=failed,
            status=status, runs=runs,
        )

    @staticmethod
    def _increment(Session, batch_id: str, *,
                   succeeded_delta: int, failed_delta: int) -> None:
        with Session() as s:
            row = s.query(FlowBatch).filter_by(batch_id=batch_id).one()
            row.succeeded += succeeded_delta
            row.failed += failed_delta
            s.commit()
