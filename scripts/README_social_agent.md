Social media image generator (social_agent.py)
=============================================

This small tool extracts text from a vote visualization image and produces
three images ready for social sharing:

- `01_title.png` — bill title and a brief description (kept under ~100 words)
- `02_pros_cons.png` — pros and cons extracted from the image
- `03_visual.png` — the original visual with state abbreviations redrawn
  bolder and column headers enlarged

Quick start (Windows PowerShell):

```powershell
# Install requirements into your env
python -m pip install -r requirements-social-agent.txt

# Ensure tesseract executable is installed and on PATH:
# https://github.com/tesseract-ocr/tesseract

# Run the script (replace the input path with your viz image path)
python scripts\social_agent.py --input path\to\viz_vote.png
```

Outputs are written to `VoteVisuals/<Month-Year>/`.

If OCR results look wrong, try tuning or run Tesseract with a different
language config or preprocess the image (increasing contrast, resizing).
