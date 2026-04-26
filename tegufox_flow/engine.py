"""Flow execution engine — tree interpreter."""

from __future__ import annotations
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .dsl import Flow, OnError
from .errors import StepError, GotoSignal, BreakSignal, ContinueSignal
from .steps import StepSpec, get_handler

from tegufox_core.database import FlowRecord, FlowRun
from tegufox_automation import TegufoxSession  # type: ignore

from .checkpoints import CheckpointStore, KVStore
from .context import FlowContext
from .expressions import ExpressionEngine


@dataclass
class RunResult:
    run_id: str
    status: str  # succeeded | failed | aborted
    last_step_id: Optional[str]
    error: Optional[str]
    inputs: dict


_LOG = logging.getLogger("tegufox_flow.engine")


def _to_spec(step) -> StepSpec:
    """Coerce a Pydantic Step into a registry StepSpec."""
    return StepSpec(
        id=step.id,
        type=step.type,
        params=step.params,
        on_error=step.on_error,
        when=step.when,
    )


class FlowEngine:
    def __init__(
        self,
        default_on_error: Optional[OnError] = None,
        *,
        db_session_factory=None,
        env_allowlist: Optional[set] = None,
    ) -> None:
        self._default_on_error = default_on_error or OnError(action="abort")
        self._db = db_session_factory
        self._env_allow = env_allowlist or set()

    def _execute_one(self, step, ctx) -> None:
        spec = step if isinstance(step, StepSpec) else _to_spec(step)
        ctx.current_step_id = spec.id

        if spec.when is not None and not bool(ctx.eval(spec.when)):
            ctx.logger.info(f"step {spec.id!r} skipped (when=false)")
            return

        policy = spec.on_error or self._default_on_error
        handler = get_handler(spec.type)

        attempt = 0
        while True:
            attempt += 1
            try:
                handler(spec, ctx)
                ctx.checkpoints.save(ctx.run_id, spec.id, ctx.vars)
                return
            except (GotoSignal, BreakSignal, ContinueSignal):
                raise
            except Exception as e:
                if isinstance(e, (StepError,)):
                    raise
                if policy.action == "retry" and attempt < policy.max_attempts:
                    ctx.logger.warning(
                        f"step {spec.id!r} failed (attempt {attempt}): {e}; retrying"
                    )
                    if policy.backoff_ms:
                        time.sleep(policy.backoff_ms / 1000.0)
                    continue
                if policy.action == "skip":
                    ctx.logger.warning(f"step {spec.id!r} failed: {e}; skipped")
                    return
                if policy.action == "goto":
                    ctx.logger.warning(
                        f"step {spec.id!r} failed: {e}; jumping to {policy.goto_step!r}"
                    )
                    raise GotoSignal(target=policy.goto_step) from e
                raise StepError(step_id=spec.id, step_type=spec.type, cause=e) from e

    def execute_steps(self, steps, ctx, *, resume_from: Optional[str] = None) -> None:
        skipping = resume_from is not None
        i = 0
        while i < len(steps):
            step = steps[i]
            spec = step if isinstance(step, StepSpec) else _to_spec(step)
            if skipping:
                if spec.id == resume_from:
                    skipping = False
                else:
                    i += 1
                    continue
            try:
                self._execute_one(spec, ctx)
            except GotoSignal as g:
                target = g.target
                idx = self._find_index(steps, target)
                if idx is None:
                    raise  # propagate to outer scope
                i = idx
                continue
            i += 1

    @staticmethod
    def _find_index(steps, target: str) -> Optional[int]:
        for idx, step in enumerate(steps):
            sid = step.id if hasattr(step, "id") else step["id"]
            if sid == target:
                return idx
        return None

    def run(
        self,
        flow: Flow,
        *,
        inputs: dict,
        profile_name: str,
        resume: Optional[str] = None,
        resume_from: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> RunResult:
        self._validate_inputs(flow, inputs)
        run_id = resume or str(uuid.uuid4())

        with self._db() as s:
            fid = s.query(FlowRecord.id).filter_by(name=flow.name).scalar()
            if fid is None:
                rec = FlowRecord(
                    name=flow.name, yaml_text="(loaded from disk)",
                    schema_version=flow.schema_version,
                    created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
                )
                s.add(rec)
                s.commit()
                fid = rec.id

            if resume:
                run_row = s.query(FlowRun).filter_by(run_id=run_id).first()
                if run_row is None:
                    raise ValueError(f"unknown run_id {run_id}")
                run_row.status = "running"
            else:
                run_row = FlowRun(
                    run_id=run_id, flow_id=fid, profile_name=profile_name,
                    inputs_json=json.dumps(inputs, default=str),
                    status="running", started_at=datetime.utcnow(),
                    batch_id=batch_id,
                )
                s.add(run_row)
            s.commit()

        status = "failed"
        err = None
        last = None

        with self._db() as s:
            checkpoints = CheckpointStore(s)
            kv = KVStore(s, flow_name=flow.name)

            vars_: dict = {}
            resume_step: Optional[str] = resume_from
            if resume:
                cp = checkpoints.last(run_id)
                if cp:
                    vars_ = dict(cp.vars)
                    resume_step = self._step_after(flow.steps, cp.step_id)

            with TegufoxSession(profile=profile_name) as session:
                try:
                    from tegufox_automation import HumanMouse, HumanKeyboard
                except ImportError:
                    HumanMouse = None
                    HumanKeyboard = None

                ctx = FlowContext(
                    session=session, page=session.page,
                    flow_name=flow.name, run_id=run_id,
                    inputs=dict(inputs), vars=vars_,
                    kv=kv, checkpoints=checkpoints,
                    expressions=ExpressionEngine(),
                    env_allowlist=self._env_allow,
                )
                ctx._human_mouse = HumanMouse(session.page) if HumanMouse else None
                ctx._human_keyboard = HumanKeyboard(session.page) if HumanKeyboard else None
                ctx._original_page = session.page
                ctx.engine = self

                try:
                    self.execute_steps(flow.steps, ctx, resume_from=resume_step)
                    status, err = "succeeded", None
                except Exception as e:
                    status = "failed"
                    err = f"{type(e).__name__}: {e}"
                finally:
                    last = ctx.current_step_id

        with self._db() as s:
            row = s.query(FlowRun).filter_by(run_id=run_id).one()
            row.status = status
            row.last_step_id = last
            row.error_text = err
            row.finished_at = datetime.utcnow()
            s.commit()

        return RunResult(
            run_id=run_id, status=status,
            last_step_id=last, error=err, inputs=inputs,
        )

    def _validate_inputs(self, flow: Flow, inputs: dict) -> None:
        for name, decl in flow.inputs.items():
            if name not in inputs and decl.required and decl.default is None:
                raise ValueError(f"missing required input {name!r}")

    @staticmethod
    def _step_after(steps, step_id: str) -> Optional[str]:
        for i, s in enumerate(steps):
            if s.id == step_id:
                if i + 1 < len(steps):
                    return steps[i + 1].id
                return None
        return None
