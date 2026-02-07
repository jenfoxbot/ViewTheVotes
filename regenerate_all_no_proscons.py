#!/usr/bin/env python
"""Regenerate all analysis files and social media images for December 2025 bills without pros/cons."""
from pathlib import Path
from customagents.analysis_agent import AnalysisAgent
import sys
import json

sys.path.insert(0, 'scripts')
import social_agent_from_json

agent = AnalysisAgent()
bills_processed = 0
bills_failed = 0

# Find all bill folders in Dec2025
base = Path('VoteData/Dec2025')
for bill_folder in sorted(base.iterdir()):
    if not bill_folder.is_dir():
        continue
    
    # Check if bill JSON exists
    bill_files = list(bill_folder.glob('bill_*.json'))
    if not bill_files:
        continue
    
    bill_name = bill_folder.name
    print(f'\nProcessing {bill_name}...', end=' ')
    
    try:
        # Regenerate analysis
        result = agent.analyze(bill_folder=str(bill_folder))
        if not result.get('success'):
            print(f'FAILED: {result.get("error")}')
            bills_failed += 1
            continue
        
        analysis = result["analysis"]
        print(f'[OK]')
        
        # Regenerate social media images
        analysis_files = list(bill_folder.glob('analysis_*.json'))
        if analysis_files:
            with open(analysis_files[0], 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            out_base = bill_folder / 'social_media'
            out_base.mkdir(exist_ok=True)
            
            title = analysis_data.get('bill_title', 'Vote')
            brief = analysis_data.get('brief_summary', '')
            
            # Create title image
            social_agent_from_json.make_title_image(title, brief, out_base / '01_title.png')
            
            # Copy viz if it exists
            viz_files = list(bill_folder.glob('viz_*.png'))
            if viz_files:
                import shutil
                shutil.copy(viz_files[0], out_base / '02_visual.png')
            
            # Clean up old pros_cons image if it exists
            old_pros_cons = out_base / '02_pros_cons.png'
            if old_pros_cons.exists():
                old_pros_cons.unlink()
            
            bills_processed += 1
    except Exception as e:
        print(f'ERROR: {e}')
        bills_failed += 1

print(f'\n\n=== SUMMARY ===')
print(f'Successfully updated: {bills_processed} bills')
if bills_failed:
    print(f'Failed: {bills_failed} bills')
print(f'\nAll analysis files and social media now updated without pros/cons.')
