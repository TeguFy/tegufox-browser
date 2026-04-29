"""Tegufox flow DSL + engine.

Public surface:
    load_flow(path) -> Flow
    FlowEngine(profile_name=..., db_path=...).run(flow, inputs=...) -> RunResult
"""
from .errors import (
    ValidationError, StepError, FlowError,
    BreakSignal, ContinueSignal, GotoSignal,
)
from .dsl import Flow, Step, Input, OnError, parse_flow, load_flow, dump_flow

__all__ = [
    "ValidationError", "StepError", "FlowError",
    "BreakSignal", "ContinueSignal", "GotoSignal",
    "Flow", "Step", "Input", "OnError",
    "parse_flow", "load_flow", "dump_flow",
]
