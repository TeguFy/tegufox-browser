"""Selector picker — opens a real Camoufox session and lets the user click
an element to capture a CSS selector. Returned to the editor's form.

Three ways to produce a selector:
  1. **Pick from page** — open browser, hover/click an element. PICKER_JS
     emits both the computed CSS selector and the element's outerHTML.
  2. **Type / edit** the selector directly in the line edit.
  3. **Paste HTML** — drop an HTML snippet of the target element and
     `html_to_selector()` extracts a selector using the same heuristics as
     PICKER_JS (id → data-testid → data-test → input[name] → aria-label →
     tag.most-specific-class → tag).

Once a selector is in the field, the **Test Click** button instructs the
running browser to actually click the element so the user can verify the
selector works before saving the flow.
"""

from __future__ import annotations
import queue
import re
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QPlainTextEdit, QGroupBox,
)


PICKER_JS = r"""
(() => {
  if (window.__teguPickerActive) return;
  window.__teguPickerActive = true;
  window.__teguPickerEnabled = false;   // armed by main thread; auto-disarms after a capture
  window.__teguPickedSelector = null;
  window.__teguPickedHtml = null;

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
  function clearLast() {
    if (last && last.style) last.style.outline = '';
    last = null;
  }

  document.addEventListener('mouseover', e => {
    if (!window.__teguPickerEnabled) { clearLast(); return; }
    if (last) last.style.outline = '';
    last = e.target;
    if (last && last.style) last.style.outline = '3px solid red';
  }, true);

  document.addEventListener('click', e => {
    if (!window.__teguPickerEnabled) return;   // armed = capture; idle = pass through
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    window.__teguPickedSelector = buildSelector(e.target);
    let html = '';
    try { html = (e.target.outerHTML || '').slice(0, 4000); } catch (_) {}
    window.__teguPickedHtml = html;
    if (last && last.style) last.style.outline = '3px solid limegreen';
    window.__teguPickerEnabled = false;       // auto-disarm — user re-arms via dialog
  }, true);

  // Banner reflects current state. updateBanner() polls the flag every
  // 200 ms which is dirt cheap and avoids a setter trap.
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;color:#fff;'
    + 'font:14px sans-serif;padding:6px 12px;z-index:2147483647;text-align:center;';
  document.documentElement.appendChild(banner);
  function updateBanner() {
    const enabled = window.__teguPickerEnabled;
    banner.textContent = enabled
      ? '🎯 Tegufox picker armed — click any element'
      : '⏸ Tegufox picker idle — interact normally; press “Pick Element” to capture';
    banner.style.background = enabled ? '#b00020' : '#37474f';
    banner.style.borderBottom = enabled ? '3px solid #ff4040' : '2px solid #555';
  }
  updateBanner();
  setInterval(updateBanner, 200);
})();
"""


# ---------------------------------------------------------------------------
# HTML → selector heuristic (mirrors PICKER_JS priority order)
# ---------------------------------------------------------------------------

_OPENING_TAG = re.compile(r"<\s*([a-zA-Z][a-zA-Z0-9-]*)\s*([^>]*)/?>", re.DOTALL)


def _attr(attrs: str, name: str) -> Optional[str]:
    m = re.search(
        rf'\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\')',
        attrs,
    )
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def html_to_selector(html: str) -> Optional[str]:
    """Extract a CSS selector from a single HTML element snippet.

    Returns None if no recognisable opening tag is found.
    Priority follows PICKER_JS:
        #id → [data-testid] → [data-test] → input[name=...] →
        tag[aria-label=...] → tag.most-specific-class → tag
    """
    if not html:
        return None
    m = _OPENING_TAG.search(html)
    if not m:
        return None
    tag = m.group(1).lower()
    attrs = m.group(2) or ""

    if (v := _attr(attrs, "id")):
        return f"#{v}"
    if (v := _attr(attrs, "data-testid")):
        return f'[data-testid="{v}"]'
    if (v := _attr(attrs, "data-test")):
        return f'[data-test="{v}"]'
    if tag == "input" and (v := _attr(attrs, "name")):
        return f'input[name="{v}"]'
    if (v := _attr(attrs, "aria-label")):
        return f'{tag}[aria-label="{v}"]'
    if (v := _attr(attrs, "class")):
        classes = [c for c in v.split() if c]
        if classes:
            best = max(classes, key=len)
            return f"{tag}.{best}"
    return tag


# ---------------------------------------------------------------------------
# Worker thread driving the captive Camoufox session
# ---------------------------------------------------------------------------

class _PickerWorker(QThread):
    status = pyqtSignal(str)
    element_picked = pyqtSignal(str, str)              # (selector, outer_html)
    pages_changed = pyqtSignal(list, int)              # (urls, current_idx)
    crashed = pyqtSignal(str)

    def __init__(self, profile_name: str, url: str, parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.url = url
        self._stop = False
        self._actions: "queue.Queue[tuple]" = queue.Queue()

    def stop(self) -> None:
        self._stop = True

    def request_test_click(self, selector: str) -> None:
        self._actions.put(("test_click", selector))

    def request_arm_picker(self) -> None:
        """Arm the picker for one capture; auto-disarms after the user clicks."""
        self._actions.put(("arm", None))

    def request_set_target(self, idx: int) -> None:
        """Switch which page (main or a popup) the picker watches and acts on."""
        self._actions.put(("set_target", int(idx)))

    def run(self) -> None:
        try:
            from tegufox_automation import TegufoxSession
            self.status.emit(f"Opening profile {self.profile_name!r}…")
            with TegufoxSession(profile=self.profile_name) as session:
                page = session.page
                self.status.emit(f"Navigating to {self.url}…")
                page.goto(self.url)
                page.evaluate(PICKER_JS)
                self.status.emit(
                    "Browser ready. Interact freely; press 'Pick Element' "
                    "in the dialog when you want to capture a selector."
                )

                tracked: List = [page]                  # all pages we've injected JS into
                target_idx = 0
                self._emit_pages(tracked, target_idx)

                while not self._stop:
                    # 1. Reconcile open pages with our tracked list — pick up
                    #    popups (Login-with-Google, OAuth, etc.) and drop closed ones.
                    try:
                        live = list(page.context.pages)
                    except Exception:
                        live = list(tracked)

                    changed = False
                    for p in live:
                        if p not in tracked:
                            tracked.append(p)
                            try:
                                p.evaluate(PICKER_JS)
                            except Exception:
                                pass
                            self.status.emit(
                                f"New popup/tab detected — switch via 'Target page'."
                            )
                            changed = True
                    new_tracked = [p for p in tracked if p in live]
                    if len(new_tracked) != len(tracked):
                        tracked = new_tracked
                        if target_idx >= len(tracked):
                            target_idx = max(0, len(tracked) - 1)
                        changed = True
                    if changed:
                        self._emit_pages(tracked, target_idx)

                    target = tracked[target_idx] if tracked else page

                    # 2. Drain queued commands against the current target.
                    try:
                        while True:
                            cmd, arg = self._actions.get_nowait()
                            if cmd == "test_click":
                                self._do_test_click(target, arg)
                            elif cmd == "arm":
                                self._do_arm(target)
                            elif cmd == "set_target":
                                if 0 <= int(arg) < len(tracked):
                                    target_idx = int(arg)
                                    self.status.emit(
                                        f"Target switched to page {target_idx + 1}: "
                                        f"{tracked[target_idx].url}"
                                    )
                                    self._emit_pages(tracked, target_idx)
                    except queue.Empty:
                        pass

                    # 3. Poll target for a captured selector.
                    target = tracked[target_idx] if tracked else page
                    try:
                        sel = target.evaluate("() => window.__teguPickedSelector")
                        html = target.evaluate("() => window.__teguPickedHtml")
                    except Exception:
                        if self._stop:
                            return
                        sel, html = None, None
                    if sel:
                        self.element_picked.emit(str(sel), str(html or ""))
                        try:
                            target.evaluate(
                                "() => { window.__teguPickedSelector = null;"
                                " window.__teguPickedHtml = null; }"
                            )
                        except Exception:
                            pass
                    self.msleep(300)
        except Exception as e:
            self.crashed.emit(f"{type(e).__name__}: {e}")

    def _emit_pages(self, tracked, target_idx: int) -> None:
        urls: List[str] = []
        for i, p in enumerate(tracked):
            try:
                u = p.url
            except Exception:
                u = "(closed)"
            urls.append(u or "(loading)")
        self.pages_changed.emit(urls, target_idx)

    def _do_arm(self, page) -> None:
        try:
            # Re-inject in case earlier navigation wiped it.
            page.evaluate(PICKER_JS)
            page.evaluate("() => { window.__teguPickerEnabled = true; }")
            self.status.emit("Picker armed — click any element in the browser.")
        except Exception as e:
            self.status.emit(f"Failed to arm picker: {type(e).__name__}: {e}")

    def _do_test_click(self, page, selector: str) -> None:
        if not selector or not selector.strip():
            self.status.emit("Test click skipped: selector is empty.")
            return
        self.status.emit(f"Testing click on {selector!r}…")
        try:
            locator = page.locator(selector)
            count = locator.count()
            if count == 0:
                self.status.emit(f"✗ No element matched {selector!r}.")
                return
            if count > 1:
                self.status.emit(f"⚠ {count} elements match {selector!r}; clicking the first.")
            locator.first.click(timeout=5000)
            self.status.emit(f"✓ Clicked {selector!r}. Re-injecting picker for next pick.")
        except Exception as e:
            self.status.emit(f"✗ Click failed: {type(e).__name__}: {e}")
        finally:
            try:
                page.evaluate(PICKER_JS)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

_MONO = QFont()
_MONO.setStyleHint(QFont.StyleHint.Monospace)
_MONO.setFamily("Menlo")


class SelectorPickerDialog(QDialog):
    def __init__(self, profile_names: List[str], default_url: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick selector")
        self.resize(720, 600)
        self._worker: Optional[_PickerWorker] = None
        self._selected_selector = ""

        layout = QVBoxLayout(self)

        # ---- URL + Profile + Open Browser + Pick Element -----------------
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(default_url)
        self.url_edit.setPlaceholderText("https://example.com/path")
        url_row.addWidget(self.url_edit, 1)
        self.open_btn = QPushButton("Open Browser")
        self.open_btn.clicked.connect(self._on_open)
        url_row.addWidget(self.open_btn)
        self.pick_btn = QPushButton("Pick Element")
        self.pick_btn.setToolTip(
            "Arm the picker for one click. Use this after you've interacted "
            "with the page enough that the target element is visible."
        )
        self.pick_btn.setEnabled(False)
        self.pick_btn.clicked.connect(self._on_pick)
        url_row.addWidget(self.pick_btn)
        layout.addLayout(url_row)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        for p in profile_names:
            self.profile_combo.addItem(p)
        profile_row.addWidget(self.profile_combo, 1)
        layout.addLayout(profile_row)

        # ---- Target page (main + popups) --------------------------------
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target page:"))
        self.target_combo = QComboBox()
        self.target_combo.setToolTip(
            "When the site opens a popup (e.g. 'Login with Google'), it "
            "appears here. Select it to pick selectors inside the popup."
        )
        self.target_combo.setMinimumWidth(360)
        self.target_combo.currentIndexChanged.connect(self._on_target_change)
        target_row.addWidget(self.target_combo, 1)
        layout.addLayout(target_row)

        # ---- Selector edit + Test Click ----------------------------------
        sel_group = QGroupBox("Selected selector (editable)")
        sg = QVBoxLayout(sel_group)
        sel_row = QHBoxLayout()
        self.selected_edit = QLineEdit()
        self.selected_edit.setPlaceholderText("Pick / type / detect a CSS selector")
        sel_row.addWidget(self.selected_edit, 1)
        self.test_btn = QPushButton("Test Click")
        self.test_btn.setToolTip("Click the element matching this selector in the running browser")
        self.test_btn.setEnabled(False)
        self.test_btn.clicked.connect(self._on_test_click)
        sel_row.addWidget(self.test_btn)
        sg.addLayout(sel_row)
        self.selected_edit.textChanged.connect(self._on_selector_text_changed)
        layout.addWidget(sel_group)

        # ---- Picked element HTML (debug) ---------------------------------
        html_group = QGroupBox("Picked element HTML (debug)")
        hg = QVBoxLayout(html_group)
        self.picked_html_view = QPlainTextEdit()
        self.picked_html_view.setReadOnly(True)
        self.picked_html_view.setFont(_MONO)
        self.picked_html_view.setPlaceholderText("Click an element in the browser; its outerHTML will appear here.")
        self.picked_html_view.setMaximumHeight(110)
        hg.addWidget(self.picked_html_view)
        layout.addWidget(html_group)

        # ---- Paste HTML to detect ---------------------------------------
        paste_group = QGroupBox("Or paste HTML to detect selector")
        pg = QVBoxLayout(paste_group)
        self.paste_html_edit = QPlainTextEdit()
        self.paste_html_edit.setFont(_MONO)
        self.paste_html_edit.setPlaceholderText(
            '<button id="submit" class="btn primary">Sign in</button>'
        )
        self.paste_html_edit.setMaximumHeight(110)
        pg.addWidget(self.paste_html_edit)
        detect_row = QHBoxLayout()
        detect_row.addStretch(1)
        self.detect_btn = QPushButton("Detect Selector")
        self.detect_btn.clicked.connect(self._on_detect)
        detect_row.addWidget(self.detect_btn)
        pg.addLayout(detect_row)
        layout.addWidget(paste_group)

        # ---- Status ------------------------------------------------------
        self.status_label = QLabel("Click 'Open Browser' to start picking, or paste HTML below.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # ---- Use / Cancel ------------------------------------------------
        btn_row = QHBoxLayout()
        self.use_btn = QPushButton("Use Selected")
        self.cancel_btn = QPushButton("Cancel")
        self.use_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.use_btn.setEnabled(False)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.use_btn)
        layout.addLayout(btn_row)

    # ----------------------------------------------------------------------
    def selected_selector(self) -> str:
        # Trust what's in the line edit — user may have typed/pasted/detected.
        return self.selected_edit.text().strip() or self._selected_selector

    def _on_selector_text_changed(self, txt: str) -> None:
        has = bool(txt.strip())
        self.use_btn.setEnabled(has)
        self.test_btn.setEnabled(
            has and self._worker is not None and self._worker.isRunning()
        )

    def _on_test_click(self) -> None:
        if self._worker is None or not self._worker.isRunning():
            self.status_label.setText("Open Browser first to use Test Click.")
            return
        sel = self.selected_edit.text().strip()
        if not sel:
            return
        self._worker.request_test_click(sel)

    def _on_detect(self) -> None:
        html = self.paste_html_edit.toPlainText().strip()
        if not html:
            self.status_label.setText("Paste an HTML element first.")
            return
        sel = html_to_selector(html)
        if not sel:
            self.status_label.setText("Could not detect a selector — couldn't find an opening tag.")
            return
        self.selected_edit.setText(sel)
        self.status_label.setText(f"Detected: {sel}")

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
        self.pick_btn.setEnabled(True)
        self._worker = _PickerWorker(profile, url, parent=self)
        self._worker.status.connect(self.status_label.setText)
        self._worker.element_picked.connect(self._on_element_picked)
        self._worker.pages_changed.connect(self._on_pages_changed)
        self._worker.crashed.connect(self._on_crashed)
        self._worker.start()

    def _on_pick(self) -> None:
        if self._worker is None or not self._worker.isRunning():
            self.status_label.setText("Open Browser first.")
            return
        self._worker.request_arm_picker()

    def _on_pages_changed(self, urls: list, current_idx: int) -> None:
        # Block signals while rebuilding so we don't echo back to the worker.
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for i, u in enumerate(urls):
            label = u if len(u) <= 80 else u[:77] + "…"
            self.target_combo.addItem(f"{i + 1}. {label}")
        if 0 <= current_idx < self.target_combo.count():
            self.target_combo.setCurrentIndex(current_idx)
        self.target_combo.blockSignals(False)

    def _on_target_change(self, idx: int) -> None:
        if idx < 0 or self._worker is None:
            return
        self._worker.request_set_target(idx)

    def _on_element_picked(self, sel: str, html: str) -> None:
        self._selected_selector = sel
        self.selected_edit.setText(sel)
        self.picked_html_view.setPlainText(html)
        self.status_label.setText("Picked! Try 'Test Click', or pick another element.")
        self.use_btn.setEnabled(True)
        self.test_btn.setEnabled(True)

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
