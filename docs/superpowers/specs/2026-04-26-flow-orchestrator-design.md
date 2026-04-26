# Multi-profile Flow Orchestrator — Design Spec

**Sub-project:** #2 of 6 (depends on #1)
**Date:** 2026-04-26
**Status:** Draft
**Owner:** lugondev

## 1. Goal

Run a single flow against N profiles with bounded concurrency. Track each profile's run as a normal `FlowRun` (from #1) plus a parent `FlowBatch` row that groups them. Surface batch progress through CLI, REST, and a GUI dialog.

In scope (v1):

- `Orchestrator` class — pure Python entrypoint with `max_concurrent`, `fail_fast`, and per-profile input overrides.
- New `flow_batches` table + `batch_id` column on `flow_runs`.
- ProcessPoolExecutor-based parallelism (each profile in its own OS process).
- CLI: `tegufox-cli flow batch run` / `batch ls` / `batch show`.
- REST: `POST /flows/{name}/batches`, `GET /batches`, `GET /batches/{id}`.
- GUI: "Run Batch…" button on the Flows page → multi-select profiles + max-concurrent spinner + live progress.

Out of scope (defer):

- Cross-profile data sharing (one profile's KV state is per-flow, shared across profiles by design — not changed here).
- Cron / schedule trigger for batches (use OS cron + CLI).
- Live streaming logs in the GUI dialog beyond status counts.
- Distributed runners across machines.
- Auto-retry of failed profiles within the same batch.
- Capacity-aware concurrency tuning (CPU/memory probing).

## 2. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  tegufox_flow.orchestrator.py                  │
│                                                                │
│   Orchestrator                                                 │
│      │ run(profiles, inputs, per_profile_inputs)               │
│      │   1. create FlowBatch row (batch_id = uuid4)            │
│      │   2. fan out FlowEngine.run via ProcessPoolExecutor     │
│      │   3. aggregate RunResult into BatchResult               │
│      │   4. update FlowBatch row (status, counts)              │
│      ▼                                                         │
│   _run_one(args) → spawned in subprocess                       │
│      │ (top-level fn, picklable)                               │
│      ▼                                                         │
│   tegufox_flow.runtime.run_flow(... batch_id=...)              │
│      → FlowEngine.run(... batch_id=...)                        │
│      → writes FlowRun.batch_id                                 │
└────────────────────────────────────────────────────────────────┘
```

`Orchestrator` is the only new class. Everything else is wiring `batch_id` through existing #1 functions.

## 3. Database changes

Two additions to `tegufox_core/database.py`:

```python
class FlowBatch(Base):
    __tablename__ = "flow_batches"
    batch_id      = Column(String(64), primary_key=True)
    flow_id       = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    inputs_json   = Column(Text, nullable=False, default="{}")
    status        = Column(String(32), nullable=False, default="running", index=True)  # running|completed|aborted
    total         = Column(Integer, nullable=False, default=0)
    succeeded     = Column(Integer, nullable=False, default=0)
    failed        = Column(Integer, nullable=False, default=0)
    started_at    = Column(DateTime, nullable=False)
    finished_at   = Column(DateTime)


# Add to existing FlowRun class:
class FlowRun(Base):
    __tablename__ = "flow_runs"
    # ... existing columns ...
    batch_id = Column(String(64), ForeignKey("flow_batches.batch_id"), nullable=True, index=True)
```

`Base.metadata.create_all()` is idempotent; SQLite tolerates the new column on existing rows because it's nullable.

## 4. API

### 4.1 Python

```python
from tegufox_flow.orchestrator import Orchestrator, BatchResult

orch = Orchestrator(
    flow_path="flows/amazon-search.yaml",
    db_path="data/tegufox.db",
    max_concurrent=3,
    fail_fast=False,
)
result = orch.run(
    profiles=["alice", "bob", "carol"],
    inputs={"query": "laptop"},
    per_profile_inputs={
        "alice": {"max_results": 5},
        "bob": {"max_results": 20},
    },
)
# result.batch_id, result.total, result.succeeded, result.failed
# result.runs: list[RunResult]
```

`per_profile_inputs[profile]` is merged shallowly over `inputs` for that profile. A profile not in `per_profile_inputs` uses just `inputs`.

### 4.2 CLI

```bash
tegufox-cli flow batch run flows/x.yaml \
    --profiles alice,bob,carol \
    --inputs query=laptop \
    --max-concurrent 3 \
    [--fail-fast]

tegufox-cli flow batch ls --limit 20
tegufox-cli flow batch show <batch_id>
```

`batch show` prints the batch summary plus a one-line-per-profile status table.

### 4.3 REST

```
POST /flows/{name}/batches
  body: { profiles: ["a","b"], inputs: {...},
          per_profile_inputs: {...},
          max_concurrent: 3, fail_fast: false }
  returns: { batch_id, total, succeeded, failed, status }

GET /batches?limit=20
GET /batches/{batch_id}
GET /batches/{batch_id}/runs
```

### 4.4 GUI

Flows page gets a third button next to **Run** and **Upload YAML…**: **Run Batch…**.

Clicking opens `BatchRunDialog`:

- Multi-select list of available profiles (from `ProfileManager.list()`).
- Max concurrent spinner (1..16, default 3).
- Fail-fast checkbox (default off).
- Inputs key=value entries (one row per `flow.inputs` declared key — pre-filled with defaults).
- "Run" button → spawns a `_BatchWorker(QThread)` calling `Orchestrator.run`.
- Progress: a `QProgressBar` showing `(succeeded + failed) / total` and a status label `X of Y done (S succeeded, F failed)`.

Closing the dialog while running asks for confirmation.

## 5. Concurrency model

`Orchestrator.run` uses `concurrent.futures.ProcessPoolExecutor(max_workers=max_concurrent)` to dispatch one `_run_one(args)` call per profile.

`_run_one` is a top-level module function (picklable) that calls `tegufox_flow.runtime.run_flow(...)`. Each subprocess imports `tegufox_flow`, which triggers Camoufox's monkeypatch and step registry — same as a fresh `tegufox-cli flow run`.

Why processes, not threads:

- Camoufox/Playwright sync API uses greenlets pinned to the creating thread; multiple sessions in one process share a single asyncio loop and step on each other.
- A crashed Firefox in profile A's subprocess does not take down profile B's subprocess.
- SQLite WAL handles concurrent writes from multiple subprocesses cleanly.

**Cost:** every subprocess imports the full Tegufox stack (~1-2 s). For batches of hundreds of profiles, optimisation is a v2 concern (worker pool reuse).

## 6. Failure policy

`fail_fast=False` (default):

- Each profile is independent.
- A profile's failure → its `FlowRun.status = "failed"`, `error_text` populated.
- The batch continues. Final batch status = `"completed"` regardless of per-profile failures.
- Counts in `FlowBatch`: `total = N`, `succeeded` = number of `RunResult.status == "succeeded"`, `failed` = `total - succeeded`.

`fail_fast=True`:

- First profile failure → orchestrator calls `executor.shutdown(wait=False, cancel_futures=True)`.
- Pending profiles never start; in-flight profiles complete naturally (no kill).
- `FlowBatch.status = "aborted"`.

## 7. Per-profile inputs

`per_profile_inputs: dict[str, dict] | None` keyed by profile name. For each profile, the orchestrator computes:

```python
merged = {**inputs, **per_profile_inputs.get(profile, {})}
```

`merged` is then validated against the flow's `inputs` declarations (each `Input(required=True, default=None)` must be satisfied or the orchestrator raises `ValueError` BEFORE submitting any work).

## 8. Persistence ordering

```
1. orch.run() called
2. Validate inputs for every profile (synchronous, before fan-out)
3. INSERT FlowBatch (status=running, total=N)
4. for each profile:
     submit _run_one(... batch_id=...) to executor
5. as each future completes:
     (FlowRun row was already written by FlowEngine.run inside subprocess)
     atomically: UPDATE FlowBatch SET succeeded=succeeded+1 (or failed)
6. all done:
     UPDATE FlowBatch SET status=completed|aborted, finished_at=NOW
```

Step 5's increment uses a transaction with `WHERE batch_id = ...` and reads the current count first; SQLite's WAL handles concurrent UPDATE on a single row well enough for our scale.

## 9. Testing strategy

- **Unit (`tests/orchestrator/test_orchestrator.py`)**:
  - `Orchestrator.run` with a stubbed `_run_one` (monkeypatched to return canned `RunResult`s) — no real Camoufox.
  - Validates: batch row created, counts updated, `fail_fast` cancels pending, per-profile input merging.
- **Integration (`tests/orchestrator/test_orchestrator_batch_id.py`)**:
  - In-process: stub `TegufoxSession` and run `runtime.run_flow(... batch_id=...)` directly. Verify `FlowRun.batch_id` is populated.
- **Golden** (`tests/orchestrator/test_golden_batch.py`, `@pytest.mark.golden`):
  - Real ProcessPoolExecutor with 2 fake "profiles" against the static page server. Manual run only.

CLI/REST/GUI tests follow the existing patterns from #1.

## 10. File layout (after impl)

```
tegufox_flow/
├── orchestrator.py              NEW — Orchestrator + BatchResult + _run_one
├── runtime.py                   modify — accept + forward batch_id
├── engine.py                    modify — accept batch_id, write to FlowRun
├── cli.py                       modify — add `flow batch ...` subcommands
└── ...

tegufox_core/database.py         modify — FlowBatch table, FlowRun.batch_id
tegufox_cli/api.py               modify — /batches endpoints
tegufox_gui/pages/flows_page.py  modify — "Run Batch…" button
tegufox_gui/dialogs/             NEW
└── batch_run_dialog.py          NEW — BatchRunDialog QDialog

tests/orchestrator/
├── __init__.py
├── conftest.py
├── test_orchestrator.py
├── test_orchestrator_batch_id.py
└── test_golden_batch.py
```

## 11. Decisions and tradeoffs

| Decision | Alternative | Why |
|---|---|---|
| ProcessPoolExecutor | ThreadPoolExecutor | Camoufox/Playwright sync API requires greenlet thread affinity; processes also isolate browser crashes. |
| `fail_fast=False` default | fail_fast=True | Most batch users want all profiles attempted regardless. Fail-fast is a debugging aid. |
| Single batch row, increment counters per future | Per-future ledger table | Simpler. Counters reconstructable from FlowRun rows if needed. |
| Inputs validated before fan-out | Validate per subprocess | Fail fast on bad inputs without spinning up N subprocesses. |
| `flow_batches.batch_id` is uuid4 string | Auto-increment int | Same convention as `flow_runs.run_id`. |
| `batch_id` on `FlowRun` is nullable | Required | Single-profile runs (#1) don't have a batch — must remain backward compatible. |

## 12. Roadmap context

- **#4 AI Copilot** can call the orchestrator to test a generated flow across N profiles for confidence.
- **#5 AI Flow Generator** is a peer of #2 — both consume the schema, neither depends on the other.
- **#6 Run dashboard** queries `flow_batches` + `flow_runs` to render batch + per-profile timelines.

The `batch_id` column is the integration point for #6.

## 13. Open questions (resolve in plan)

- Whether to surface batch-level Jinja template variables (`batch.profile`, `batch.index`) in the flow's inputs. Probably not in v1 — use `per_profile_inputs` for variation.
- Default `max_concurrent` value: chosen 3 (browsers are heavy on RAM). Reconsider once we measure.
- Whether GUI's `_BatchWorker` should poll the DB for progress or get push notifications via Qt signals from a separate listener thread. v1: polls every 500 ms via QTimer.
