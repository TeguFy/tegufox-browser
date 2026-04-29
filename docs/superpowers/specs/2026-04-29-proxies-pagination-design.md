# Proxies Page — Pagination Design Spec

**Scope:** GUI-only change to `tegufox_gui/pages/proxies_page.py`
**Date:** 2026-04-29
**Status:** Draft
**Owner:** lugondev

## 1. Goal

Eliminate UI lag when the Proxies page holds many proxy records (typical
import 100–500 entries). Today every `ProxyCard` (a `QFrame` with
stylesheets, child widgets, and 5 signals) is created up-front in
`load_proxies()`, all kept in `_all_cards`, all parented to
`_list_widget`. With ~500 cards the initial render and every
`_apply_filter()` pass become visibly slow.

Goal: render at most one page worth of cards at a time
(default 100). The remaining cards stay in `_all_cards` (so search/sort
are still in-memory and instant) but are detached from the layout and
hidden, so Qt does not paint them.

In scope (v1):

- Page-size dropdown with options `50 / 100 / 200 / All`, persisted in
  `QSettings("Tegufox", "GUI")` under key `proxies/page_size`.
- Numbered page bar (max ~9 buttons with ellipsis) + "showing X-Y of Z" label.
- Reset to page 1 on: search change, sort change, page-size change,
  bulk import.
- After bulk import: force sort to "Newest" + page = 1 so freshly
  imported proxies appear at the top of the first page.
- Reuse existing `ProxyCard` widgets across page navigation (reparent,
  do not destroy) — only widget-creation cost is moved off the hot path.

Out of scope (defer / YAGNI):

- Pagination on other list pages (Profiles, Sessions, Runs, Flows,
  Schedules). They have their own performance characteristics; if any
  one of them needs the same treatment it gets its own task.
- Server-side / DB-side pagination — `proxy_manager.list()` reads from
  the filesystem and is cheap for the target scale (≤500).
- Async / background loading — synchronous load is fast enough once
  cards aren't all painted.
- Persisting `_current_page` across app restarts — only `_page_size`
  is persisted; page resets to 1 on launch.
- Generalising the page-bar widget into a reusable component for
  other pages.

## 2. Why this exists

Two concrete failure modes today:

1. **Initial load lag.** `load_proxies()` constructs all `ProxyCard`
   instances at startup. With 500 entries that is ~500 `QFrame`
   constructions, ~500 stylesheet parses, ~5 × 500 signal connections.
   Visible UI freeze.

2. **Filter / sort lag.** `_apply_filter()` calls
   `self._list_layout.takeAt(0)` in a loop, then iterates over all
   cards toggling visibility. Even toggling visibility on 500 widgets
   parented to one `QVBoxLayout` causes layout invalidation and
   repaint cost.

A previous fix in this file (commit on `feat/flow-orchestrator`)
addressed a related zombie-widget bug after delete. This change builds
on top of that fix; the cleanup helpers added there will be reused.

## 3. UI

### 3.1 Header strip

Append a "Show" group to the right of the existing Sort combo box:

```
[Search...]   [Sort ▾]   Show [100 ▾]
```

Dropdown items: `50`, `100`, `200`, `All`. Default `100`.

### 3.2 Footer (pagination bar)

New widget added below the scroll area:

```
< 1 2 3 4 5 >          showing 101-200 of 500
```

- Page buttons: previous arrow, page numbers, next arrow.
- Numbered buttons follow standard sliding-window logic with ellipses
  (see §6.2). Maximum ~9 visible buttons including ellipsis tokens.
- Current page button is highlighted (uses `DarkPalette.ACCENT`).
- Right-aligned status label: `showing X-Y of Z`.
- Footer is **hidden** when `total_pages ≤ 1` (no need to show "1 of 1").
- Footer is **hidden** when `_page_size == 0` ("All" mode) — only the
  status label is shown.

## 4. State

Added to `ProxiesList`:

| Field                | Type                | Notes                                                                |
|----------------------|---------------------|----------------------------------------------------------------------|
| `_page_size`         | `int`               | 50 / 100 / 200, or `0` for "All". Loaded from QSettings on init.     |
| `_current_page`      | `int`               | 1-indexed. Resets to 1 on app launch and on most state changes.      |
| `_visible_filtered`  | `list[ProxyCard]`   | Output of search+sort applied to `_all_cards`. Source for paginator. |

`QSettings` key: `proxies/page_size` (int, 0 means "All").

## 5. Render flow

`_apply_filter()` is split into two phases:

```
_apply_filter():
    1. _visible_filtered = sort(filter(_all_cards, search_text), sort_idx)
    2. total_pages = max(1, ceil(len(_visible_filtered) / page_size))
       (when page_size == 0: total_pages = 1)
    3. clamp _current_page to [1, total_pages]
    4. _render_current_page()

_render_current_page():
    1. Detach every card currently in _list_layout:
         - takeAt(0) until empty
         - For the widget on each item: setParent(None)  (no deleteLater — reused)
    2. For card in _all_cards: setVisible(False)
       (covers cards that were never in the layout this pass)
    3. Compute slice:
         if page_size == 0: slice = _visible_filtered
         else: start = (page-1) * page_size; slice = _visible_filtered[start:start+page_size]
    4. For card in slice:
         setParent(_list_widget)  (idempotent if already parented)
         _list_layout.addWidget(card)
         setVisible(True)
    5. _rebuild_page_bar(current=_current_page, total=total_pages)
    6. Update "showing X-Y of Z" label
       (X = start+1 or 0 if empty, Y = start+len(slice), Z = len(_visible_filtered))
```

Note: cards are reparented as the user paginates. No `QFrame` is
created or destroyed during paging — only on initial load and on
add/import/delete.

## 6. Hooks into existing events

### 6.1 Event table

| Event                         | Behavior                                                                                       |
|-------------------------------|------------------------------------------------------------------------------------------------|
| Search text change            | `_current_page = 1` → `_apply_filter()`                                                        |
| Sort change                   | `_current_page = 1` → `_apply_filter()`                                                        |
| Page-size dropdown change     | Save QSettings, `_current_page = 1`, `_apply_filter()`                                         |
| Page-bar button click         | `_current_page = N` → `_render_current_page()` (no re-filter needed)                           |
| Single delete (`on_proxy_delete`) | After destroying card, `_apply_filter()` (clamp handles "last page now empty")             |
| Bulk delete (`delete_selected_proxies`) | `load_proxies()` (already cleaned up by previous zombie-widget fix)                   |
| Bulk import success           | Set `sort_combo` to "Newest" + `_current_page = 1` + `load_proxies()`                          |

### 6.2 Page-bar logic

`_rebuild_page_bar(current, total)` — destroys old buttons (`deleteLater`),
creates fresh ones each call (max 11 widgets, cheap). Layout rules:

- `total ≤ 7`: show every page `1 2 … total`
- `current ≤ 4`: `1 2 3 4 5 … total`
- `current ≥ total-3`: `1 … total-4 total-3 total-2 total-1 total`
- otherwise: `1 … current-1 current current+1 … total`

Plus a `<` (Prev) button (disabled at page 1) and `>` (Next) button
(disabled at last page) flanking the numbers. Ellipsis tokens are
non-clickable `QLabel`s.

## 7. Data flow

```
User action (search / sort / page click / page-size / import / delete)
    ↓
_apply_filter()
    ↓
_render_current_page()
    ↓
_update_title(total)        (unchanged: shows "Proxies (N)")
```

`_update_title` keeps its existing meaning — total count across all
pages, not per-page count.

## 8. Edge cases

- **Empty list.** `_visible_filtered = []` → `total_pages = 1`,
  `_current_page = 1`, slice empty, label `"showing 0-0 of 0"`,
  footer hidden.
- **Search yields zero matches.** Same as empty list.
- **Delete the last card on the last page.** `_apply_filter` recomputes
  `total_pages`; clamp pulls `_current_page` back so the user is no
  longer stranded on a page that no longer exists.
- **Import while on page 5.** Bulk-import success forcibly resets to
  page 1 + sort=Newest (per §6.1), so the user always sees what they
  just imported.
- **`_page_size == 0` ("All") with 500 cards.** Footer hidden (page bar
  removed); cards all rendered. Performance regresses to today's
  baseline — acceptable because the user explicitly opted in.
- **QSettings missing or malformed.** Default to 100. Validate value
  is in `{0, 50, 100, 200}`; otherwise reset to 100.

## 9. Out of scope

(Repeated for emphasis.)

- Pagination on other list pages.
- Persisting current page across sessions.
- Server-side or DB-side pagination.
- Async loading / progress indicator during initial render.
- Refactoring the page-bar widget into a shared component.

## 10. Test plan

Manual — no GUI test framework in this project. Each step run on a
profile with 500 imported proxies:

1. Launch app → Proxies page → confirm dropdown shows "100", footer
   shows page 1 of 5, "showing 1-100 of 500".
2. Click page 3 → cards 201-300 visible, page button "3" highlighted.
3. Click `>` → page 4. Click `<` twice → page 2.
4. Type "abc" in search → page resets to 1, paginator recomputes for
   filtered subset.
5. Clear search → page still 1 (it was reset on search change), 5 pages
   restored.
6. Change Sort → page resets to 1.
7. Change dropdown 100 → 50 → page bar now spans 1..10, position
   resets to 1.
8. Change dropdown 50 → All → footer hidden, all 500 rendered (lag is
   acceptable).
9. Single-delete the only card on page 5 → page silently drops to 4.
10. Bulk-delete 50 selected → list reloads, paginator recomputes.
11. Bulk-import 50 fresh proxies → sort flips to "Newest", page = 1,
    new proxies visible at top.
12. Restart app → dropdown remembers last page-size; current page = 1.

Pass criteria for the original complaint: step 11 with import of 500
fresh proxies completes without the user perceiving freeze (only 100
cards painted instead of 500).
