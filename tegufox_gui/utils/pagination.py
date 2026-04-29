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
