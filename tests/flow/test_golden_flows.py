import pytest
from pathlib import Path

from tegufox_flow.runtime import run_flow


@pytest.mark.golden
def test_linear_search(tmp_path, static_pages):
    db = tmp_path / "g.db"
    flow = Path(__file__).parent / "flows" / "linear_search.yaml"
    result = run_flow(
        flow,
        profile_name="default",  # requires a profile named 'default'
        inputs={"base_url": static_pages},
        db_path=db,
    )
    assert result.status == "succeeded", result.error
