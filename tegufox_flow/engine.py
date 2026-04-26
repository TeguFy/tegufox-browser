"""Flow execution engine — tree interpreter."""

from __future__ import annotations
import logging
import time
from typing import List, Optional

from .dsl import Flow, OnError
from .errors import StepError, GotoSignal
from .steps import StepSpec, get_handler


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
    def __init__(self, default_on_error: Optional[OnError] = None) -> None:
        self._default_on_error = default_on_error or OnError(action="abort")

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
            except (GotoSignal,):
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
