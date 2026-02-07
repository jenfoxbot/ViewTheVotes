"""
Simple Web Agent CLI using the example web tools in this repo.

Commands:
 - search <query>         : search the web (uses Tavily if configured, otherwise DuckDuckGo fallback)
 - visit <url>            : fetch a URL and display title + summary
 - links                  : list last-visited page links with indexes
 - follow <n>             : follow link number n from last-visited page
 - open <n>               : same as follow
 - quit / exit            : exit

This is intended as a minimal example demonstrating search, fetch, and navigation.
"""
from __future__ import annotations

import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional, Tuple

import importlib.util
import pathlib
import re
import json

# Try to import the example MCP tools module if present so we behave like the examples
tavily_search = None
examples_tools = None
try:
    examples_path = pathlib.Path(__file__).parents[1] / "examples" / "deepagents" / "web_tools_mcp.py"
    if examples_path.exists():
        spec = importlib.util.spec_from_file_location("examples.deepagents.web_tools_mcp", str(examples_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        examples_tools = module
        # module defines web_search, fetch_url, http_request
        tavily_search = getattr(module, "web_search", None)
except Exception:
    tavily_search = None
    examples_tools = None


class WebAgent:
    def __init__(self):
        self.last_url: Optional[str] = None
        self.last_html: Optional[str] = None
        self.last_links: List[Tuple[str, str]] = []  # (text, url)
        self._browser = None
        self._page = None
        self._playwright = None

    def search(self, query: str, max_results: int = 5):
        if tavily_search is not None:
            try:
                return tavily_search(query=query, max_results=max_results)
            except Exception as e:
                print(f"Tavily search failed: {e}")

        # Fallback: DuckDuckGo HTML scraping
        print("Using DuckDuckGo fallback search (no API key configured).")
        q = requests.utils.requote_uri(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "web-agent/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("/l/?kh="):
                # duckduckgo redirect wrapper like /l/?kh=1&uddg=<encoded-url>
                from urllib.parse import parse_qs, urlparse, unquote

                qs = parse_qs(urlparse(href).query)
                if "uddg" in qs:
                    target = unquote(qs["uddg"][0])
                else:
                    continue
            else:
                target = href

            if target.startswith("http"):
                title = a.get_text(strip=True) or target
                results.append({"title": title, "url": target})
            if len(results) >= max_results:
                break

        return {"query": query, "results": results}

    def visit(self, url: str):
        # Use a session with retries and realistic headers to avoid simple bot blocks
        session = requests.Session()
        # Retry strategy for transient errors
        try:
            from urllib3.util import Retry
            from requests.adapters import HTTPAdapter

            retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        except Exception:
            # ignore if urllib3 Retry isn't available for some reason
            pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url,
            "Connection": "keep-alive",
        }
        # Delegate actual fetching to _fetch_raw (handles cloudscraper/playwright fallbacks)
        fetched = self._fetch_raw(url)
        if not fetched or not fetched.get("success"):
            err = None if not fetched else fetched.get("error")
            return {"success": False, "error": err or "failed to fetch", "url": url}

        html = fetched.get("html", "")
        text = fetched.get("text", "")
        page_url = fetched.get("url", url)

        # Parse title and links
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else page_url
            anchors = soup.find_all("a")
            links = []
            for a in anchors:
                href = a.get("href")
                if not href:
                    continue
                full = urljoin(page_url, href)
                links.append((a.get_text(" ", strip=True) or full, full))
        except Exception:
            title = page_url
            links = []

        self.last_url = page_url
        self.last_html = html
        self.last_links = links

        summary = text[:2000] if isinstance(text, str) else None
        return {
            "success": True,
            "title": title,
            "url": page_url,
            "links_count": len(links),
            "summary": summary,
            "html": html,
            "text": text,
        }

    def _extract_bill_abbrev(self, bill_url: str) -> Optional[str]:
        """Extract bill abbreviation from congress.gov URL.
        
        Examples:
            'https://www.congress.gov/bill/119th-congress/house-bill/498' -> 'HR498'
            'https://www.congress.gov/bill/119th-congress/senate-bill/123' -> 'S123'
        """
        # Match patterns like 'house-bill/498' or 'senate-bill/123'
        match = re.search(r'/(house-bill|senate-bill|house-joint-resolution|senate-joint-resolution|house-concurrent-resolution|senate-concurrent-resolution|house-resolution|senate-resolution)/(\d+)', bill_url, re.IGNORECASE)
        if match:
            bill_type = match.group(1).lower()
            bill_num = match.group(2)
            
            # Map bill types to abbreviations
            type_map = {
                'house-bill': 'HR',
                'senate-bill': 'S',
                'house-joint-resolution': 'HJRes',
                'senate-joint-resolution': 'SJRes',
                'house-concurrent-resolution': 'HConRes',
                'senate-concurrent-resolution': 'SConRes',
                'house-resolution': 'HRes',
                'senate-resolution': 'SRes',
            }
            abbrev = type_map.get(bill_type, 'BILL')
            return f"{abbrev}{bill_num}"
        return None

    def _parse_month_folder(self, date_str: str) -> Optional[str]:
        """Parse date string and return folder name in format MonthYear (e.g., 'Jan2025', 'Dec2025').
        
        Args:
            date_str: Date in format MM/DD/YYYY (e.g., '01/16/2025')
            
        Returns:
            Folder name like 'Jan2025' or None if parsing fails
        """
        try:
            from datetime import datetime
            # Parse date from MM/DD/YYYY format
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            # Format as MonthYear (e.g., 'Jan2025')
            return dt.strftime('%b%Y')
        except Exception:
            return None

    def _get_browser(self):
        """Get or create a persistent Playwright browser session."""
        if self._playwright is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._page = self._browser.new_page()
            self._page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
        return self._page
    
    def close_browser(self):
        """Close the Playwright browser if it's open."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def _fetch_raw(self, url: str):
        """Fetch a URL and return a dict with keys: success, url, html, text, error"""
        # Use persistent Playwright browser to bypass Cloudflare protection
        try:
            import time
            page = self._get_browser()
            
            try:
                # Add delay to avoid rate limiting
                time.sleep(3)
                
                page.goto(url, wait_until="load", timeout=45000)
                page.wait_for_timeout(4000)  # Wait for JavaScript/Cloudflare to complete
                
                html = page.content()
                final_url = page.url
                
                # Check if we got a Cloudflare challenge page
                if "Just a moment" in html or "Verifying you are human" in html:
                    print(f"Warning: Cloudflare challenge detected for {url}, waiting longer...")
                    page.wait_for_timeout(8000)  # Wait longer for Cloudflare
                    html = page.content()
                    
                    # If still blocked, give up on this page
                    if "Just a moment" in html:
                        return {"success": False, "error": "Cloudflare blocked request", "url": url}
                
                # Extract text
                try:
                    text = page.evaluate("() => document.body.innerText")
                except:
                    text = html
                
                return {
                    "success": True,
                    "url": final_url,
                    "html": html,
                    "text": text,
                }
            except Exception as e:
                return {"success": False, "error": f"Playwright navigation failed: {e}", "url": url}
        except Exception as e:
            # Fallback to requests if Playwright fails
            pass
        
        # Fallback: use requests with retry logic
        session = requests.Session()
        try:
            from urllib3.util import Retry
            from requests.adapters import HTTPAdapter

            retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        except Exception:
            pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url,
            "Connection": "keep-alive",
        }

        resp = None
        # Prefer example tools if available
        if examples_tools is not None:
            try:
                if hasattr(examples_tools, "http_request"):
                    http_req = getattr(examples_tools.http_request, "fn", examples_tools.http_request)
                    hr = http_req(url=url, method="GET", headers=headers, timeout=20)
                    if hr.get("success"):
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = hr.get("url", url)
                        resp.text = hr.get("content") if isinstance(hr.get("content"), str) else str(hr.get("content"))
                    else:
                        resp = session.get(url, timeout=20, headers=headers)
                        resp.raise_for_status()
                elif hasattr(examples_tools, "fetch_url"):
                    fetch_f = getattr(examples_tools.fetch_url, "fn", examples_tools.fetch_url)
                    fr = fetch_f(url=url, timeout=20)
                    if fr.get("success"):
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = fr.get("url", url)
                        resp.text = fr.get("markdown_content", "")
                    else:
                        resp = session.get(url, timeout=20, headers=headers)
                        resp.raise_for_status()
                else:
                    resp = session.get(url, timeout=20, headers=headers)
                    resp.raise_for_status()
            except requests.exceptions.HTTPError as he:
                status = getattr(he.response, "status_code", None)
                if status == 403:
                    resp = None
                else:
                    return {"success": False, "error": f"HTTP error: {he}", "url": url}
            except Exception as e:
                return {"success": False, "error": str(e), "url": url}
        else:
            try:
                resp = session.get(url, timeout=20, headers=headers)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as he:
                status = getattr(he.response, "status_code", None)
                if status == 403:
                    resp = None
                else:
                    return {"success": False, "error": f"HTTP error: {he}", "url": url}
            except Exception as e:
                return {"success": False, "error": str(e), "url": url}

        if resp is None:
            try:
                import cloudscraper

                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, timeout=30)
                resp.raise_for_status()
            except Exception:
                try:
                    from playwright.sync_api import sync_playwright

                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.goto(url, timeout=30000)
                        html = page.content()
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = page.url or url
                        resp.text = html
                        browser.close()
                except Exception as e:
                    return {
                        "success": False,
                        "error": (
                            "HTTP 403 Forbidden (cloudscraper/playwright failed). "
                            "Install 'cloudscraper' or 'playwright' and run 'playwright install chromium'."
                        ),
                        "url": url,
                    }

        html = resp.text
        # Extract text fallback
        try:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n", strip=True)
        except Exception:
            text = html

        return {"success": True, "url": resp.url, "html": html, "text": text}

    def fetch_bill_tabs(self, bill_url: str, tabs: Optional[List[str]] = None, out_file: Optional[str] = None, vote_date: Optional[str] = None):
        """Fetch specified tabs for a bill page and store consolidated JSON to `out_file`.

        tabs: list of tab names to collect (case-insensitive). Defaults to ['summary','text','amendments','committees']
        out_file: optional path to write JSON; if not provided, derives from bill URL and vote_date.
        vote_date: optional date string in format MM/DD/YYYY to determine output folder (e.g., '01/16/2025' -> 'Jan2025')
        Returns dict with file path and collected data or error.
        """
        if tabs is None:
            tabs = ["summary", "text", "amendments", "committees"]

        base_fetch = self._fetch_raw(bill_url)
        if not base_fetch.get("success"):
            return {"success": False, "error": f"Failed to fetch base bill page: {base_fetch.get('error')}", "url": bill_url}

        collected = {"base_url": bill_url, "title": None, "tabs": {}}
        try:
            soup = BeautifulSoup(base_fetch["html"], "html.parser")
            collected["title"] = soup.title.string.strip() if soup.title and soup.title.string else bill_url
        except Exception:
            collected["title"] = bill_url

        # Find candidate links for tabs
        anchors = BeautifulSoup(base_fetch["html"], "html.parser").find_all("a")
        hrefs = {}
        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            text = (a.get_text(" ", strip=True) or "").lower()
            full = urljoin(bill_url, href)
            hrefs.setdefault(full, set()).add(text)

        # helper to find URL for a given tab name
        def find_tab_url(tabname: str):
            lname = tabname.lower()
            # Prefer anchors with text matching tab
            for u, texts in hrefs.items():
                for t in texts:
                    if lname in t:
                        return u
            # Prefer hrefs containing patterns
            for u in hrefs.keys():
                if re.search(rf"[?&]tab={lname}", u, re.IGNORECASE) or re.search(rf"/{lname}(/|$|\?)", u, re.IGNORECASE) or (lname in u.lower()):
                    return u
            # fallback: try common patterns
            candidate = bill_url + ("?tab=" + lname)
            return candidate

        for tab in tabs:
            tab_url = find_tab_url(tab)
            res = self._fetch_raw(tab_url)
            if not res.get("success"):
                collected["tabs"][tab] = {"success": False, "error": res.get("error"), "url": tab_url}
            else:
                # store html and a short text preview
                collected["tabs"][tab] = {"success": True, "url": res.get("url"), "text": res.get("text"), "html": res.get("html")}

        # derive out_file if not provided — save into VoteData/{MonthYear}/{BillAbbrev}/ at the repo root
        if not out_file:
            repo_root = pathlib.Path(__file__).parents[1]
            vote_data_root = repo_root / "VoteData"
            
            # Extract bill abbreviation from URL (e.g., 'house-bill-498' -> 'HR498')
            bill_abbrev = self._extract_bill_abbrev(bill_url)
            
            # Determine month folder from vote_date if provided (e.g., '01/16/2025' -> 'Jan2025')
            month_folder = None
            if vote_date:
                month_folder = self._parse_month_folder(vote_date)
            
            # Build folder path: VoteData/{MonthYear}/{BillAbbrev}/
            if month_folder and bill_abbrev:
                vote_dir = vote_data_root / month_folder / bill_abbrev
            elif month_folder:
                vote_dir = vote_data_root / month_folder
            elif bill_abbrev:
                vote_dir = vote_data_root / bill_abbrev
            else:
                vote_dir = vote_data_root
            
            try:
                vote_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                # fallback to current working directory if creation fails
                vote_dir = pathlib.Path(os.getcwd())
            
            # sanitize bill_url to filename
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", bill_url)
            out_file = str(vote_dir / f"bill_{safe}.json")

        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(collected, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return {"success": False, "error": f"Failed to write output file: {e}", "path": out_file}

        return {"success": True, "path": out_file, "data": collected}

        # If example tools are available, prefer their `http_request` or `fetch_url` implementation
        if examples_tools is not None:
            try:
                if hasattr(examples_tools, "http_request"):
                    # FunctionTool produced by FastMCP exposes the underlying function at .fn
                    http_req = getattr(examples_tools.http_request, "fn", examples_tools.http_request)
                    hr = http_req(url=url, method="GET", headers=headers, timeout=20)
                    if hr.get("success"):
                        # hr['content'] may be JSON or text
                        html = hr.get("content") if isinstance(hr.get("content"), str) else hr.get("content")
                        # create minimal response-like object
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = hr.get("url", url)
                        resp.text = html if isinstance(html, str) else str(html)
                    else:
                        # fall back to direct session.get
                        resp = session.get(url, timeout=20, headers=headers)
                        resp.raise_for_status()
                elif hasattr(examples_tools, "fetch_url"):
                    fetch_f = getattr(examples_tools.fetch_url, "fn", examples_tools.fetch_url)
                    fr = fetch_f(url=url, timeout=20)
                    if fr.get("success"):
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = fr.get("url", url)
                        resp.text = fr.get("markdown_content", "")
                    else:
                        resp = session.get(url, timeout=20, headers=headers)
                        resp.raise_for_status()
                else:
                    resp = session.get(url, timeout=20, headers=headers)
                    resp.raise_for_status()
            except requests.exceptions.HTTPError as he:
                status = getattr(he.response, "status_code", None)
                if status == 403:
                    # try cloudscraper/playwright below
                    resp = None
                else:
                    return {"success": False, "error": f"HTTP error: {he}", "url": url}
            except Exception as e:
                return {"success": False, "error": str(e), "url": url}
        else:
            try:
                resp = session.get(url, timeout=20, headers=headers)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as he:
                status = getattr(he.response, "status_code", None)
                if status == 403:
                    resp = None
                else:
                    return {"success": False, "error": f"HTTP error: {he}", "url": url}
            except Exception as e:
                return {"success": False, "error": str(e), "url": url}
        # If resp is None here, previous request returned HTTP 403 -> try cloudscraper and Playwright
        if resp is None:
            try:
                import cloudscraper

                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, timeout=30)
                resp.raise_for_status()
            except Exception:
                try:
                    from playwright.sync_api import sync_playwright

                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.goto(url, timeout=30000)
                        html = page.content()
                        class _Resp:
                            pass

                        resp = _Resp()
                        resp.url = page.url or url
                        resp.text = html
                        browser.close()
                except Exception:
                    return {
                        "success": False,
                        "error": (
                            "HTTP 403 Forbidden (cloudscraper failed). "
                            "Install 'cloudscraper' and/or 'playwright' and run 'playwright install chromium' to enable a browser fallback.\n"
                            "Example: python -m pip install cloudscraper playwright && python -m playwright install chromium"
                        ),
                        "url": url,
                    }

        html = resp.text
        self.last_url = resp.url
        self.last_html = html
        self.last_links = []

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else resp.url

        # Extract textual summary: first few paragraphs
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        summary = "\n\n".join(paragraphs[:3])

        # Extract links
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            full = urljoin(self.last_url, href)
            text = a.get_text(strip=True) or full
            if full.startswith("http"):
                self.last_links.append((text, full))

        return {
            "success": True,
            "url": self.last_url,
            "title": title,
            "summary": summary,
            "links_count": len(self.last_links),
        }

    def list_links(self):
        return [(i + 1, text, href) for i, (text, href) in enumerate(self.last_links)]

    def follow(self, index: int):
        if not self.last_links:
            return {"success": False, "error": "No page loaded"}
        if index < 1 or index > len(self.last_links):
            return {"success": False, "error": "Index out of range"}
        _, url = self.last_links[index - 1]
        return self.visit(url)


def interactive_cli():
    agent = WebAgent()
    print("Web Agent CLI — type 'help' for commands")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit"):
            break
        if cmd == "help":
            print("Commands: search <query>, visit <url>, links, follow <n>, quit")
            continue
        if cmd == "search":
            if not arg:
                print("Usage: search <query>")
                continue
            res = agent.search(arg, max_results=8)
            if isinstance(res, dict) and "results" in res:
                for i, r in enumerate(res["results"], 1):
                    print(f"[{i}] {r.get('title')} — {r.get('url')}")
            else:
                print(res)
            continue
        if cmd == "visit":
            if not arg:
                print("Usage: visit <url>")
                continue
            res = agent.visit(arg)
            if not res.get("success"):
                print(f"Error: {res.get('error')}")
                continue
            print(f"Visited: {res['title']}\nURL: {res['url']}\nLinks: {res['links_count']}")
            if res["summary"]:
                print("\nSummary:\n", res["summary"][:1000])
            continue
        if cmd == "fetch_tabs":
            if not arg:
                print("Usage: fetch_tabs <bill_url> [out_file]")
                continue
            parts = arg.split(maxsplit=1)
            bill = parts[0]
            out = parts[1] if len(parts) > 1 else None
            res = agent.fetch_bill_tabs(bill, out_file=out)
            if not res.get("success"):
                print(f"Error: {res.get('error')}")
            else:
                print(f"Saved tabs to: {res.get('path')}")
            continue
        if cmd == "links":
            links = agent.list_links()
            if not links:
                print("No links available. Use 'visit <url>' first.")
                continue
            for i, text, href in links:
                print(f"[{i}] {text} — {href}")
            continue
        if cmd in ("follow", "open"):
            if not arg or not arg.isdigit():
                print("Usage: follow <link-number>")
                continue
            idx = int(arg)
            res = agent.follow(idx)
            if not res.get("success"):
                print(f"Error: {res.get('error')}")
                continue
            print(f"Followed to: {res['title']}\nURL: {res['url']}\nLinks: {res['links_count']}")
            continue

        print("Unknown command. Type 'help'.")


if __name__ == "__main__":
    interactive_cli()
