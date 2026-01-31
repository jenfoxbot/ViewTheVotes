import sys
import os

# Ensure repository root is on sys.path so top-level packages are importable
repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from customagents.web_agent import WebAgent


if __name__ == '__main__':
    agent = WebAgent()
    url = 'https://www.congress.gov/bill/119th-congress/house-bill/498'
    print(f'Visiting: {url}')
    res = agent.visit(url)
    if not res.get('success'):
        print('Failed:', res.get('error'))
        sys.exit(1)
    print('Title:', res.get('title'))
    print('URL:', res.get('url'))
    print('Links found:', res.get('links_count'))
    if res.get('summary'):
        print('Summary (first 300 chars):')
        print(res.get('summary')[:300])
    sys.exit(0)
