"""
Planner agent for processing bills by month.

This module orchestrates the full pipeline for all bills in a given month:
1. web_agent_get_bill_data - Fetch bill metadata and tabs
2. web_agent_get_vote_data - Fetch vote records
3. analysis_agent - Analyze bill and generate summary
4. web_agent_visualize_votes - Generate vote visualization
5. social_agent_from_json - Create social media assets

Usage (CLI):
    # Process all bills in a specific month
    python planner_agent.py --month "Jan2025"
    
    # Or process a single bill
    python planner_agent.py --url "https://www.congress.gov/bill/119th-congress/house-bill/498" --date "01/16/2025"

Design goals:
 - Batch process all bills in a month folder
 - Execute full pipeline for each bill
 - Handle errors gracefully and continue processing remaining bills
 - Provide progress updates and final summary
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from customagents.web_agent_get_bill_data import WebAgent
from customagents.web_agent_get_vote_data import VoteAgent
from customagents.web_agent_visualize_votes import VoteVisualizer
from customagents.analysis_agent import AnalysisAgent

import re
from urllib.parse import urljoin


def fetch_votes_for_month(month_year: str) -> List[Dict[str, str]]:
    """Fetch all House votes for a given month/year from Congress.gov.
    
    Args:
        month_year: Month and year like "December 2025" or "Dec2025"
        
    Returns:
        List of dicts with 'vote_url', 'bill_url', 'date', 'description'
    """
    # For December 2025, use known votes from Congress.gov
    # TODO: Replace with actual API call when Congress.gov API is available
    if month_year in ["Dec2025", "December 2025"]:
        print(f"  Using known December 2025 votes...")
        return [
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/362', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/498', 'date': '12/18/2025', 'description': 'H.R.498 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/361', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/498', 'date': '12/18/2025', 'description': 'H.R.498 - On motion to recommit'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/351', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3492', 'date': '12/17/2025', 'description': 'H.R.3492 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/346', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3616', 'date': '12/17/2025', 'description': 'H.R.3616 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/342', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3632', 'date': '12/16/2025', 'description': 'H.R.3632 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/338', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4371', 'date': '12/16/2025', 'description': 'H.R.4371 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/334', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3668', 'date': '12/12/2025', 'description': 'H.R.3668 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/330', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3898', 'date': '12/11/2025', 'description': 'H.R.3898 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/328', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3383', 'date': '12/11/2025', 'description': 'H.R.3383 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/324', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3638', 'date': '12/11/2025', 'description': 'H.R.3638 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/323', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/3628', 'date': '12/11/2025', 'description': 'H.R.3628 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/322', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/2550', 'date': '12/11/2025', 'description': 'H.R.2550 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/320', 'bill_url': 'https://www.congress.gov/bill/119th-congress/senate-bill/1071', 'date': '12/10/2025', 'description': 'S.1071 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/314', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1049', 'date': '12/04/2025', 'description': 'H.R.1049 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/313', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1069', 'date': '12/04/2025', 'description': 'H.R.1069 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/310', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1005', 'date': '12/03/2025', 'description': 'H.R.1005 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/309', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4305', 'date': '12/03/2025', 'description': 'H.R.4305 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/304', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/2965', 'date': '12/03/2025', 'description': 'H.R.2965 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/298', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/1366', 'date': '12/02/2025', 'description': 'H.R.1366 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/288', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/4776', 'date': '12/02/2025', 'description': 'H.R.4776 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/278', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/845', 'date': '12/01/2025', 'description': 'H.R.845 - On passage'},
            {'vote_url': 'https://www.congress.gov/votes/house/119-1/277', 'bill_url': 'https://www.congress.gov/bill/119th-congress/house-bill/6703', 'date': '12/01/2025', 'description': 'H.R.6703 - On passage'},
        ]
    
    # For other months, fall back to web scraping
    # Parse the month_year to get the full month name and year
    month_abbrevs = {
        'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
        'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August',
        'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
    }
    
    # Extract month and year
    if len(month_year) > 3 and month_year[0:3] in month_abbrevs:
        # e.g., "Dec2025"
        month_full = month_abbrevs[month_year[0:3]]
        year = month_year[3:]
    else:
        # Assume full month name, e.g., "December 2025"
        parts = month_year.split()
        month_full = parts[0]
        year = parts[1] if len(parts) > 1 else str(datetime.now().year)
    
    # Fetch the Congress.gov votes page
    from playwright.sync_api import sync_playwright
    
    votes = []
    
    print(f"  Fetching votes from Congress.gov for {month_full} {year}...")
    
    # Map month name to month number
    month_num = str(list(month_abbrevs.values()).index(month_full) + 1).zfill(2)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the House votes page for 119th Congress
        url = "https://www.congress.gov/votes/house/119th-congress/1st-session"
        print(f"  Loading page: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for the vote table to appear
        try:
            page.wait_for_selector('a[href*="/votes/house/119-1/"]', timeout=15000)
            print(f"  Vote links loaded")
        except:
            print(f"  Warning: Vote links did not load in time")
        
        page.wait_for_timeout(2000)  # Additional wait for stability
        
        print(f"  Searching for votes in month {month_num}/{year}...")
        
        # Find all table rows
        vote_rows = page.locator('table tr').all()
        
        print(f"  Found {len(vote_rows)} total rows on page")
        
        for row in vote_rows:
            try:
                # Get all cells in the row
                cells = row.locator('td').all()
                if len(cells) < 4:
                    continue
                
                # Column 0: Vote number
                vote_link = cells[0].locator('a').first
                if vote_link.count() == 0:
                    continue
                vote_url = vote_link.get_attribute('href')
                if not vote_url:
                    continue
                vote_url = urljoin("https://www.congress.gov", vote_url)
                
                # Column 1: Date
                date_text = cells[1].inner_text().strip()
                
                # Check if date matches our target month (e.g., "12/18/2025")
                if not (f"{month_num}/" in date_text and year in date_text):
                    continue
                
                # Column 2: Vote Question
                question_text = cells[2].inner_text().strip()
                
                # Column 3: Description (includes bill link)
                description_cell = cells[3]
                description = description_cell.inner_text().strip()
                
                # Extract bill URL if present
                bill_link = description_cell.locator('a').first
                bill_url = None
                if bill_link.count() > 0:
                    bill_url = bill_link.get_attribute('href')
                    if bill_url:
                        bill_url = urljoin("https://www.congress.gov", bill_url)
                
                # Only include "On Passage" votes
                if "On passage" in question_text or "On Passage" in question_text:
                    votes.append({
                        'vote_url': vote_url,
                        'bill_url': bill_url,
                        'date': date_text,
                        'description': description
                    })
                    print(f"    Added vote: {date_text} - {bill_url}")
            
            except Exception as e:
                print(f"  Warning: Could not parse row: {e}")
                continue
        
        browser.close()
    
    return votes


def process_month(month_folder: str, vote_data_root: Optional[Path] = None) -> Dict[str, Any]:
    """Fetch and process all bills for a given month.
    
    This function:
    1. Fetches all "On Passage" votes for the month from Congress.gov
    2. For each vote, runs the full 4-step pipeline:
       - Step 1: web_agent_get_bill_data (fetch bill metadata)
       - Step 2: web_agent_get_vote_data (fetch vote records)
       - Step 3: web_agent_visualize_votes (generate visualization)
       - Step 4: social_agent_from_json (create social media assets)
    
    Args:
        month_folder: Month folder name (e.g., 'Jan2025', 'Dec2025')
        vote_data_root: Optional path to VoteData root; defaults to repo/VoteData
        
    Returns:
        Dict with processing summary and results
    """
    if vote_data_root is None:
        repo_root = Path(__file__).parents[1]
        vote_data_root = repo_root / 'VoteData'
    
    print(f"\n{'='*70}")
    print(f"FETCHING VOTES FOR: {month_folder}")
    print(f"{'='*70}\n")
    
    # Fetch all votes for this month
    votes = fetch_votes_for_month(month_folder)
    
    if not votes:
        return {
            'success': False,
            'error': f'No votes found for {month_folder}',
            'month': month_folder
        }
    
    print(f"Found {len(votes)} 'On Passage' vote(s)\n")
    print(f"{'='*70}")
    print(f"PROCESSING BILLS")
    print(f"{'='*70}\n")
    
    results = []
    completed = 0
    
    # Create shared agents to reuse browser sessions
    web_agent = WebAgent()
    
    for i, vote_info in enumerate(votes, 1):
        print(f"\n--- Processing vote {i}/{len(votes)} ---")
        print(f"  Bill: {vote_info.get('bill_url', 'Unknown')}")
        print(f"  Date: {vote_info.get('date')}")
        
        bill_result = {
            'vote_url': vote_info.get('vote_url'),
            'bill_url': vote_info.get('bill_url'),
            'date': vote_info.get('date'),
            'steps': {}
        }
        
        try:
            # Step 1: Fetch bill data
            print(f"  1. Fetching bill data...")
            try:
                bill_result_data = web_agent.fetch_bill_tabs(
                    vote_info['bill_url'],
                    vote_date=vote_info['date']
                )
            except Exception as e:
                print(f"  ✗ Bill fetch failed: {e}")
                results.append(bill_result)
                continue
                
            bill_result['steps']['bill_data'] = {
                'success': bill_result_data.get('success', False),
                'path': bill_result_data.get('bill_file')
            }
            if bill_result_data.get('success'):
                print(f"     [OK] Saved to: {bill_result_data.get('bill_file')}")
            else:
                print(f"     ✗ Failed: {bill_result_data.get('error')}")
                results.append(bill_result)
                continue
            
            # Step 2: Fetch vote data
            print(f"  2. Fetching vote data...")
            try:
                vote_agent = VoteAgent()
                # Set the shared web agent's browser for the vote agent
                vote_agent._agent = web_agent
            
                # Extract bill abbreviation from the bill URL directly
                # e.g., "https://www.congress.gov/bill/119th-congress/house-bill/498" -> "HR498"
                bill_abbrev = None
                if vote_info['bill_url']:
                    import re
                    bill_url_match = re.search(r'/(house-bill|senate-bill|house-joint-resolution|senate-joint-resolution|house-concurrent-resolution|senate-concurrent-resolution|house-resolution|senate-resolution)/(\d+)', vote_info['bill_url'])
                    if bill_url_match:
                        bill_type = bill_url_match.group(1)
                        bill_num = bill_url_match.group(2)
                        
                        # Map bill type to abbreviation
                        type_map = {
                            'house-bill': 'HR',
                            'senate-bill': 'S',
                            'house-joint-resolution': 'HJRes',
                            'senate-joint-resolution': 'SJRes',
                            'house-concurrent-resolution': 'HConRes',
                            'senate-concurrent-resolution': 'SConRes',
                            'house-resolution': 'HRes',
                            'senate-resolution': 'SRes'
                        }
                        bill_abbrev = f"{type_map.get(bill_type, 'BILL')}{bill_num}"
                
                vote_result_data = vote_agent.fetch_vote_data(
                    vote_info['vote_url'],
                    vote_date=vote_info['date'],
                    bill_abbrev=bill_abbrev
                )
            except Exception as e:
                print(f"  ✗ Vote fetch failed: {e}")
                results.append(bill_result)
                continue
                
            bill_result['steps']['vote_data'] = {
                'success': vote_result_data.get('success', False),
                'path': vote_result_data.get('path')
            }
            if vote_result_data.get('success'):
                print(f"     ✓ Saved to: {vote_result_data.get('path')}")
            else:
                print(f"     ✗ Failed: {vote_result_data.get('error')}")
                results.append(bill_result)
                continue
            
            # Step 3: Run analysis agent
            print(f"  3. Analyzing bill...")
            try:
                # Get the bill folder path (e.g., VoteData/Dec2025/HR498)
                bill_folder = Path(vote_result_data['path']).parent
                
                analysis_agent = AnalysisAgent()
                analysis_result = analysis_agent.analyze(
                    bill_folder=str(bill_folder),
                    bill_url=vote_info['bill_url'],
                    vote_url=vote_info['vote_url']
                )
                bill_result['steps']['analysis'] = {
                    'success': analysis_result.get('success', False),
                    'path': analysis_result.get('analysis_file')
                }
                if analysis_result.get('success'):
                    print(f"     ✓ Analysis saved to: {analysis_result.get('analysis_file')}")
                else:
                    print(f"     ⚠ Analysis failed: {analysis_result.get('error')}")
            except Exception as e:
                print(f"     ⚠ Analysis error: {e}")
                bill_result['steps']['analysis'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Step 4: Generate visualization
            print(f"  4. Generating visualization...")
            visualizer = VoteVisualizer()
            viz_result = visualizer.visualize(
                vote_json_path=vote_result_data['path'],
                vote_date=vote_info['date'],
                bill_abbrev=bill_abbrev
            )
            bill_result['steps']['visualize'] = {
                'success': viz_result.get('success', False),
                'path': viz_result.get('path')
            }
            if viz_result.get('success'):
                print(f"     ✓ Saved to: {viz_result.get('path')}")
            else:
                print(f"     ✗ Failed")
                results.append(bill_result)
                continue
            
            # Step 5: Generate social media assets
            print(f"  5. Generating social media assets...")
            
            # Find the analysis file
            bill_folder = Path(vote_result_data['path']).parent
            analysis_files = list(bill_folder.glob('analysis_bill_*.json'))
            
            if analysis_files:
                try:
                    sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
                    import social_agent_from_json
                    
                    # Load analysis data
                    with open(analysis_files[0], 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                    
                    out_base = bill_folder / 'social_media'
                    out_base.mkdir(exist_ok=True)
                    
                    title = analysis.get('bill_title', 'Vote')
                    brief = analysis.get('brief_summary', '')
                    
                    social_agent_from_json.make_title_image(title, brief, out_base / '01_title.png')
                    
                    # Copy the visualization
                    viz_files = list(bill_folder.glob('viz_*.png'))
                    if viz_files:
                        import shutil
                        shutil.copy(viz_files[0], out_base / '02_visual.png')
                    
                    bill_result['steps']['social_media'] = {
                        'success': True,
                        'path': str(out_base)
                    }
                    print(f"     ✓ Saved to: {out_base}")
                    completed += 1
                    
                except Exception as e:
                    bill_result['steps']['social_media'] = {
                        'success': False,
                        'error': str(e)
                    }
                    print(f"     ✗ Error: {e}")
            else:
                print(f"     ⚠ No analysis file found")
                bill_result['steps']['social_media'] = {
                    'success': False,
                    'reason': 'no_analysis_file'
                }
        
        except Exception as e:
            print(f"  [FAIL] Error processing bill: {e}")
            bill_result['error'] = str(e)
        
        results.append(bill_result)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY for {month_folder}")
    print(f"{'='*70}")
    print(f"Total votes: {len(votes)}")
    print(f"Completed: {completed}")
    print(f"Failed: {len(votes) - completed}")
    print(f"{'='*70}\n")
    
    if completed > 0:
        print(f"✅ Successfully processed {completed} of {len(votes)} bills")
    else:
        print(f"❌ No bills were successfully processed")
    
    return {
        'success': True,
        'month': month_folder,
        'total': len(votes),
        'completed': completed,
        'results': results
    }


def main():
    parser = argparse.ArgumentParser(description="Planner agent for processing bills")
    parser.add_argument("--month", help="Month folder to process (e.g., 'Jan2025', 'Dec2025')")
    parser.add_argument("--url", help="Single bill URL to process")
    parser.add_argument("--date", help="Vote date for single bill (MM/DD/YYYY format)")
    args = parser.parse_args()
    
    if args.month:
        # Process all bills in the month
        result = process_month(args.month)
        if not result.get('success'):
            print(f"Error: {result.get('error')}")
            sys.exit(1)
    elif args.url:
        # Process single bill (legacy mode)
        print("Single bill processing not yet implemented in new version.")
        print("Use --month to process all bills in a month folder.")
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

