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
from typing import List, Optional

from bs4 import BeautifulSoup

from customagents.web_agent_get_bill_data import WebAgent as BaseWebAgent


class VoteAgent:
    def __init__(self):
        self._agent = BaseWebAgent()

    def _sanitize(self, url: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]", "_", url)

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

    def fetch_vote_data(self, vote_url: str, out_file: Optional[str] = None):
        """Fetch a roll-call vote page, extract summary and individual votes, and save JSON to VoteData/.

        Returns dict {success, path, data} or {success: False, error: ...}
        """
        base = self._agent._fetch_raw(vote_url)
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

        # derive out_file in VoteData
        if not out_file:
            safe = self._sanitize(vote_url)
            repo_root = pathlib.Path(__file__).parents[1]
            vote_dir = repo_root / "VoteData"
            try:
                vote_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                vote_dir = pathlib.Path(os.getcwd())
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
