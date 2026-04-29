"""Tests for tegufox_gui.utils.pagination."""

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
