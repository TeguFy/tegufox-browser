# Proxies Page Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Eliminate UI lag on the Proxies page when ~500 proxies are loaded by rendering at most one page worth of `ProxyCard` widgets at a time, with a configurable page size (50/100/200/All) persisted in `QSettings` and a numbered pagination bar.

**Architecture:** Cards are still all created up-front in `load_proxies()` (kept in `_all_cards` so search/sort stay in-memory and instant), but only the cards for the current page are attached to the layout. Switching pages reparents cards instead of constructing new ones. A pure `compute_page_window` helper drives the page-bar layout and is unit-testable.

**Tech Stack:** Python 3.14, PyQt6, `QSettings("Tegufox", "GUI")`, `pytest`. Modifies `tegufox_gui/pages/proxies_page.py`. Adds `tegufox_gui/utils/pagination.py` and `tests/test_pagination.py`.

**Spec reference:** `docs/superpowers/specs/2026-04-29-proxies-pagination-design.md`. Section numbers below refer to that spec.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `tegufox_gui/utils/pagination.py` | Create | Pure helper `compute_page_window(current, total) -> list[int \| None]` driving the numbered page bar (spec §6.2). |
| `tests/test_pagination.py` | Create | Unit tests for `compute_page_window` covering all cases in spec §6.2 + edge cases. |
| `tegufox_gui/pages/proxies_page.py` | Modify | Add pagination state, page-size dropdown, footer with page bar + status label, refactor `_apply_filter`, add `_render_current_page` and `_rebuild_page_bar`, wire reset-page hooks, hook bulk_import to force sort=Newest + page=1. |

---

## Task 1: Pagination window helper (TDD)

**Files:**
- Create: `tegufox_gui/utils/pagination.py`
- Test: `tests/test_pagination.py`

- [ ] **Step 1: Write the failing tests**

Write `tests/test_pagination.py`:

```python
"""Tests for tegufox_gui.utils.pagination."""

import pytest

from tegufox_gui.utils.pagination import compute_page_window


class TestComputePageWindow:
    """Spec §6.2 — page-bar windowing logic."""

    def test_single_page(self):
        assert compute_page_window(1, 1) == [1]

    def test_total_le_7_shows_all(self):
        assert compute_page_window(1, 5) == [1, 2, 3, 4, 5]
        assert compute_page_window(3, 5) == [1, 2, 3, 4, 5]
        assert compute_page_window(1, 7) == [1, 2, 3, 4, 5, 6, 7]
        assert compute_page_window(7, 7) == [1, 2, 3, 4, 5, 6, 7]

    def test_current_near_start(self):
        # current ≤ 4: "1 2 3 4 5 … total"
        assert compute_page_window(1, 10) == [1, 2, 3, 4, 5, None, 10]
        assert compute_page_window(4, 10) == [1, 2, 3, 4, 5, None, 10]

    def test_current_near_end(self):
        # current ≥ total-3: "1 … total-4 total-3 total-2 total-1 total"
        assert compute_page_window(7, 10) == [1, None, 6, 7, 8, 9, 10]
        assert compute_page_window(10, 10) == [1, None, 6, 7, 8, 9, 10]

    def test_current_in_middle(self):
        # otherwise: "1 … current-1 current current+1 … total"
        assert compute_page_window(5, 10) == [1, None, 4, 5, 6, None, 10]
        assert compute_page_window(6, 10) == [1, None, 5, 6, 7, None, 10]

    def test_invariants(self):
        # Always starts with 1 and ends with total when total > 1.
        for total in [2, 3, 5, 7, 8, 15, 100]:
            for current in range(1, total + 1):
                window = compute_page_window(current, total)
                assert window[0] == 1, f"current={current} total={total}"
                assert window[-1] == total, f"current={current} total={total}"
                assert current in window, f"current={current} total={total}"

    def test_zero_total(self):
        # Defensive: empty list yields a single page 1 (caller should hide the bar).
        assert compute_page_window(1, 0) == [1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pagination.py -v`
Expected: ImportError (`tegufox_gui.utils.pagination` doesn't exist yet).

- [ ] **Step 3: Implement helper**

Write `tegufox_gui/utils/pagination.py`:

```python
"""Pure helpers for the Proxies page paginator (spec §6.2)."""

from __future__ import annotations


def compute_page_window(current: int, total: int) -> list[int | None]:
    """Return the list of page numbers to render in the pagination bar.

    `None` represents an ellipsis (non-clickable). The list always starts
    with 1 and ends with `total` (when `total > 1`), and `current` is
    always present. Maximum length is 7 entries.

    Spec §6.2 layout rules:
        total <= 7         -> show every page
        current <= 4       -> "1 2 3 4 5 … total"
        current >= total-3 -> "1 … total-4 total-3 total-2 total-1 total"
        otherwise          -> "1 … current-1 current current+1 … total"
    """
    if total <= 1:
        return [1]
    if total <= 7:
        return list(range(1, total + 1))
    if current <= 4:
        return [1, 2, 3, 4, 5, None, total]
    if current >= total - 3:
        return [1, None, total - 4, total - 3, total - 2, total - 1, total]
    return [1, None, current - 1, current, current + 1, None, total]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pagination.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/utils/pagination.py tests/test_pagination.py
git commit -m "feat(gui): pure helper for proxy pagination window layout"
```

---

## Task 2: Add pagination state with QSettings persistence

**Files:**
- Modify: `tegufox_gui/pages/proxies_page.py` (imports + `ProxiesList.__init__`)

- [ ] **Step 1: Add QSettings import**

At the top of `tegufox_gui/pages/proxies_page.py`, find the existing PyQt imports block (the one that contains `QComboBox`, `QPushButton`, etc.) and add `QSettings` to the `QtCore` import line. If `QtCore` is not yet imported, add:

```python
from PyQt6.QtCore import QSettings
```

(Place it next to the other `from PyQt6.QtCore import …` line. Do NOT duplicate.)

- [ ] **Step 2: Add helper module-level constants**

Just below `class ProxiesList` opening, near `_SORT_OPTIONS`, add:

```python
    _PAGE_SIZE_OPTIONS = [50, 100, 200, 0]  # 0 sentinel = "All"
    _PAGE_SIZE_LABELS = ["50", "100", "200", "All"]
    _DEFAULT_PAGE_SIZE = 100
    _SORT_NEWEST_INDEX = 2  # matches "Date newest" in _SORT_OPTIONS
```

- [ ] **Step 3: Initialize state in `__init__`**

Inside `ProxiesList.__init__`, after the existing `self._active_tests = {}` line and before `self._setup_ui()`, add:

```python
        # Pagination state (spec §4)
        settings = QSettings("Tegufox", "GUI")
        raw_size = settings.value("proxies/page_size", self._DEFAULT_PAGE_SIZE, type=int)
        self._page_size = (
            raw_size if raw_size in self._PAGE_SIZE_OPTIONS else self._DEFAULT_PAGE_SIZE
        )
        self._current_page = 1
        self._visible_filtered: list = []
```

- [ ] **Step 4: Smoke check syntax**

Run: `python -c "import ast; ast.parse(open('tegufox_gui/pages/proxies_page.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tegufox_gui/pages/proxies_page.py
git commit -m "feat(proxies): pagination state with QSettings persistence"
```

---

## Task 3: Add page-size dropdown to header

**Files:**
- Modify: `tegufox_gui/pages/proxies_page.py` (`ProxiesList._setup_ui` header section, new `_on_page_size_changed`)

- [ ] **Step 1: Insert dropdown widget in header**

In `_setup_ui`, find the block that builds `self.sort_combo` (around the line `self.sort_combo.currentIndexChanged.connect(self._apply_filter)`). Immediately AFTER the `hdr.addWidget(self.sort_combo)` line and BEFORE the `self.search_input = QLineEdit()` line, insert:

```python
        # Page-size dropdown (spec §3.1)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(self._PAGE_SIZE_LABELS)
        self.page_size_combo.setCurrentIndex(self._PAGE_SIZE_OPTIONS.index(self._page_size))
        self.page_size_combo.setFixedHeight(32)
        self.page_size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                border: 1px solid {DarkPalette.BORDER}; border-radius: 4px;
                padding: 4px 10px; min-width: 70px; font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {DarkPalette.CARD}; color: {DarkPalette.TEXT};
                selection-background-color: {DarkPalette.ACCENT};
            }}
        """)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        hdr.addWidget(QLabel("Show:"))
        hdr.addWidget(self.page_size_combo)
```

- [ ] **Step 2: Add the handler method**

Add a new method to `ProxiesList`, placed between `_update_title` and `_apply_filter`:

```python
    def _on_page_size_changed(self, index: int):
        """Page-size dropdown changed. Persist + reset to page 1 + re-render."""
        if index < 0 or index >= len(self._PAGE_SIZE_OPTIONS):
            return
        self._page_size = self._PAGE_SIZE_OPTIONS[index]
        QSettings("Tegufox", "GUI").setValue("proxies/page_size", self._page_size)
        self._current_page = 1
        self._apply_filter()
```

- [ ] **Step 3: Smoke check syntax**

Run: `python -c "import ast; ast.parse(open('tegufox_gui/pages/proxies_page.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tegufox_gui/pages/proxies_page.py
git commit -m "feat(proxies): page-size dropdown in header"
```

---

## Task 4: Add pagination footer container

**Files:**
- Modify: `tegufox_gui/pages/proxies_page.py` (`ProxiesList._setup_ui` end of layout)

- [ ] **Step 1: Add footer widget below scroll area**

In `_setup_ui`, find the line `layout.addWidget(scroll)` (the very last `addWidget` in the method). Immediately AFTER it, append:

```python
        # Pagination footer (spec §3.2). Hidden until first render decides
        # whether it's needed.
        self.pagination_footer = QWidget()
        self.pagination_footer.setStyleSheet(
            f"background-color: {DarkPalette.BACKGROUND};"
        )
        footer_row = QHBoxLayout(self.pagination_footer)
        footer_row.setContentsMargins(0, 6, 0, 0)
        footer_row.setSpacing(6)

        self.page_bar_container = QWidget()
        self.page_bar_layout = QHBoxLayout(self.page_bar_container)
        self.page_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.page_bar_layout.setSpacing(4)
        footer_row.addWidget(self.page_bar_container)

        footer_row.addStretch()

        self.page_status_lbl = QLabel("")
        self.page_status_lbl.setStyleSheet(
            f"color: {DarkPalette.TEXT_DIM}; font-size: 11px;"
        )
        footer_row.addWidget(self.page_status_lbl)

        self.pagination_footer.setVisible(False)
        layout.addWidget(self.pagination_footer)
```

- [ ] **Step 2: Smoke check syntax**

Run: `python -c "import ast; ast.parse(open('tegufox_gui/pages/proxies_page.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tegufox_gui/pages/proxies_page.py
git commit -m "feat(proxies): pagination footer scaffold"
```

---

## Task 5: Refactor render flow (`_apply_filter` + `_render_current_page` + `_rebuild_page_bar`)

This is the core change. It replaces the current `_apply_filter` body with the two-phase flow from spec §5.

**Files:**
- Modify: `tegufox_gui/pages/proxies_page.py` (`_apply_filter`, add `_render_current_page`, add `_rebuild_page_bar`, add `_goto_page`)

- [ ] **Step 1: Add pagination helper import**

At the top of `tegufox_gui/pages/proxies_page.py`, alongside the other tegufox imports, add:

```python
from tegufox_gui.utils.pagination import compute_page_window
```

- [ ] **Step 2: Replace `_apply_filter` body**

Find the existing `_apply_filter` method:

```python
    def _apply_filter(self):
        """Apply search and sort filters"""
        text = self.search_input.text() if hasattr(self, "search_input") else ""
        sort_idx = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0
        
        visible = [c for c in self._all_cards if c.matches(text)]
        
        if sort_idx == 0:
            visible.sort(key=lambda c: c._name.lower())
        elif sort_idx == 1:
            visible.sort(key=lambda c: c._name.lower(), reverse=True)
        elif sort_idx == 2:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""), reverse=True)
        elif sort_idx == 3:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""))
        
        while self._list_layout.count():
            self._list_layout.takeAt(0)
        for card in self._all_cards:
            card.setVisible(False)
        for card in visible:
            card.setVisible(True)
```

Replace it with:

```python
    def _apply_filter(self):
        """Recompute visible+sorted list, clamp current page, render (spec §5)."""
        text = self.search_input.text() if hasattr(self, "search_input") else ""
        sort_idx = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0

        visible = [c for c in self._all_cards if c.matches(text)]

        if sort_idx == 0:
            visible.sort(key=lambda c: c._name.lower())
        elif sort_idx == 1:
            visible.sort(key=lambda c: c._name.lower(), reverse=True)
        elif sort_idx == 2:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""), reverse=True)
        elif sort_idx == 3:
            visible.sort(key=lambda c: c.proxy_data.get("created", ""))

        self._visible_filtered = visible

        if self._page_size == 0:
            total_pages = 1
        else:
            total_pages = max(1, (len(visible) + self._page_size - 1) // self._page_size)
        self._current_page = max(1, min(self._current_page, total_pages))

        self._render_current_page()
```

- [ ] **Step 3: Add `_render_current_page` method**

Immediately after the `_apply_filter` method, add:

```python
    def _render_current_page(self):
        """Detach all, attach the current-page slice, refresh footer (spec §5)."""
        # 1. Detach every card currently in layout (no deleteLater — reused).
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)

        # 2. Hide every known card up-front (covers cards that weren't in
        #    the layout this round).
        for card in self._all_cards:
            card.setVisible(False)

        # 3. Compute the slice for the current page.
        if self._page_size == 0:
            slice_cards = self._visible_filtered
            total_pages = 1
        else:
            start = (self._current_page - 1) * self._page_size
            end = start + self._page_size
            slice_cards = self._visible_filtered[start:end]
            total_pages = max(1, (len(self._visible_filtered) + self._page_size - 1) // self._page_size)

        # 4. Attach + show the slice.
        for card in slice_cards:
            card.setParent(self._list_widget)
            self._list_layout.addWidget(card)
            card.setVisible(True)

        # 5. Refresh footer.
        self._rebuild_page_bar(self._current_page, total_pages)

        total = len(self._visible_filtered)
        if total == 0:
            self.page_status_lbl.setText("showing 0-0 of 0")
        elif self._page_size == 0:
            self.page_status_lbl.setText(f"showing 1-{total} of {total}")
        else:
            shown_start = (self._current_page - 1) * self._page_size + 1
            shown_end = shown_start + len(slice_cards) - 1
            self.page_status_lbl.setText(f"showing {shown_start}-{shown_end} of {total}")

        # 6. Show/hide the whole footer.
        #    Spec §3.2: hidden when total_pages <= 1; in "All" mode hide the
        #    page bar but still show the status label.
        self.page_bar_container.setVisible(self._page_size != 0 and total_pages > 1)
        self.pagination_footer.setVisible(total_pages > 1 or self._page_size == 0)
```

- [ ] **Step 4: Add `_rebuild_page_bar` method**

Immediately after `_render_current_page`, add:

```python
    def _rebuild_page_bar(self, current: int, total: int):
        """Rebuild numbered page buttons + Prev/Next (spec §6.2)."""
        # Destroy old buttons (cheap — at most ~9 widgets).
        while self.page_bar_layout.count():
            item = self.page_bar_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        if total <= 1:
            return

        prev_btn = QPushButton("<")
        prev_btn.setFixedSize(28, 28)
        prev_btn.setEnabled(current > 1)
        prev_btn.clicked.connect(lambda: self._goto_page(current - 1))
        self.page_bar_layout.addWidget(prev_btn)

        for token in compute_page_window(current, total):
            if token is None:
                lbl = QLabel("…")
                lbl.setStyleSheet(f"color: {DarkPalette.TEXT_DIM}; padding: 0 4px;")
                self.page_bar_layout.addWidget(lbl)
                continue
            btn = QPushButton(str(token))
            btn.setFixedSize(28, 28)
            if token == current:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {DarkPalette.ACCENT}; color: white;
                        border: none; border-radius: 4px; font-weight: 600;
                    }}
                """)
            page = token
            btn.clicked.connect(lambda _=False, p=page: self._goto_page(p))
            self.page_bar_layout.addWidget(btn)

        next_btn = QPushButton(">")
        next_btn.setFixedSize(28, 28)
        next_btn.setEnabled(current < total)
        next_btn.clicked.connect(lambda: self._goto_page(current + 1))
        self.page_bar_layout.addWidget(next_btn)
```

- [ ] **Step 5: Add `_goto_page` method**

Immediately after `_rebuild_page_bar`, add:

```python
    def _goto_page(self, page: int):
        """Page-bar button handler. Re-renders without re-filtering."""
        self._current_page = page
        self._render_current_page()
```

- [ ] **Step 6: Smoke check syntax**

Run: `python -c "import ast; ast.parse(open('tegufox_gui/pages/proxies_page.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 7: Smoke launch the app**

Run: `python -m tegufox_gui &` (or however the project launches the GUI; check `Makefile` if unsure)

Click into Proxies page. Expect:
- Existing proxies still show (whatever count is in DB).
- If count > 100: footer visible at bottom showing `< 1 2 ... > showing 1-100 of N`.
- If count <= 100: footer hidden.

Kill the app after the smoke check.

- [ ] **Step 8: Commit**

```bash
git add tegufox_gui/pages/proxies_page.py
git commit -m "feat(proxies): paginated render with numbered page bar"
```

---

## Task 6: Reset-page hooks for search/sort + bulk-import behavior

**Files:**
- Modify: `tegufox_gui/pages/proxies_page.py` (search/sort wiring, `open_import_dialog`)

- [ ] **Step 1: Wrap search/sort hooks to reset page**

Find these two existing lines in `_setup_ui`:

```python
        self.sort_combo.currentIndexChanged.connect(self._apply_filter)
```
and
```python
        self.search_input.textChanged.connect(self._apply_filter)
```

Replace BOTH with calls to a new wrapper. Change them to:

```python
        self.sort_combo.currentIndexChanged.connect(self._on_filter_changed)
```
and
```python
        self.search_input.textChanged.connect(self._on_filter_changed)
```

Then add the new method, placed next to `_on_page_size_changed`:

```python
    def _on_filter_changed(self, *_):
        """Search or sort changed — reset to page 1, re-render (spec §6.1)."""
        self._current_page = 1
        self._apply_filter()
```

- [ ] **Step 2: Hook bulk-import to force sort=Newest + page=1**

Find `open_import_dialog`. The success path currently looks like:

```python
            success_count, errors = self.proxy_manager.bulk_import(lines)
            
            self.refresh_proxies()
            
            msg = f"Successfully imported {success_count} proxy(ies)."
```

Replace those three lines (the import call, the refresh, and the assignment of `msg`) with:

```python
            success_count, errors = self.proxy_manager.bulk_import(lines)

            # Spec §6.1: after bulk import, surface freshly imported proxies
            # by switching to "Date newest" + first page.
            if success_count > 0:
                self.sort_combo.blockSignals(True)
                self.sort_combo.setCurrentIndex(self._SORT_NEWEST_INDEX)
                self.sort_combo.blockSignals(False)
                self._current_page = 1

            self.refresh_proxies()

            msg = f"Successfully imported {success_count} proxy(ies)."
```

(Note `blockSignals` prevents the sort change from firing `_on_filter_changed` and double-resetting page; `refresh_proxies` already calls `_apply_filter` via `load_proxies`.)

- [ ] **Step 3: Smoke check syntax**

Run: `python -c "import ast; ast.parse(open('tegufox_gui/pages/proxies_page.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tegufox_gui/pages/proxies_page.py
git commit -m "feat(proxies): reset page on search/sort, surface fresh imports"
```

---

## Task 7: Manual integration smoke test

This is the only realistic verification — the project has no GUI test framework (spec §10).

**Files:** none (verification only)

- [ ] **Step 1: Launch the GUI**

Run: `python -m tegufox_gui` (or the project's launch entry point — check `Makefile`).

- [ ] **Step 2: Walk through spec §10 manual test plan**

For each step below, verify the expected outcome and note any deviation.

1. Navigate to Proxies page. Confirm the dropdown reads `100`. If proxies > 100, footer reads `< 1 2 … > showing 1-100 of <total>`. If ≤ 100, footer hidden.
2. Click page `3` button → cards 201-300 visible, button `3` highlighted accent color.
3. Click `>` → page 4. Click `<` twice → page 2.
4. Type some characters in search → page resets to 1, filtered subset paginates correctly.
5. Clear search → still on page 1, full pagination restored.
6. Change Sort dropdown → page resets to 1.
7. Change page-size dropdown 100 → 50 → page bar widens, position resets to 1.
8. Change page-size dropdown 50 → All → page-bar buttons disappear; status label still shows `showing 1-N of N`; all cards rendered.
9. Single-delete the only card on the highest page → page silently drops by 1.
10. Bulk-delete several selected → list reloads, paginator recomputes.
11. **Bulk-import test:** import 50 fresh proxies via the Import dialog → after dialog closes, sort dropdown shows "Date newest", page = 1, freshly imported proxies appear at the top.
12. Restart the app → Proxies page → dropdown remembers last page-size; current page = 1.

- [ ] **Step 3: Performance pass criteria**

Bulk-import 500 proxies (or however many are available). After the import dialog confirms success, the app should not freeze visibly while rendering page 1. Compare against `git stash` of this branch on `main` to confirm the difference if uncertain.

- [ ] **Step 4: If everything passes, no commit**

Verification only. If any step uncovered a bug, file a fix as a follow-up task and address before merging.

---

## Self-review notes

Spec coverage check:

- §3.1 page-size dropdown — Task 3 ✓
- §3.2 numbered page bar + status label + visibility rules — Task 4 (scaffold) + Task 5 step 4 (logic) ✓
- §4 state fields + QSettings — Task 2 ✓
- §5 render flow split — Task 5 ✓
- §6.1 event hooks — Tasks 5, 6 ✓
- §6.2 page-bar window math — Task 1 (helper + tests) + Task 5 step 4 (consumer) ✓
- §7 data-flow diagram — covered by Tasks 5+6 ✓
- §8 edge cases — empty list (Task 5 step 3 status label branch), zero matches (same), delete last card (clamp in Task 5 step 2), import behavior (Task 6 step 2), All mode (Task 5 step 3 footer-visibility branch), QSettings malformed (Task 2 step 3 validation) ✓
- §9 out of scope — observed (no other pages touched, no async, no per-session current-page persistence) ✓
- §10 manual test plan — Task 7 ✓

No placeholders, no TBDs, no "implement later". Method names consistent across tasks (`_apply_filter`, `_render_current_page`, `_rebuild_page_bar`, `_goto_page`, `_on_filter_changed`, `_on_page_size_changed`). QSettings org/app names consistent (`"Tegufox"`, `"GUI"`, key `"proxies/page_size"`).
