"""Critical-thinking / analysis agent for bill JSON outputs.

Reads a bill JSON file produced by `web_agent_get_bill_data`, extracts facts,
briefly summarizes the bill (2-3 simple sentences), identifies likely pros
and cons (including potential harms and impacts on real people), and writes
an analysis JSON into `VoteData/` beside the input file.

Usage:
  from customagents.analysis_agent import AnalysisAgent
  AnalysisAgent().analyze('VoteData/bill_...498.json')
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from typing import Dict, List, Optional


class AnalysisAgent:
    def __init__(self):
        pass

    def _read_json(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_date(self, text: str) -> Optional[str]:
        # Look for MM/DD/YYYY
        m = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text)
        if m:
            return m.group(0)
        # Look for Month DD, YYYY
        m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", text)
        if m:
            return m.group(0)
        return None

    def _extract_bill_description(self, text: str, title: str, max_sentences: int = 2) -> str:
        """Try to extract a concise, human-friendly description of what the bill does.

        Heuristics (in order):
        - Sentences that contain action verbs (prohibit, restrict, require, authorize, provide, etc.)
        - Sentences that start with or contain 'This bill' / 'The bill' / 'H.R.'
        - First non-boilerplate sentences found on the page
        - Fallback to a short form of the title
        """
        s = re.sub(r"\s+", " ", (text or "")).strip()
        if not s:
            return self._short_sentences(title, max_sentences=1)

        # Remove obvious site boilerplate fragments
        blacklist = ("skip to main content", "navigation", "advanced searches", "browse", "help", "contact", "examples:")
        sentences = [seg.strip() for seg in re.split(r'(?<=[.!?])\s+', s) if seg.strip()]
        filtered = [sent for sent in sentences if not any(b in sent.lower() for b in blacklist)]

        verbs_pattern = r"\b(prohibit|prohibits|ban|bans|prevent|prevents|restrict|restricts|require|requires|authorize|authorizes|allow|allows|establish|establishes|provide|provides|amend|amends|medicaid payment)\b"
        action_sents = [sent for sent in filtered if re.search(verbs_pattern, sent, re.IGNORECASE)]
        if action_sents:
            return " ".join(action_sents[:max_sentences])

        key_sents = [sent for sent in filtered if re.search(r"\b(This bill|The bill|This resolution|H\.R\.|S\.)", sent, re.IGNORECASE)]
        if key_sents:
            return " ".join(key_sents[:max_sentences])

        if filtered:
            return " ".join(filtered[:max_sentences])

        return self._short_sentences(title, max_sentences=1)

    def _short_sentences(self, text: str, max_sentences: int = 2) -> str:
        # Normalize whitespace
        s = re.sub(r"\s+", " ", (text or "")).strip()
        if not s:
            return ""
        parts = re.split(r'(?<=[.!?])\s+', s)
        chosen = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # keep sentence simple by truncating to ~25 words
            words = p.split()
            if len(words) > 28:
                p = " ".join(words[:28]) + "..."
            chosen.append(p)
            if len(chosen) >= max_sentences:
                break
        return " ".join(chosen)

    def _derive_pros_cons(self, text: str) -> (List[str], List[str]):
        t = (text or "").lower()
        pros: List[str] = []
        cons: List[str] = []

        # Heuristic pro statements (what supporters might argue)
        if any(k in t for k in ("prohibit", "ban", "prevent", "restrict")):
            pros.append("May be intended to protect minors by restricting federal coverage of certain procedures.")
        if "parent" in t or "guardian" in t:
            pros.append("Includes exceptions referencing parental or guardian involvement, which supporters may see as protective.")
        if "cost" in t or "medicaid" in t:
            pros.append("Could reduce federal Medicaid expenditures for the specified services.")

        # Heuristic con statements (potential harms / impacts)
        if any(k in t for k in ("gender", "transition", "transgender", "gender-affirming")):
            cons.append("Targets gender-related healthcare and may stigmatize or reduce access for transgender youth.")
        if any(k in t for k in ("limit", "restrict", "deny", "prevent", "ban")):
            cons.append("May restrict access to medically recommended care and impose financial or health burdens on families.")
        if any(k in t for k in ("mental health", "harm", "suicide", "depress")):
            cons.append("Could increase mental health risks for affected individuals if care is delayed or denied.")
        if not cons and not pros:
            # fallback neutral observations
            if len(t) > 200:
                pros.append("Contains policy changes that affect coverage and clinical practice.")
                cons.append("Could have unintended impacts on people who rely on covered services.")
        return pros, cons

    def analyze(self, bill_json_path: str, out_path: Optional[str] = None) -> Dict:
        """Analyze a bill JSON file and return analysis dict; also write to VoteData/.

        Output structure:
          { bill_title, date_of_vote, brief_summary, pros, cons, path }
        """
        data = self._read_json(bill_json_path)

        # Title
        title = data.get("title") or data.get("data", {}).get("title") or ""

        # Combine available text to search for dates and context
        combined_text = ""
        # Look into top-level tabs
        tabs = data.get("tabs") or {}
        if isinstance(tabs, dict):
            for v in tabs.values():
                if isinstance(v, dict):
                    combined_text += "\n" + (v.get("text") or v.get("html") or "")
        # Also try to capture any top-level text
        if "text" in data:
            combined_text += "\n" + (data.get("text") or "")

        date_of_vote = self._find_date(combined_text) or None

        # Brief summary: prefer summary tab
        brief_source = ""
        if isinstance(tabs, dict) and "summary" in tabs and isinstance(tabs["summary"], dict):
            brief_source = tabs["summary"].get("text") or tabs["summary"].get("html") or ""
        # fallback to top-level description in JSON
        if not brief_source:
            # try to pick short paragraphs from combined_text
            brief_source = combined_text

        brief = self._extract_bill_description(brief_source, title, max_sentences=2)
        if not brief:
            brief = self._short_sentences(title, max_sentences=1)

        pros, cons = self._derive_pros_cons(brief_source + "\n" + title)

        analysis = {
            "bill_title": title,
            "date_of_vote": date_of_vote,
            "brief_summary": brief,
            "pros": pros,
            "cons": cons,
        }

        # prepare out path
        if not out_path:
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", os.path.basename(bill_json_path))
            repo_root = pathlib.Path(__file__).parents[1]
            vote_dir = repo_root / "VoteData"
            try:
                vote_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                vote_dir = pathlib.Path(os.getcwd())
            out_path = str(vote_dir / f"analysis_{safe}")
            if not out_path.lower().endswith(".json"):
                out_path = out_path + ".json"

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return {"success": False, "error": f"Failed to write analysis file: {e}", "path": out_path}

        result = {"success": True, "path": out_path, "analysis": analysis}
        return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python customagents/analysis_agent.py <path-to-bill-json>")
        sys.exit(1)
    path = sys.argv[1]
    agent = AnalysisAgent()
    res = agent.analyze(path)
    print(res)
