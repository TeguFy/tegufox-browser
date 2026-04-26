"""Selector picker — opens a real Camoufox session and lets the user click
an element to capture a CSS selector. Returned to the editor's form.

Workflow:
    1. User opens dialog from a "Pick…" button next to a selector field.
    2. Enters URL, picks profile, clicks "Open Browser".
    3. Camoufox launches in a worker QThread; PICKER_JS is injected.
    4. User hovers (red highlight) and clicks (green confirm) elements.
    5. Each click writes window.__teguPickedSelector; main thread polls.
    6. User clicks "Use Selected" → dialog closes; selector returned.

The browser stays open until the user closes the dialog, so multiple
selectors can be picked against the same page.
"""

from __future__ import annotations
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton,
)


PICKER_JS = r"""
(() => {
  if (window.__teguPickerActive) return;
  window.__teguPickerActive = true;
  window.__teguPickedSelector = null;

  function escId(id) {
    if (window.CSS && window.CSS.escape) return CSS.escape(id);
    return id.replace(/[^a-zA-Z0-9_-]/g, c => '\\' + c);
  }

  function buildSelector(el) {
    if (!el || el === document.body || el === document.documentElement) return 'body';
    if (el.id) return '#' + escId(el.id);
    if (el.dataset && el.dataset.testid) return '[data-testid="' + el.dataset.testid + '"]';
    if (el.dataset && el.dataset.test)   return '[data-test="' + el.dataset.test + '"]';
    if (el.tagName === 'INPUT' && el.name) return 'input[name="' + el.name + '"]';
    if (el.getAttribute && el.getAttribute('aria-label')) {
      return el.tagName.toLowerCase() + '[aria-label="' + el.getAttribute('aria-label') + '"]';
    }
    const parts = [];
    let cur = el;
    while (cur && cur.parentNode && cur !== document.body && parts.length < 6) {
      const tag = cur.tagName.toLowerCase();
      const sibs = Array.from(cur.parentNode.children).filter(c => c.tagName === cur.tagName);
      const idx = sibs.indexOf(cur) + 1;
      parts.unshift(tag + (sibs.length > 1 ? ':nth-of-type(' + idx + ')' : ''));
      cur = cur.parentNode;
    }
    return parts.join(' > ');
  }

  let last = null;
  document.addEventListener('mouseover', e => {
    if (last) last.style.outline = '';
    last = e.target;
    if (last && last.style) last.style.outline = '3px solid red';
  }, true);

  document.addEventListener('click', e => {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    window.__teguPickedSelector = buildSelector(e.target);
    if (last && last.style) last.style.outline = '3px solid limegreen';
  }, true);

  // Visible banner so users know picker mode is active.
  const banner = document.createElement('div');
  banner.textContent = 'Tegufox picker — click any element';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#222;color:#fff;'
    + 'font:14px sans-serif;padding:6px 12px;z-index:2147483647;text-align:center;'
    + 'border-bottom:2px solid red;';
  document.documentElement.appendChild(banner);
})();
"""


class _PickerWorker(QThread):
    status = pyqtSignal(str)
    selector_picked = pyqtSignal(str)
    crashed = pyqtSignal(str)

    def __init__(self, profile_name: str, url: str, parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.url = url
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            from tegufox_automation import TegufoxSession
            self.status.emit(f"Opening profile {self.profile_name!r}…")
            with TegufoxSession(profile=self.profile_name) as session:
                page = session.page
                self.status.emit(f"Navigating to {self.url}…")
                page.goto(self.url)
                page.evaluate(PICKER_JS)
                self.status.emit("Click any element in the browser to capture its selector.")
                while not self._stop:
                    try:
                        sel = page.evaluate("() => window.__teguPickedSelector")
                    except Exception:
                        if self._stop:
                            return
                        sel = None
                    if sel:
                        self.selector_picked.emit(str(sel))
                        try:
                            page.evaluate("() => { window.__teguPickedSelector = null; }")
                        except Exception:
                            pass
                    self.msleep(300)
        except Exception as e:
            self.crashed.emit(f"{type(e).__name__}: {e}")


class SelectorPickerDialog(QDialog):
    def __init__(self, profile_names: List[str], default_url: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick selector")
        self.resize(560, 220)
        self._worker: Optional[_PickerWorker] = None
        self._selected_selector = ""

        layout = QVBoxLayout(self)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(default_url)
        self.url_edit.setPlaceholderText("https://example.com/path")
        url_row.addWidget(self.url_edit, 1)
        layout.addLayout(url_row)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        for p in profile_names:
            self.profile_combo.addItem(p)
        profile_row.addWidget(self.profile_combo, 1)
        layout.addLayout(profile_row)

        layout.addWidget(QLabel("Selected selector:"))
        self.selected_edit = QLineEdit()
        self.selected_edit.setReadOnly(True)
        layout.addWidget(self.selected_edit)

        self.status_label = QLabel("Click 'Open Browser' to start picking.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("Open Browser")
        self.use_btn = QPushButton("Use Selected")
        self.cancel_btn = QPushButton("Cancel")
        self.open_btn.clicked.connect(self._on_open)
        self.use_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.use_btn.setEnabled(False)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.use_btn)
        layout.addLayout(btn_row)

    def selected_selector(self) -> str:
        return self._selected_selector

    def _on_open(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("URL is required.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_edit.setText(url)
        profile = self.profile_combo.currentText().strip()
        if not profile:
            self.status_label.setText("Pick a profile.")
            return

        self.open_btn.setEnabled(False)
        self._worker = _PickerWorker(profile, url, parent=self)
        self._worker.status.connect(self.status_label.setText)
        self._worker.selector_picked.connect(self._on_selector_picked)
        self._worker.crashed.connect(self._on_crashed)
        self._worker.start()

    def _on_selector_picked(self, sel: str) -> None:
        self._selected_selector = sel
        self.selected_edit.setText(sel)
        self.status_label.setText("Picked! Click another element to refine, or 'Use Selected'.")
        self.use_btn.setEnabled(True)

    def _on_crashed(self, msg: str) -> None:
        self.status_label.setText(f"Error: {msg}")
        self.open_btn.setEnabled(True)

    def _stop_worker(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)

    def _on_cancel(self) -> None:
        self._stop_worker()
        self.reject()

    def accept(self) -> None:
        self._stop_worker()
        super().accept()

    def reject(self) -> None:
        self._stop_worker()
        super().reject()
