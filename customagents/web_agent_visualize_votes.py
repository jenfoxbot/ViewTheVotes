"""Vote visualization agent.

Creates a simple 3-column visualization of For / Against / Abstained votes.
Circles are colored by party (blue=Dem, red=Rep, yellow=Ind) and contain the
two-letter state abbreviation. No names or other identifiers are shown.

Output is written to `VoteData/` next to the source JSON.
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
from typing import Dict, List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

# US state name -> USPS two-letter codes
_STATES = {
    'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT',
    'Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL',
    'Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA',
    'Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH',
    'New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR',
    'Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT',
    'Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'
}

def _state_abbrev(s: str) -> str:
    if not s:
        return "--"
    s = s.strip()
    # If already two-letter
    if re.fullmatch(r"[A-Za-z]{2}", s):
        return s.upper()
    # Try exact match
    if s in _STATES:
        return _STATES[s]
    # Try last word (e.g., 'North Carolina' already key; fallback)
    parts = s.split()
    # try Title-case join
    candidate = ' '.join([p.capitalize() for p in parts])
    return _STATES.get(candidate, (parts[-1][:2].upper() if parts else '--'))

def _party_color(party: str) -> Tuple[str,str]:
    p = (party or "").lower()
    if 'dem' in p:
        return ('#0000FF','#FFFFFF')  # blue circle, white text
    if 'rep' in p or 'gop' in p:
        return ('#FF0000','#FFFFFF')  # red circle, white text
    # independent / other
    return ('#FFD700','#000000')


class VoteVisualizer:
    def __init__(self):
        if Image is None:
            raise RuntimeError('Pillow is required for visualization. Install with: python -m pip install pillow')

    def _parse_month_folder(self, date_str: str) -> str | None:
        """Parse date string and return folder name in format MonthYear (e.g., 'Jan2025', 'Dec2025').
        
        Args:
            date_str: Date in format MM/DD/YYYY (e.g., '01/16/2025')
            
        Returns:
            Folder name like 'Jan2025' or None if parsing fails
        """
        try:
            from datetime import datetime
            # Parse date from MM/DD/YYYY format
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            # Format as MonthYear (e.g., 'Jan2025')
            return dt.strftime('%b%Y')
        except Exception:
            return None

    def _locate_member_table(self, data: Dict) -> List[Dict]:
        # Look for a table that has headers containing Representative/Party/State/Vote
        tables = data.get('tables') or []
        for t in tables:
            headers = [h.lower() for h in (t.get('headers') or [])]
            if any('representative' in h for h in headers) and any('vote' in h for h in headers) and any('state' in h for h in headers):
                return t.get('rows', [])
        # fallback: try to find first table with rows
        for t in tables:
            if t.get('rows'):
                return t.get('rows')
        return []

    def _classify_vote(self, vote_text: str) -> str:
        if not vote_text:
            return 'abstained'
        vt = vote_text.strip().lower()
        # Prefer explicit abstentions like 'not voting' and 'present'
        if 'not voting' in vt:
            return 'abstained'
        if 'present' in vt:
            return 'abstained'
        # Affirmative votes
        if 'yea' in vt or 'aye' in vt or 'yes' in vt:
            return 'for'
        # Negative votes: use word boundaries to avoid matching 'no' inside other words
        if re.search(r"\bnay\b", vt) or re.search(r"\bno\b", vt):
            return 'against'
        # fallback: treat unknown as abstained
        return 'abstained'

    def visualize(self, vote_json_path: str, out_path: str | None = None, circle_diameter: int = 36, per_row: int = 10, analysis_json_path: str | None = None, vote_date: str | None = None, bill_abbrev: str | None = None) -> Dict:
        """Create a 3-column visualization of vote data.
        
        Args:
            vote_json_path: Path to the vote JSON file
            out_path: Optional output path; if not provided, derives from vote_json_path
            circle_diameter: Diameter of circles representing votes
            per_row: Number of circles per row
            analysis_json_path: Optional path to analysis JSON for header info
            vote_date: Optional date string in format MM/DD/YYYY to determine output folder (e.g., '01/16/2025' -> 'Jan2025')
            bill_abbrev: Optional bill abbreviation (e.g., 'HR498') to determine output folder
            
        Returns:
            Dict with success status, output path, and vote counts
        """
        # Read JSON
        with open(vote_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        rows = self._locate_member_table(data)
        members = []
        for r in rows:
            # rows may be dict with keys Representative/Party/State/Vote or numeric keys
            rep = r.get('Representative') or r.get('representative') or r.get('0') or ''
            party = r.get('Party') or r.get('party') or r.get('1') or ''
            state = r.get('State') or r.get('state') or r.get('2') or ''
            vote = r.get('Vote') or r.get('vote') or r.get('3') or ''
            members.append({'party': party, 'state': state, 'vote': vote})

        # classify and bucket
        buckets = {'for': [], 'against': [], 'abstained': []}
        for m in members:
            cls = self._classify_vote(m.get('vote', ''))
            abbrev = _state_abbrev(m.get('state', ''))
            buckets[cls].append({'party': m.get('party',''), 'state': abbrev})

        # --- Optional analysis header ---
        analysis = None
        if analysis_json_path:
            try:
                with open(analysis_json_path, 'r', encoding='utf-8') as af:
                    analysis = json.load(af)
            except Exception:
                analysis = None
        else:
            # try auto-locating an analysis file next to VoteData with prefix 'analysis_' + bill filename
            try:
                repo_root = pathlib.Path(__file__).parents[1]
                vote_dir = repo_root / 'VoteData'
                base = os.path.basename(vote_json_path)
                candidate = vote_dir / f'analysis_{base.replace("vote_", "bill_")}'
                if candidate.exists():
                    with open(candidate, 'r', encoding='utf-8') as af:
                        analysis = json.load(af)
            except Exception:
                analysis = None

        # Layout: three columns left->for, middle->against, right->abstained
        counts = {k: len(v) for k,v in buckets.items()}
        max_count = max(counts.values() or [0])
        rows_needed = math.ceil(max_count / per_row) or 1

        pad = 16
        d = circle_diameter
        col_width = per_row * (d + 6) + pad
        width = col_width * 3 + pad * 4
        # reserve extra space for header if analysis present
        header_height = 0
        header_lines = []
        if analysis:
            # Build simple header: title, date, 1-2 line brief
            title = analysis.get('bill_title') or analysis.get('title') or ''
            date = analysis.get('date_of_vote') or analysis.get('date') or ''
            brief = analysis.get('brief_summary') or analysis.get('brief') or ''
            pros = analysis.get('pros') or []
            cons = analysis.get('cons') or []
            # Build structured header lines with simple wrapping
            import textwrap
            wrap_width = max(40, (col_width*3)//8)
            structured = []
            if title:
                structured.append(('title', title))
            if date:
                structured.append(('date', f'Date: {date}'))
            if brief:
                for ln in textwrap.wrap(brief, width=wrap_width):
                    structured.append(('brief', ln))
            if pros:
                structured.append(('subhead', 'Pros:'))
                for p in pros[:3]:
                    for ln in textwrap.wrap(f'- {p}', width=wrap_width):
                        structured.append(('pros', ln))
            if cons:
                structured.append(('subhead', 'Cons:'))
                for c in cons[:3]:
                    for ln in textwrap.wrap(f'- {c}', width=wrap_width):
                        structured.append(('cons', ln))
            header_lines = structured
            # estimate header height (title slightly larger)
            est_lines = 0
            for kind, _ in header_lines:
                est_lines += 1
            header_height = 24 + est_lines * 18

        height = rows_needed * (d + 10) + 120 + header_height

        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)

        # font: base font, bold state font (for inside circles), heading font
        try:
            font = ImageFont.truetype('arial.ttf', int(d*0.5))
        except Exception:
            font = ImageFont.load_default()

        try:
            bold_state_font = ImageFont.truetype('arialbd.ttf', int(d*0.6))
        except Exception:
            try:
                bold_state_font = ImageFont.truetype('DejaVuSans-Bold.ttf', int(d*0.6))
            except Exception:
                bold_state_font = font

        try:
            heading_font = ImageFont.truetype('arial.ttf', max(28, int(d * 1.0)))
        except Exception:
            heading_font = font

        # draw header lines (analysis)
        y_offset = 10
        # prepare title font if available
        try:
            title_font = ImageFont.truetype('arial.ttf', int(d*0.75))
        except Exception:
            title_font = font

        if analysis and header_lines:
            left_x = pad
            for kind, line in header_lines:
                if kind == 'title':
                    fnt = title_font
                    fill = '#000000'
                    indent = 0
                elif kind == 'subhead':
                    fnt = font
                    fill = '#222222'
                    indent = 0
                elif kind in ('pros', 'cons'):
                    fnt = font
                    fill = '#333333'
                    indent = 12
                else:
                    fnt = font
                    fill = '#000000'
                    indent = 0
                try:
                    w,h = fnt.getsize(line)
                except Exception:
                    bbox = draw.textbbox((0,0), line, font=fnt)
                    w = bbox[2]-bbox[0]
                    h = bbox[3]-bbox[1]
                draw.text((left_x + indent, y_offset), line, fill=fill, font=fnt)
                y_offset += h + 4
            # small separator under header
            draw.line([(pad, y_offset), (width-pad, y_offset)], fill='#CCCCCC', width=1)
            y_offset += 8

        # headings with counts
        headings = [('For', buckets['for']), ('Against', buckets['against']), ('Abstained', buckets['abstained'])]
        heading_heights = []
        for i, (label, list_) in enumerate(headings):
            count = len(list_)
            text = f"{label} ({count})"
            x = pad + i*(col_width+pad) + col_width//2
            try:
                w,h = heading_font.getsize(text)
            except Exception:
                bbox = draw.textbbox((0,0), text, font=heading_font)
                w = bbox[2]-bbox[0]
                h = bbox[3]-bbox[1]
            draw.text((x - w/2, y_offset), text, fill='#000000', font=heading_font)
            heading_heights.append(h)

        # Add vertical padding after headings so circles don't overlap headers
        max_heading_h = max(heading_heights) if heading_heights else 0
        extra_padding_after_headings = max(12, int(d * 0.5))
        y_offset += max_heading_h + extra_padding_after_headings

        # separators between columns (start below header area so top has no vertical lines)
        sep_start = y_offset + 10
        for i in range(1,3):
            sx = pad + i*(col_width+pad) - pad//2
            draw.line([(sx, sep_start), (sx, height)], fill='#CCCCCC', width=2)

        # draw circles per column
        for col_idx, key in enumerate(['for','against','abstained']):
            # sort items alphabetically by state abbreviation for consistent ordering
            items = sorted(buckets[key], key=lambda it: (it.get('state') or '').upper())
            base_x = pad + col_idx*(col_width+pad) + 8
            y0 = y_offset + 30
            for idx, it in enumerate(items):
                row = idx // per_row
                colpos = idx % per_row
                cx = base_x + colpos*(d+6) + d//2
                cy = y0 + row*(d+10) + d//2
                fill, textcol = _party_color(it.get('party',''))
                # circle bbox
                bbox = [cx-d//2, cy-d//2, cx+d//2, cy+d//2]
                draw.ellipse(bbox, fill=fill, outline='#000000')
                st = it.get('state','--')[:2].upper()
                # center text
                # measure text using bold font and draw with a black stroke and white fill
                try:
                    bbox = draw.textbbox((0,0), st, font=bold_state_font)
                    w = bbox[2]-bbox[0]
                    h = bbox[3]-bbox[1]
                except Exception:
                    try:
                        w,h = bold_state_font.getsize(st)
                    except Exception:
                        # last-resort approximate
                        w = len(st) * 6
                        h = int(d * 0.6)
                tx = cx - w/2
                ty = cy - h/2 - 1
                # draw bold state text without an outline (white fill)
                try:
                    draw.text((tx, ty), st, font=bold_state_font, fill='white')
                except TypeError:
                    # fallback for older Pillow: just draw the white text
                    draw.text((tx, ty), st, font=bold_state_font, fill='white')

        # derive out_path with same folder structure as bill/vote data
        if not out_path:
            repo_root = pathlib.Path(__file__).parents[1]
            vote_data_root = repo_root / 'VoteData'
            
            # Determine month folder from vote_date if provided (e.g., '01/16/2025' -> 'Jan2025')
            month_folder = None
            if vote_date:
                month_folder = self._parse_month_folder(vote_date)
            
            # Build folder path: VoteData/{MonthYear}/{BillAbbrev}/
            if month_folder and bill_abbrev:
                vote_dir = vote_data_root / month_folder / bill_abbrev
            elif month_folder:
                vote_dir = vote_data_root / month_folder
            elif bill_abbrev:
                vote_dir = vote_data_root / bill_abbrev
            else:
                vote_dir = vote_data_root
            
            try:
                vote_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                vote_dir = pathlib.Path(os.getcwd())
            
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", os.path.basename(vote_json_path))
            out_path = str(vote_dir / f'viz_{safe}.png')

        img.save(out_path)
        return {'success': True, 'path': out_path, 'counts': counts}


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python customagents/web_agent_visualize_votes.py <vote_json_path>')
        sys.exit(1)
    vv = VoteVisualizer()
    res = vv.visualize(sys.argv[1])
    print(res)
