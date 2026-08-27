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

def box(x, y, w, h, text, fs=15, dashed=False, bold_first=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="white" stroke="black" stroke-width="1.5"{dash}/>']
    lines = _wrap(text, w - 14, fs)
    total = len(lines) * (fs + 3)
    ty = y + (h - total) / 2 + fs
    for i, ln in enumerate(lines):
        wt = "700" if (bold_first and i == 0) else "400"
        s.append(f'<text x="{x + w/2}" y="{ty:.0f}" font-size="{fs}" font-weight="{wt}" text-anchor="middle" font-family="Georgia,serif">{html.escape(ln)}</text>')
        ty += fs + 3
    return "".join(s)

def _arrowdefs():
    return ('<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" '
            'markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 z" fill="black"/></marker></defs>')

def arrow(x1, y1, x2, y2, label="", fs=13, dashed=False):
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    s = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="1.5" marker-end="url(#ah)"{dash}/>']
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 5
        s.append(f'<rect x="{mx-len(label)*3.6-3}" y="{my-fs}" width="{len(label)*7.2+6}" height="{fs+5}" fill="white" opacity="0.9"/>')
        s.append(f'<text x="{mx}" y="{my}" font-size="{fs}" text-anchor="middle" font-style="italic" font-family="Georgia,serif">{html.escape(label)}</text>')
    return "".join(s)

def txt(x, y, s, fs=14, anchor="middle", style="normal", weight="400"):
    return f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" font-style="{style}" font-weight="{weight}" font-family="Georgia,serif">{html.escape(s)}</text>'

def _maxy(body):
    """Bottom-most drawn coordinate in the body SVG, so the caption never overlaps the diagram."""
    m = 0.0
    for a, b in re.findall(r'<rect[^>]*?\sy="([\d.]+)"[^>]*?\sheight="([\d.]+)"', body):
        m = max(m, float(a) + float(b))
    for v in re.findall(r'\sy1="([\d.]+)"', body):
        m = max(m, float(v))
    for v in re.findall(r'\sy2="([\d.]+)"', body):
        m = max(m, float(v))
    for v in re.findall(r'<text[^>]*?\sy="([\d.]+)"', body):
        m = max(m, float(v))
    return m

def fig(num, caption, _hint, body):
    # auto-size: caption sits BELOW the lowest diagram element (the _hint arg is ignored)
    dbottom = _maxy(body) + 14
    cap = _wrap(caption, 860, 14)
    height = dbottom + 22 + len(cap) * 18
    sep = f'<line x1="40" y1="{dbottom:.0f}" x2="860" y2="{dbottom:.0f}" stroke="#cccccc" stroke-width="1"/>'
    cy0 = dbottom + 20
    capsvg = "".join(txt(450, cy0 + i * 18, ln, fs=14, weight="400") for i, ln in enumerate(cap))
    return (f'<div class="figwrap"><svg viewBox="0 0 900 {height:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'class="fig">{_arrowdefs()}'
            f'{txt(450, 26, f"FIG. {num}", fs=18, weight="700")}'
            f'{body}{sep}{capsvg}</svg></div>')

# ----------------------------------------------------------------------------- figures per doc
def figs_whitebox():
    F = []
    # FIG 1 — overall flow
    b = []
    b.append(box(30, 50, 150, 60, "Parameter file (stored bits)", bold_first=False))
    b.append(box(240, 50, 140, 60, "Bit-level reader (no inference)"))
    b.append(box(440, 40, 200, 34, "Anatomy · Precision map · Layer scan"))
    b.append(box(440, 82, 200, 34, "Decompiler · Tensor scope"))
    b.append(box(440, 130, 200, 40, "Search-and-destroy · Alignment (edit)"))
    b.append(box(700, 70, 165, 70, "Genome journal (byte-exact revert)"))
    b.append(arrow(180, 80, 238, 80))
    b.append(arrow(380, 68, 438, 57))
    b.append(arrow(380, 80, 438, 99))
    b.append(arrow(380, 92, 438, 150))
    b.append(arrow(640, 150, 700, 120, "edit"))
    b.append(arrow(700, 90, 640, 57, "revert", dashed=True))
    b.append(arrow(782, 140, 782, 175))
    b.append(arrow(782, 175, 105, 175, "byte-exact restore", dashed=True))
    b.append(arrow(105, 175, 105, 112))
    F.append(fig(1, "The instrument's overall flow: a parameter file is opened by a bit-level reader (no forward pass); "
                    "analysis panels read meaning and structure while edit panels reversibly modify the file; every edit is "
                    "journaled to a byte-exact genome enabling exact revert.", 240, "".join(b)))
    # FIG 2 — decompiler + bit-edit
    b = []
    b.append(box(30, 46, 120, 46, "token “cat”"))
    b.append(box(190, 40, 150, 58, "stored embedding row (dequantized bits)"))
    b.append(box(390, 40, 175, 58, "nearest stored tokens: kitten, feline, gato…"))
    b.append(arrow(150, 69, 188, 69))
    b.append(arrow(340, 69, 388, 69, "cosine"))
    b.append(box(190, 130, 150, 54, "bit-edit: row ← (1−a)·cat + a·dog, re-quantized in place"))
    b.append(box(390, 132, 175, 50, "re-read neighbors: dog, puppy, canine…"))
    b.append(arrow(265, 98, 265, 128, "edit"))
    b.append(arrow(340, 157, 388, 157, "re-decompile"))
    b.append(arrow(478, 132, 478, 100, "before / after", dashed=True))
    F.append(fig(2, "The decompiler reads a token's stored meaning as its nearest stored neighbors, straight from the "
                    "dequantized bits with no inference; a reversible bit-edit interpolates the row toward a target token "
                    "and the changed meaning is re-read immediately (before vs. after).", 230, "".join(b)))
    # FIG 3 — alignment axis
    b = []
    b.append(box(30, 46, 120, 40, "positive concept set P"))
    b.append(box(30, 104, 120, 40, "negative concept set N"))
    b.append(box(200, 66, 150, 58, "axis d̂ = (mean ÊP − mean ÊN) / ‖·‖"))
    b.append(box(400, 40, 175, 44, "vocabulary projected on d̂ (the SIGHT): toward pole / away pole"))
    b.append(box(400, 108, 175, 48, "move token i by β: E′[i]=E[i]+β‖E[i]‖d̂ (journaled)"))
    b.append(box(630, 74, 165, 60, "measure ⟨E[i],d̂⟩ and neighbors, before / after"))
    b.append(arrow(150, 66, 198, 82))
    b.append(arrow(150, 124, 198, 108))
    b.append(arrow(350, 82, 398, 66, "see"))
    b.append(arrow(350, 100, 398, 128, "then move"))
    b.append(arrow(575, 132, 628, 110, "reversible"))
    F.append(fig(3, "Targeted, sighted alignment: an axis is formed from contrasting concept sets; the whole vocabulary is "
                    "projected onto it so the practitioner sees which meanings it moves before touching a parameter; one "
                    "token is then moved along the axis reversibly, with a measured before/after — the opposite of a "
                    "blind global gradient nudge.", 240, "".join(b)))
