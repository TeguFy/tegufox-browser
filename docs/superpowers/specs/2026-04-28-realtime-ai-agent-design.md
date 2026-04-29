# Realtime AI Agent — Design Spec

**Sub-project:** #7 (depends on #1 engine + #4 ai_providers)
**Date:** 2026-04-28
**Status:** Draft
**Owner:** lugondev

## 1. Goal

Provide an interactive agent loop that drives a TegufoxSession against
a goal stated in plain language. The LLM observes the current page,
picks one action from a curated 10-verb vocabulary, executes it, and
repeats until the goal is achieved or a stop condition trips.

The agent **coexists with flows** (sub-project #1) — it is for one-off
exploration, not for replacing repeatable scripted automation. After a
successful agent run the user can opt to **auto-record the trace as a
YAML flow** so the next execution is deterministic and free.

In scope (v1):

- DOM-only observation (truncated outerHTML).
- 10-verb action vocabulary.
- Stop on: `max_steps`, `max_time`, LLM-emitted `done`, user "Stop".
- Single-call ReAct loop (one LLM call per turn).
- Provider-agnostic via the existing `ai_providers.ask_llm`.
- New "Agent" GUI page with live trace + Stop.
- Persist agent runs in `flow_runs` (with `kind='agent'`).
- Optional auto-record to `flows` table (default off).

Out of scope (defer):

- Multimodal vision (screenshot inputs).
- Plan-then-execute / re-planning patterns.
- Per-provider tool-calling (Anthropic tool_use, OpenAI function_call).
- AI verifier as second LLM check.
- Confirmation dialogs for dangerous actions.
- Token-cost tracking (covered indirectly by `max_steps`).
- Pause + resume across app restarts.

## 2. Architecture

```
┌────────────────────────────────────────────────────────────┐
│              tegufox_flow/agent.py                         │
│                                                            │
│   AgentAction   = {verb: str, args: dict, reasoning?: str} │
│   AgentResult   = {status, reason, steps, history,         │
│                    started_at, finished_at, run_id}        │
│                                                            │
│   AgentRunner.run() → AgentResult                          │
│      with TegufoxSession(profile, proxy) as s:             │
│         loop ≤ max_steps:                                  │
│            obs    = _observe(s.page)                       │
│            action = _decide(history, obs)   # 1 LLM call   │
│            emit signal(step_i, action)                     │
│            if action.verb == 'done': return …              │
│            if action.verb == 'ask_user': pause …           │
│            result = _dispatch(action, s)    # → step       │
│            history.append({obs, action, result})           │
│         until: time exceeded | user_stop                   │
│      if record_as_flow: save YAML                          │
└────────────────────────────────────────────────────────────┘
        ▲
        │
   tegufox_gui/pages/agent_page.py
        ↑ goal text, profile/proxy/options, live trace,
          🦾 Run / 🛑 Stop, Save-as-flow checkbox
```

Dependencies (no new external):
- `tegufox_automation.TegufoxSession` (existing)
- `tegufox_flow.steps.ai_providers.ask_llm` (existing, multi-provider)
- `tegufox_flow.steps.{browser,extract}` handler functions (re-used by dispatcher)
- `tegufox_core.database.FlowRun` (extended with two new columns)

## 3. Action vocabulary

10 verbs. Each maps to one existing step handler invoked through the
dispatcher (no `FlowEngine` required — the agent runs simpler ad-hoc
machinery).

| Verb | Args | Maps to |
|---|---|---|
| `goto` | `url`, `wait_until?` | `browser.goto` |
| `click` | `selector` | `browser.click` (force=true) |
| `click_text` | `text`, `role?` | `browser.click_text` |
| `type` | `selector`, `text` | `browser.type` (human=false) |
| `scroll` | `direction` (up/down), `pixels?` OR `to` (top/bottom/<sel>) | `browser.scroll` |
| `wait_for` | `selector`, `state?` | `browser.wait_for` |
| `read_text` | `selector` | `extract.read_text` — value returned in result |
| `screenshot` | `path` | `browser.screenshot` |
| `done` | `reason` | terminate loop, status='done' |
| `ask_user` | `question` | pause loop, GUI dialog, resume with reply |

LLM must emit one verb per turn as JSON:

```json
{
  "reasoning": "user wants to login to Google; click email field",
  "verb": "type",
  "args": { "selector": "#identifierId", "text": "alice@example.com" }
}
```

The parser validates `verb` ∈ vocabulary and that required `args` keys
are present. Malformed output triggers a retry with the parser error
fed back to the LLM as a system message; up to 3 total attempts (1
initial + 2 retries) before the agent aborts with status `parse_error`.

## 4. Loop pseudocode

```python
class AgentRunner:
    SYSTEM_PROMPT = (
        "You are a browser-automation agent.\n"
        "Goal: {goal}\n\n"
        "On each turn output ONE JSON object with these keys:\n"
        "  reasoning  — one short sentence explaining the choice\n"
        "  verb       — exactly one of [goto, click, click_text, type,\n"
        "                scroll, wait_for, read_text, screenshot,\n"
        "                done, ask_user]\n"
        "  args       — verb-specific keys (see catalogue)\n\n"
        "Emit verb='done' with args.reason when you've achieved the\n"
        "goal. Emit verb='ask_user' with args.question if a piece of\n"
        "information is missing (e.g. 2FA code).\n"
        "Output ONLY the JSON, no markdown, no prose."
    )

    def run(self) -> AgentResult:
        with TegufoxSession(profile=..., config=...) as session:
            history: list = []
            started = datetime.utcnow()
            for step_i in range(self.max_steps):
                if self._stop.is_set():
                    return AgentResult(status="aborted", ...)
                if (datetime.utcnow() - started).total_seconds() > self.max_time:
                    return AgentResult(status="timeout", ...)

                obs = self._observe(session.page)
                action = self._decide(history, obs)        # parser-validated
                self.step_emitted.emit(step_i, action)

                if action.verb == "done":
                    return AgentResult(status="done",
                                       reason=action.args["reason"], ...)
                if action.verb == "ask_user":
                    reply = self._signal_ask(action.args["question"])
                    history.append({"obs": obs, "action": action,
                                    "result": {"user_reply": reply}})
                    continue

                try:
                    result = self._dispatch(action, session)
                except Exception as e:
                    result = {"error": f"{type(e).__name__}: {e}"}
                history.append({"obs": obs, "action": action, "result": result})

            return AgentResult(status="max_steps", ...)

    def _observe(self, page) -> dict:
        return {
            "url": page.url,
            "title": page.title()[:200],
            "dom": _truncate_dom(page.content(), 8000),
        }

    def _decide(self, history, obs) -> AgentAction:
        messages = [
            self.SYSTEM_PROMPT.format(goal=self.goal),
            self._format_history(history[-10:]),     # last 10 turns
            f"CURRENT PAGE:\nURL: {obs['url']}\nTITLE: {obs['title']}\n"
            f"DOM:\n{obs['dom']}\n\nNext action JSON:",
        ]
        for retry in range(3):
            raw = ask_llm(system=messages[0], user="\n\n".join(messages[1:]),
                          provider=self.provider, model=self.model,
                          max_tokens=512)
            try:
                return AgentAction.parse(raw)
            except ParseError as e:
                messages.append(f"PARSE ERROR: {e}\nReturn valid JSON.")
        raise RuntimeError("LLM produced malformed JSON 3 times")
```

## 5. Persistence

Schema additions to `flow_runs`:

```sql
ALTER TABLE flow_runs ADD COLUMN kind VARCHAR(16) DEFAULT 'flow';
ALTER TABLE flow_runs ADD COLUMN goal_text TEXT;
```

`ensure_schema()` extended with these ALTERs (idempotent).

Per-step trace persisted as `flow_checkpoints` rows:
- `step_id = f"agent_step_{i}"`
- `vars_json = {"verb": ..., "args": ..., "reasoning": ..., "result": ...}`

Run-level row in `flow_runs`:
- `kind = 'agent'`
- `goal_text = <user goal>`
- `inputs_json = <user inputs dict>`
- `last_step_id = <last verb executed>`
- `error_text = <reason / parse_error / timeout / abort>`

Auto-record (when checkbox ON and `status == 'done'`):
- Build YAML by iterating history, mapping each verb back to its step
  type with the same args. Insert a `name`, `inputs:` block, ordered
  `steps:` list.
- Insert into `flows` with name `agent-{slug(goal)}-{timestamp}`.
- Show toast/log: "Saved as flow `<name>`".

## 6. GUI — Agent page

New sidebar entry "🦾 Agent". Layout:

```
┌─ Agent ───────────────────────────────────────────┐
│ Goal: [QPlainTextEdit, multiline, 4 visible rows] │
│       e.g. "Login to Google with the email and    │
│       password from inputs, then post 'Hello'     │
│       on x.com home"                              │
│                                                   │
│ Profile: [combo]  Proxy: [combo]                  │
│ Max steps: [SpinBox 30]   Max time (min): [5]     │
│ ☐ Save as flow after success                      │
│                                                   │
│ Provider: [combo (auto)]                          │
│ Model: [QLineEdit, optional]                      │
│ Inputs (JSON): [QLineEdit]                        │
│                                                   │
│             [🦾 Run Agent] [🛑 Stop]              │
├───────────────────────────────────────────────────┤
│ Live trace (scrollable, monospace):               │
│ Step 1 [goto] https://accounts.google.com/signin  │
│   reasoning: "go to Google sign-in page"          │
│   ✓ ok                                            │
│ Step 2 [type] #identifierId ← "alice@x.com"       │
│ Step 3 [click] #identifierNext                    │
│ Step 4 [wait_for] input[type=password] (visible)  │
│ ...                                               │
│ Step 12 [done] "tweet posted successfully"        │
└───────────────────────────────────────────────────┘
```

Wiring:
- `_AgentWorker(QThread)` runs `AgentRunner.run()`.
- `step_emitted(int, AgentAction)` Qt signal pushes lines into trace.
- `🛑 Stop` sets `AgentRunner._stop` event; QThread checks at loop top.
- `ask_user` blocks via a Qt signal that opens a `QInputDialog` on the
  main thread; reply piped back through a queue.

## 7. Stop conditions (consolidated)

| Condition | Default | Status emitted |
|---|---|---|
| `max_steps` exceeded | 30 | `max_steps` |
| `max_time` exceeded | 300 s | `timeout` |
| LLM emits `done(reason)` | — | `done` |
| LLM emits `ask_user`, then user cancels | — | `aborted` |
| User clicks 🛑 Stop | — | `aborted` |
| LLM fails to produce valid JSON in 3 attempts (1 + 2 retries) | — | `parse_error` |

## 8. Decisions and tradeoffs

| Decision | Alternative | Rationale |
|---|---|---|
| DOM-only | screenshot / multimodal | 90% web tasks; cost ~$0.01/step vs $0.10. v1.5 can add `vision: true`. |
| Curated 10 verbs | full 44-step library | smaller prompt, less hallucination, clean auto-record mapping. |
| Single-call ReAct | plan-then-execute / verifier | simplest viable; cost ceiling via max_steps. |
| Provider-agnostic via `ask_llm` | per-provider tool_use / function_call | reuse existing `ai_providers.py`; no per-provider adapter. |
| Reuse `flow_runs` w/ `kind` | new `agent_runs` table | single Runs dashboard surfaces both; less migration. |
| Auto-record default OFF | always-on | user opt-in keeps DB clean; one click to enable when needed. |
| No cost meter | live token counter | `max_steps` is a sufficient ceiling for v1. |

## 9. Testing strategy

Three layers, all pytest:

1. **Unit (`tests/agent/test_action_dispatcher.py`)** — every verb maps to
   the right step handler with right args; bad verb / bad args raises.
2. **Unit (`tests/agent/test_agent_runner.py`)** — runner with stubbed
   `_decide` (no LLM) drives the loop through canned actions; verifies
   stop conditions, history shape, persistence calls.
3. **Smoke (`tests/agent/test_agent_page.py`)** — GUI page constructs,
   widgets exist, Stop button connects.

No live LLM tests (network + cost). Provider integration covered by
existing `ai_providers` tests.

## 10. File layout

```
tegufox_flow/
└── agent.py                            NEW
        AgentAction, AgentResult, AgentRunner

tegufox_gui/pages/
└── agent_page.py                       NEW
        AgentPage, _AgentWorker

tegufox_core/database.py                MODIFY
        FlowRun.kind, FlowRun.goal_text columns
        ensure_schema() extended

tegufox_gui/app.py                      MODIFY
        register sidebar entry "🦾 Agent" at switch_page index 10

tests/agent/
├── __init__.py
├── conftest.py                         qapp fixture
├── test_action_dispatcher.py
├── test_agent_runner.py
└── test_agent_page.py
```

## 11. Decisions remaining for writing-plans

- **Default decide-step model**: `claude-sonnet-4-6` (matches existing
  ai_providers default; reasoning quality matters more than per-step
  cost since `max_steps` already caps the run). The user may set a
  different model per run.
- **`ask_user` reply in auto-record**: becomes a flow input. The
  recorded YAML adds an `inputs:` entry with the AI's `question` text
  as the input description; the original verb that emitted ask_user is
  replaced by a `control.set` step assigning the input to the var the
  next action would have used.
- **History truncation past 10 turns**: drop the oldest turns. v1.5 may
  summarise.

## 12. Roadmap

After this ships, natural follow-ups (each its own sub-project):

- **#7.5 Vision agent** — add screenshot input + click-by-bbox.
- **#7.6 Plan-then-execute** — upfront plan, fewer re-decisions.
- **#7.7 Cost meter** — per-run token + USD tracking.
- **#7.8 Pause + resume** — agent state checkpoints, survive restart.
- **#7.9 Conversational mode** — multi-turn agent chat alongside browsing.
