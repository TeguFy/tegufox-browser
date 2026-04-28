"""Form schema for every step type in tegufox_flow.

This is a pure-data declaration — no Qt imports — so it can be unit-tested
without a display server. step_form_panel.py consumes it to build widgets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List


_VALID_KINDS = {"string", "int", "bool", "select", "code", "steps"}


@dataclass
class Field:
    name: str
    kind: str
    label: str = ""
    required: bool = False
    default: Any = None
    placeholder: str = ""
    choices: List[str] = field(default_factory=list)
    multiline: bool = False
    help: str = ""

    def __post_init__(self):
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"unknown field kind {self.kind!r}")
        if not self.label:
            self.label = self.name.replace("_", " ").title()


def fields_for(step_type: str) -> List[Field]:
    return STEP_FORM.get(step_type, [])


_WAIT_UNTIL = ["load", "domcontentloaded", "networkidle", "commit"]
_WAIT_STATE = ["visible", "attached", "hidden", "detached"]


STEP_FORM: dict = {
    # ---- Browser steps ----
    "browser.goto": [
        Field("url", "string", required=True, placeholder="https://example.com"),
        Field("wait_until", "select", choices=_WAIT_UNTIL, default="load"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.click": [
        Field("selector", "string", required=True, placeholder="#submit"),
        Field("human", "bool", default=True),
        Field("button", "select", choices=["left", "right", "middle"], default="left"),
        Field("click_count", "int", default=1),
        Field("force", "bool", default=False,
              help="Bypass actionability checks (use when overlays intercept clicks)"),
    ],
    "browser.type": [
        Field("selector", "string", required=True, placeholder="#q"),
        Field("text", "string", required=True, placeholder="hello world"),
        Field("clear_first", "bool", default=False),
        Field("human", "bool", default=True),
        Field("delay_ms", "int", default=0),
    ],
    "browser.hover": [
        Field("selector", "string", required=True),
        Field("human", "bool", default=True),
    ],
    "browser.scroll": [
        Field("direction", "select", choices=["down", "up"], default="down"),
        Field("pixels", "int", default=500),
        Field("to", "string", placeholder="top | bottom | <selector>"),
    ],
    "browser.wait_for": [
        Field("selector", "string", required=True),
        Field("state", "select", choices=_WAIT_STATE, default="visible"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.select_option": [
        Field("selector", "string", required=True),
        Field("value", "string", required=True),
    ],
    "browser.screenshot": [
        Field("path", "string", required=True, placeholder="screenshots/x.png"),
        Field("full_page", "bool", default=False),
        Field("selector", "string", placeholder="(optional) for element shot"),
    ],
    "browser.press_key": [
        Field("key", "string", required=True, placeholder="Enter"),
        Field("selector", "string", placeholder="(optional) focus this first"),
    ],
    "browser.disable_popups": [],
    "browser.click_text": [
        Field("text", "string", required=True,
              placeholder='e.g. "Đăng nhập bằng Google"',
              help="Visible text or aria-label to match"),
        Field("role", "select", choices=["", "button", "link"], default="",
              help="Restrict to button/link/any (empty = any clickable)"),
        Field("exact", "bool", default=False,
              help="Require exact match (default = substring contains)"),
        Field("timeout_ms", "int", default=15000),
        Field("force", "bool", default=True),
    ],
    "browser.save_cookies": [
        Field("path", "string", required=True,
              placeholder="data/cookies/{{ profile_name }}.json"),
        Field("domain_contains", "string",
              placeholder="(optional) e.g. google.com"),
    ],
    "browser.load_cookies": [
        Field("path", "string", required=True,
              placeholder="data/cookies/{{ profile_name }}.json"),
    ],
    "browser.click_and_wait_popup": [
        Field("selector", "string", required=True,
              placeholder="selector that triggers window.open"),
        Field("timeout_ms", "int", default=30000),
        Field("force", "bool", default=False,
              help="Bypass actionability checks for the click"),
    ],
    "browser.wait_for_popup": [
        Field("url_contains", "string",
              placeholder="(optional) e.g. accounts.google",
              help="Substring that must appear in the popup's URL"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.wait_for_url": [
        Field("url_contains", "string",
              placeholder="(optional) e.g. accounts.google",
              help="Substring; matches popup OR same-tab redirect"),
        Field("timeout_ms", "int", default=30000),
    ],
    "browser.switch_to_main": [],

    # ---- Extract steps ----
    "extract.read_text": [
        Field("selector", "string", required=True),
        Field("set", "string", required=True, placeholder="my_var"),
    ],
    "extract.read_attr": [
        Field("selector", "string", required=True),
        Field("attr", "string", required=True, placeholder="href"),
        Field("set", "string", required=True),
    ],
    "extract.eval_js": [
        Field("script", "code", required=True,
              placeholder="() => document.title", multiline=True),
        Field("set", "string", required=True),
    ],
    "extract.url": [
        Field("set", "string", required=True),
    ],
    "extract.title": [
        Field("set", "string", required=True),
    ],

    # ---- Control steps ----
    "control.set": [
        Field("var", "string", required=True),
        Field("value", "code", required=True, placeholder="vars.x + 1"),
    ],
    "control.sleep": [
        Field("ms", "int", required=True, default=1000),
    ],
    "control.if": [
        Field("when", "string", required=True, placeholder="{{ vars.x > 0 }}"),
        Field("then", "steps", required=True, label="Then body"),
        Field("else", "steps", label="Else body"),
    ],
    "control.for_each": [
        Field("items", "code", required=True, placeholder="vars.list"),
        Field("var", "string", required=True, placeholder="item"),
        Field("body", "steps", required=True),
        Field("index_var", "string"),
    ],
    "control.while": [
        Field("when", "code", required=True, placeholder="vars.i < 10"),
        Field("body", "steps", required=True),
        Field("max_iterations", "int", default=1000),
    ],
    "control.break": [],
    "control.continue": [],
    "control.goto": [
        Field("step_id", "string", required=True),
    ],

    # ---- I/O steps ----
    "io.log": [
        Field("message", "string", required=True, multiline=True),
        Field("level", "select",
              choices=["debug", "info", "warning", "error"], default="info"),
    ],
    "io.write_file": [
        Field("path", "string", required=True),
        Field("content", "code", required=True, multiline=True),
        Field("append", "bool", default=False),
        Field("encoding", "string", default="utf-8"),
    ],
    "io.read_file": [
        Field("path", "string", required=True),
        Field("set", "string", required=True),
        Field("format", "select", choices=["text", "json", "csv"], default="text"),
        Field("encoding", "string", default="utf-8"),
    ],
    "io.record": [
        Field("path", "string", required=True,
              placeholder="data/registrations.csv"),
        Field("format", "select", choices=["csv", "jsonl"], default="csv"),
        Field("data", "code", required=True, multiline=True,
              placeholder='{"email": "{{ vars.email }}", "phone": "{{ vars.phone }}"}',
              help="YAML/JSON map of column → value (values are Jinja-rendered)"),
    ],
    "io.http_request": [
        Field("method", "select", required=True,
              choices=["GET", "POST", "PUT", "DELETE", "PATCH"], default="GET"),
        Field("url", "string", required=True),
        Field("body", "code", multiline=True),
        Field("set", "string"),
        Field("timeout_ms", "int", default=30000),
    ],

    # ---- AI Copilot steps ----
    "ai.click": [
        Field("description", "string", required=True,
              placeholder='e.g. "the Sign in with Google button"'),
        Field("force", "bool", default=True),
        Field("timeout_ms", "int", default=15000),
        Field("provider", "select",
              choices=["", "anthropic", "openai", "gemini"], default="",
              help="Empty = auto-detect from env"),
        Field("model", "string", placeholder="(optional) override default model"),
    ],
    "ai.fix_selector": [
        Field("selector", "string", required=True,
              placeholder="The current (possibly broken) selector"),
        Field("description", "string", required=True,
              placeholder='e.g. "Sign in button on x.com login modal"'),
        Field("set", "string", required=True,
              placeholder="var name to store the validated/repaired selector"),
        Field("provider", "select",
              choices=["", "anthropic", "openai", "gemini"], default=""),
        Field("model", "string"),
    ],
    "ai.extract": [
        Field("description", "string", required=True,
              placeholder='e.g. "the order total on the receipt"'),
        Field("set", "string", required=True),
        Field("max_tokens", "int", default=256),
        Field("provider", "select",
              choices=["", "anthropic", "openai", "gemini"], default=""),
        Field("model", "string"),
    ],
    "ai.ask": [
        Field("question", "string", required=True, multiline=True),
        Field("set", "string", required=True),
        Field("include_dom", "bool", default=True),
        Field("max_tokens", "int", default=512),
        Field("provider", "select",
              choices=["", "anthropic", "openai", "gemini"], default=""),
        Field("model", "string"),
    ],

    # ---- State steps ----
    "state.save": [
        Field("key", "string", required=True),
        Field("value", "code", required=True),
    ],
    "state.load": [
        Field("key", "string", required=True),
        Field("set", "string", required=True),
        Field("default", "string"),
    ],
    "state.delete": [
        Field("key", "string", required=True),
    ],
}
