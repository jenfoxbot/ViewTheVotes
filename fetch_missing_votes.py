#!/usr/bin/env python
"""Quick script to fetch missing vote data for December 2025 bills."""

from customagents.web_agent_get_vote_data import VoteAgent
from customagents.web_agent_get_bill_data import WebAgent

missing_votes = [
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/310', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1005', 'date': '12/03/2025', 'abbrev': 'HR1005'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/298', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1366', 'date': '12/02/2025', 'abbrev': 'HR1366'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/322', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/2550', 'date': '12/11/2025', 'abbrev': 'HR2550'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/304', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/2965', 'date': '12/03/2025', 'abbrev': 'HR2965'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/328', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3383', 'date': '12/11/2025', 'abbrev': 'HR3383'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/346', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3616', 'date': '12/17/2025', 'abbrev': 'HR3616'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/309', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4305', 'date': '12/03/2025', 'abbrev': 'HR4305'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/338', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4371', 'date': '12/16/2025', 'abbrev': 'HR4371'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/288', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4776', 'date': '12/02/2025', 'abbrev': 'HR4776'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/277', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/6703', 'date': '12/01/2025', 'abbrev': 'HR6703'},
    {'vote_url': 'https://www.congress.gov/votes/house/119-1/278', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/845', 'date': '12/01/2025', 'abbrev': 'HR845'},
]

print("Fetching missing vote data for December 2025...")

# Create a shared web agent for efficient browser reuse
web_agent = WebAgent()

for vote_info in missing_votes:
    print(f"\nFetching {vote_info['abbrev']}...")
    
    vote_agent = VoteAgent()
    # Share the browser session
    vote_agent._agent = web_agent
    
    result = vote_agent.fetch_vote_data(
        vote_info['vote_url'],
        vote_date=vote_info['date'],
        bill_abbrev=vote_info['abbrev']
    )
    
    if result.get('success'):
        print(f"  ✓ Saved vote data to {result.get('path')}")
    else:
        print(f"  ✗ Failed: {result.get('error')}")

print("\nDone!")
