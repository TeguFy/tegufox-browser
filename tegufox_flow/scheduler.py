"""Flow scheduler — runs flows on a cron schedule or at a specific time.

The daemon polls flow_schedules every `tick_seconds` (default 30s):
  - For each enabled row whose next_run_at <= now, kick off run_flow()
    in a worker thread.
  - After dispatch, advance next_run_at: cron_expression → next cron tick;
    one-shot (run_at set, no cron) → disable the schedule.

Persistence model lets the daemon survive app restarts: rebuilding
next_run_at from cron at startup catches up any missed ticks (we only
fire once for any missed window — the scheduler is best-effort, not a
guaranteed-delivery queue).
"""

from __future__ import annotations
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import (
    Base, ensure_schema, FlowSchedule,
)
from .runtime import run_flow


_LOG = logging.getLogger("tegufox_flow.scheduler")


def _next_cron(cron_expression: str, base: Optional[datetime] = None) -> datetime:
    """Return the next time `cron_expression` fires after `base`."""
    from croniter import croniter
    base = base or datetime.utcnow()
    return croniter(cron_expression, base).get_next(datetime)


def session_factory(db_path: Path):
    eng = create_engine(f"sqlite:///{db_path.resolve()}")
    Base.metadata.create_all(eng)
    ensure_schema(eng)
    return sessionmaker(bind=eng)


class SchedulerDaemon:
    """Background polling thread that fires due schedules.

    Use `.start()` once at app boot, `.stop()` on app shutdown.
    """

    def __init__(self, db_path: str = "data/tegufox.db", tick_seconds: int = 30):
        self._db_path = Path(db_path)
        self._tick = max(5, int(tick_seconds))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._workers: list[threading.Thread] = []

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="flow-scheduler", daemon=True,
        )
        self._thread.start()
        _LOG.info("scheduler started (tick=%ss, db=%s)", self._tick, self._db_path)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        _LOG.info("scheduler stopped")

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        Session = session_factory(self._db_path)
        # On startup, fix any schedule with a stale / missing next_run_at.
        with Session() as s:
            for sch in s.query(FlowSchedule).filter_by(enabled=True).all():
                if sch.cron_expression and not sch.next_run_at:
                    sch.next_run_at = _next_cron(sch.cron_expression)
            s.commit()

        while not self._stop.is_set():
            try:
                self._tick_once(Session)
            except Exception as e:
                _LOG.exception("scheduler tick failed: %s", e)
            self._stop.wait(self._tick)

    def _tick_once(self, Session) -> None:
        now = datetime.utcnow()
        with Session() as s:
            due = (s.query(FlowSchedule)
                   .filter(FlowSchedule.enabled == True)        # noqa: E712
                   .filter(FlowSchedule.next_run_at != None)    # noqa: E711
                   .filter(FlowSchedule.next_run_at <= now)
                   .all())
            if not due:
                return
            for sch in due:
                # Mark fired BEFORE dispatch so a slow run doesn't re-trigger.
                if sch.cron_expression:
                    sch.next_run_at = _next_cron(sch.cron_expression, now)
                else:
                    # One-shot — disable.
                    sch.enabled = False
                    sch.next_run_at = None
                sch.last_run_at = now
                s.commit()
                # Refresh snapshot used in worker (detach from session).
                snapshot = {
                    "id": sch.id,
                    "name": sch.name,
                    "flow_name": sch.flow_name,
                    "profile_name": sch.profile_name,
                    "proxy_name": sch.proxy_name,
                    "inputs_json": sch.inputs_json,
                }
                self._dispatch(snapshot)

    def _dispatch(self, schedule: dict) -> None:
        def runner():
            import json as _json
            from tegufox_core.database import FlowRecord
            try:
                inputs = _json.loads(schedule.get("inputs_json") or "{}")
            except Exception:
                inputs = {}

            # Materialise the flow YAML to a temp file (run_flow expects a path).
            Session = session_factory(self._db_path)
            with Session() as s:
                rec = (s.query(FlowRecord)
                       .filter_by(name=schedule["flow_name"]).first())
                if rec is None:
                    _LOG.error("schedule %s: flow %r not in DB",
                               schedule["name"], schedule["flow_name"])
                    return
                yaml_text = rec.yaml_text

            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(yaml_text)
                path = Path(f.name)

            try:
                _LOG.info("schedule %s firing flow=%s profile=%s",
                          schedule["name"], schedule["flow_name"],
                          schedule["profile_name"])
                result = run_flow(
                    path,
                    profile_name=schedule["profile_name"],
                    inputs=inputs,
                    proxy_name=schedule.get("proxy_name") or None,
                    db_path=self._db_path,
                )
                _LOG.info("schedule %s done: status=%s run_id=%s",
                          schedule["name"], result.status, result.run_id)
                # Persist last_run_id on the schedule row.
                with Session() as s2:
                    row = s2.query(FlowSchedule).filter_by(id=schedule["id"]).first()
                    if row:
                        row.last_run_id = result.run_id
                        s2.commit()
            except Exception as e:
                _LOG.exception("schedule %s failed: %s", schedule["name"], e)

        t = threading.Thread(target=runner, daemon=True,
                             name=f"sched-{schedule['name']}")
        t.start()
        self._workers.append(t)


# ---------------------------------------------------------------------------
# CRUD helpers used by GUI/CLI
# ---------------------------------------------------------------------------

def add_schedule(
    db_path: str,
    *,
    name: str,
    flow_name: str,
    profile_name: str,
    cron_expression: Optional[str] = None,
    run_at: Optional[datetime] = None,
    inputs: Optional[dict] = None,
    proxy_name: Optional[str] = None,
    enabled: bool = True,
) -> int:
    if not cron_expression and not run_at:
        raise ValueError("schedule needs cron_expression OR run_at")
    if cron_expression and run_at:
        raise ValueError("schedule cannot have both cron_expression and run_at")

    import json as _json
    Session = session_factory(Path(db_path))
    with Session() as s:
        now = datetime.utcnow()
        row = FlowSchedule(
            name=name, flow_name=flow_name, profile_name=profile_name,
            proxy_name=proxy_name,
            inputs_json=_json.dumps(inputs or {}, default=str),
            cron_expression=cron_expression,
            run_at=run_at,
            enabled=enabled,
            next_run_at=(_next_cron(cron_expression) if cron_expression
                          else run_at),
            created_at=now, updated_at=now,
        )
        s.add(row)
        s.commit()
        return row.id


def list_schedules(db_path: str) -> list:
    Session = session_factory(Path(db_path))
    with Session() as s:
        return [
            {
                "id": r.id, "name": r.name, "flow_name": r.flow_name,
                "profile_name": r.profile_name, "proxy_name": r.proxy_name,
                "cron_expression": r.cron_expression,
                "run_at": r.run_at.isoformat() if r.run_at else None,
                "enabled": r.enabled,
                "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                "last_run_id": r.last_run_id,
                "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            }
            for r in s.query(FlowSchedule)
            .order_by(FlowSchedule.next_run_at.asc().nullslast()).all()
        ]


def delete_schedule(db_path: str, schedule_id: int) -> None:
    Session = session_factory(Path(db_path))
    with Session() as s:
        s.query(FlowSchedule).filter_by(id=schedule_id).delete()
        s.commit()


def set_enabled(db_path: str, schedule_id: int, enabled: bool) -> None:
    Session = session_factory(Path(db_path))
    with Session() as s:
        row = s.query(FlowSchedule).filter_by(id=schedule_id).first()
        if not row:
            return
        row.enabled = enabled
        if enabled and row.cron_expression and not row.next_run_at:
            row.next_run_at = _next_cron(row.cron_expression)
        s.commit()
