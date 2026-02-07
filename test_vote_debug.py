#!/usr/bin/env python
import sys
sys.path.insert(0, 'customagents')
from web_agent_get_vote_data import VoteAgent
from web_agent import WebAgent

web_agent = WebAgent()

# Test fetch_vote_data without bill_abbrev first
print("Test 1: fetch_vote_data with bill_abbrev...")
vote_agent = VoteAgent()
vote_agent._agent = web_agent
result = vote_agent.fetch_vote_data(
    'https://www.congress.gov/votes/house/119-1/298',
    vote_date='12/02/2025',
    bill_abbrev='HR1366'
)
print(f"  Success: {result.get('success')}")

# Test 2: Without bill_abbrev
print("\nTest 2: fetch_vote_data without bill_abbrev...")
vote_agent2 = VoteAgent()
vote_agent2._agent = web_agent
result2 = vote_agent2.fetch_vote_data(
    'https://www.congress.gov/votes/house/119-1/298',
    vote_date='12/02/2025'
)
print(f"  Success: {result2.get('success')}")
