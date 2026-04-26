"""Exception hierarchy for the flow engine.

ValidationError is raised at parse time and never caught by the engine.
StepError is raised by step handlers; the engine applies on_error policy.
FlowError is the terminal run failure surfaced to callers.

Break/Continue/Goto are control-flow signals (not errors) used inside loops.
"""

from typing import List, Optional


class FlowEngineException(Exception):
    """Base class — never raise directly."""


class ValidationError(FlowEngineException):
    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        super().__init__("flow validation failed:\n  - " + "\n  - ".join(self.problems))


class StepError(FlowEngineException):
    def __init__(self, step_id: str, step_type: str, cause: BaseException):
        self.step_id = step_id
        self.step_type = step_type
        self.cause = cause
        super().__init__(f"step {step_id!r} ({step_type}) failed: {cause}")


class FlowError(FlowEngineException):
    def __init__(self, run_id: str, flow_name: str, cause: BaseException):
        self.run_id = run_id
        self.flow_name = flow_name
        self.cause = cause
        super().__init__(f"flow {flow_name!r} run {run_id} failed: {cause}")


class BreakSignal(FlowEngineException):
    """Raised by control.break, caught by control.for_each / control.while."""


class ContinueSignal(FlowEngineException):
    """Raised by control.continue, caught by control.for_each / control.while."""


class GotoSignal(FlowEngineException):
    def __init__(self, target: str):
        self.target = target
        super().__init__(f"goto {target!r}")
