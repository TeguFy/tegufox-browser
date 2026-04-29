"""Checkpoint and KV state stores backed by SQLAlchemy.

CheckpointStore: per-run, append-only, monotonic seq.
KVStore: per-flow, last-write-wins on (flow_name, key).
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from tegufox_core.database import FlowCheckpoint, FlowKVState

_MISSING = object()


@dataclass
class Checkpoint:
    run_id: str
    step_id: str
    seq: int
    vars: dict


class CheckpointStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def save(self, run_id: str, step_id: str, vars: dict) -> int:
        last = (
            self._s.query(FlowCheckpoint.seq)
            .filter_by(run_id=run_id)
            .order_by(FlowCheckpoint.seq.desc())
            .first()
        )
        next_seq = (last[0] + 1) if last else 1
        row = FlowCheckpoint(
            run_id=run_id,
            seq=next_seq,
            step_id=step_id,
            vars_json=json.dumps(vars, default=str),
            created_at=datetime.utcnow(),
        )
        self._s.add(row)
        self._s.commit()
        return next_seq

    def last(self, run_id: str) -> Optional[Checkpoint]:
        row = (
            self._s.query(FlowCheckpoint)
            .filter_by(run_id=run_id)
            .order_by(FlowCheckpoint.seq.desc())
            .first()
        )
        if row is None:
            return None
        return Checkpoint(
            run_id=row.run_id,
            step_id=row.step_id,
            seq=row.seq,
            vars=json.loads(row.vars_json),
        )


class KVStore:
    def __init__(self, session: Session, flow_name: str) -> None:
        self._s = session
        self._flow = flow_name

    def save(self, key: str, value: Any) -> None:
        row = (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .first()
        )
        payload = json.dumps(value, default=str)
        now = datetime.utcnow()
        if row is None:
            row = FlowKVState(
                flow_name=self._flow, key=key, value_json=payload, updated_at=now,
            )
            self._s.add(row)
        else:
            row.value_json = payload
            row.updated_at = now
        self._s.commit()

    def load(self, key: str, default: Any = _MISSING) -> Any:
        row = (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .first()
        )
        if row is None:
            if default is _MISSING:
                return None
            return default
        return json.loads(row.value_json)

    def delete(self, key: str) -> None:
        (
            self._s.query(FlowKVState)
            .filter_by(flow_name=self._flow, key=key)
            .delete()
        )
        self._s.commit()
