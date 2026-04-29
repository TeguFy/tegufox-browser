"""AI Flow Generator — describe a flow in plain language, get YAML.

User types a goal ("login Google with random email then post tweet on
x.com"), picks a provider, and clicks Generate. The page sends a prompt
including the full step-type catalogue and an example flow, then shows
the AI's YAML output for review. User can save (validates via parse_flow
and writes to flow DB) or copy.

This is sub-project #5 from the original decomposition.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QLineEdit, QComboBox, QSplitter, QMessageBox, QGroupBox, QFormLayout,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tegufox_core.database import Base, ensure_schema, FlowRecord


_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


# Step catalogue compiled into the prompt so AI knows the DSL.
_STEP_CATALOG = """\
BROWSER:
  browser.goto(url, wait_until=load|domcontentloaded|networkidle, timeout_ms)
  browser.click(selector, human=true|false, force=true|false, button, click_count)
  browser.type(selector, text, clear_first=bool, human, delay_ms)
  browser.hover(selector)
  browser.scroll(direction=up|down, pixels, to=top|bottom|<sel>)
  browser.wait_for(selector, state=visible|attached|hidden, timeout_ms)
  browser.select_option(selector, value)
  browser.screenshot(path, full_page=bool, selector?)
  browser.press_key(key, selector?)
  browser.click_text(text, role=button|link|"", exact=bool, force, timeout_ms)
  browser.fill_form_by_labels(fields={Label:Value,...}, use_ai=bool, human=bool)
  browser.click_and_wait_popup(selector, timeout_ms, force)
  browser.wait_for_popup(url_contains, timeout_ms)
  browser.wait_for_url(url_contains, timeout_ms)
  browser.switch_to_main()
  browser.disable_popups()
  browser.save_cookies(path, domain_contains?)
  browser.load_cookies(path)

EXTRACT:
  extract.read_text(selector, set)
  extract.read_attr(selector, attr, set)
  extract.eval_js(script, set)
  extract.url(set)
  extract.title(set)

CONTROL:
  control.set(var, value)
  control.sleep(ms)
  control.if(when, then=[...], else=[...])
  control.for_each(items, var, body=[...], index_var?)
  control.while(when, body=[...], max_iterations)
  control.break() / control.continue() / control.goto(step_id)

I/O:
  io.log(message, level=debug|info|warning|error)
  io.write_file(path, content, append=bool)
  io.read_file(path, set, format=text|json|csv)
  io.http_request(method, url, headers?, body?, set, timeout_ms)
  io.record(path, format=csv|jsonl, data={col:val,...})

STATE:
  state.save(key, value)
  state.load(key, set, default?)
  state.delete(key)

AI (optional, only when stable selectors are not feasible):
  ai.click(description, force, timeout_ms, provider, model)
  ai.fix_selector(selector, description, set, provider, model)
  ai.extract(description, set, max_tokens, provider, model)
  ai.ask(question, set, include_dom=bool, max_tokens, provider, model)
  ai.verify(expected, set?, on_fail=abort|warn, provider, model)

JINJA HELPERS available in any string field via {{ ... }}:
  inputs.<name>     vars.<name>     state.<name>     env.<NAME>
  now()  today()  uuid()  random_int(a,b)
  random_email(domain?, locale?)   random_phone(country)
  random_name(locale)   random_first_name / random_last_name
  random_username(locale)   random_password(length)
  random_string(length, charset)   random_choice(items)
  random_address(locale)
  filters: |slug |tojson |b64encode |b64decode

Each step needs unique `id` (slug). on_error: {action: abort|retry|skip|goto, ...}.
"""


_EXAMPLE_FLOW = """\
schema_version: 1
name: example_signup
description: |
  Generate random identity, navigate to signup form, fill it,
  save cookies, log row to CSV.
inputs:
  domain: { type: string, default: "hejito.com" }
defaults:
  on_error: { action: abort }
steps:
  - id: gen_email
    type: control.set
    var: email
    value: "random_email(inputs.domain)"
  - id: gen_password
    type: control.set
    var: password
    value: "random_password(14)"
  - id: open_site
    type: browser.goto
    url: "https://example.com/signup"
    wait_until: load
  - id: fill
    type: browser.fill_form_by_labels
    fields:
      Email: "{{ vars.email }}"
      Password: "{{ vars.password }}"
  - id: submit
    type: browser.click_text
    text: "Sign up"
    role: button
    force: true
  - id: record
    type: io.record
    path: "data/registrations.csv"
    format: csv
    data:
      timestamp: "{{ now() }}"
      email: "{{ vars.email }}"
"""


class _GenerateWorker(QThread):
    finished_with = pyqtSignal(str, str)   # (yaml or "", error_or_"")

    def __init__(self, goal: str, provider: Optional[str], model: Optional[str]):
        super().__init__()
        self.goal = goal
        self.provider = provider or None
        self.model = model or None

    def run(self) -> None:
        try:
            from tegufox_flow.steps.ai_providers import ask_llm
            system = (
                "You generate Tegufox flow YAML. Output VALID YAML only — no "
                "markdown fences, no commentary. Use only the step types and "
                "fields listed in the catalogue. Each step needs a unique id "
                "(snake_case slug). Use Jinja {{ ... }} for variable refs.\n\n"
                "STEP CATALOG:\n" + _STEP_CATALOG +
                "\nEXAMPLE FLOW (for shape reference):\n" + _EXAMPLE_FLOW
            )
            user = (
                "Write a Tegufox flow that achieves the following goal. "
                "Pick `inputs:` for any user-supplied secrets, generate "
                "everything else with random_* helpers when reasonable.\n\n"
                f"GOAL: {self.goal}"
            )
            yaml_text = ask_llm(
                system=system, user=user, max_tokens=4000,
                provider=self.provider, model=self.model,
            )
            # Strip code fences if AI included them despite instruction.
            yaml_text = yaml_text.strip()
            if yaml_text.startswith("```"):
                lines = yaml_text.splitlines()
                # remove first ``` and last ```
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                yaml_text = "\n".join(lines).strip()
            self.finished_with.emit(yaml_text, "")
        except Exception as e:
            self.finished_with.emit("", f"{type(e).__name__}: {e}")


class FlowGeneratorPage(QWidget):
    def __init__(self, db_path: str = "data/tegufox.db", parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._workers: list[_GenerateWorker] = []

        layout = QVBoxLayout(self)

        # ---- Goal + provider --------------------------------------------
        top = QGroupBox("Describe what the flow should do")
        tg = QVBoxLayout(top)
        self.goal_edit = QPlainTextEdit()
        self.goal_edit.setPlaceholderText(
            "e.g. Log into Google with random email + password, then post a "
            "random tweet on x.com about today's weather. Save cookies and "
            "log the email to data/registrations.csv."
        )
        self.goal_edit.setMaximumHeight(120)
        tg.addWidget(self.goal_edit)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("(auto)", "")
        try:
            from tegufox_flow.steps.ai_providers import list_configured_providers
            for p in list_configured_providers():
                self.provider_combo.addItem(p, p)
        except Exception:
            pass
        opts.addWidget(self.provider_combo)
        opts.addWidget(QLabel("Model:"))
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("(default for provider)")
        opts.addWidget(self.model_edit, 1)
        self.generate_btn = QPushButton("🤖 Generate")
        self.generate_btn.clicked.connect(self._on_generate)
        opts.addWidget(self.generate_btn)
        tg.addLayout(opts)
        layout.addWidget(top)

        # ---- Output YAML -----------------------------------------------
        bottom = QGroupBox("Generated YAML — review, edit, save")
        bg = QVBoxLayout(bottom)
        self.yaml_view = QPlainTextEdit()
        self.yaml_view.setFont(_MONO)
        self.yaml_view.setPlaceholderText("AI output appears here.")
        bg.addWidget(self.yaml_view)

        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("Save as flow name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("my_generated_flow")
        save_row.addWidget(self.name_edit, 1)
        self.validate_btn = QPushButton("Validate")
        self.save_btn = QPushButton("Save to DB")
        self.copy_btn = QPushButton("Copy YAML")
        self.validate_btn.clicked.connect(self._on_validate)
        self.save_btn.clicked.connect(self._on_save)
        self.copy_btn.clicked.connect(self._on_copy)
        save_row.addWidget(self.validate_btn)
        save_row.addWidget(self.save_btn)
        save_row.addWidget(self.copy_btn)
        bg.addLayout(save_row)
        layout.addWidget(bottom, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------
    def _on_generate(self) -> None:
        goal = self.goal_edit.toPlainText().strip()
        if not goal:
            self.status_label.setText("Type a goal first.")
            return
        provider_text = self.provider_combo.currentText()
        provider = "" if provider_text == "(auto)" else provider_text
        model = self.model_edit.text().strip()
        self.generate_btn.setEnabled(False)
        self.status_label.setText("Generating… (may take 5-30s)")

        worker = _GenerateWorker(goal, provider, model)
        worker.finished_with.connect(self._on_generate_done)
        self._workers.append(worker)
        worker.start()

    def _on_generate_done(self, yaml_text: str, error: str) -> None:
        self.generate_btn.setEnabled(True)
        if error:
            self.status_label.setText(f"Error: {error}")
            return
        self.yaml_view.setPlainText(yaml_text)
        self.status_label.setText(
            "Generated. Validate before save to catch schema issues."
        )

    def _on_validate(self) -> None:
        text = self.yaml_view.toPlainText().strip()
        if not text:
            self.status_label.setText("Nothing to validate.")
            return
        try:
            import yaml as _yaml
            from tegufox_flow.dsl import parse_flow
            data = _yaml.safe_load(text)
            flow = parse_flow(data)
            if not self.name_edit.text().strip():
                self.name_edit.setText(flow.name)
            self.status_label.setText(f"Valid. Flow name: {flow.name}, steps: {len(flow.steps)}")
        except Exception as e:
            self.status_label.setText(f"Invalid: {type(e).__name__}: {e}")

    def _on_save(self) -> None:
        text = self.yaml_view.toPlainText().strip()
        if not text:
            return
        try:
            import yaml as _yaml
            from tegufox_flow.dsl import parse_flow
            data = _yaml.safe_load(text)
            flow = parse_flow(data)
        except Exception as e:
            QMessageBox.critical(self, "Invalid flow", f"{type(e).__name__}: {e}")
            return
        name = self.name_edit.text().strip() or flow.name

        eng = create_engine(f"sqlite:///{Path(self._db_path).resolve()}")
        Base.metadata.create_all(eng)
        ensure_schema(eng)
        S = sessionmaker(bind=eng)
        with S() as s:
            now = datetime.utcnow()
            rec = s.query(FlowRecord).filter_by(name=name).first()
            if rec is None:
                rec = FlowRecord(name=name, yaml_text=text, schema_version=1,
                                 created_at=now, updated_at=now)
                s.add(rec)
            else:
                rec.yaml_text = text
                rec.updated_at = now
            s.commit()
        self.status_label.setText(f"Saved as flow {name!r}.")

    def _on_copy(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.yaml_view.toPlainText())
        self.status_label.setText("YAML copied to clipboard.")
