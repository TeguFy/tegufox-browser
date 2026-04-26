# Flow DSL + Execution Engine — Design Spec

**Sub-project:** #1 of 6 (foundation for the automation toolkit)
**Date:** 2026-04-25
**Status:** Draft, awaiting user review
**Owner:** lugondev

## 1. Goal

Provide a deterministic, file-based way to describe a browser automation flow and execute it on top of an existing `TegufoxSession` (one profile per run). The flow file is the single source of truth — both human-editable and machine-generable — so that the visual editor (#3), AI generators (#4/#5), and dashboard (#6) can be built on a stable contract.

In scope (v1):

- YAML schema for flows (lossless round-trip with the future visual editor).
- A tree-interpreter engine that walks the YAML and dispatches to step handlers.
- Step vocabulary covering browser actions, data extraction, control flow, external I/O, and persistent state.
- Per-step error policy (retry / skip / abort / goto).
- Crash-resume via per-step checkpoints.
- CLI command, plus a programmatic API the GUI/REST layer will reuse.

Out of scope (deferred to other sub-projects):

- Multi-profile orchestration (#2)
- Visual editor (#3)
- AI step / AI flow generator (#4, #5)
- Run dashboard UI (#6)
- Cron / schedule trigger (use OS cron + CLI for now)
- Sub-flow / include
- Notification steps (use `io.http_request` to a webhook)

## 2. Non-goals / explicit YAGNI

- No coroutine transpiler. Tree interpreter only.
- No compiled state machine. Resume is checkpoint-based, not FSM-based.
- No expression DSL of our own. Reuse Jinja2 (sandboxed).
- No plugin loader from external packages in v1. Step types live inside `tegufox_flow.steps`.

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         tegufox_flow/                          │
│                                                                │
│   dsl.py   ──── parses + validates YAML (pydantic)             │
│      │                                                         │
│      ▼                                                         │
│   engine.py ──── FlowEngine: walks ParsedFlow                  │
│      │                                                         │
│      ├── context.py ──── FlowContext (vars, session, logger)   │
│      ├── expressions.py ─ Jinja2 sandbox + helpers             │
│      ├── checkpoints.py ─ SQLite checkpoint + KV state         │
│      ├── errors.py     ── FlowError, StepError, ValidationError│
│      └── steps/                                                │
│          ├── browser.py  (uses tegufox_automation.TegufoxSession)
│          ├── extract.py                                        │
│          ├── control.py                                        │
│          ├── io.py                                             │
│          └── state.py                                          │
│                                                                │
│   runtime.py ─── high-level entrypoint (load YAML → run)       │
│   cli.py     ─── tegufox-cli flow ... commands                 │
└────────────────────────────────────────────────────────────────┘
        ▲                          ▲
        │                          │
   tegufox_cli                 tegufox_gui
   (CLI + REST)                (GUI runner button)
```

Dependency direction stays consistent with the existing layout:

```
GUI ─┐
     ├──> tegufox_flow ──> tegufox_automation ──> tegufox_core
CLI ─┘
```

`tegufox_flow` does not depend on PyQt6, Camoufox internals, or browserforge. It only depends on `tegufox_automation` (for `TegufoxSession`) and `tegufox_core` (for `ProfileManager`, `ProxyManager`).

## 4. YAML schema

A flow is a single YAML document.

```yaml
schema_version: 1
name: amazon-search
description: "Search Amazon for a query, save top results to JSON."
inputs:
  query:
    type: string
    required: true
  max_results:
    type: int
    default: 10
defaults:
  on_error:
    action: abort
steps:
  - id: open
    type: browser.goto
    url: "https://www.amazon.com"
    wait_until: load

  - id: search_box
    type: browser.type
    selector: "#twotabsearchtextbox"
    text: "{{ inputs.query }}"

  - id: submit
    type: browser.click
    selector: "#nav-search-submit-button"
    on_error:
      action: retry
      max_attempts: 3
      backoff_ms: 1000

  - id: wait_results
    type: browser.wait_for
    selector: ".s-result-item"
    state: visible
    timeout_ms: 10000

  - id: extract
    type: extract.eval_js
    set: results
    script: |
      return Array.from(
        document.querySelectorAll('.s-result-item h2 a')
      ).slice(0, {{ inputs.max_results }}).map(a => ({
        title: a.innerText.trim(),
        href: a.href
      }));

  - id: filter
    type: control.if
    when: "{{ vars.results | length > 0 }}"
    then:
      - id: write_out
        type: io.write_file
        path: "out/{{ inputs.query | slug }}.json"
        content: "{{ vars.results | tojson(indent=2) }}"
    else:
      - id: log_empty
        type: io.log
        level: warning
        message: "No results for {{ inputs.query }}"

editor:
  positions:
    open:        { x: 100, y: 100 }
    search_box:  { x: 100, y: 200 }
    submit:      { x: 100, y: 300 }
    wait_results:{ x: 100, y: 400 }
    extract:     { x: 100, y: 500 }
    filter:      { x: 100, y: 600 }
```

### 4.1 Top-level fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | int | yes | Always `1` for v1. Engine refuses unknown versions. |
| `name` | string | yes | Slug used as file stem and DB key. |
| `description` | string | no | Free text. |
| `inputs` | map | no | Declared inputs with type + default. Engine validates inputs at run start. |
| `defaults` | map | no | `on_error`, `timeout_ms`, etc. inherited by steps that omit them. |
| `steps` | list | yes | Ordered list of step nodes. |
| `editor` | map | no | Editor metadata namespace. Ignored by engine. Round-trip preserved. |

### 4.2 Step node

Common fields on every step:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique within the flow. Used in checkpoints, logs, `goto`. |
| `type` | string | yes | `<category>.<action>`, e.g. `browser.click`. Must be in `STEP_REGISTRY`. |
| `on_error` | map | no | `{ action, max_attempts, backoff_ms, goto_step }`. Inherits from `defaults`. |
| `when` | string | no | Jinja expression. If false, step is skipped. (Inline guard, alternative to `control.if`.) |
| Type-specific fields | — | varies | Defined per step type below. |

### 4.3 Step types (v1, frozen contract)

**Browser** (operates on `TegufoxSession.page`):

| Type | Required fields | Optional fields |
|---|---|---|
| `browser.goto` | `url` | `wait_until` (load/domcontentloaded/networkidle), `timeout_ms` |
| `browser.click` | `selector` | `button` (left/right/middle), `click_count`, `human` (default true) |
| `browser.type` | `selector`, `text` | `delay_ms`, `clear_first` (default false), `human` |
| `browser.hover` | `selector` | — |
| `browser.scroll` | `direction` (up/down) or `to` (top/bottom/selector) | `pixels`, `smooth` |
| `browser.wait_for` | `selector` | `state` (visible/attached/hidden), `timeout_ms` |
| `browser.select_option` | `selector`, `value` | — |
| `browser.screenshot` | `path` | `full_page`, `selector` (element screenshot) |
| `browser.press_key` | `key` | `selector` (focus first) |

**Extract**:

| Type | Required fields | Optional fields |
|---|---|---|
| `extract.read_text` | `selector`, `set` | — |
| `extract.read_attr` | `selector`, `attr`, `set` | — |
| `extract.eval_js` | `script`, `set` | — |
| `extract.url` | `set` | — |
| `extract.title` | `set` | — |

**Control** (note: any step also accepts an inline `when:` guard from §4.2 — use `control.if` only when you need an `else` branch or want to group multiple steps under one condition):

| Type | Required fields | Optional fields |
|---|---|---|
| `control.if` | `when`, `then` | `else` |
| `control.for_each` | `items`, `var`, `body` | `index_var` |
| `control.while` | `when`, `body`, `max_iterations` (default 1000) | — |
| `control.set` | `var`, `value` | — |
| `control.break` | — | — |
| `control.continue` | — | — |
| `control.sleep` | `ms` | — |
| `control.goto` | `step_id` | — |

**I/O**:

| Type | Required fields | Optional fields |
|---|---|---|
| `io.http_request` | `method`, `url` | `headers`, `body`, `set`, `timeout_ms` |
| `io.read_file` | `path`, `set` | `format` (text/json/csv), `encoding` |
| `io.write_file` | `path`, `content` | `append`, `encoding` |
| `io.log` | `message` | `level` (debug/info/warning/error) |

**State** (persistent KV, scoped by flow name):

| Type | Required fields | Optional fields |
|---|---|---|
| `state.save` | `key`, `value` | — |
| `state.load` | `key`, `set` | `default` |
| `state.delete` | `key` | — |

### 4.4 Expression language

Jinja2 in **sandboxed** mode (`jinja2.sandbox.SandboxedEnvironment`).

Variable namespaces visible to expressions:

- `inputs.<name>` — flow inputs (immutable per run).
- `vars.<name>` — runtime variables set by `extract.*`, `control.set`, or any step's `set:` field.
- `state.<name>` — persistent KV (lazy-loaded; reading it triggers a checkpoint read).
- `env.<NAME>` — environment variables, **allowlist-only** (configured in `data/settings.conf`).
- Built-in helpers: `now()`, `today()`, `uuid()`, `random_int(a, b)`, `slug(s)`, `tojson(x)`.

Filter additions: `slug`, `tojson`, `b64encode`, `b64decode`.

Templates appear inside string fields (`url`, `text`, `path`, `script`, `message`, `value`). Engine renders **before** dispatching to the step handler.

### 4.5 Round-trip rules (editor compatibility)

- Step ordering is preserved.
- Unknown keys in a step **fail validation** (so editor can never silently drop user data).
- The `editor:` top-level namespace is preserved verbatim, even if the engine doesn't read it.
- YAML comments on individual steps are preserved when the editor saves (using `ruamel.yaml`, not `pyyaml`).

## 5. Engine semantics

### 5.1 Run lifecycle

```
load YAML → parse + validate (pydantic)
          → assign run_id (uuid4)
          → create Run row (status=running)
          → bind TegufoxSession (open browser)
          → execute steps
          → close session
          → update Run row (status, finished_at, last_step_id, error)
```

### 5.2 Step dispatch

```python
def execute_steps(steps: list[Step], ctx: FlowContext, resume_from: str | None):
    skipping = resume_from is not None
    for step in steps:
        if skipping:
            if step.id == resume_from:
                skipping = False
            else:
                continue
        execute_one(step, ctx)

def execute_one(step: Step, ctx: FlowContext):
    ctx.current_step_id = step.id

    if step.when and not ctx.eval(step.when):
        ctx.logger.info(f"step {step.id} skipped (when=false)")
        return

    handler = STEP_REGISTRY[step.type]
    attempt = 0
    policy = step.on_error or ctx.flow.defaults.on_error
    while True:
        attempt += 1
        try:
            ctx.checkpoints.save(ctx.run_id, step.id, ctx.snapshot())
            handler(step, ctx)
            return
        except StepError as e:
            ctx.logger.warning(f"step {step.id} failed (attempt {attempt}): {e}")
            if policy.action == "retry" and attempt < policy.max_attempts:
                time.sleep(policy.backoff_ms / 1000)
                continue
            if policy.action == "skip":
                return
            if policy.action == "goto":
                raise GotoSignal(policy.goto_step)
            raise
```

`control.if`, `control.for_each`, `control.while` are step types whose handlers recursively call `execute_steps` on their `then`/`else`/`body`.

### 5.3 Variable scoping

- `inputs` — frozen at run start; set/mutate raises.
- `vars` — flat dict, top-level scope. `for_each` shadows the loop var inside its body; restored on exit. Nested `for_each` inside the same loop variable name raises a validation error at parse time.
- `state` — read/write via `state.*` steps. Engine writes through to SQLite synchronously.

### 5.4 Resume

Two resume modes:

1. **Auto-resume after crash** — `tegufox-cli flow run <name> --resume <run_id>`. Engine reads the last successful checkpoint from `checkpoints` table, restores `vars`, finds the next step by id, and continues.
2. **Manual jump** — `--resume-from <step_id>` starts from a specific step with empty `vars` (debugging aid).

Limitations (accepted):

- A step that crashes mid-execution (e.g., halfway through `browser.click`) loses progress in *that step*. Resume re-runs the failing step, which is fine for idempotent browser actions. The user is responsible for using `state.save` before non-idempotent operations (purchase confirmation, send message, etc.).
- `for_each` does not checkpoint individual iterations. To make a long loop resumable, the user should `state.save` an "index processed so far" key inside the body and skip processed indices on resume.

### 5.5 Error policy

Per-step `on_error.action`:

- `abort` (default) — propagate, mark run failed.
- `retry` — re-run the step up to `max_attempts` times with `backoff_ms` between attempts.
- `skip` — log and continue with the next sibling step.
- `goto` — jump to `goto_step` (must be a step id at the same or an outer scope; cannot jump into a control block). The `control.goto` step type follows the same scope rule.

`defaults.on_error` at flow level applies to any step without an explicit `on_error`.

## 6. Persistence schema

New tables added to the existing `data/tegufox.db` (SQLAlchemy migration):

```sql
CREATE TABLE flows (
    id           INTEGER PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,
    description  TEXT,
    yaml_text    TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL
);

CREATE TABLE flow_runs (
    run_id        TEXT PRIMARY KEY,            -- uuid4
    flow_id       INTEGER NOT NULL REFERENCES flows(id),
    profile_name  TEXT NOT NULL,
    inputs_json   TEXT NOT NULL,
    status        TEXT NOT NULL,               -- running|succeeded|failed|aborted
    started_at    DATETIME NOT NULL,
    finished_at   DATETIME,
    last_step_id  TEXT,
    error_text    TEXT
);

CREATE TABLE flow_checkpoints (
    run_id      TEXT NOT NULL REFERENCES flow_runs(run_id),
    step_id     TEXT NOT NULL,
    seq         INTEGER NOT NULL,              -- monotonic per run
    vars_json   TEXT NOT NULL,
    created_at  DATETIME NOT NULL,
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX idx_checkpoints_run ON flow_checkpoints(run_id, seq DESC);

CREATE TABLE flow_kv_state (
    flow_name   TEXT NOT NULL,
    key         TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    updated_at  DATETIME NOT NULL,
    PRIMARY KEY (flow_name, key)
);
```

On-disk artifacts per run, under `data/runs/<run_id>/`:

- `log.jsonl` — one JSON line per log event, `{ts, level, step_id, message, ...}`.
- `screenshots/<step_id>.png` — written by `browser.screenshot` if `path` starts with `runs/`.

## 7. Public API

### 7.1 Python

```python
from tegufox_flow import load_flow, FlowEngine, FlowContext

flow = load_flow("flows/amazon-search.yaml")  # raises ValidationError on bad YAML
engine = FlowEngine(profile_name="seller-1")
result = engine.run(flow, inputs={"query": "laptop"})
# result.status, result.run_id, result.last_step_id, result.error
```

### 7.2 CLI

```bash
tegufox-cli flow validate flows/amazon-search.yaml
tegufox-cli flow run flows/amazon-search.yaml \
    --profile seller-1 \
    --inputs query=laptop max_results=20

tegufox-cli flow runs ls --flow amazon-search --limit 20
tegufox-cli flow runs show <run_id>
tegufox-cli flow run flows/amazon-search.yaml --resume <run_id>
tegufox-cli flow run flows/amazon-search.yaml --resume-from <step_id>   # debug start
```

### 7.3 REST (added to existing FastAPI app)

```
POST /flows                      # upload/replace YAML
GET  /flows                      # list
GET  /flows/{name}               # get YAML
POST /flows/{name}/runs          # body: {profile, inputs}; returns {run_id}
GET  /flows/{name}/runs          # list runs
GET  /runs/{run_id}              # status + last step
GET  /runs/{run_id}/log          # stream log.jsonl
```

The GUI page (`flows_page.py`) in v1 is a minimal list + "Run on profile" button. Real visual editing is sub-project #3.

## 8. Error model

Three exception classes, all in `tegufox_flow.errors`:

- `ValidationError` — raised at parse time, lists all schema problems with line numbers.
- `StepError` — raised by step handlers; carries `step_id`, `step_type`, `cause`.
- `FlowError` — terminal run failure, wraps the chain of `StepError`s.

Engine never catches `ValidationError`. It catches `StepError` and applies the `on_error` policy. Anything else (`Exception`) is treated as a bug, logged with full traceback, and surfaces as a `FlowError`.

## 9. Testing strategy

Three layers, all pytest-driven:

1. **Unit** (`tests/flow/test_dsl.py`, `test_steps_*.py`) — schema validation, expression rendering, individual step handlers with a fake `FlowContext` and a fake Page.
2. **Integration** (`tests/flow/test_engine.py`) — engine on synthetic flows against `tests/fixtures/static_pages/` served by a local `http.server`, real Camoufox in headless mode.
3. **Golden flows** (`tests/flow/flows/`) — YAML fixtures (`linear_search.yaml`, `conditional_filter.yaml`, `stateful_loop.yaml`) executed end-to-end, compared against expected output and screenshot hashes.

Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.golden`. CI runs unit by default; integration/golden behind a flag because they launch a real browser.

## 10. Implementation file layout

```
tegufox_flow/
├── __init__.py              # re-exports load_flow, FlowEngine, FlowContext
├── dsl.py                   # pydantic models + YAML loader (ruamel.yaml)
├── engine.py                # FlowEngine, execute_steps, execute_one
├── context.py               # FlowContext dataclass
├── expressions.py           # Jinja2 sandbox + filters/helpers
├── checkpoints.py           # CheckpointStore + KVStore (SQLAlchemy)
├── errors.py
├── runtime.py               # high-level run() helper
├── cli.py                   # tegufox-cli flow ... subcommands
└── steps/
    ├── __init__.py          # STEP_REGISTRY
    ├── browser.py
    ├── extract.py
    ├── control.py
    ├── io.py
    └── state.py

tests/flow/
├── __init__.py
├── conftest.py              # fakes, fixtures, static page server
├── test_dsl.py
├── test_expressions.py
├── test_engine.py
├── test_steps_browser.py
├── test_steps_extract.py
├── test_steps_control.py
├── test_steps_io.py
├── test_steps_state.py
└── flows/
    ├── linear_search.yaml
    ├── conditional_filter.yaml
    └── stateful_loop.yaml

docs/
└── FLOW_DSL_GUIDE.md        # user-facing doc, v1 minimal
```

Existing files touched:

- `tegufox-cli` entrypoint script — register `flow` subcommand group.
- `tegufox_cli/api.py` — add the `/flows`, `/runs` endpoints.
- `tegufox_core/database.py` — add the four new tables to the SQLAlchemy schema, plus a small migration helper (`alembic` is overkill; a one-shot `CREATE TABLE IF NOT EXISTS` via `Base.metadata.create_all` suffices).
- `tegufox_gui/pages/flows_page.py` — new minimal list page; sidebar entry added in `tegufox_gui/app.py` or wherever pages are registered.
- `pytest.ini` — register the new markers.

## 11. Decisions and tradeoffs

| Decision | Alternative considered | Why this |
|---|---|---|
| Tree interpreter | State machine, async coroutines | 1:1 with YAML, easy editor round-trip, easy AI generation, < 500 LOC core. Resume is "good enough" via checkpoints + idempotent steps. |
| YAML (ruamel) | JSON node-graph, Python script | Human-editable, comment-preserving, lossless round-trip with the future visual editor. JSON-graph forces editor to be primary; Python kills editor round-trip and AI verifiability. |
| Jinja2 sandbox | Custom expression parser, pure-Python `eval` | Already widely understood, has filters, sandboxable, zero invented syntax. |
| Checkpoint per step | Per iteration / per coroutine yield | Simpler. Long loops resume by user-managed `state.save` of an index. |
| New tables in `tegufox.db` | Separate `flows.db` | One DB simplifies cross-references (a run references a profile). |
| pydantic for schema | jsonschema, dataclasses + custom | Best error messages, integrates with FastAPI naturally. |
| `on_error.action = abort` default | Default to retry | Fail-fast. User opts into retry/skip explicitly per step. |
| No external step plugins in v1 | Entry-point plugin loader | YAGNI. Add later when there's a concrete reason. |

## 12. Roadmap relative to other sub-projects

Once #1 lands and the YAML schema is frozen:

- **#2 Multi-profile orchestrator** consumes a flow file + a list of profiles, runs N `FlowEngine` instances with concurrency limits, aggregates results.
- **#3 Visual editor** reads/writes the same YAML, uses `editor:` namespace for canvas positions. No engine changes needed.
- **#4 AI Copilot step** adds `ai.ask` / `ai.act` step types in a new `tegufox_flow/steps/ai.py`. Step contract; no engine changes.
- **#5 AI Flow Generator** produces a YAML that validates against the v1 schema. Pure consumer of the schema.
- **#6 Run dashboard** queries `flow_runs` + `flow_checkpoints` tables and the on-disk `log.jsonl`. Pure consumer of the persistence layer.

The schema is the contract; treat it as a published API after v1.

## 13. Open questions

None blocking the spec. Items to revisit when implementation starts:

- Exact Jinja2 sandbox allowlist (expressions vs helpers vs filters).
- Whether `browser.*` steps default `human=true` (use `HumanMouse`/`HumanKeyboard`) or `human=false`. Leaning `human=true` since this whole project is anti-detection-first.
- Screenshot path policy — auto-rewrite relative paths to `data/runs/<run_id>/screenshots/`?

These are implementation-level decisions; the writing-plans pass will pin them.
