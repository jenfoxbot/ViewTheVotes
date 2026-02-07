"""
Vote data agent — fetches roll-call vote pages and saves structured JSON into VoteData/.

Usage:
  from customagents.web_agent_get_vote_data import VoteAgent
  VoteAgent().fetch_vote_data('<vote_page_url>')

This file reuses the low-level fetcher from `web_agent_get_bill_data` for robust HTTP/playwright fallbacks.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from typing import List, Optional, Dict

from bs4 import BeautifulSoup

from customagents.web_agent_get_bill_data import WebAgent as BaseWebAgent


class VoteAgent:
    def __init__(self):
        self._agent = BaseWebAgent()
        self._browser = None
        self._page = None
        self._playwright = None

    def _sanitize(self, url: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]", "_", url)
    
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
    
    def _fetch_vote_page(self, url: str) -> Dict:
        """Fetch a vote page with Playwright, handling Cloudflare blocks.
        
        For vote pages, Cloudflare blocks are more aggressive. If Playwright
        can't load within 30s or detects Cloudflare, immediately delegate to
        the base agent which has cloudscraper fallback.
        """
        import time
        try:
            page = self._get_browser()
            
            # Add delay to avoid rate limiting
            time.sleep(2)
            
            # Shorter timeout for vote pages (30s vs 45s for bills)
            try:
                page.goto(url, wait_until="load", timeout=30000)
            except Exception as nav_err:
                print(f"  Playwright timeout for {url}, delegating to base agent...")
                return self._agent._fetch_raw(url)
            
            page.wait_for_timeout(2000)  # Brief wait for JS
            
            html = page.content()
            final_url = page.url
            
            # Check if we got a Cloudflare challenge page
            if "Just a moment" in html or "Verifying you are human" in html:
                print(f"  Cloudflare detected for {url}, delegating to base agent...")
                return self._agent._fetch_raw(url)
            
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
            print(f"  Playwright exception: {type(e).__name__} for {url}, trying base agent...")
            return self._agent._fetch_raw(url)

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

    def _extract_member_lists_after_heading(self, heading):
        """Given a heading tag, collect following <ul>/<ol> lists or comma-separated text as member names."""
        members = []
        # Look for immediate list sibling
        sib = heading.find_next_sibling()
        if sib and sib.name in ("ul", "ol"):
            for li in sib.find_all("li"):
                name = li.get_text(" ", strip=True)
                if name:
                    members.append(name)
            return members

        # fallback: gather text until next heading and split commas/newlines
        texts = []
        node = heading.next_sibling
        while node and (not getattr(node, "name", None) or node.name not in ("h2", "h3", "h4")):
            try:
                t = node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node)
            except Exception:
                t = str(node)
            if t:
                texts.append(t)
            node = node.next_sibling

        joined = " ".join(texts)
        # split on semicolon, comma, or newline
        for part in re.split(r"[;\n,]", joined):
            p = part.strip()
            if p:
                members.append(p)
        return members

    def fetch_vote_data(self, vote_url: str, out_file: Optional[str] = None, vote_date: Optional[str] = None, bill_abbrev: Optional[str] = None):
        """Fetch a roll-call vote page, extract summary and individual votes, and save JSON to VoteData/{MonthYear}/{BillAbbrev}/.

        Args:
            vote_url: URL of the vote page to fetch
            out_file: optional path to write JSON; if not provided, derives from vote_url
            vote_date: optional date string in format MM/DD/YYYY to determine output folder (e.g., '01/16/2025' -> 'Jan2025')
            bill_abbrev: optional bill abbreviation (e.g., 'HR498') to determine output folder
            
        Returns dict {success, path, data} or {success: False, error: ...}
        """
        # Use the specialized vote page fetcher
        base = self._fetch_vote_page(vote_url)
        if not base.get("success"):
            return {"success": False, "error": f"Failed to fetch vote page: {base.get('error')}", "url": vote_url}

        html = base.get("html", "")
        page_url = base.get("url", vote_url)
        soup = BeautifulSoup(html, "html.parser")

        collected = {"vote_url": page_url, "title": None, "summary": None, "counts": {}, "members": {}, "tables": []}

        # Title
        try:
            collected["title"] = soup.title.string.strip() if soup.title and soup.title.string else page_url
        except Exception:
            collected["title"] = page_url

        # Summary: first few paragraphs under main content
        try:
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
            collected["summary"] = "\n\n".join(paragraphs[:4])
        except Exception:
            collected["summary"] = None

        # Try to extract counts (Yea/Nay/Present/Not Voting) from page text
        text = soup.get_text("\n", strip=True)
        # look for patterns like 'Yea: 215 — Nay: 201 — Not Voting: 0'
        m = re.search(r"Yea[:\s]+(\d+).*?Nay[:\s]+(\d+)", text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                collected["counts"]["yea"] = int(m.group(1))
                collected["counts"]["nay"] = int(m.group(2))
            except Exception:
                pass

        # Extract member lists grouped by headings (Yea/Nay/Not Voting/Present)
        members = {"Yea": [], "Nay": [], "Not Voting": [], "Present": []}
        for h in soup.find_all(["h2", "h3", "h4"]):
            txt = h.get_text(" ", strip=True).lower()
            if "yea" in txt or "yeas" in txt:
                names = self._extract_member_lists_after_heading(h)
                members["Yea"].extend(names)
            elif "nay" in txt or "nays" in txt:
                names = self._extract_member_lists_after_heading(h)
                members["Nay"].extend(names)
            elif "not voting" in txt or "not voting" in txt:
                names = self._extract_member_lists_after_heading(h)
                members["Not Voting"].extend(names)
            elif "present" in txt:
                names = self._extract_member_lists_after_heading(h)
                members["Present"].extend(names)

        # Normalize empty lists
        for k, v in members.items():
            if v:
                collected["members"][k] = v

        # Try to parse structured tables of individual votes
        for table in soup.find_all("table"):
            # collect headers
            headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td"]) ]
                if cells:
                    if headers and len(headers) == len(cells):
                        row = dict(zip(headers, cells))
                    else:
                        # fallback: use numeric keys
                        row = {str(i): c for i, c in enumerate(cells)}
                    rows.append(row)
            if rows:
                collected["tables"].append({"headers": headers, "rows": rows})

        # derive out_file in VoteData/{MonthYear}/{BillAbbrev}/
        if not out_file:
            repo_root = pathlib.Path(__file__).parents[1]
            vote_data_root = repo_root / "VoteData"
            
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
                vote_dir = pathlib.Path(os.getcwd())
            
            safe = self._sanitize(vote_url)
            out_file = str(vote_dir / f"vote_{safe}.json")

        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(collected, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return {"success": False, "error": f"Failed to write vote output: {e}", "path": out_file}

        return {"success": True, "path": out_file, "data": collected}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python web_agent_get_vote_data.py <vote_page_url>")
        sys.exit(1)
    url = sys.argv[1]
    va = VoteAgent()
    res = va.fetch_vote_data(url)
    print(res)
