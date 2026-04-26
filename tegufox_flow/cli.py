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

    return 1


def _runs_cmd(args) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tegufox_core.database import Base, FlowRun, FlowRecord

    eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
    Base.metadata.create_all(eng)
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
