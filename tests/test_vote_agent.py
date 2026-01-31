import os
import json

from customagents.web_agent_get_vote_data import VoteAgent


def test_vote_agent_fetches_and_writes_json(tmp_path):
    # Use a temporary output path to avoid overwriting existing data during tests
    url = "https://www.congress.gov/index.php/votes/house/119-1/362"
    va = VoteAgent()
    # produce output into tmp_path
    out = tmp_path / "vote_test.json"
    res = va.fetch_vote_data(url, out_file=str(out))

    assert isinstance(res, dict)
    assert res.get("success") is True, res.get("error")
    path = res.get("path")
    assert path is not None
    assert os.path.exists(path)

    # Basic content checks
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "vote_url" in data
    assert "tables" in data
    # Expect at least one table with rows (roll-call membership table)
    assert isinstance(data["tables"], list)
    assert any(t.get("rows") for t in data["tables"])
