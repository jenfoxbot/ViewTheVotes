"""Test that web_agent_get_bill_data creates proper folder structure."""
import pytest
from pathlib import Path
import shutil
import sys

# Add customagents to path
sys.path.insert(0, str(Path(__file__).parents[1] / "customagents"))

from web_agent_get_bill_data import WebAgent


def test_folder_structure_with_date():
    """Test that bill data is saved to VoteData/{MonthYear}/{BillAbbrev}/ structure."""
    agent = WebAgent()
    
    # Test URL parsing helpers
    bill_url = "https://www.congress.gov/bill/119th-congress/house-bill/498"
    
    # Test bill abbreviation extraction
    abbrev = agent._extract_bill_abbrev(bill_url)
    assert abbrev == "HR498", f"Expected 'HR498', got '{abbrev}'"
    
    # Test month folder parsing
    vote_date = "01/16/2025"
    month_folder = agent._parse_month_folder(vote_date)
    assert month_folder == "Jan2025", f"Expected 'Jan2025', got '{month_folder}'"
    
    # Test Senate bill
    senate_url = "https://www.congress.gov/bill/119th-congress/senate-bill/123"
    s_abbrev = agent._extract_bill_abbrev(senate_url)
    assert s_abbrev == "S123", f"Expected 'S123', got '{s_abbrev}'"
    
    # Test December date
    dec_date = "12/15/2025"
    dec_folder = agent._parse_month_folder(dec_date)
    assert dec_folder == "Dec2025", f"Expected 'Dec2025', got '{dec_folder}'"
    
    print("✓ All folder structure tests passed")


def test_folder_structure_edge_cases():
    """Test edge cases for folder structure parsing."""
    agent = WebAgent()
    
    # Test invalid date
    invalid_date = "not-a-date"
    result = agent._parse_month_folder(invalid_date)
    assert result is None, f"Expected None for invalid date, got '{result}'"
    
    # Test invalid URL
    invalid_url = "https://example.com/not-a-bill"
    result = agent._extract_bill_abbrev(invalid_url)
    assert result is None, f"Expected None for invalid URL, got '{result}'"
    
    # Test joint resolution
    hjres_url = "https://www.congress.gov/bill/119th-congress/house-joint-resolution/42"
    hjres = agent._extract_bill_abbrev(hjres_url)
    assert hjres == "HJRes42", f"Expected 'HJRes42', got '{hjres}'"
    
    print("✓ All edge case tests passed")


if __name__ == "__main__":
    test_folder_structure_with_date()
    test_folder_structure_edge_cases()
    print("\n✅ All tests passed!")
