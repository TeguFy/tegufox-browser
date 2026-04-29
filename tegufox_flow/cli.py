"""tegufox-cli flow ... subcommand."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .dsl import load_flow
from .errors import ValidationError
from .runtime import run_flow


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tegufox-cli flow")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a flow YAML file")
    v.add_argument("path")

    r = sub.add_parser("run", help="Run a flow on a single profile")
    r.add_argument("path")
    r.add_argument("--profile", required=True)
    r.add_argument("--inputs", nargs="*", default=[],
                   help="key=value pairs (parsed as JSON if possible)")
    r.add_argument("--db", default="data/tegufox.db")
    r.add_argument("--proxy", dest="proxy_name", default=None,
                   help="Name of an imported proxy from proxies.db")
    r.add_argument("--keep-browser", dest="keep_browser_open",
                   action="store_true",
                   help="Leave the browser open after the flow finishes "
                        "so you can interact manually; close the window to exit.")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--resume")
    g.add_argument("--resume-from", dest="resume_from")

    runs = sub.add_parser("runs", help="Run history")
    runs_sub = runs.add_subparsers(dest="runs_cmd", required=True)
    ls = runs_sub.add_parser("ls")
    ls.add_argument("--flow", required=False)
    ls.add_argument("--limit", type=int, default=20)
    show = runs_sub.add_parser("show")
    show.add_argument("run_id")

    batch = sub.add_parser("batch", help="Run a flow against N profiles")
    batch_sub = batch.add_subparsers(dest="batch_cmd", required=True)

    bb = batch_sub.add_parser("run")
    bb.add_argument("path")
    bb.add_argument("--profiles", required=True,
                    help="comma-separated profile names")
    bb.add_argument("--inputs", nargs="*", default=[])
    bb.add_argument("--max-concurrent", type=int, default=3, dest="max_concurrent")
    bb.add_argument("--fail-fast", action="store_true", dest="fail_fast")
    bb.add_argument("--db", default="data/tegufox.db")

    bls = batch_sub.add_parser("ls")
    bls.add_argument("--limit", type=int, default=20)

    bsh = batch_sub.add_parser("show")
    bsh.add_argument("batch_id")

    return p


def _parse_inputs(items: List[str]) -> dict:
    out = {}
    for it in items:
        if "=" not in it:
            raise ValueError(f"input must be key=value: {it!r}")
        k, v = it.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _run_batch(flow_path, db_path, profiles, inputs, max_concurrent, fail_fast):
    from .orchestrator import Orchestrator
    orch = Orchestrator(
        flow_path=flow_path, db_path=db_path,
        max_concurrent=max_concurrent, fail_fast=fail_fast,
    )
    return orch.run(profiles=profiles, inputs=inputs)


def _batch_cmd(args) -> int:
    if args.batch_cmd == "run":
        result = _run_batch(
            flow_path=Path(args.path),
            db_path=Path(args.db),
            profiles=[p.strip() for p in args.profiles.split(",") if p.strip()],
            inputs=_parse_inputs(args.inputs),
            max_concurrent=args.max_concurrent,
            fail_fast=args.fail_fast,
        )
        print(json.dumps({
            "batch_id": result.batch_id,
            "status": result.status,
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
        }, indent=2))
        return 0 if result.status == "completed" and result.failed == 0 else 2

    if args.batch_cmd == "ls":
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from tegufox_core.database import Base, ensure_schema, FlowBatch, FlowRecord

        eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
        Base.metadata.create_all(eng)

        ensure_schema(eng)
        s = sessionmaker(bind=eng)()
        try:
            q = (s.query(FlowBatch, FlowRecord)
                 .join(FlowRecord, FlowRecord.id == FlowBatch.flow_id)
                 .order_by(FlowBatch.started_at.desc())
                 .limit(args.limit))
            for b, f in q:
                print(f"{b.batch_id}\t{f.name}\t{b.status}\t{b.succeeded}/{b.total}\t{b.started_at.isoformat()}")
            return 0
        finally:
            s.close()

    if args.batch_cmd == "show":
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from tegufox_core.database import Base, ensure_schema, FlowBatch, FlowRun, FlowRecord

        eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
        Base.metadata.create_all(eng)

        ensure_schema(eng)
        s = sessionmaker(bind=eng)()
        try:
            b = s.query(FlowBatch).filter_by(batch_id=args.batch_id).first()
            if b is None:
                print(f"not found: {args.batch_id}", file=sys.stderr)
                return 1
            print(json.dumps({
                "batch_id": b.batch_id,
                "status": b.status,
                "total": b.total,
                "succeeded": b.succeeded,
                "failed": b.failed,
                "started_at": b.started_at.isoformat() if b.started_at else None,
                "finished_at": b.finished_at.isoformat() if b.finished_at else None,
            }, indent=2))
            print()
            print("Per-profile runs:")
            for r in s.query(FlowRun).filter_by(batch_id=b.batch_id):
                print(f"  {r.run_id}\t{r.profile_name}\t{r.status}\t{r.error_text or ''}")
            return 0
        finally:
            s.close()

    return 1


def run_cli(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "validate":
        try:
            load_flow(args.path)
            print(f"ok: {args.path}")
            return 0
        except (ValidationError, Exception) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if args.cmd == "run":
        result = run_flow(
            Path(args.path),
            profile_name=args.profile,
            inputs=_parse_inputs(args.inputs),
            db_path=Path(args.db),
            resume=args.resume,
            resume_from=args.resume_from,
            proxy_name=args.proxy_name,
            keep_browser_open=args.keep_browser_open,
        )
        print(json.dumps({
            "run_id": result.run_id,
            "status": result.status,
            "last_step_id": result.last_step_id,
            "error": result.error,
        }, indent=2))
        return 0 if result.status == "succeeded" else 2

    if args.cmd == "runs":
        return _runs_cmd(args)

    if args.cmd == "batch":
        return _batch_cmd(args)

    return 1


def _runs_cmd(args) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tegufox_core.database import Base, ensure_schema, FlowRun, FlowRecord

    eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
    Base.metadata.create_all(eng)

    ensure_schema(eng)
    s = sessionmaker(bind=eng)()
    try:
        if args.runs_cmd == "ls":
            q = s.query(FlowRun).join(FlowRecord, FlowRecord.id == FlowRun.flow_id)
            if args.flow:
                q = q.filter(FlowRecord.name == args.flow)
            q = q.order_by(FlowRun.started_at.desc()).limit(args.limit)
            for r in q:
                print(f"{r.run_id}\t{r.status}\t{r.profile_name}\t{r.started_at.isoformat()}")
            return 0
        if args.runs_cmd == "show":
            r = s.query(FlowRun).filter_by(run_id=args.run_id).first()
            if r is None:
                print(f"not found: {args.run_id}", file=sys.stderr); return 1
            print(json.dumps({
                "run_id": r.run_id,
                "status": r.status,
                "profile": r.profile_name,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "last_step_id": r.last_step_id,
                "error": r.error_text,
                "inputs": json.loads(r.inputs_json or "{}"),
            }, indent=2))
            return 0
    finally:
        s.close()
    return 1
