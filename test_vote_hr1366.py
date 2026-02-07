#!/usr/bin/env python
import sys
sys.path.insert(0, 'customagents')
from web_agent_get_vote_data import VoteAgent
from web_agent import WebAgent

web_agent = WebAgent()
vote_agent = VoteAgent()
vote_agent._agent = web_agent

# Test full fetch_vote_data
result = vote_agent.fetch_vote_data(
    'https://www.congress.gov/votes/house/119-1/298',
    vote_date='12/02/2025',
    bill_abbrev='HR1366'
)

print(f'Success: {result.get("success")}')
if result.get('error'):
    print(f'Error: {result.get("error")}')
if result.get('path'):
    print(f'Path: {result.get("path")}')
    # Check if file exists
    import os
    if os.path.exists(result.get('path')):
        print('File exists!')
