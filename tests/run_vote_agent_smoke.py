"""Standalone smoke runner for VoteAgent that doesn't rely on pytest or project conftest.

Usage:
  python tests/run_vote_agent_smoke.py
"""
import sys
import os
import pathlib

# Ensure repo root is on sys.path so `customagents` is importable when running this script
repo_root = pathlib.Path(__file__).parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from customagents.web_agent_get_vote_data import VoteAgent


def main():
    url = "https://www.congress.gov/index.php/votes/house/119-1/362"
    va = VoteAgent()
    res = va.fetch_vote_data(url)
    print(res)
    if not res.get("success"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
