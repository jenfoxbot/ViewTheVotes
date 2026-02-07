#!/usr/bin/env python
"""Regenerate all 01_title.png files with updated title cleanup."""
from pathlib import Path
import sys
import json

sys.path.insert(0, 'scripts')
import social_agent_from_json

bills_processed = 0
bills_failed = 0

# Find all bill folders in Dec2025
base = Path('VoteData/Dec2025')
for bill_folder in sorted(base.iterdir()):
    if not bill_folder.is_dir():
        continue
    
    bill_name = bill_folder.name
    print(f'Processing {bill_name}...', end=' ')
    
    try:
        # Load analysis data
        analysis_files = list(bill_folder.glob('analysis_*.json'))
        if not analysis_files:
            print('SKIPPED (no analysis file)')
            continue
        
        with open(analysis_files[0], 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        out_base = bill_folder / 'social_media'
        out_base.mkdir(exist_ok=True)
        
        title = analysis.get('bill_title', 'Vote')
        brief = analysis.get('brief_summary', '')
        
        # Regenerate title image with new title cleanup
        social_agent_from_json.make_title_image(title, brief, out_base / '01_title.png')
        
        print('[OK]')
        bills_processed += 1
    except Exception as e:
        print(f'ERROR: {e}')
        bills_failed += 1

print(f'\n=== SUMMARY ===')
print(f'Successfully regenerated: {bills_processed} title images')
if bills_failed:
    print(f'Failed: {bills_failed} bills')
