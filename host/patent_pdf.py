#!/usr/bin/env python3
"""Patent-spec -> print-ready HTML (for headless-Edge -> PDF).

Fixes over the first quick converter:
  * multi-line list items (claims, summary items) stay ONE block instead of splitting the
    numbered first line from its continuation lines;
  * markdown tables render as real <table>s, not raw pipe lines;
  * math blockquotes render as monospace with the markdown backtick delimiters stripped
    (so `x = s(q-8)` shows as x = s(q-8), not with literal backticks);
  * patent line-art FIGURES (monochrome SVG) are generated and injected right after the
    "BRIEF DESCRIPTION OF THE DRAWINGS" section, so every referenced FIG. N actually exists.

Run:  python patent_pdf.py            # writes <Desktop>/PATENT_*.html for all three
Then headless Edge --print-to-pdf each HTML.
"""
import html, re, os

DESK = "C:/Users/lucys/OneDrive/Desktop"
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs", "patents")

# ----------------------------------------------------------------------------- figure DSL
# Monochrome patent line-art. Absolute coords in a 900xH viewBox. Boxes auto-wrap text.
def _wrap(text, w, fs=15):
    cpl = max(6, int(w / (fs * 0.54)))
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 <= cpl:
            line = (line + " " + word).strip()
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out
