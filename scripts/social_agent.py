#!/usr/bin/env python3
"""Generate social-media-ready images from a vote visualization image.

Produces three images:
  1) Title + brief description (<=100 words)
  2) Pros / Cons text image
  3) Enhanced visual image with bolder state abbreviations and larger column headers

Usage:
  python scripts/social_agent.py --input path/to/viz_vote.png

Notes:
  - This script uses Tesseract OCR via `pytesseract` to extract text from the
    provided image. On Windows you must also install the Tesseract executable
    (https://github.com/tesseract-ocr/tesseract). Add it to PATH or set
    `pytesseract.pytesseract.tesseract_cmd` accordingly.
  - Output images are written to `VoteVisuals/<Month-Year>/` by default.
"""

from __future__ import annotations

import argparse
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import pytesseract
    from pytesseract import Output
except Exception as e:
    raise RuntimeError("pytesseract required: pip install pytesseract") from e

# Minimal set of US state abbreviations for recognition
US_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI',
    'MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT',
    'VT','VA','WA','WV','WI','WY','DC'
}


def extract_text_blocks(img: Image.Image) -> str:
    """Run OCR and return full text (single string)."""
    text = pytesseract.image_to_string(img)
    return text


def extract_date_month(text: str) -> str:
    # Look for Date: mm/dd/yyyy or variants
    m = re.search(r"Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE)
    if not m:
        # fallback: look for yyyy-mm-dd
        m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if m2:
            dt = datetime.strptime(m2.group(0), "%Y-%m-%d")
            return dt.strftime("%B-%Y")
        return "Unknown"
    date_str = m.group(1)
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%B-%Y")
        except Exception:
            continue
    return "Unknown"


def extract_title_and_description(text: str) -> Tuple[str, str]:
    # Heuristic: title appears in the first non-empty line(s).
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ("Vote", "")

    # Title often contains bill id like H.R.498 - take first line as title
    title = lines[0]
    # Description: take next 2-4 lines joined, clip to 100 words
    desc_lines = []
    for l in lines[1:6]:
        # stop if we hit Pros: or Cons:
        if re.match(r"^(Pros|Cons)\b", l, re.IGNORECASE):
            break
        desc_lines.append(l)
    desc = " ".join(desc_lines)
    # normalize whitespace and limit words
    desc = re.sub(r"\s+", " ", desc).strip()
    words = desc.split()
    if len(words) > 100:
        desc = " ".join(words[:100]) + "..."
    return title, desc


def extract_pros_cons(text: str) -> Dict[str, List[str]]:
    # Find Pros: and Cons: and parse bullets (lines starting with - or •)
    result = {"Pros": [], "Cons": []}
    lines = [l.rstrip() for l in text.splitlines()]
    current = None
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if re.match(r"^Pros\b", s, re.IGNORECASE):
            current = "Pros"
            continue
        if re.match(r"^Cons\b", s, re.IGNORECASE):
            current = "Cons"
            continue
        if current and re.match(r"^[\-•]\s+", s):
            result[current].append(re.sub(r"^[\-•]\s+", "", s))
        elif current and len(result[current]) == 0 and len(s) > 20:
            # fallback: if no bullet but lines likely are part of a pro/cons
            result[current].append(s)
    return result


def make_text_image(title: str, desc: str, out_path: Path, width: int = 1200) -> None:
    # Create a white image with title and description
    margin = 40
    title_font_size = 48
    desc_font_size = 22
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", title_font_size)
        desc_font = ImageFont.truetype("DejaVuSans.ttf", desc_font_size)
    except Exception:
        title_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()

    # Wrap text
    wrapper = textwrap.TextWrapper(width=80)
    desc_wrapped = wrapper.fill(desc)

    # Estimate height
    dummy = Image.new("RGB", (width, 200), "white")
    draw = ImageDraw.Draw(dummy)
    title_h = draw.multiline_textsize(title, font=title_font)[1]
    desc_h = draw.multiline_textsize(desc_wrapped, font=desc_font)[1]
    height = margin * 2 + title_h + 20 + desc_h

    img = Image.new("RGB", (width, max(height, 300)), "white")
    d = ImageDraw.Draw(img)
    x = margin
    y = margin
    d.text((x, y), title, fill="black", font=title_font)
    y += title_h + 20
    d.text((x, y), desc_wrapped, fill="black", font=desc_font)
    img.save(out_path)


def make_pros_cons_image(pros: List[str], cons: List[str], out_path: Path, width: int = 1200) -> None:
    margin = 40
    heading_size = 36
    item_size = 22
    try:
        heading_font = ImageFont.truetype("DejaVuSans-Bold.ttf", heading_size)
        item_font = ImageFont.truetype("DejaVuSans.ttf", item_size)
    except Exception:
        heading_font = ImageFont.load_default()
        item_font = ImageFont.load_default()

    wrapper = textwrap.TextWrapper(width=60)

    # Build lines
    lines = ["Pros:"]
    for p in pros:
        lines.extend(["- " + l for l in wrapper.wrap(p)])
    lines.append("")
    lines.append("Cons:")
    for c in cons:
        lines.extend(["- " + l for l in wrapper.wrap(c)])

    # Estimate height
    dummy = Image.new("RGB", (width, 200), "white")
    draw = ImageDraw.Draw(dummy)
    total_h = 0
    for i, ln in enumerate(lines):
        f = heading_font if ln in ("Pros:", "Cons:") else item_font
        total_h += draw.multiline_textsize(ln, font=f)[1] + 6

    img = Image.new("RGB", (width, max(300, total_h + margin * 2)), "white")
    d = ImageDraw.Draw(img)
    y = margin
    for ln in lines:
        f = heading_font if ln in ("Pros:", "Cons:") else item_font
        d.text((margin, y), ln, fill="black", font=f)
        y += d.multiline_textsize(ln, font=f)[1] + 6

    img.save(out_path)


def enhance_visual_image(in_path: Path, out_path: Path) -> None:
    img = Image.open(in_path).convert("RGBA")
    # Work on a copy for drawing
    canvas = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)

    # OCR with bounding boxes
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    n = len(data['text'])

    # Determine a font size relative to image width
    base_font_size = max(14, img.width // 60)
    try:
        bold_font = ImageFont.truetype("DejaVuSans-Bold.ttf", base_font_size)
        regular_font = ImageFont.truetype("DejaVuSans.ttf", base_font_size)
    except Exception:
        bold_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()

    # Draw larger column headers and bold state abbreviations
    for i in range(n):
        txt = data['text'][i].strip()
        if not txt:
            continue
        left = int(data['left'][i])
        top = int(data['top'][i])
        w = int(data['width'][i])
        h = int(data['height'][i])

        # Column headers like 'For', 'Against', 'Abstained' -> enlarge
        if re.match(r'^(For|Against|Abstained)\b', txt, re.IGNORECASE):
            fsize = base_font_size + 8
            try:
                f = ImageFont.truetype("DejaVuSans-Bold.ttf", fsize)
            except Exception:
                f = bold_font
            # Draw white rectangle behind to ensure readability
            pad = 6
            draw.rectangle([left-pad, top-pad, left+w+pad, top+h+pad], fill=(255,255,255,200))
            draw.text((left, top), txt, fill=(0,0,0,255), font=f)

        # Two-letter uppercase words that match state abbreviations -> bold and larger
        elif re.fullmatch(r"[A-Z]{2}", txt) and txt in US_STATES:
            fsize = int(h * 1.6)
            try:
                f = ImageFont.truetype("DejaVuSans-Bold.ttf", fsize)
            except Exception:
                f = bold_font
            # Draw a filled circle similar to original and write text centered
            cx = left + w//2
            cy = top + h//2
            radius = max(w, h) // 1
            # cover original area with a semi-transparent white to ensure redraw
            pad = 2
            draw.ellipse([left-pad, top-pad, left+w+pad, top+h+pad], fill=(255,255,255,180))
            # Center text
            tw, th = draw.textsize(txt, font=f)
            tx = cx - tw/2
            ty = cy - th/2
            draw.text((tx, ty), txt, fill=(0,0,0,255), font=f)

    # Composite and save as PNG
    out = Image.alpha_composite(img, canvas).convert("RGB")
    out.save(out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to the vote visualization image")
    p.add_argument("--outdir", default="VoteVisuals", help="Base output directory")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    img = Image.open(in_path).convert("RGB")
    text = extract_text_blocks(img)

    month_name = extract_date_month(text)
    out_base = Path(args.outdir) / month_name
    out_base.mkdir(parents=True, exist_ok=True)

    title, desc = extract_title_and_description(text)
    pros_cons = extract_pros_cons(text)

    title_path = out_base / "01_title.png"
    proscons_path = out_base / "02_pros_cons.png"
    visual_path = out_base / "03_visual.png"

    make_text_image(title, desc, title_path)
    make_pros_cons_image(pros_cons.get("Pros", []), pros_cons.get("Cons", []), proscons_path)
    enhance_visual_image(in_path, visual_path)

    print(f"Wrote images to: {out_base}\n- {title_path.name}\n- {proscons_path.name}\n- {visual_path.name}")


if __name__ == "__main__":
    main()
