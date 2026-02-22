#!/usr/bin/env python3
"""Generate shareable social media cards from vote data.

Creates eye-catching single-stat graphics designed for social sharing:
- Bold vote count
- Simple action description  
- Call to action: "Was your rep one of them?"

Usage:
    python scripts/shareable_card_generator.py --bill-folder VoteData/Dec2025/HR4776
    python scripts/shareable_card_generator.py --all-december
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# Color schemes for different vote outcomes
COLORS = {
    'passed': {
        'background': '#1a5f2a',  # Dark green
        'text': '#ffffff',
        'accent': '#4ade80',  # Light green
    },
    'failed': {
        'background': '#7f1d1d',  # Dark red  
        'text': '#ffffff',
        'accent': '#f87171',  # Light red
    },
    'neutral': {
        'background': '#1e3a5f',  # Dark blue
        'text': '#ffffff', 
        'accent': '#60a5fa',  # Light blue
    }
}


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font at the specified size."""
    candidates = ['arialbd.ttf', 'Arial Bold.ttf'] if bold else ['arial.ttf', 'Arial.ttf']
    candidates += ['DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf']
    
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def get_vote_action_text(analysis: Dict, vote_passed: bool) -> str:
    """Generate a simple action description from the bill analysis.
    
    Returns something like "voted to limit environmental reviews"
    """
    title = analysis.get('bill_title', '')
    summary = analysis.get('brief_summary', '')
    
    # Extract short title from full title
    # "H.R.4776 - 119th Congress (2025-2026): SPEED Act | ..." -> "SPEED Act"
    title_match = re.search(r':\s*([^|]+?)(?:\s*\||$)', title)
    short_title = title_match.group(1).strip() if title_match else ''
    
    # Common action patterns based on keywords
    text_lower = (summary + ' ' + short_title).lower()
    
    if re.search(r'(nepa|environmental\s+review).*?(limit|scope|narrow)', text_lower):
        return "limit environmental reviews"
    if re.search(r'(pipeline|ferc).*?(review|coordinat)', text_lower):
        return "speed up pipeline approvals"
    if re.search(r'(health\s*care|premium).*?(lower|reduce|cost)', text_lower):
        return "change health care costs"
    if re.search(r'(school|education).*?(foreign|china|adversar)', text_lower):
        return "require schools to report foreign influence"
    if re.search(r'(mining|mineral).*?(regulat|permit)', text_lower):
        return "change mining regulations"
    if re.search(r'(child|minor).*?(protect|safe)', text_lower):
        return "strengthen child protections"
    if re.search(r'(medicaid|medicare).*?(prohibit|restrict)', text_lower):
        return "restrict Medicaid coverage"
    if re.search(r'(wildlife|endangered|species)', text_lower):
        return "change wildlife protections"
    if re.search(r'(tax|income).*?(cut|reduce|lower)', text_lower):
        return "cut taxes"
    if re.search(r'(military|defense|armed)', text_lower):
        return "authorize military spending"
    if re.search(r'(immigration|border|visa)', text_lower):
        return "change immigration rules"
    if re.search(r'(electric|utility|energy)', text_lower):
        return "change energy regulations"
    
    # Fallback: use short title if available
    if short_title and len(short_title) < 40:
        return f"pass the {short_title}"
    
    return "pass this bill"


def load_bill_data(bill_folder: Path) -> Tuple[Dict, Dict, bool]:
    """Load analysis and vote data for a bill.
    
    Returns: (analysis_data, vote_data, vote_passed)
    """
    # Find analysis file
    analysis_files = list(bill_folder.glob('analysis_*.json'))
    if not analysis_files:
        raise FileNotFoundError(f"No analysis file found in {bill_folder}")
    
    with open(analysis_files[0], 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    # Find vote file
    vote_files = list(bill_folder.glob('vote_*.json'))
    if not vote_files:
        raise FileNotFoundError(f"No vote file found in {bill_folder}")
    
    with open(vote_files[0], 'r', encoding='utf-8') as f:
        vote_data = json.load(f)
    
    # Determine if vote passed
    counts = vote_data.get('counts', {})
    yea = counts.get('yea', 0)
    nay = counts.get('nay', 0)
    vote_passed = yea > nay
    
    return analysis, vote_data, vote_passed


def create_shareable_card(
    bill_folder: Path,
    output_path: Optional[Path] = None,
    width: int = 1080,
    height: int = 1080
) -> Path:
    """Create a shareable social media card for a bill vote.
    
    Args:
        bill_folder: Path to the bill's data folder
        output_path: Where to save the image (defaults to social_media/03_shareable.png)
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Path to the created image
    """
    # Load data
    analysis, vote_data, vote_passed = load_bill_data(bill_folder)
    
    counts = vote_data.get('counts', {})
    yea_count = counts.get('yea', 0)
    nay_count = counts.get('nay', 0)
    
    # Determine which count to feature (the winning side)
    if vote_passed:
        featured_count = yea_count
        vote_verb = "voted to"
        colors = COLORS['passed']
    else:
        featured_count = nay_count
        vote_verb = "voted against"
        colors = COLORS['failed']
    
    # Get action text
    action_text = get_vote_action_text(analysis, vote_passed)
    
    # Create image
    img = Image.new('RGB', (width, height), colors['background'])
    draw = ImageDraw.Draw(img)
    
    # Fonts
    count_font = _get_font(180, bold=True)
    label_font = _get_font(48, bold=False)
    action_font = _get_font(42, bold=True)
    cta_font = _get_font(36, bold=False)
    
    # Layout calculations
    margin = 60
    center_x = width // 2
    
    # Draw the big number
    count_text = str(featured_count)
    count_bbox = draw.textbbox((0, 0), count_text, font=count_font)
    count_width = count_bbox[2] - count_bbox[0]
    count_height = count_bbox[3] - count_bbox[1]
    count_y = 180
    draw.text((center_x - count_width // 2, count_y), count_text, 
              fill=colors['accent'], font=count_font)
    
    # Draw "representatives" label
    label_text = "representatives"
    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
    label_width = label_bbox[2] - label_bbox[0]
    label_y = count_y + count_height + 20
    draw.text((center_x - label_width // 2, label_y), label_text,
              fill=colors['text'], font=label_font)
    
    # Draw action text (voted to + action)
    full_action = f"{vote_verb} {action_text}"
    
    # Wrap if needed
    import textwrap
    wrapped_action = textwrap.fill(full_action, width=28)
    action_lines = wrapped_action.split('\n')
    
    action_y = label_y + 100
    for line in action_lines:
        line_bbox = draw.textbbox((0, 0), line, font=action_font)
        line_width = line_bbox[2] - line_bbox[0]
        draw.text((center_x - line_width // 2, action_y), line,
                  fill=colors['text'], font=action_font)
        action_y += 55
    
    # Draw separator line
    line_y = action_y + 60
    line_margin = 150
    draw.line([(line_margin, line_y), (width - line_margin, line_y)], 
              fill=colors['accent'], width=3)
    
    # Draw call to action
    cta_text = "Was your representative"
    cta2_text = "one of them?"
    
    cta_y = line_y + 80
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_width = cta_bbox[2] - cta_bbox[0]
    draw.text((center_x - cta_width // 2, cta_y), cta_text,
              fill=colors['text'], font=cta_font)
    
    cta2_bbox = draw.textbbox((0, 0), cta2_text, font=cta_font)
    cta2_width = cta2_bbox[2] - cta2_bbox[0]
    draw.text((center_x - cta2_width // 2, cta_y + 50), cta2_text,
              fill=colors['accent'], font=cta_font)
    
    # Draw bill number at bottom
    bill_match = re.search(r'([HS]\.?R\.?\s*\d+)', analysis.get('bill_title', ''))
    if bill_match:
        bill_num = bill_match.group(1).replace(' ', '')
        bill_font = _get_font(28, bold=False)
        bill_bbox = draw.textbbox((0, 0), bill_num, font=bill_font)
        bill_width = bill_bbox[2] - bill_bbox[0]
        draw.text((center_x - bill_width // 2, height - 80), bill_num,
                  fill=colors['text'], font=bill_font)
    
    # Save image
    if output_path is None:
        output_path = bill_folder / 'social_media' / '03_shareable.png'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"Created {output_path}")
    
    return output_path


def process_all_december():
    """Process all December 2025 bills."""
    base = Path('VoteData/Dec2025')
    success_count = 0
    
    for bill_folder in sorted(base.iterdir()):
        if not bill_folder.is_dir():
            continue
        
        try:
            create_shareable_card(bill_folder)
            success_count += 1
        except Exception as e:
            print(f"Error processing {bill_folder.name}: {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Successfully created: {success_count} shareable cards")


def main():
    parser = argparse.ArgumentParser(description='Generate shareable social media cards')
    parser.add_argument('--bill-folder', type=Path, help='Path to a single bill folder')
    parser.add_argument('--all-december', action='store_true', help='Process all December 2025 bills')
    
    args = parser.parse_args()
    
    if args.all_december:
        process_all_december()
    elif args.bill_folder:
        create_shareable_card(args.bill_folder)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
