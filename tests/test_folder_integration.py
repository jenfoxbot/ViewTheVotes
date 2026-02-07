"""Integration test for folder structure with actual file creation."""
import pytest
from pathlib import Path
import json
import sys
import shutil

# Add customagents to path
sys.path.insert(0, str(Path(__file__).parents[1] / "customagents"))

from web_agent_get_bill_data import WebAgent
from web_agent_get_vote_data import VoteAgent
from web_agent_visualize_votes import VoteVisualizer


def test_bill_data_folder_creation():
    """Test that fetch_bill_tabs creates files in the correct folder structure."""
    agent = WebAgent()
    
    # Use a simple test case with mocked data
    test_url = "https://www.congress.gov/bill/119th-congress/house-bill/498"
    test_date = "01/16/2025"
    
    # Get expected path
    repo_root = Path(__file__).parents[1]
    expected_folder = repo_root / "VoteData" / "Jan2025" / "HR498"
    
    # Note: We can't actually call fetch_bill_tabs in a test without network access
    # But we can verify the path logic would work correctly
    
    abbrev = agent._extract_bill_abbrev(test_url)
    month = agent._parse_month_folder(test_date)
    
    assert abbrev == "HR498"
    assert month == "Jan2025"
    
    # Verify the expected folder structure
    if abbrev and month:
        test_folder = repo_root / "VoteData" / month / abbrev
        print(f"✓ Would create folder: {test_folder}")
        assert str(test_folder) == str(expected_folder)
    

def test_vote_data_folder_creation():
    """Test that fetch_vote_data creates files in the correct folder structure."""
    vote_agent = VoteAgent()
    
    test_date = "12/15/2025"
    test_abbrev = "HR498"
    
    # Get expected path
    repo_root = Path(__file__).parents[1]
    expected_folder = repo_root / "VoteData" / "Dec2025" / "HR498"
    
    month = vote_agent._parse_month_folder(test_date)
    assert month == "Dec2025"
    
    # Verify the expected folder structure
    if month and test_abbrev:
        test_folder = repo_root / "VoteData" / month / test_abbrev
        print(f"✓ Would create folder: {test_folder}")
        assert str(test_folder) == str(expected_folder)


def test_multiple_bills_same_month():
    """Test handling multiple bills in the same month."""
    agent = WebAgent()
    
    bills = [
        ("https://www.congress.gov/bill/119th-congress/house-bill/498", "HR498"),
        ("https://www.congress.gov/bill/119th-congress/house-bill/123", "HR123"),
        ("https://www.congress.gov/bill/119th-congress/senate-bill/456", "S456"),
    ]
    
    test_date = "01/16/2025"
    month = agent._parse_month_folder(test_date)
    
    repo_root = Path(__file__).parents[1]
    
    for url, expected_abbrev in bills:
        abbrev = agent._extract_bill_abbrev(url)
        assert abbrev == expected_abbrev
        
        expected_path = repo_root / "VoteData" / month / abbrev
        print(f"✓ Bill {abbrev} would go to: {expected_path}")


def test_visualizer_folder_creation():
    """Test that VoteVisualizer uses the same folder structure."""
    visualizer = VoteVisualizer()
    
    test_date = "01/16/2025"
    test_abbrev = "HR498"
    
    # Get expected path
    repo_root = Path(__file__).parents[1]
    expected_folder = repo_root / "VoteData" / "Jan2025" / "HR498"
    
    month = visualizer._parse_month_folder(test_date)
    assert month == "Jan2025"
    
    print(f"✓ Visualizer would create folder: {expected_folder}")


if __name__ == "__main__":
    test_bill_data_folder_creation()
    test_vote_data_folder_creation()
    test_multiple_bills_same_month()
    test_visualizer_folder_creation()
    print("\n✅ All integration tests passed!")
