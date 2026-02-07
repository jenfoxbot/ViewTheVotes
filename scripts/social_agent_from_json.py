#!/usr/bin/env python3
"""Generate social-media-ready images from VoteData JSON files.

This script reads `analysis_bill_*.json` and `vote_*.json` in the `VoteData`
folder and creates title images in social_media folders with descriptions
that highlight impacts and consequences.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont
import shutil
import re
import textwrap

# Font scale multiplier
FONT_SCALE = 1


def _get_font(candidates, size: int):
    """Try loading a TrueType font from a list of candidate filenames."""
    for name in candidates:
        try:
            return ImageFont.truetype(name, int(size))
        except Exception:
            continue
    try:
        return ImageFont.truetype('arial.ttf', int(size))
    except Exception:
        return ImageFont.load_default()


STATE_TO_ABBR = {
    'Alabama': 'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA',
    'Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC',
    'Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL',
    'Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA',
    'Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN',
    'Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV',
    'New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC',
    'North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA',
    'Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX',
    'Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'
}


def find_files(votedir: Path):
    analysis = None
    vote = None
    for p in votedir.iterdir():
        if p.name.startswith('analysis_bill_') and p.suffix == '.json':
            analysis = p
        if p.name.startswith('vote_') and p.suffix == '.json':
            vote = p
    return analysis, vote


def load_json(path: Path):
    return json.loads(path.read_text())


def simplify_to_eli5(description: str) -> str:
    """
    Convert a bill description to a clear overview highlighting impacts and consequences.
    
    Focus on: What the bill does, who it affects, and what the real-world consequences
    might be—both intended and potential unintended. Explain nuances and trade-offs.
    Stick to facts; highlight potential harms and benefits for different groups.
    """
    if not description or len(description.strip()) < 10:
        return "This bill makes changes to federal policy."
    
    text_lower = description.lower()
    
    # ===== EDUCATION & SCHOOL FUNDING RESTRICTIONS =====
    if re.search(r'school.*?(china|foreign|communist).*?(prohibit|ban|prevent|restrict|disclose)', text_lower):
        return "This bill bars schools from accepting money or materials from the Chinese government.\nCritics worry it could damage educational partnerships and research.\nSupporters say it protects against foreign influence.\nSchools losing Chinese partnerships might need to find alternate funding."
    
    if re.search(r'school.*?(disclose|report).*?(foreign|china|contribution)', text_lower):
        return "Schools must now report foreign funding and contracts.\nThis increases transparency but adds administrative burden.\nSome worry it could chill legitimate international educational partnerships and research collaborations with scholars from China and other countries."
    
    if re.search(r'(prohibit|ban|restrict).*?(curriculum|teaching|teach|material)', text_lower):
        return "This bill limits what curriculum schools can use with federal funding, restricting certain educational materials and viewpoints.\nSupporters see it as preventing ideological bias; critics worry it restricts academic freedom and could remove important historical context about America's challenges.\nTeachers may face confusion about what's allowed."
    
    if re.search(r'school.*?(prohibit|ban|restrict).*?(fund|money|contract)', text_lower) or \
       re.search(r'(prohibit|ban|restrict).*?school.*?(fund|money)', text_lower):
        return "This bill changes what schools can do to keep federal funding.\nSchools may lose funding if they don't comply, which could impact student services and programs.\nSmaller districts with fewer resources may struggle more with compliance."
    
    # ===== HEALTHCARE RESTRICTIONS =====
    if re.search(r'(gender|transition|medicaid|medicare).*?(prohibit|ban|restrict).*(minor|youth|child|under.*age)', text_lower):
        return "This bill blocks Medicaid from paying for gender transition procedures for minors.\nSupporters argue it's protective; medical organizations and families of trans youth say it interferes with medical decisions between doctors, patients, and families.\nSome young people may lack access to recommended medical care, particularly low-income families."
    
    if re.search(r'(medicaid|medicare).*?(prohibit|ban|restrict)', text_lower):
        return "This bill stops Medicare or Medicaid from covering certain medical treatments.\nPatients, especially low-income and elderly, may lose access to these treatments or face higher out-of-pocket costs.\nMedical providers and patient advocates may oppose restrictions on treatments they say are medically necessary."
    
    # ===== WORKER & LABOR RIGHTS =====
    if re.search(r'(collective\s+bargain|union|worker.*right|labor.*right|federal.*employ)', text_lower):
        return "This bill protects federal employees' right to collective bargaining.\nBusiness groups worry it increases labor costs and reduces management flexibility; unions support stronger worker protections and wages.\nGovernment operations and costs could be affected by changed labor arrangements."
    
    # ===== CHILD PROTECTION & WELFARE =====
    if re.search(r'(child.*protection|child.*safety|children.*protect|genital|abuse)', text_lower):
        return "This bill strengthens protections against harmful practices and child abuse.\nSome groups worry about federal overreach into medical and family decisions; supporters say children need protection from harm.\nImplementation may increase enforcement and penalties."
    
    # ===== ENVIRONMENTAL & WILDLIFE =====
    if re.search(r'(wildlife|endangered|fish|wolf|animal|endangered.*species)', text_lower):
        return "This bill changes how endangered species and wildlife are protected.\nEnvironmental groups worry it weakens protections; industry and rural communities argue it restricts land use and economic activities.\nThe balance between conservation and economic development is contentious."
    
    # ===== REGULATORY & FEDERAL AGENCY PROCESS =====
    if re.search(r'(ferc|regulatory|commission|federal.*agency|environmental.*review|nepa)', text_lower):
        if re.search(r'(deadline|process|review|authorize|expedite|shorten)', text_lower):
            return "This bill speeds up federal agency reviews and project approvals.\nEnvironmental and community groups worry faster timelines mean less scrutiny of potential harms.\nIndustry supports faster approvals but critics say it reduces public input and environmental safeguards."
    
    # ===== ENERGY & UTILITIES =====
    if re.search(r'(electric|generation|facility|generation facility|transmission|utility)', text_lower):
        return "This bill changes rules for electric utilities and power generation.\nEnvironmental advocates worry it favors certain energy sources or weakens emissions rules; industry supports it as reducing costs.\nThe bill likely affects electricity prices and climate goals in competing ways."
    
    # ===== MINING & NATURAL RESOURCES =====
    if re.search(r'(mining|mine|hardrock|mineral|extraction|resource)', text_lower):
        return "This bill affects mining and natural resource extraction rules.\nEnvironmental groups fear it weakens protections for land and water quality; mining companies say it streamlines operations and jobs.\nCommunities near mining operations may see increased environmental risks or economic benefits depending on the specific rules."
    
    # ===== BUSINESS & INVESTMENT =====
    if re.search(r'(closed.*end.*fund|investment|investor|securities|exchange|business)', text_lower):
        return "This bill changes investment and business regulations.\nSupporters say it eases restrictions and promotes growth; critics worry it reduces investor protections and increases financial risk.\nSmall investors may benefit or face greater market volatility and fraud risk."
    
    # ===== REGULATORY REDUCTION =====
    if re.search(r'(regulatory|red tape|regulation|deregul|simplif|burden)', text_lower):
        return "This bill reduces regulations and government requirements for businesses.\nCompanies support lower compliance costs; consumer advocates and environmental groups worry it removes protections for workers, consumers, and the environment.\nThe trade-off between business freedom and safety/environmental protections is disputed."
    
    # ===== MILITARY & DEFENSE =====
    if re.search(r'(military|defense|department.*defense|armed.*forces|procurement|aircraft|missile|ship)', text_lower):
        return "This bill authorizes military spending on equipment and personnel.\nSome argue it's necessary for national security; others worry about spending priorities and defense budgets taking resources from social programs.\nInternational relations could be affected by U.S. military posture changes."
    
    # ===== IMMIGRATION =====
    if re.search(r'(immigration|border|citizen|visa|refugee|asylum)', text_lower):
        return "This bill changes immigration, border, or citizenship rules.\nImmigration advocates worry about reduced access and family separation; enforcement supporters say it's necessary for security and rule of law.\nThe impacts fall heavily on vulnerable migrants and their families."
    
    # ===== TAXES & FINANCIAL POLICY =====
    if re.search(r'(reduce|cut|relief|lower).*?(tax|income)', text_lower) or \
       re.search(r'(tax|income).*(reduce|cut|relief|lower)', text_lower):
        return "This bill cuts taxes for individuals or businesses.\nSupporters say it boosts the economy and incomes; critics worry it reduces government revenue for programs and increases deficits.\nThe benefits and burdens are distributed unevenly across income levels."
    
    if re.search(r'(increase|raise|expand).*?(tax|income)', text_lower) or \
       re.search(r'(tax|income).*(increase|raise|expand)', text_lower):
        return "This bill raises taxes on individuals or businesses.\nCritics say it slows growth and raises costs; supporters argue it funds important programs and makes the system fairer.\nThe impacts vary by income level and sector."
    
    if re.search(r'(appropriat|budget|allocate).*?(fund|program|agency)', text_lower):
        return "This bill distributes federal money to agencies and programs.\nSome programs gain resources while others may lose them, affecting which government services expand or shrink.\nBudget impacts vary across different regions and populations."
    
    # ===== TRANSPARENCY & REPORTING =====
    if re.search(r'(require|mandate).*?(disclose|report|transparency|register)', text_lower):
        return "This bill requires disclosure of information about operations or finances.\nTransparency supporters value increased oversight; those affected say it creates burdens and exposes proprietary information.\nThe balance between transparency and privacy is contested."
    
    # ===== FALLBACK: Extract key details =====
    text_clean = re.sub(r'^shown\s+here:[^.]*\.\s*', '', description, flags=re.I)
    text_clean = re.sub(r'^[A-Z]\.R\.\d+.*?(?=This bill|Introduced|This Act)', '', text_clean, flags=re.I | re.DOTALL)
    
    sentences = text_clean.split('. ')
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:
            continue
        if re.search(r'(this bill|prohibits|requires|establishes|authorizes|impacts|changes|sets|amends)', sentence, re.I):
            if not sentence.endswith('.'):
                sentence += '.'
            if len(sentence) > 220:
                sentence = sentence[:220].rsplit(' ', 1)[0] + '...'
            if len(sentence) > 35:
                return sentence if sentence[0].isupper() else sentence.capitalize()
    
    return "This bill makes changes to federal law and policy. The impacts on different groups and interests are likely to be mixed."


def make_title_image(title: str, desc: str, out_path: Path, width=1080, subheader: str | None = None):
    simple_desc = simplify_to_eli5(desc)
    margin = 40
    height = width
    base_desc = max(18, int(width * 0.018 * FONT_SCALE * 3))
    title_font_size = base_desc  # Reverted: no longer * 2
    desc_font_size = max(8, int(base_desc / 2)) * 2  # Keep 2x for description
    title_font_size = min(title_font_size, int(width * 0.8))
    title_font = _get_font(['DejaVuSans-Bold.ttf', 'arialbd.ttf', 'arial.ttf', 'DejaVuSans.ttf'], title_font_size)
    desc_font = _get_font(['DejaVuSans.ttf', 'arial.ttf'], desc_font_size)

    tmp_img = Image.new('RGB', (width, height), 'white')
    tmp_draw = ImageDraw.Draw(tmp_img)

    # Extract bill number and short title from full title
    # Format: "H.R.1366 - 119th Congress (2025-2026): Mining Regulatory Clarity Act | Congress.gov | Library of Congress"
    # Want: "H.R.1366 Mining Regulatory Clarity Act"
    
    # First, remove everything after the first "|"
    if '|' in title:
        title = title.split('|')[0].strip()
    
    # Extract bill number and short title
    # Pattern: "BILL_NUMBER - Congress info: SHORT_TITLE"
    match = re.match(r'^([HS]\.\s*(?:R\.|J\.\s*Res\.|Con\.\s*Res\.|Res\.)\s*\d+)\s*-\s*.*?:\s*(.+)$', title)
    if match:
        bill_num = match.group(1)
        short_title = match.group(2).strip()
        title = f"{bill_num} {short_title}"
    
    # Wrap title based on pixel width, not character count
    avg_title_char_width = tmp_draw.textbbox((0, 0), 'A', font=title_font)[2]
    target_width = width - 2 * margin
    title_chars_per_line = max(10, target_width // avg_title_char_width)
    title_lines = textwrap.wrap(title, width=title_chars_per_line)
    title = '\n'.join(title_lines[:3])
    if len(title_lines) > 3:
        title_text = '\n'.join(title_lines[:3])
        title_text = title_text[:title_text.rfind('\n')] + '...'
        title = title_text

    # Calculate title height
    title_bbox = tmp_draw.textbbox((margin, margin), title, font=title_font)
    title_h = title_bbox[3] - title_bbox[1]
    
    # Position description with more spacing and center vertically in remaining space
    desc_start_y = margin + title_h + 60
    available_height = height - desc_start_y - margin
    
    # Wrap description to fill available space
    avg_char_width = tmp_draw.textbbox((0, 0), 'a', font=desc_font)[2]
    target_width = width - 2 * margin
    desc_chars_per_line = max(10, target_width // avg_char_width)
    
    # Split on newlines first (for our sentence-per-line formatting), then wrap long lines
    desc_paragraphs = simple_desc.split('\n')
    wrapped_lines = []
    for para in desc_paragraphs:
        if para.strip():
            wrapped = textwrap.wrap(para, width=desc_chars_per_line)
            wrapped_lines.extend(wrapped)
            # Add blank line after each paragraph for spacing
            wrapped_lines.append('')
    
    # Remove trailing blank line and join
    if wrapped_lines and wrapped_lines[-1] == '':
        wrapped_lines.pop()
    simple_desc = '\n'.join(wrapped_lines)

    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    draw.text((margin, margin), title, fill='black', font=title_font)
    draw.text((margin, desc_start_y), simple_desc, fill='#333333', font=desc_font)

    img.save(out_path)
    print(f"Created {out_path}")
