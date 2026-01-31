"""
Planner agent for fetching public-record voting data for a single bill.

This module lives in `customagents` and produces a clear, step-by-step plan
(natural language + structured tasks) for an execution agent (the Web Agent)
that knows how to visit pages, click links, and extract content.

Usage (CLI):
    python planner_agent.py --url "https://www.congress.gov/bill/119th-congress/house-bill/498"

Outputs:
 - Printed human-readable plan
 - JSON structured plan (printed) containing a sequence of web-agent tasks
   and handoff payload schemas for the Critical Thinking and Visualization agents.

Design goals:
 - Generic for a single bill; supports bill page -> votes index -> individual vote details
 - Produces explicit selectors/intent (e.g. "click left nav link text 'Votes' or follow href containing '/votes/'")
 - Includes data schema for extracted items: bill metadata, page summary, vote records
 - Includes error handling and retry suggestions
"""
from __future__ import annotations

import argparse
import json
from typing import Dict, List, Any


def build_plan_for_bill(bill_url: str) -> Dict[str, Any]:
    """Return a structured plan (and human-readable steps) for a single bill.

    The plan is generic: it instructs the Web Agent to fetch the bill page,
    extract metadata and summary, find the votes link in the left navigation,
    visit the votes index page, extract the top-level summary and the list of
    individual votes (with names, party, state, and vote), then produce a
    handoff payload to the Critical Thinking agent and the Visualization agent.
    """

    # Schema definitions
    bill_schema = {
        "bill_url": bill_url,
        "fields": [
            "bill_number",
            "congress",
            "title",
            "sponsor",
            "latest_action",
            "official_summary",
            "full_text_url",
            "votes_index_url",
        ],
    }

    vote_record_schema = {
        "fields": ["vote_id", "vote_date", "chamber", "vote_type", "result", "description"],
        "member_record": ["name", "party", "state", "vote"],
    }

    # High-level human steps
    human_steps = [
        "Identify the target bill page (provided URL).",
        "Visit the bill page and extract: bill title, bill number, congress session, sponsor(s), official summary/description, and any full-text or summary links.",
        "From the bill page, locate the left-hand navigation link for 'Votes' (or any href containing '/votes/' or link text containing 'Votes').",
        "Visit the votes index page for that bill. Extract the top summary located at the top of the votes page (one-paragraph summary).",
        "From the votes index page, identify each individual vote entry and extract per-vote metadata: vote id/number, date, chamber, roll-call URL (link to detailed breakdown), vote type, description, and result.",
        "For each individual vote roll-call URL: visit the page and extract the roll-call table with member-level results (name, party, state, vote). Normalize member names and party/state fields.",
        "Validate and normalize extracted data (consistent date format, chamber names, canonical party abbreviations 'D', 'R', 'I').",
        "Prepare handoff payloads: (a) send bill metadata + page summary + per-vote metadata to the Critical Thinking agent for analysis; (b) send the selected vote's member-level records to the Visualization agent to render a simple visual (e.g., stacked bar or dot grid).",
        "If any page fails to load or expected selectors are missing, retry up to 2 times, and log the failure with the target URL and HTTP status or parsing error.",
    ]

    # Structured web-agent tasks (ordered)
    tasks: List[Dict[str, Any]] = []

    # Task 1: Fetch bill page
    tasks.append({
        "id": "fetch_bill_page",
        "action": "visit",
        "target": bill_url,
        "notes": [
            "Return final URL after redirects",
            "Extract page title and canonical meta tags",
            "Extract main summary: first 2-4 paragraphs or the element with id/class containing 'summary' or 'description'",
            "Collect any links to full text or 'Related bill' pages",
        ],
        "output": {
            "page_url": "string",
            "title": "string",
            "summary_html": "html/string",
            "summary_text": "string",
            "candidate_votes_index_hints": ["hrefs containing '/votes/'", "nav link text 'Votes'"] ,
        },
    })

    # Task 2: Locate votes index link
    tasks.append({
        "id": "locate_votes_index",
        "action": "find_link",
        "from_task": "fetch_bill_page",
        "intent": "Find a left-nav link labeled 'Votes' or any link whose href contains '/votes/' or '/roll-call/'",
        "selectors_suggestions": [
            "left navigation area: look for <nav> or elements with class containing 'left' or 'toc'",
            "anchor text contains 'Votes' (case-insensitive)",
            "href contains '/votes/'",
        ],
        "output": {"votes_index_url": "string"},
    })

    # Task 3: Fetch votes index
    tasks.append({
        "id": "fetch_votes_index",
        "action": "visit",
        "from_task": "locate_votes_index",
        "target": "{{votes_index_url}}",
        "notes": [
            "Extract summary paragraph(s) at top of page",
            "Extract the list of vote entries with per-vote metadata and roll-call links",
        ],
        "output": {
            "votes_summary": "string",
            "votes": [
                {
                    "vote_id": "string",
                    "date": "ISO8601 string",
                    "chamber": "string (House/Senate)",
                    "vote_type": "string",
                    "result": "string (Pass/Fail)",
                    "description": "string",
                    "roll_call_url": "string",
                }
            ],
        },
    })

    # Task 4: For each vote, fetch roll-call detail and extract member-level results
    tasks.append({
        "id": "fetch_roll_calls",
        "action": "map",
        "from_task": "fetch_votes_index",
        "for_each": "votes",
        "subtask": {
            "action": "visit",
            "target": "{{roll_call_url}}",
            "notes": [
                "Extract page header summary (top-of-page description)",
                "Find the roll-call table or list with member names, party, state, and vote choice",
                "Prefer structured tables (<table>) otherwise parse lists or preformatted text",
            ],
            "output": {
                "vote_id": "string",
                "roll_call_summary": "string",
                "member_votes": [
                    {"name": "string", "party": "string", "state": "string", "vote": "string"}
                ],
            },
        },
    })

    # Task 5: Normalize and validate data
    tasks.append({
        "id": "normalize_validate",
        "action": "process",
        "from_task": "fetch_roll_calls",
        "notes": [
            "Normalize date formats to ISO-8601",
            "Canonicalize party to one-letter codes (D, R, I)",
            "Normalize state to two-letter code",
            "Trim and canonicalize member names (Lastname, Firstname) if possible",
            "Verify that each vote has at least one member record; flag if empty",
        ],
        "output": {"normalized_votes": "array of vote_record_schema"},
    })

    # Handoff payloads
    handoffs = {
        "critical_thinking_agent": {
            "purpose": "Analyze bill and vote context; produce concise natural-language summary and highlight key takeaways.",
            "input": [
                "bill_metadata (from fetch_bill_page)",
                "bill_summary (fetch_bill_page.summary_text)",
                "per_vote_metadata (fetch_votes_index.votes)",
                "selected_roll_call_details (fetch_roll_calls.member_votes for the vote of interest)",
            ],
            "expected_output": [
                "short_summary: 2-3 sentences",
                "key_points: bullet list",
                "potential biases or notable patterns in voting",
            ],
        },
        "visualization_agent": {
            "purpose": "Create a simple visual (PNG/SVG) showing vote breakdown for a chosen vote.",
            "input": ["normalized member-level vote records (name, party, state, vote)", "metadata: vote_id, date, chamber"],
            "visual_spec": "stacked bar by party (Yes/No/Other) or grid of dots colored by party and shaped by vote",
            "expected_output": ["image_url_or_base64", "small legend and caption text"],
        },
    }

    # Guidance for web-agent implementer / selectors
    selector_guidance = [
        "Prefer semantic selectors: look for id/class that contains 'summary', 'overview', or 'bill-summary'.",
        "Left navigation often uses <nav>, <aside>, or elements with class 'left' or 'toc' — search these first for 'Votes'.",
        "Roll-call detail pages usually have a <table> with headers like 'Member', 'Vote' or 'State'. Prefer parsing <table> rows for reliability.",
        "If content is dynamically generated (JS), consider using an environment that can render JS or an alternate API (Congress.gov provides structured APIs in some cases).",
        "Always return the final URL after redirects so references are stable.",
    ]

    # Retry and error policy
    error_policy = {
        "retries": 2,
        "backoff_seconds": [2, 5],
        "on_failure": "log and continue with remaining votes; mark missing data in handoff payload",
    }

    plan = {
        "human_readable_steps": human_steps,
        "web_agent_tasks": tasks,
        "handoffs": handoffs,
        "schemas": {"bill": bill_schema, "vote_record": vote_record_schema},
        "selector_guidance": selector_guidance,
        "error_policy": error_policy,
    }

    return plan


def pretty_print_plan(plan: Dict[str, Any]):
    print("High-level plan (human-readable):\n")
    for i, s in enumerate(plan["human_readable_steps"], 1):
        print(f"{i}. {s}")

    print("\nWeb-agent task sequence (summaries):\n")
    for t in plan["web_agent_tasks"]:
        print(f"- {t['id']}: {t.get('action')} -> target: {t.get('target', t.get('from_task','<derived>'))}")

    print("\nHandoffs:\n")
    for k, v in plan["handoffs"].items():
        print(f"- {k}: {v['purpose']}")

    print("\nSchemas:\n")
    print(json.dumps(plan["schemas"], indent=2))


def main():
    parser = argparse.ArgumentParser(description="Planner agent for fetching bill votes")
    parser.add_argument("--url", required=True, help="Bill page URL (e.g. congress.gov bill URL)")
    args = parser.parse_args()

    plan = build_plan_for_bill(args.url)
    pretty_print_plan(plan)
    print("\nStructured plan (JSON):\n")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
