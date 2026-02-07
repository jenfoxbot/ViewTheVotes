#!/usr/bin/env python
"""Regenerate all analysis files and social media images for December 2025 bills."""
from pathlib import Path
from customagents.analysis_agent import AnalysisAgent
import sys
import json

sys.path.insert(0, 'scripts')
import social_agent_from_json

agent = AnalysisAgent()
bills_processed = 0

# Find all bill folders in Dec2025
base = Path('VoteData/Dec2025')
for bill_folder in sorted(base.iterdir()):
    if not bill_folder.is_dir():
        continue
    
    # Check if bill JSON exists
    bill_files = list(bill_folder.glob('bill_*.json'))
    if not bill_files:
        continue
    
    print(f'\nProcessing {bill_folder.name}...')
    
    # Regenerate analysis
    result = agent.analyze(bill_folder=str(bill_folder))
    if not result.get('success'):
        print(f'  Analysis failed: {result.get("error")}')
        continue
    
    pros_count = len(result["analysis"]["pros"])
    cons_count = len(result["analysis"]["cons"])
    print(f'  Analysis: {pros_count} pros, {cons_count} cons')
    
    # Regenerate social media images
    analysis_files = list(bill_folder.glob('analysis_*.json'))
    if analysis_files:
        with open(analysis_files[0], 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        out_base = bill_folder / 'social_media'
        out_base.mkdir(exist_ok=True)
        
        title = analysis.get('bill_title', 'Vote')
        brief = analysis.get('brief_summary', '')
        pros = analysis.get('pros', [])
        cons = analysis.get('cons', [])
        
        social_agent_from_json.make_title_image(title, brief, out_base / '01_title.png')
        social_agent_from_json.make_pros_cons_image(pros, cons, out_base / '02_pros_cons.png')
        print(f'  Social media images regenerated')
        bills_processed += 1

print(f'\n\nTotal: Regenerated analysis and social media for {bills_processed} bills')
