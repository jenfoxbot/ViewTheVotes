Web Agent Example

This example demonstrates a minimal web-search-and-navigation agent built using the examples in this repository.

Files:
- web_agent.py: interactive CLI that supports `search`, `visit`, `links`, and `follow`.
- web_tools_mcp.py: existing MCP tools in this folder (search, fetch_url, http_request).

Quick start (from this folder):

1. Create a virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the interactive CLI:

```powershell
python web_agent.py
```

Notes:
- If you set `TAVILY_API_KEY` in your environment and have `tavily-python` installed, `search` will use that API. Otherwise the CLI falls back to DuckDuckGo HTML scraping.
- `visit` fetches a page and extracts links; `follow <n>` navigates using an indexed link from the last-visited page.
- This is a simple example; for production use consider adding robust error handling, rate limiting, caching, and obeying robots.txt.
