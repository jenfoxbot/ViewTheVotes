# VoteData Folder Structure Update

## Overview

The `web_agent_get_bill_data.py` and `web_agent_get_vote_data.py` agents now organize their outputs into a hierarchical folder structure within `/VoteData`:

```
VoteData/
├── {MonthYear}/        # e.g., "Jan2025", "Dec2025"
│   └── {BillAbbrev}/   # e.g., "HR498", "S123"
│       ├── bill_*.json
│       └── vote_*.json
```

## Examples

### Single Bill
For H.R.498 voted on January 16, 2025:
```
VoteData/Jan2025/HR498/
├── bill_https___www_congress_gov_bill_119th-congress_house-bill_498.json
└── vote_https___www_congress_gov_index_php_votes_house_119-1_362.json
```

### Multiple Bills in Same Month
```
VoteData/Jan2025/
├── HR498/
│   ├── bill_*.json
│   └── vote_*.json
├── HR123/
│   ├── bill_*.json
│   └── vote_*.json
└── S456/
    ├── bill_*.json
    └── vote_*.json
```

## Bill Abbreviation Mapping

| Bill Type | Abbreviation | Example URL | Output Folder |
|-----------|-------------|-------------|---------------|
| House Bill | `HR{num}` | `.../house-bill/498` | `HR498` |
| Senate Bill | `S{num}` | `.../senate-bill/123` | `S123` |
| House Joint Resolution | `HJRes{num}` | `.../house-joint-resolution/42` | `HJRes42` |
| Senate Joint Resolution | `SJRes{num}` | `.../senate-joint-resolution/15` | `SJRes15` |
| House Concurrent Resolution | `HConRes{num}` | `.../house-concurrent-resolution/10` | `HConRes10` |
| Senate Concurrent Resolution | `SConRes{num}` | `.../senate-concurrent-resolution/20` | `SConRes20` |
| House Resolution | `HRes{num}` | `.../house-resolution/99` | `HRes99` |
| Senate Resolution | `SRes{num}` | `.../senate-resolution/88` | `SRes88` |

## Month Format

Date strings in `MM/DD/YYYY` format are converted to abbreviated month folders:

| Date | Output Folder |
|------|---------------|
| `01/16/2025` | `Jan2025` |
| `12/15/2025` | `Dec2025` |
| `07/04/2025` | `Jul2025` |

## Usage

### WebAgent (Bill Data)

```python
from customagents.web_agent_get_bill_data import WebAgent

agent = WebAgent()

# Fetch bill data with automatic folder organization
result = agent.fetch_bill_tabs(
    bill_url="https://www.congress.gov/bill/119th-congress/house-bill/498",
    vote_date="01/16/2025"  # Optional: creates Jan2025/HR498/ folder
)

# Output: VoteData/Jan2025/HR498/bill_*.json
```

### VoteAgent (Vote Data)

```python
from customagents.web_agent_get_vote_data import VoteAgent

vote_agent = VoteAgent()

# Fetch vote data with automatic folder organization
result = vote_agent.fetch_vote_data(
    vote_url="https://www.congress.gov/index.php?votes/house/119-1/362",
    vote_date="01/16/2025",  # Optional: creates Jan2025/ folder
    bill_abbrev="HR498"      # Optional: creates HR498/ subfolder
)

# Output: VoteData/Jan2025/HR498/vote_*.json
```

## Backward Compatibility

The agents remain backward compatible:

- If `vote_date` is not provided, files go directly into `VoteData/`
- If `bill_abbrev` is not provided (or cannot be extracted), files go into `VoteData/{MonthYear}/`
- If neither is provided, behavior is unchanged: files go into `VoteData/`

## Testing

Run the folder structure tests:

```bash
# Run all folder structure tests
python -m pytest tests/test_bill_folder_structure.py -v

# Run integration tests
python -m pytest tests/test_folder_integration.py -v

# Run all web agent tests
python -m pytest tests/ -k "web_agent or folder" -v
```

All tests pass successfully! ✅

## Migration Notes

Existing files in `VoteData/` (without subfolders) will continue to work. The new structure only applies to newly fetched data when the optional `vote_date` parameter is provided.

To migrate existing data:
1. Manually move files into appropriate `{MonthYear}/{BillAbbrev}/` folders
2. Or re-fetch the data with the `vote_date` parameter specified
