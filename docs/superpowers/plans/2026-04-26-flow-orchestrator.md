# Multi-profile Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Build sub-project #2 — run a flow across N profiles with bounded concurrency, batch tracking in DB, and CLI/REST/GUI integration.

**Architecture:** New `Orchestrator` class fans out via `ProcessPoolExecutor`; each subprocess runs `tegufox_flow.runtime.run_flow(... batch_id=...)`. New `flow_batches` table groups per-profile `FlowRun` rows.

**Tech Stack:** Python `concurrent.futures`, existing #1 stack (pydantic, ruamel.yaml, jinja2, sqlalchemy), PyQt6 for GUI.

**Spec reference:** `docs/superpowers/specs/2026-04-26-flow-orchestrator-design.md`.

---

## File Structure

| File | Responsibility |
|---|---|
| `tegufox_core/database.py` | (modify) Add `FlowBatch` table + `FlowRun.batch_id` column. |
| `tegufox_flow/engine.py` | (modify) Accept `batch_id` in `run()`, write to `FlowRun.batch_id`. |
| `tegufox_flow/runtime.py` | (modify) Forward `batch_id` to `FlowEngine.run`. |
| `tegufox_flow/orchestrator.py` | NEW. `Orchestrator` + `BatchResult` + `_run_one_subprocess`. |
| `tegufox_flow/cli.py` | (modify) Add `flow batch run / ls / show` subcommands. |
| `tegufox_cli/api.py` | (modify) Add `/batches` REST endpoints. |
| `tegufox_gui/dialogs/__init__.py` | NEW (empty). |
| `tegufox_gui/dialogs/batch_run_dialog.py` | NEW. `BatchRunDialog` QDialog. |
| `tegufox_gui/pages/flows_page.py` | (modify) Add "Run Batch…" button. |
| `tests/orchestrator/__init__.py` | NEW. |
| `tests/orchestrator/conftest.py` | NEW. |
| `tests/orchestrator/test_orchestrator.py` | Unit tests w/ stubbed `_run_one`. |
| `tests/orchestrator/test_orchestrator_batch_id.py` | Engine + runtime forwarding `batch_id`. |
| `tests/orchestrator/test_cli_batch.py` | CLI subcommand parsing. |
| `tests/orchestrator/test_api_batch.py` | REST endpoint integration. |

---

## Conventions

- venv: `source venv/bin/activate`
- Bypass GPG: `git commit --no-gpg-sign`
- Branch: stay on `feat/flow-editor` (it includes #1 code). Or branch fresh `feat/flow-orchestrator` from `feat/flow-editor`. Plan assumes the latter.

---

## Task 1: DB schema (FlowBatch + FlowRun.batch_id)

**Files:**
- Modify: `tegufox_core/database.py`
- Create: `tests/orchestrator/__init__.py`
- Create: `tests/orchestrator/test_db_batch.py`

- [ ] **Step 1: Failing test**

```python
# tests/orchestrator/test_db_batch.py
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowBatch, FlowRun, FlowRecord


def _session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_flow_batch_table_exists():
    s = _session()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    b = FlowBatch(batch_id="b1", flow_id=f.id,
                  inputs_json="{}", status="running",
                  total=2, started_at=datetime.utcnow())
    s.add(b); s.commit()
    assert s.query(FlowBatch).first().batch_id == "b1"


def test_flow_run_has_optional_batch_id():
    s = _session()
    r = FlowRun(run_id="r1", flow_id=1, profile_name="p", inputs_json="{}",
                status="running", started_at=datetime.utcnow(), batch_id=None)
    s.add(r); s.commit()
    assert s.query(FlowRun).one().batch_id is None


def test_flow_run_batch_id_persists():
    s = _session()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit()
    s.add(FlowBatch(batch_id="b1", flow_id=f.id,
                    inputs_json="{}", status="running",
                    total=1, started_at=datetime.utcnow()))
    s.commit()
    s.add(FlowRun(run_id="r1", flow_id=f.id, profile_name="p",
                  inputs_json="{}", status="running",
                  started_at=datetime.utcnow(), batch_id="b1"))
    s.commit()
    assert s.query(FlowRun).filter_by(run_id="r1").one().batch_id == "b1"
```

- [ ] **Step 2: Run, expect ImportError**

```bash
mkdir -p tests/orchestrator
touch tests/orchestrator/__init__.py
source venv/bin/activate
pytest tests/orchestrator/test_db_batch.py -v
```

- [ ] **Step 3: Implement**

In `tegufox_core/database.py`, append after the existing `FlowKVState` class (the last sub-project #1 class):

```python
class FlowBatch(Base):
    __tablename__ = "flow_batches"

    batch_id    = Column(String(64), primary_key=True)
    flow_id     = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    inputs_json = Column(Text, nullable=False, default="{}")
    status      = Column(String(32), nullable=False, default="running", index=True)
    total       = Column(Integer, nullable=False, default=0)
    succeeded   = Column(Integer, nullable=False, default=0)
    failed      = Column(Integer, nullable=False, default=0)
    started_at  = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
```

In the existing `FlowRun` class (defined earlier in the same file), add ONE new column line, alongside the others:

```python
    batch_id = Column(String(64), ForeignKey("flow_batches.batch_id"), nullable=True, index=True)
```

- [ ] **Step 4: Run**

```bash
pytest tests/orchestrator/test_db_batch.py -v
pytest tests/flow -m "not golden" -q          # 116 unchanged
pytest tests/flow_editor -q                   # 26 unchanged
```

- [ ] **Step 5: Commit**

```bash
git add tegufox_core/database.py tests/orchestrator/__init__.py tests/orchestrator/test_db_batch.py
git commit --no-gpg-sign -m "feat(orchestrator): FlowBatch table + FlowRun.batch_id"
```

---

## Task 2: Wire batch_id through engine + runtime

**Files:**
- Modify: `tegufox_flow/engine.py`
- Modify: `tegufox_flow/runtime.py`
- Create: `tests/orchestrator/test_orchestrator_batch_id.py`

- [ ] **Step 1: Failing tests**

```python
# tests/orchestrator/test_orchestrator_batch_id.py
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowRecord, FlowRun, FlowBatch
from tegufox_flow.engine import FlowEngine
from tegufox_flow.dsl import parse_flow
from tegufox_flow.steps import register, STEP_REGISTRY


@pytest.fixture(autouse=True)
def _iso():
    snap = dict(STEP_REGISTRY)
    yield
    STEP_REGISTRY.clear()
    STEP_REGISTRY.update(snap)


@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    yield Session
    eng.dispose()


def test_run_writes_batch_id_when_provided(db):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "x",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    # Pre-create the batch row so the FK is satisfied.
    s = db()
    f = FlowRecord(name="x", yaml_text="...", schema_version=1,
                   created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    s.add(f); s.commit(); fid = f.id
    s.add(FlowBatch(batch_id="b1", flow_id=fid, inputs_json="{}",
                    status="running", total=1,
                    started_at=datetime.utcnow()))
    s.commit(); s.close()

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p", batch_id="b1")
    assert result.status == "succeeded"

    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.batch_id == "b1"


def test_run_default_batch_id_is_none(db):
    @register("t.ok")
    def _(spec, ctx):
        pass

    flow = parse_flow({
        "schema_version": 1, "name": "x",
        "steps": [{"id": "a", "type": "t.ok"}],
    })
    fake_session = MagicMock()
    fake_session.page = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)

    with patch("tegufox_flow.engine.TegufoxSession", return_value=fake_session):
        eng = FlowEngine(db_session_factory=db)
        result = eng.run(flow, inputs={}, profile_name="p")
    s = db()
    row = s.query(FlowRun).filter_by(run_id=result.run_id).one()
    assert row.batch_id is None
```

- [ ] **Step 2: Run, expect failure** (`run()` doesn't accept batch_id yet, or doesn't persist it).

- [ ] **Step 3: Modify FlowEngine.run signature**

Open `tegufox_flow/engine.py`. Find the `def run(self, flow, *, inputs, profile_name, resume=None, resume_from=None) -> RunResult:` and add a kwarg:

```python
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
```

In the body, where `FlowRun(...)` is constructed inside the `else:` branch (for new runs, not resume), add `batch_id=batch_id`:

```python
run_row = FlowRun(
    run_id=run_id, flow_id=fid, profile_name=profile_name,
    inputs_json=json.dumps(inputs, default=str),
    status="running", started_at=datetime.utcnow(),
    batch_id=batch_id,
)
```

(Don't touch the resume branch — resuming does not change batch_id.)

- [ ] **Step 4: Modify runtime.run_flow**

Open `tegufox_flow/runtime.py`. Add `batch_id` kwarg + forward:

```python
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
```

- [ ] **Step 5: Run**

```bash
pytest tests/orchestrator/test_orchestrator_batch_id.py -v
pytest tests/flow -m "not golden" -q   # all 116 still pass
```

- [ ] **Step 6: Commit**

```bash
git add tegufox_flow/engine.py tegufox_flow/runtime.py tests/orchestrator/test_orchestrator_batch_id.py
git commit --no-gpg-sign -m "feat(orchestrator): forward batch_id through runtime + engine"
```

---

## Task 3: Orchestrator class

**Files:**
- Create: `tegufox_flow/orchestrator.py`
- Create: `tests/orchestrator/test_orchestrator.py`

- [ ] **Step 1: Failing tests**

```python
# tests/orchestrator/test_orchestrator.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tegufox_core.database import Base, FlowBatch, FlowRecord, FlowRun
from tegufox_flow.engine import RunResult
from tegufox_flow.orchestrator import Orchestrator, BatchResult


def _make_db(tmp_path):
    db = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(eng)
    return db


def _ok_result(profile, run_id):
    return RunResult(run_id=run_id, status="succeeded",
                     last_step_id="a", error=None, inputs={})


def _fail_result(profile, run_id):
    return RunResult(run_id=run_id, status="failed",
                     last_step_id="a", error="boom", inputs={})


def test_orchestrator_runs_each_profile(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    calls = []
    def fake(args):
        flow_path, profile, inputs, db_path, batch_id = args
        calls.append(profile)
        return RunResult(run_id=f"r-{profile}", status="succeeded",
                         last_step_id="a", error=None, inputs=inputs)

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1)
        result = orch.run(profiles=["a", "b", "c"], inputs={})

    assert sorted(calls) == ["a", "b", "c"]
    assert result.total == 3
    assert result.succeeded == 3
    assert result.failed == 0


def test_orchestrator_writes_batch_row(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    with patch("tegufox_flow.orchestrator._run_one_subprocess",
               side_effect=lambda args: _ok_result(args[1], f"r-{args[1]}")):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1)
        result = orch.run(profiles=["x"], inputs={})

    eng = create_engine(f"sqlite:///{db}")
    s = sessionmaker(bind=eng)()
    rows = s.query(FlowBatch).all()
    assert len(rows) == 1
    assert rows[0].batch_id == result.batch_id
    assert rows[0].status == "completed"
    assert rows[0].succeeded == 1
    assert rows[0].failed == 0
    assert rows[0].total == 1


def test_orchestrator_aggregates_failures(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")

    def fake(args):
        _, profile, _, _, _ = args
        return (_ok_result(profile, f"r-{profile}") if profile == "a"
                else _fail_result(profile, f"r-{profile}"))

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1)
        result = orch.run(profiles=["a", "b", "c"], inputs={})
    assert result.succeeded == 1
    assert result.failed == 2


def test_per_profile_inputs_override(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\n"
        "inputs:\n  q:\n    type: string\n    required: true\n"
        "steps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    seen = {}
    def fake(args):
        _, profile, inputs, _, _ = args
        seen[profile] = inputs
        return _ok_result(profile, f"r-{profile}")

    with patch("tegufox_flow.orchestrator._run_one_subprocess", side_effect=fake):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1)
        orch.run(profiles=["a", "b"], inputs={"q": "default"},
                 per_profile_inputs={"a": {"q": "alice"}})

    assert seen["a"]["q"] == "alice"
    assert seen["b"]["q"] == "default"


def test_validates_required_inputs_before_dispatch(tmp_path):
    db = _make_db(tmp_path)
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\n"
        "inputs:\n  q:\n    type: string\n    required: true\n"
        "steps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    with patch("tegufox_flow.orchestrator._run_one_subprocess",
               side_effect=AssertionError("should not be called")):
        orch = Orchestrator(flow_path=flow_yaml, db_path=db, max_concurrent=1)
        with pytest.raises(ValueError) as e:
            orch.run(profiles=["a"], inputs={})
        assert "q" in str(e.value)
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest tests/orchestrator/test_orchestrator.py -v
```

- [ ] **Step 3: Implement**

Write `tegufox_flow/orchestrator.py`:

```python
"""Multi-profile orchestrator: run one flow on N profiles with bounded concurrency."""

from __future__ import annotations
import json
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
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

        with ProcessPoolExecutor(max_workers=self._max) as ex:
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
```

- [ ] **Step 4: Run**

```bash
pytest tests/orchestrator/test_orchestrator.py -v
pytest tests/orchestrator -q                  # 5 + 2 + 3 = 10
pytest tests/flow -m "not golden" -q          # 116
pytest tests/flow_editor -q                   # 26
```

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/orchestrator.py tests/orchestrator/test_orchestrator.py
git commit --no-gpg-sign -m "feat(orchestrator): Orchestrator class with bounded concurrency"
```

---

## Task 4: CLI batch subcommands

**Files:**
- Modify: `tegufox_flow/cli.py`
- Create: `tests/orchestrator/test_cli_batch.py`

- [ ] **Step 1: Failing tests**

```python
# tests/orchestrator/test_cli_batch.py
import pytest
from pathlib import Path
from unittest.mock import patch

from tegufox_flow.cli import build_parser, run_cli
from tegufox_flow.orchestrator import BatchResult


def test_batch_run_parses_profiles_csv():
    p = build_parser()
    ns = p.parse_args([
        "batch", "run", "f.yaml",
        "--profiles", "a,b,c",
        "--inputs", "q=hello",
        "--max-concurrent", "2",
    ])
    assert ns.cmd == "batch"
    assert ns.batch_cmd == "run"
    assert ns.profiles == "a,b,c"
    assert ns.max_concurrent == 2


def test_batch_run_invokes_orchestrator(tmp_path):
    flow_yaml = tmp_path / "f.yaml"
    flow_yaml.write_text(
        "schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"
    )

    fake_result = BatchResult(
        batch_id="b1", flow_name="f", total=2,
        succeeded=2, failed=0, status="completed", runs=[],
    )
    with patch("tegufox_flow.cli._run_batch", return_value=fake_result) as p:
        rc = run_cli([
            "batch", "run", str(flow_yaml),
            "--profiles", "a,b",
            "--max-concurrent", "1",
            "--db", str(tmp_path / "t.db"),
        ])
        assert rc == 0
        p.assert_called_once()
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/orchestrator/test_cli_batch.py -v
```

- [ ] **Step 3: Modify `tegufox_flow/cli.py`**

In `build_parser()`, after the existing `runs = sub.add_parser("runs", ...)` block, add:

```python
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
```

Add a small helper at module level (above `run_cli`):

```python
def _run_batch(flow_path, db_path, profiles, inputs, max_concurrent, fail_fast):
    from .orchestrator import Orchestrator
    orch = Orchestrator(
        flow_path=flow_path, db_path=db_path,
        max_concurrent=max_concurrent, fail_fast=fail_fast,
    )
    return orch.run(profiles=profiles, inputs=inputs)
```

In `run_cli`, after the existing `if args.cmd == "runs": ...` branch, add:

```python
    if args.cmd == "batch":
        return _batch_cmd(args)
```

And define `_batch_cmd`:

```python
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
        from tegufox_core.database import Base, FlowBatch, FlowRecord

        eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
        Base.metadata.create_all(eng)
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
        from tegufox_core.database import Base, FlowBatch, FlowRun, FlowRecord

        eng = create_engine(f"sqlite:///{Path('data/tegufox.db').resolve()}")
        Base.metadata.create_all(eng)
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
```

- [ ] **Step 4: Run**

```bash
pytest tests/orchestrator/test_cli_batch.py -v
pytest tests/flow -m "not golden" -q   # still 116
```

- [ ] **Step 5: Commit**

```bash
git add tegufox_flow/cli.py tests/orchestrator/test_cli_batch.py
git commit --no-gpg-sign -m "feat(orchestrator): tegufox-cli flow batch run/ls/show"
```

---

## Task 5: REST batch endpoints

**Files:**
- Modify: `tegufox_cli/api.py`
- Create: `tests/orchestrator/test_api_batch.py`

- [ ] **Step 1: Failing tests**

```python
# tests/orchestrator/test_api_batch.py
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_post_batch_invokes_orchestrator(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    from tegufox_flow.orchestrator import BatchResult

    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/flows", json={"name": "f", "yaml":
        "schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n"})

    fake = BatchResult(batch_id="b1", flow_name="f", total=2,
                       succeeded=2, failed=0, status="completed", runs=[])

    with patch("tegufox_cli.api.Orchestrator") as O:
        O.return_value.run.return_value = fake
        r = client.post("/flows/f/batches", json={
            "profiles": ["a", "b"], "inputs": {}, "max_concurrent": 1,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["batch_id"] == "b1"
        assert body["succeeded"] == 2


def test_post_batch_404_unknown_flow(tmp_path, monkeypatch):
    from tegufox_cli.api import create_app
    monkeypatch.setenv("TEGUFOX_DB", str(tmp_path / "t.db"))
    app = create_app()
    client = TestClient(app)
    r = client.post("/flows/ghost/batches", json={"profiles": ["a"], "inputs": {}})
    assert r.status_code == 404
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/orchestrator/test_api_batch.py -v
```

- [ ] **Step 3: Modify `tegufox_cli/api.py`**

Near the existing `flow_router` endpoints, add at module level:

```python
from tegufox_flow.orchestrator import Orchestrator, BatchResult


class BatchRequest(BaseModel):
    profiles: list
    inputs: dict = {}
    per_profile_inputs: dict = {}
    max_concurrent: int = 3
    fail_fast: bool = False


@flow_router.post("/flows/{name}/batches")
def post_batch(name: str, body: BatchRequest):
    s = _flow_db_session()
    try:
        rec = s.query(FlowRecord).filter_by(name=name).first()
        if rec is None:
            raise HTTPException(404, "flow not found")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(rec.yaml_text); tmp = f.name
    finally:
        s.close()

    orch = Orchestrator(
        flow_path=tmp, db_path=os.environ.get("TEGUFOX_DB", "data/tegufox.db"),
        max_concurrent=body.max_concurrent, fail_fast=body.fail_fast,
    )
    result = orch.run(
        profiles=body.profiles, inputs=body.inputs,
        per_profile_inputs=body.per_profile_inputs or None,
    )
    return {
        "batch_id": result.batch_id, "status": result.status,
        "total": result.total, "succeeded": result.succeeded,
        "failed": result.failed,
    }


@flow_router.get("/batches")
def list_batches(limit: int = 20):
    s = _flow_db_session()
    try:
        from tegufox_core.database import FlowBatch
        rows = (s.query(FlowBatch)
                .order_by(FlowBatch.started_at.desc())
                .limit(limit).all())
        return [{
            "batch_id": r.batch_id, "status": r.status,
            "total": r.total, "succeeded": r.succeeded, "failed": r.failed,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        } for r in rows]
    finally:
        s.close()


@flow_router.get("/batches/{batch_id}")
def get_batch(batch_id: str):
    s = _flow_db_session()
    try:
        from tegufox_core.database import FlowBatch
        b = s.query(FlowBatch).filter_by(batch_id=batch_id).first()
        if b is None:
            raise HTTPException(404, "not found")
        return {
            "batch_id": b.batch_id, "status": b.status,
            "total": b.total, "succeeded": b.succeeded, "failed": b.failed,
            "started_at": b.started_at.isoformat() if b.started_at else None,
            "finished_at": b.finished_at.isoformat() if b.finished_at else None,
        }
    finally:
        s.close()


@flow_router.get("/batches/{batch_id}/runs")
def get_batch_runs(batch_id: str):
    s = _flow_db_session()
    try:
        from tegufox_core.database import FlowRun
        rows = s.query(FlowRun).filter_by(batch_id=batch_id).all()
        return [{
            "run_id": r.run_id, "profile_name": r.profile_name,
            "status": r.status, "last_step_id": r.last_step_id,
            "error": r.error_text,
        } for r in rows]
    finally:
        s.close()
```

- [ ] **Step 4: Run**

```bash
pytest tests/orchestrator/test_api_batch.py -v
pytest tests/flow -m "not golden" -q   # 116 unchanged
```

- [ ] **Step 5: Commit**

```bash
git add tegufox_cli/api.py tests/orchestrator/test_api_batch.py
git commit --no-gpg-sign -m "feat(orchestrator): REST endpoints for batches"
```

---

## Task 6: GUI BatchRunDialog + Flows page button

**Files:**
- Create: `tegufox_gui/dialogs/__init__.py` (empty)
- Create: `tegufox_gui/dialogs/batch_run_dialog.py`
- Modify: `tegufox_gui/pages/flows_page.py`
- Create: `tests/orchestrator/test_batch_dialog.py`

- [ ] **Step 1: conftest exists already from flow_editor; create one for orchestrator**

```python
# tests/orchestrator/conftest.py
import importlib.util
import sys

import pytest


@pytest.fixture(scope="session")
def qapp():
    if importlib.util.find_spec("PyQt6") is None:
        pytest.skip("PyQt6 not available", allow_module_level=False)
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)
```

- [ ] **Step 2: Failing test**

```python
# tests/orchestrator/test_batch_dialog.py
import importlib.util
import pytest

if importlib.util.find_spec("PyQt6") is None:
    pytest.skip("PyQt6 not available", allow_module_level=True)


def test_batch_dialog_constructs(qapp, tmp_path):
    from tegufox_gui.dialogs.batch_run_dialog import BatchRunDialog
    dlg = BatchRunDialog(
        flow_name="x",
        flow_yaml="schema_version: 1\nname: x\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n",
        profile_names=["alice", "bob"],
        db_path=str(tmp_path / "t.db"),
    )
    assert dlg.profile_list.count() == 2
    assert dlg.max_concurrent_spin.value() == 3


def test_flows_page_has_batch_button(qapp, tmp_path):
    from tegufox_gui.pages.flows_page import FlowsPage
    page = FlowsPage(db_path=str(tmp_path / "t.db"))
    assert hasattr(page, "batch_btn")
    assert page.batch_btn is not None
```

- [ ] **Step 3: Run, expect failure**

```bash
pytest tests/orchestrator/test_batch_dialog.py -v
```

- [ ] **Step 4: Implement BatchRunDialog**

Write `tegufox_gui/dialogs/__init__.py` empty. Then `tegufox_gui/dialogs/batch_run_dialog.py`:

```python
"""Modal dialog to launch a multi-profile batch run."""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QPushButton, QProgressBar, QMessageBox,
)

from tegufox_flow.orchestrator import Orchestrator, BatchResult


class _BatchWorker(QThread):
    finished_with = pyqtSignal(object)   # BatchResult

    def __init__(self, flow_path: Path, db_path: Path, profiles: List[str],
                 max_concurrent: int, fail_fast: bool):
        super().__init__()
        self.flow_path = flow_path
        self.db_path = db_path
        self.profiles = profiles
        self.max_concurrent = max_concurrent
        self.fail_fast = fail_fast

    def run(self):
        try:
            orch = Orchestrator(
                flow_path=self.flow_path, db_path=self.db_path,
                max_concurrent=self.max_concurrent, fail_fast=self.fail_fast,
            )
            result = orch.run(profiles=self.profiles, inputs={})
            self.finished_with.emit(result)
        except Exception as e:
            self.finished_with.emit(BatchResult(
                batch_id="error", flow_name="?", total=0,
                succeeded=0, failed=0, status=f"crashed: {e}", runs=[],
            ))


class BatchRunDialog(QDialog):
    def __init__(self, *, flow_name: str, flow_yaml: str,
                 profile_names: List[str], db_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Run batch: {flow_name}")
        self.resize(500, 500)

        self._flow_yaml = flow_yaml
        self._db_path = Path(db_path)
        self._worker: _BatchWorker | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Profiles (Ctrl/Cmd-click to multi-select):"))
        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for p in profile_names:
            self.profile_list.addItem(QListWidgetItem(p))
        layout.addWidget(self.profile_list, 1)

        row = QHBoxLayout()
        row.addWidget(QLabel("Max concurrent:"))
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 16)
        self.max_concurrent_spin.setValue(3)
        row.addWidget(self.max_concurrent_spin)

        self.fail_fast_check = QCheckBox("Fail fast")
        row.addWidget(self.fail_fast_check)
        row.addStretch(1)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # indeterminate until run starts
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.run_btn = QPushButton("Run")
        self.close_btn = QPushButton("Close")
        self.run_btn.clicked.connect(self._on_run)
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)
        btn_row.addWidget(self.run_btn)
        layout.addLayout(btn_row)

    def _selected_profiles(self) -> List[str]:
        return [self.profile_list.item(i).text()
                for i in range(self.profile_list.count())
                if self.profile_list.item(i).isSelected()]

    def _on_run(self):
        profiles = self._selected_profiles()
        if not profiles:
            QMessageBox.warning(self, "Select profiles", "Pick at least one profile.")
            return

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(self._flow_yaml); flow_path = Path(f.name)

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText(f"Running on {len(profiles)} profile(s)…")

        self._worker = _BatchWorker(
            flow_path=flow_path, db_path=self._db_path,
            profiles=profiles,
            max_concurrent=self.max_concurrent_spin.value(),
            fail_fast=self.fail_fast_check.isChecked(),
        )
        self._worker.finished_with.connect(self._on_done)
        self._worker.start()

    def _on_done(self, result: BatchResult):
        self.progress.setVisible(False)
        self.status_label.setText(
            f"{result.status}: {result.succeeded}/{result.total} succeeded; "
            f"{result.failed} failed (batch {result.batch_id[:8]}…)"
        )
        self.run_btn.setEnabled(True)
```

- [ ] **Step 5: Modify FlowsPage**

In `tegufox_gui/pages/flows_page.py`, add a `self.batch_btn = QPushButton("Run Batch…")` near the other buttons, append to the row layout AFTER `self.upload_btn` and BEFORE `self.run_btn`:

```python
self.batch_btn = QPushButton("Run Batch…")
self.batch_btn.clicked.connect(self._on_batch)
row.addWidget(self.batch_btn)
```

(Look at the existing layout order — the goal is just to be visible alongside Run / Upload / New. Exact ordering is not critical.)

Add slot:

```python
def _on_batch(self):
    item = self.list_widget.currentItem()
    if item is None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Pick a flow", "Select a flow first.")
        return

    s = self._session()
    try:
        from tegufox_core.database import FlowRecord
        rec = s.query(FlowRecord).filter_by(name=item.text()).one()
        flow_yaml = rec.yaml_text
    finally:
        s.close()

    profiles = []
    try:
        from tegufox_core.profile_manager import ProfileManager
        pm = ProfileManager()
        profiles = [(p["name"] if isinstance(p, dict) else getattr(p, "name", str(p)))
                    for p in pm.list_profiles() if hasattr(pm, "list_profiles") else pm.list()]
    except Exception:
        pass

    from tegufox_gui.dialogs.batch_run_dialog import BatchRunDialog
    dlg = BatchRunDialog(
        flow_name=item.text(), flow_yaml=flow_yaml,
        profile_names=profiles, db_path=self._db_path, parent=self,
    )
    dlg.exec()
```

NB: the ProfileManager method might be `list()` rather than `list_profiles()` — check the existing FlowsPage `_refresh()` for how profiles are loaded and copy that exact call. Don't invent a new one. If the existing call fails silently in `_refresh`, mirror that fallback.

- [ ] **Step 6: Run**

```bash
pytest tests/orchestrator/test_batch_dialog.py -v
pytest tests/orchestrator -q          # all orchestrator tests
pytest tests/flow_editor -q           # 26
pytest tests/flow -m "not golden" -q  # 116
```

- [ ] **Step 7: Commit**

```bash
git add tegufox_gui/dialogs/__init__.py tegufox_gui/dialogs/batch_run_dialog.py tegufox_gui/pages/flows_page.py tests/orchestrator/conftest.py tests/orchestrator/test_batch_dialog.py
git commit --no-gpg-sign -m "feat(orchestrator): GUI BatchRunDialog + Flows page button"
```

---

## Self-review notes

**Spec coverage:**

| Spec § | Implemented in |
|---|---|
| §3 schema | Task 1 |
| §4.1 Python API | Task 3 |
| §4.2 CLI | Task 4 |
| §4.3 REST | Task 5 |
| §4.4 GUI | Task 6 |
| §5 concurrency | Task 3 |
| §6 failure policy | Task 3 |
| §7 per-profile inputs | Task 3 |
| §8 persistence ordering | Task 3 |
| §9 testing | Tasks 1-6 |

**Placeholder scan:** Task 6 has one "look up the existing ProfileManager call" instruction — not a placeholder, but an instruction to mirror existing code. Acceptable.

**Type consistency:** `BatchResult` defined in Task 3 is consumed identically in Tasks 4-6. `RunResult` from #1 is reused.

**Concerns to flag during execution:**

1. ProcessPoolExecutor on macOS uses `spawn` (not `fork`) since Python 3.8+ — slower per-process startup but safer with Cocoa. Subprocess imports `tegufox_flow` which loads Camoufox monkeypatch. Should work; note in commit if startup is noticeably slow.
2. SQLite WAL mode is enabled by default for newer SQLAlchemy — if not, increment writes from multiple subprocesses + main may serialise. If tests are flaky, set `PRAGMA journal_mode=WAL` on engine creation in `_session_factory`.
3. The GUI test for `BatchRunDialog` doesn't actually run the batch — it only constructs the dialog. Real e2e is manual.
