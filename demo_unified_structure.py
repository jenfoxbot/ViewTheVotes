"""
Demonstration of unified folder structure across all web agents.

All three agents (bill data, vote data, and visualizer) now use the same
folder structure: /VoteData/{MonthYear}/{BillAbbrev}/

Example usage:
    python demo_unified_structure.py
"""
from pathlib import Path
import sys

# Add customagents to path
sys.path.insert(0, str(Path(__file__).parent / "customagents"))

from web_agent_get_bill_data import WebAgent
from web_agent_get_vote_data import VoteAgent
from web_agent_visualize_votes import VoteVisualizer


def demo_unified_structure():
    """Demonstrate that all agents use the same folder structure."""
    
    # Example data
    bill_url = "https://www.congress.gov/bill/119th-congress/house-bill/498"
    vote_url = "https://www.congress.gov/index.php?votes/house/119-1/362"
    vote_date = "01/16/2025"
    
    # Initialize agents
    bill_agent = WebAgent()
    vote_agent = VoteAgent()
    visualizer = VoteVisualizer()
    
    # Extract common metadata
    bill_abbrev = bill_agent._extract_bill_abbrev(bill_url)
    month_folder = bill_agent._parse_month_folder(vote_date)
    
    print("=" * 70)
    print("UNIFIED FOLDER STRUCTURE DEMONSTRATION")
    print("=" * 70)
    print()
    print(f"Bill URL: {bill_url}")
    print(f"Vote URL: {vote_url}")
    print(f"Vote Date: {vote_date}")
    print()
    print(f"Extracted Bill Abbreviation: {bill_abbrev}")
    print(f"Extracted Month Folder: {month_folder}")
    print()
    
    # Show where each agent would save its output
    repo_root = Path(__file__).parent
    base_folder = repo_root / "VoteData" / month_folder / bill_abbrev
    
    print("ALL AGENTS SAVE TO THE SAME FOLDER:")
    print(f"  {base_folder}")
    print()
    
    print("FILE ORGANIZATION:")
    print(f"  ├─ bill_*.json           (from web_agent_get_bill_data)")
    print(f"  ├─ vote_*.json           (from web_agent_get_vote_data)")
    print(f"  └─ viz_vote_*.png        (from web_agent_visualize_votes)")
    print()
    
    print("EXAMPLE USAGE:")
    print()
    
    print("1. Fetch Bill Data:")
    print(f"   agent = WebAgent()")
    print(f"   agent.fetch_bill_tabs(")
    print(f"       bill_url='{bill_url}',")
    print(f"       vote_date='{vote_date}'")
    print(f"   )")
    print(f"   → Saves to: VoteData/{month_folder}/{bill_abbrev}/bill_*.json")
    print()
    
    print("2. Fetch Vote Data:")
    print(f"   vote_agent = VoteAgent()")
    print(f"   vote_agent.fetch_vote_data(")
    print(f"       vote_url='{vote_url}',")
    print(f"       vote_date='{vote_date}',")
    print(f"       bill_abbrev='{bill_abbrev}'")
    print(f"   )")
    print(f"   → Saves to: VoteData/{month_folder}/{bill_abbrev}/vote_*.json")
    print()
    
    print("3. Generate Visualization:")
    print(f"   visualizer = VoteVisualizer()")
    print(f"   visualizer.visualize(")
    print(f"       vote_json_path='VoteData/{month_folder}/{bill_abbrev}/vote_*.json',")
    print(f"       vote_date='{vote_date}',")
    print(f"       bill_abbrev='{bill_abbrev}'")
    print(f"   )")
    print(f"   → Saves to: VoteData/{month_folder}/{bill_abbrev}/viz_vote_*.png")
    print()
    
    print("=" * 70)
    print("BENEFITS:")
    print("  ✓ All related files in one folder")
    print("  ✓ Easy to find by month and bill")
    print("  ✓ Clean organization for social media workflows")
    print("  ✓ Backward compatible (works without date/abbrev too)")
    print("=" * 70)


if __name__ == "__main__":
    demo_unified_structure()
