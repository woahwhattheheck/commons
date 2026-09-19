#!/usr/bin/env python3
"""Print-pagination renderer and page inspector (UIOWA-123).

WHY THIS EXISTS
---------------
An assessment report that is correct on screen can be unreadable on paper. The
defects are specific and boring: a finding runs off the bottom of the page, a
section heading sits alone as the last line with its body overleaf, a wide
table continues onto page 4 with its header row left behind on page 3, a source
locator breaks mid-string so nobody can follow the citation.

This module renders a report to real PDF and then INSPECTS EVERY PAGE
geometrically for exactly those four defects. It ships two renderers on
purpose:

    NAIVE  -- paginates by counting blocks instead of measuring them, the way
              a first implementation usually does. It produces all four
              defects.
    FIXED  -- measures every block after wrapping, keeps headings with their
              body, repeats table headers on continuation pages, and keeps
              citations atomic.

The naive renderer is a NEGATIVE CONTROL. An inspector that has never gone red
is not evidence of anything, so the test suite asserts the inspector finds the
defects in NAIVE and finds none in FIXED. Both PDFs ship.

THE RULE THAT OUTRANKS LOOKING TIDY
-----------------------------------
**No text is ever dropped to make a page fit.** Clipping, truncating, or
eliding a cell to keep a table inside the margin would produce a clean-looking
page that has silently deleted evidence from the report. The fixed renderer
wraps instead, and `audit_text_conservation()` compares every non-whitespace
character of the source document against every character actually placed on a
page. If one character goes missing the audit fails. A test asserts this.

HONEST LIMIT -- READ THIS
-------------------------
The order's completion bar says "every page is visually checked". Every page
here is checked GEOMETRICALLY, by measuring the box of every placed glyph run
against the content box. That is stronger than eyeballing in coverage (it
examines every run on every page) and weaker in kind (it cannot see that a
table is ugly, or that a colour is unreadable). No human has looked at these
PDFs. That step is listed as OUTSTANDING in README.md and the PDFs are shipped
so it can actually be done.

Fonts: the base-14 Courier family only. Courier is metrically exact -- every
glyph advances 600/1000 em at any size -- so text measurement needs no font
file, no metrics table, and no guessed widths. Nothing is embedded, nothing is
downloaded, and every measurement in this file is arithmetic that can be
checked by hand.

Python 3 standard library only. No network. Deterministic.
"""

import argparse
import json
import os
import sys
import zlib
from collections import OrderedDict

# --------------------------------------------------------------------------
# Page geometry. US Letter, 0.75in margins, in PDF points (1/72 inch).
# --------------------------------------------------------------------------
PAGE_W = 612.0
PAGE_H = 792.0
MARGIN_L = 54.0
MARGIN_R = 54.0
MARGIN_T = 54.0
MARGIN_B = 54.0

CONTENT_L = MARGIN_L
CONTENT_R = PAGE_W - MARGIN_R
CONTENT_TOP = PAGE_H - MARGIN_T
CONTENT_BOTTOM = MARGIN_B
CONTENT_W = CONTENT_R - CONTENT_L

# Courier advance width, in em/1000. This is a fixed property of the base-14
# Courier font, which is why this renderer uses it: the number is exact and
# needs no font file to justify.
COURIER_ADVANCE = 600.0 / 1000.0

BODY_SIZE = 9.0
H1_SIZE = 15.0
H2_SIZE = 12.0
H3_SIZE = 10.0
LINE_FACTOR = 1.38
SPACE_BEFORE = {1: 14.0, 2: 11.0, 3: 8.0}

FICTION_BANNER = (
    "FICTIONAL CONTENT. Example State University is an invented organization. "
    "No finding, citation, locator or figure here describes the University of "
    "Iowa or any real institution, system or person."
)


def char_width(size):
    return size * COURIER_ADVANCE


def text_width(text, size):
    return len(text) * char_width(size)


def line_height(size):
    return size * LINE_FACTOR


def max_chars(width, size):
    """How many Courier glyphs fit in `width`. Exact, not an estimate."""
    per = char_width(size)
    if per <= 0:
        return 0
    return int(width // per)


def wrap(text, width, size):
    """Greedy wrap at spaces. A token longer than the line is hard-split rather
    than allowed to overflow -- but it is never DROPPED, which is the part that
    matters. See audit_text_conservation()."""
    limit = max_chars(width, size)
    if limit <= 0:
        return [text] if text else [""]
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], ""
    for word in words:
        while len(word) > limit:
            # An unbreakable token wider than the column. Split it rather than
            # let it run past the margin; losing it would be worse than both.
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(word[:limit])
            word = word[limit:]
        candidate = word if not cur else cur + " " + word
        if len(candidate) <= limit:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Placed output model. The inspector reads THIS, not the PDF bytes, because a
# defect is a geometry fact and should be findable without parsing a PDF.
# --------------------------------------------------------------------------

class Run(object):
    """One line of text placed at an absolute position on a page."""

    __slots__ = ("text", "x", "baseline", "size", "bold", "block_id",
                 "block_kind", "role")

    def __init__(self, text, x, baseline, size, bold, block_id, block_kind, role):
        self.text = text
        self.x = x
        self.baseline = baseline
        self.size = size
        self.bold = bold
        self.block_id = block_id
        self.block_kind = block_kind
        self.role = role

    @property
    def x_end(self):
        return self.x + text_width(self.text, self.size)

    @property
    def top(self):
        return self.baseline + self.size * 0.8

    @property
    def bottom(self):
        return self.baseline - self.size * 0.25

    def as_dict(self):
        return OrderedDict([
            ("text", self.text), ("x", round(self.x, 2)),
            ("baseline", round(self.baseline, 2)), ("size", self.size),
            ("block_id", self.block_id), ("block_kind", self.block_kind),
            ("role", self.role),
        ])


# --------------------------------------------------------------------------
# Document loading
# --------------------------------------------------------------------------

class DocumentError(Exception):
    """Malformed document input. Collects every problem before raising."""


VALID_KINDS = ("heading", "paragraph", "citation", "table")

# Typographic characters that the base-14 WinAnsi encoding cannot carry, with
# an ASCII rendering that means the same thing. Applied ONCE at load time so
# layout, the conservation audit and the PDF all see identical text, and
# RECORDED so the substitution appears in the output rather than happening
# behind the reader's back. Anything not in this table is left alone and
# reported by unencodable_characters() -- inventing an ASCII stand-in for a
# character we do not understand would be the silent loss this module exists
# to prevent.
TRANSLITERATE = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00a0": " ",    # non-breaking space
    "\u2212": "-",    # minus sign
    "\u2022": "*",    # bullet
}


def _translit(text, tally):
    if not isinstance(text, str):
        return text
    for src, dst in TRANSLITERATE.items():
        if src in text:
            tally[src] = tally.get(src, 0) + text.count(src)
            text = text.replace(src, dst)
    return text


def normalize_document(doc):
    """Apply TRANSLITERATE across every text field, recording what changed."""
    tally = {}
    doc["title"] = _translit(doc.get("title", ""), tally)
    for blk in doc.get("blocks", []):
        if "text" in blk:
            blk["text"] = _translit(blk["text"], tally)
        if "caption" in blk and blk["caption"]:
            blk["caption"] = _translit(blk["caption"], tally)
        if "lines" in blk:
            blk["lines"] = [_translit(x, tally) for x in blk["lines"]]
        if "headers" in blk:
            blk["headers"] = [_translit(x, tally) for x in blk["headers"]]
        if "rows" in blk:
            blk["rows"] = [[_translit(str(c), tally) for c in row]
                           for row in blk["rows"]]
    doc["_transliterations"] = OrderedDict(sorted(tally.items()))
    return doc


def load_document(path):
    if not os.path.exists(path):
        raise DocumentError("missing document file: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as exc:
        raise DocumentError("%s is not valid JSON: %s"
                            % (os.path.basename(path), exc))

    problems = []
    if not isinstance(doc, dict):
        raise DocumentError("document must be a JSON object")
    if "title" not in doc:
        problems.append("document is missing 'title'")
    blocks = doc.get("blocks")
    if not isinstance(blocks, list):
        raise DocumentError("document 'blocks' must be a list")

    seen = set()
    for idx, blk in enumerate(blocks):
        label = "blocks[%d] %s" % (idx, blk.get("id", "<no id>"))
        if "id" not in blk:
            problems.append("%s is missing 'id'" % label)
        elif blk["id"] in seen:
            problems.append("duplicate block id %r" % blk["id"])
        else:
            seen.add(blk["id"])
        kind = blk.get("kind")
        if kind not in VALID_KINDS:
            problems.append("%s has unknown kind %r (expected one of %s)"
                            % (label, kind, ", ".join(VALID_KINDS)))
            continue
        if kind == "heading":
            if blk.get("level") not in (1, 2, 3):
                problems.append("%s heading level must be 1, 2 or 3" % label)
            if not blk.get("text"):
                problems.append("%s heading has no text" % label)
        elif kind == "paragraph":
            if not blk.get("text"):
                problems.append("%s paragraph has no text" % label)
        elif kind == "citation":
            if not blk.get("lines"):
                problems.append("%s citation has no lines" % label)
        elif kind == "table":
            headers = blk.get("headers")
            rows = blk.get("rows")
            if not headers:
                problems.append("%s table has no headers" % label)
            if not isinstance(rows, list) or not rows:
                problems.append("%s table has no rows" % label)
            elif headers:
                for r_i, row in enumerate(rows):
                    if len(row) != len(headers):
                        problems.append(
                            "%s row %d has %d cells but there are %d headers"
                            % (label, r_i, len(row), len(headers)))

    if problems:
        raise DocumentError("%d document problem(s): %s"
                            % (len(problems), " | ".join(problems)))
    return normalize_document(doc)


# --------------------------------------------------------------------------
# Column sizing for tables
# --------------------------------------------------------------------------

GUTTER = 6.0


def compute_columns(headers, rows, size, avail):
    """Give every column a share of the available width proportional to its
    widest content, with a floor, then scale to fit.

    Columns are never dropped and cells are never truncated -- a column too
    narrow for its content wraps onto more lines. That is the whole point: a
    wide table costs vertical space, it does not cost evidence.
    """
    ncols = len(headers)
    gutters = GUTTER * (ncols - 1)
    usable = avail - gutters
    natural = []
    for c in range(ncols):
        widest = len(headers[c])
        for row in rows:
            widest = max(widest, len(str(row[c])))
        natural.append(max(widest, 4))
    total = float(sum(natural))
    floor_chars = 6
    floor_w = floor_chars * char_width(size)
    widths = []
    for n in natural:
        widths.append(max(floor_w, usable * (n / total)))
    # Scaling up from the floors can overshoot; renormalize.
    over = sum(widths) - usable
    if over > 0:
        shrinkable = [i for i, w in enumerate(widths) if w > floor_w]
        pool = sum(widths[i] - floor_w for i in shrinkable)
        if pool > 0:
            for i in shrinkable:
                widths[i] -= over * ((widths[i] - floor_w) / pool)
    return widths


def table_row_lines(cells, widths, size):
    """Wrap every cell, then return the row as a list of line-tuples."""
    wrapped = [wrap(str(cells[c]), widths[c], size) for c in range(len(cells))]
    height = max(len(w) for w in wrapped)
    out = []
    for i in range(height):
        out.append([w[i] if i < len(w) else "" for w in wrapped])
    return out


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

class Layout(object):
    def __init__(self, mode):
        assert mode in ("naive", "fixed")
        self.mode = mode
        self.pages = [[]]
        self.y = CONTENT_TOP

    @property
    def page_index(self):
        return len(self.pages) - 1

    def new_page(self):
        self.pages.append([])
        self.y = CONTENT_TOP

    def room(self):
        return self.y - CONTENT_BOTTOM

    def place(self, text, x, size, bold, block_id, block_kind, role):
        lh = line_height(size)
        baseline = self.y - size * 0.8
        self.pages[-1].append(
            Run(text, x, baseline, size, bold, block_id, block_kind, role))
        self.y -= lh

    def need(self, height):
        """Break to a new page if `height` will not fit.

        THE NAIVE BUG LIVES HERE. In naive mode the caller passes the height of
        ONE line regardless of how many lines the block will actually occupy,
        because it counted blocks instead of measuring them. So a block that
        wraps to eleven lines is admitted on the strength of one line fitting,
        and the remaining ten run off the bottom of the page. This is the most
        common real pagination bug there is: estimating instead of measuring.
        """
        if self.room() < height:
            self.new_page()
            return True
        return False


def render_blocks(doc, mode):
    lay = Layout(mode)

    # Title block, first page.
    for line in wrap(doc["title"], CONTENT_W, H1_SIZE):
        lay.place(line, CONTENT_L, H1_SIZE, True, "__title__", "heading", "title")
    lay.y -= 4.0
    for line in wrap(FICTION_BANNER, CONTENT_W, BODY_SIZE):
        lay.place(line, CONTENT_L, BODY_SIZE, False, "__banner__",
                  "paragraph", "banner")
    lay.y -= 10.0

    blocks = doc["blocks"]
    for i, blk in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        _render_block(lay, blk, nxt, mode)
    return lay.pages


def _heading_size(level):
    return {1: H1_SIZE, 2: H2_SIZE, 3: H3_SIZE}[level]


def _render_block(lay, blk, nxt, mode):
    kind = blk["kind"]

    if kind == "heading":
        size = _heading_size(blk["level"])
        lay.y -= SPACE_BEFORE[blk["level"]]
        lines = wrap(blk["text"], CONTENT_W, size)
        block_h = len(lines) * line_height(size)
        if mode == "naive":
            # Reserves one line. A heading therefore lands at the very bottom
            # of a page with its body pushed overleaf -- an orphaned heading.
            lay.need(line_height(size))
        else:
            # keep-with-next: the heading and at least the first two lines of
            # whatever follows must fit together, or both move to a new page.
            follow = 2 * line_height(BODY_SIZE) if nxt else 0.0
            lay.need(block_h + follow)
        for line in lines:
            lay.place(line, CONTENT_L, size, True, blk["id"], "heading",
                      "h%d" % blk["level"])
        lay.y -= 2.0
        return

    if kind == "paragraph":
        lines = wrap(blk["text"], CONTENT_W, BODY_SIZE)
        lh = line_height(BODY_SIZE)
        if mode == "naive":
            lay.need(lh)  # one line reserved for a block that may need twenty
            for line in lines:
                lay.place(line, CONTENT_L, BODY_SIZE, False, blk["id"],
                          "paragraph", "body")
        else:
            for line in lines:
                lay.need(lh)  # measured per line; a paragraph may split, text may not vanish
                lay.place(line, CONTENT_L, BODY_SIZE, False, blk["id"],
                          "paragraph", "body")
        lay.y -= 4.0
        return

    if kind == "citation":
        indent = 12.0
        width = CONTENT_W - indent
        all_lines = []
        for src in blk["lines"]:
            all_lines.extend(wrap(src, width, BODY_SIZE))
        lh = line_height(BODY_SIZE)
        block_h = len(all_lines) * lh
        if mode == "naive":
            pass  # no keep-together at all; see the per-line break below
        else:
            # A citation is atomic. A source locator broken across a page break
            # cannot be followed, so the whole block moves. If it is taller
            # than a full page it must split -- refusing would lose it.
            if block_h <= (CONTENT_TOP - CONTENT_BOTTOM):
                lay.need(block_h)
            else:
                lay.need(lh)
        for line in all_lines:
            # Both modes break per line here. The difference is above: the
            # fixed renderer has already moved the whole citation to a fresh
            # page if it would not fit, so this break never fires mid-block.
            # The naive renderer has not, so a source locator gets torn in
            # half at whatever line the page happens to end on.
            lay.need(lh)
            lay.place(line, CONTENT_L + indent, BODY_SIZE, False, blk["id"],
                      "citation", "citation")
        lay.y -= 5.0
        return

    if kind == "table":
        _render_table(lay, blk, mode)
        return

    raise DocumentError("unhandled block kind %r" % kind)


def _render_table(lay, blk, mode):
    size = BODY_SIZE
    lh = line_height(size)
    headers = blk["headers"]
    rows = blk["rows"]

    if blk.get("caption"):
        for line in wrap(blk["caption"], CONTENT_W, size):
            if mode == "fixed":
                lay.need(lh)
            lay.place(line, CONTENT_L, size, True, blk["id"], "table", "caption")

    if mode == "naive":
        # THE NAIVE TABLE BUGS, both real and both common:
        #  1. Columns are sized to their natural content width with no check
        #     against the content box, so a wide table runs past the right
        #     margin and the last column is clipped off the page.
        #  2. The header row is written once. Rows that land on a later page
        #     arrive with no header, so nobody can tell what the columns mean.
        widths = [max(len(headers[c]),
                      max(len(str(r[c])) for r in rows)) * char_width(size)
                  for c in range(len(headers))]
    else:
        widths = compute_columns(headers, rows, size, CONTENT_W)

    def emit_header():
        for line_cells in table_row_lines(headers, widths, size):
            _emit_cells(lay, line_cells, widths, size, True, blk["id"], "header")

    if mode == "fixed":
        lay.need(lh * 3)  # never start a table with only its header on the page
    emit_header()

    page_h = CONTENT_TOP - CONTENT_BOTTOM
    for row in rows:
        line_cells_list = table_row_lines(row, widths, size)
        need_h = lh * len(line_cells_list)
        if mode == "fixed" and need_h <= page_h and lay.room() < need_h:
            # The row fits on a page, just not on this one. Move it whole so a
            # single logical row is never torn across the break.
            lay.new_page()
            emit_header()  # continuation pages repeat the header
        for line_cells in line_cells_list:
            if mode == "naive":
                lay.need(lh)  # may cross the page with no header behind it
            elif lay.room() < lh:
                # A row TALLER than a whole page has nowhere to be moved to, so
                # it must split -- found by a hostile test feeding one cell more
                # content than a page can hold. Before this, such a row was
                # emitted in full and simply ran off the bottom. Splitting it
                # keeps every line on a page, and the header is re-emitted so
                # the continuation is still labelled.
                lay.new_page()
                emit_header()
            _emit_cells(lay, line_cells, widths, size, False, blk["id"], "cell")
    lay.y -= 6.0


def _emit_cells(lay, cells, widths, size, bold, block_id, role):
    x = CONTENT_L
    baseline_y = lay.y
    for c, cell in enumerate(cells):
        if cell:
            lay.pages[-1].append(
                Run(cell, x, baseline_y - size * 0.8, size, bold, block_id,
                    "table", role))
        x += widths[c] + GUTTER
    lay.y -= line_height(size)


# --------------------------------------------------------------------------
# Page inspection -- the four defects named in the work order
# --------------------------------------------------------------------------

DEFECT_MEANINGS = OrderedDict([
    ("CLIPPED_TEXT",
     "A glyph run falls outside the printable content box. On paper this text "
     "is cut off at the page edge and cannot be read at all."),
    ("ORPHANED_HEADING",
     "A heading is the last thing on its page and the body it introduces "
     "begins on the next page. The reader turns the page to find out what the "
     "heading was about."),
    ("TABLE_HEADER_SEPARATED",
     "Table rows continue onto a page whose header row was left behind. The "
     "columns on that page are unlabelled."),
    ("CITATION_SPLIT",
     "A citation block is broken across a page boundary, so a source locator "
     "is torn in half and the reference cannot be followed."),
])


def inspect_pages(pages):
    """Check every run on every page. Returns a list of defect dicts."""
    defects = []

    for p_i, runs in enumerate(pages):
        for run in runs:
            if run.bottom < CONTENT_BOTTOM - 0.01:
                defects.append(_defect(
                    "CLIPPED_TEXT", p_i, run.block_id,
                    "run bottom %.1fpt is below the content box floor %.1fpt "
                    "(text ran off the bottom of the page)"
                    % (run.bottom, CONTENT_BOTTOM), run.text))
            elif run.x_end > CONTENT_R + 0.01:
                defects.append(_defect(
                    "CLIPPED_TEXT", p_i, run.block_id,
                    "run ends at x=%.1fpt, past the right margin %.1fpt "
                    "(column runs off the side of the page)"
                    % (run.x_end, CONTENT_R), run.text))
            elif run.top > CONTENT_TOP + 0.01:
                defects.append(_defect(
                    "CLIPPED_TEXT", p_i, run.block_id,
                    "run top %.1fpt is above the content box ceiling %.1fpt"
                    % (run.top, CONTENT_TOP), run.text))

    # Where does each block appear?
    first_page, last_page, order = {}, {}, []
    for p_i, runs in enumerate(pages):
        for run in runs:
            if run.block_id not in first_page:
                first_page[run.block_id] = p_i
                order.append(run.block_id)
            last_page[run.block_id] = p_i

    kind_of, role_of = {}, {}
    for runs in pages:
        for run in runs:
            kind_of.setdefault(run.block_id, run.block_kind)
            role_of.setdefault(run.block_id, run.role)

    for i, bid in enumerate(order):
        if kind_of.get(bid) != "heading" or bid == "__title__":
            continue
        nxt = order[i + 1] if i + 1 < len(order) else None
        if nxt is None:
            continue
        if first_page[nxt] > last_page[bid]:
            defects.append(_defect(
                "ORPHANED_HEADING", last_page[bid], bid,
                "heading ends on page %d but its following block %s starts on "
                "page %d" % (last_page[bid] + 1, nxt, first_page[nxt] + 1),
                _first_text(pages, bid)))

    # Table headers: every page carrying cells of a table must also carry that
    # table's header row.
    tables = {}
    for p_i, runs in enumerate(pages):
        for run in runs:
            if run.block_kind == "table" and run.role in ("header", "cell"):
                tables.setdefault(run.block_id, {}).setdefault(
                    p_i, set()).add(run.role)
    for bid, per_page in sorted(tables.items()):
        for p_i in sorted(per_page):
            roles = per_page[p_i]
            if "cell" in roles and "header" not in roles:
                defects.append(_defect(
                    "TABLE_HEADER_SEPARATED", p_i, bid,
                    "table rows appear on page %d with no header row on that "
                    "page" % (p_i + 1), ""))

    # Citations must not straddle a page boundary.
    for bid, kind in sorted(kind_of.items()):
        if kind != "citation":
            continue
        if last_page[bid] != first_page[bid]:
            defects.append(_defect(
                "CITATION_SPLIT", first_page[bid], bid,
                "citation spans pages %d-%d, breaking a source locator across "
                "the page break"
                % (first_page[bid] + 1, last_page[bid] + 1),
                _first_text(pages, bid)))

    defects.sort(key=lambda d: (d["page"], d["defect"], d["block_id"]))
    return defects


def _first_text(pages, block_id):
    for runs in pages:
        for run in runs:
            if run.block_id == block_id:
                return run.text
    return ""


def _defect(name, page_index, block_id, detail, sample):
    return OrderedDict([
        ("defect", name), ("page", page_index + 1), ("block_id", block_id),
        ("detail", detail), ("sample_text", sample[:90]),
    ])


def audit_text_conservation(doc, pages):
    """Every non-whitespace character of the document must reach a page.

    This is the guard against the tempting fix: clip the cell, elide the line,
    truncate the locator, and the page looks clean. A report that drops
    evidence to fit the margin is worse than an ugly one, so this audit is a
    hard check rather than a warning.

    Compared as MULTISETS, not as ordered strings. Two legitimate behaviours
    make an ordered comparison wrong: a table is placed column-major within
    each wrapped line while the source reads row-major, and the fixed renderer
    repeats a table header on every continuation page on purpose. Neither
    loses a character, which is the property being guaranteed.
    """
    import collections as _c
    src = []
    src.append(doc["title"])
    src.append(FICTION_BANNER)
    for blk in doc["blocks"]:
        if blk["kind"] == "heading":
            src.append(blk["text"])
        elif blk["kind"] == "paragraph":
            src.append(blk["text"])
        elif blk["kind"] == "citation":
            src.extend(blk["lines"])
        elif blk["kind"] == "table":
            if blk.get("caption"):
                src.append(blk["caption"])
            src.extend(blk["headers"])
            for row in blk["rows"]:
                src.extend(str(c) for c in row)
    want = "".join("".join(s.split()) for s in src)

    got = []
    for runs in pages:
        for run in runs:
            got.append("".join(run.text.split()))
    got = "".join(got)
    missing = dict(_c.Counter(want) - _c.Counter(got))

    return OrderedDict([
        ("source_chars", len(want)),
        ("placed_chars", len(got)),
        ("no_text_lost", not missing),
        ("missing_char_counts", missing),
        ("added_chars", max(0, len(got) - len(want))),
        ("note",
         "Compared as character multisets over non-whitespace characters. "
         "no_text_lost is the guarantee that matters: every character of the "
         "source reaches a page. Ordered comparison would be the wrong test "
         "-- a table wraps column-major while the source reads row-major, and "
         "the fixed renderer deliberately REPEATS a table header on each "
         "continuation page, so placed_chars legitimately exceeds "
         "source_chars. Note this audit says nothing about whether placed "
         "text is READABLE: the naive renderer also loses nothing here, "
         "because it places its overflow below the bottom of the page rather "
         "than dropping it. CLIPPED_TEXT is the check that catches that."),
    ])


# --------------------------------------------------------------------------
# Minimal PDF writer. Base-14 Courier, so nothing is embedded.
# --------------------------------------------------------------------------

def _esc(text):
    return (text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)"))


def _content_stream(runs):
    out = ["BT"]
    cur_font = None
    cur_size = None
    for run in runs:
        font = "/F2" if run.bold else "/F1"
        if font != cur_font or run.size != cur_size:
            out.append("%s %.2f Tf" % (font, run.size))
            cur_font, cur_size = font, run.size
        out.append("1 0 0 1 %.2f %.2f Tm" % (run.x, run.baseline))
        out.append("(%s) Tj" % _esc(run.text))
    out.append("ET")
    return "\n".join(out).encode("latin-1", "replace")


def write_pdf(pages, path, title):
    objects = []           # 1-indexed on append

    def add(body):
        objects.append(body)
        return len(objects)

    font_regular = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier "
                       b"/Encoding /WinAnsiEncoding >>")
    font_bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold "
                    b"/Encoding /WinAnsiEncoding >>")
    pages_obj = add(b"")   # patched below once kids are known

    kids = []
    for runs in pages:
        raw = _content_stream(runs)
        packed = zlib.compress(raw, 9)
        stream = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n"
                     % len(packed) + packed + b"\nendstream")
        page = add(
            ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.0f %.0f] "
             "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
             "/Contents %d 0 R >>"
             % (pages_obj, PAGE_W, PAGE_H, font_regular, font_bold, stream)
             ).encode("latin-1"))
        kids.append(page)

    objects[pages_obj - 1] = (
        "<< /Type /Pages /Count %d /Kids [%s] >>"
        % (len(kids), " ".join("%d 0 R" % k for k in kids))
    ).encode("latin-1")

    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj)
    info = add(("<< /Title (%s) /Producer (UIOWA-123 stdlib print renderer) >>"
                % _esc(title)).encode("latin-1", "replace"))

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objects) + 1)
    for i, body in enumerate(objects, start=1):
        offsets[i] = len(buf)
        buf += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_at = len(buf)
    buf += b"xref\n0 %d\n" % (len(objects) + 1)
    buf += b"0000000000 65535 f \n"
    for i in range(1, len(objects) + 1):
        buf += b"%010d 00000 n \n" % offsets[i]
    buf += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n"
            b"%d\n%%%%EOF\n" % (len(objects) + 1, catalog, info, xref_at))

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return len(kids)


def unencodable_characters(pages):
    """Characters the base-14 WinAnsi encoding cannot carry.

    The PDF writer encodes text as latin-1 with replacement, which means a
    character outside that range becomes a '?' in the file WITHOUT anything
    complaining. That is silent content loss of exactly the kind this module
    exists to prevent, so it is detected and reported rather than tolerated.
    A real fix is an embedded Unicode font, which is out of scope for a
    stdlib-only renderer; naming the limitation is not.
    """
    bad = {}
    for runs in pages:
        for run in runs:
            for ch in run.text:
                try:
                    ch.encode("latin-1")
                except UnicodeEncodeError:
                    bad[ch] = bad.get(ch, 0) + 1
    return OrderedDict(sorted(bad.items()))


def verify_pdf(path, expected_pages, pages=None):
    """Read the file back and confirm it is a structurally sane PDF.

    Not a full parser. It checks the things that break silently: the header,
    the EOF marker, a startxref pointing at an actual 'xref' table, and a page
    count matching what we meant to write.
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    problems = []
    if not blob.startswith(b"%PDF-1."):
        problems.append("missing %PDF header")
    if not blob.rstrip().endswith(b"%%EOF"):
        problems.append("missing %%EOF trailer")
    idx = blob.rfind(b"startxref")
    if idx == -1:
        problems.append("no startxref")
    else:
        try:
            pos = int(blob[idx + 9:].split()[0])
            if blob[pos:pos + 4] != b"xref":
                problems.append("startxref does not point at an xref table")
        except (ValueError, IndexError):
            problems.append("unreadable startxref offset")
    count = blob.count(b"/Type /Page\n") + blob.count(b"/Type /Page ")
    if count != expected_pages:
        problems.append("found %d page objects, expected %d"
                        % (count, expected_pages))
    bad = unencodable_characters(pages) if pages is not None else OrderedDict()
    return OrderedDict([
        ("path", os.path.basename(path)), ("bytes", len(blob)),
        ("pages", expected_pages), ("structurally_valid", not problems),
        ("problems", problems),
        ("unencodable_characters", bad),
        ("all_characters_encodable", not bad),
    ])


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

def render(doc, mode):
    pages = render_blocks(doc, mode)
    return pages, inspect_pages(pages), audit_text_conservation(doc, pages)


def inspection_report_md(mode, pages, defects, audit, pdf_info, doc=None):
    out = []
    a = out.append
    a("# Page inspection — `%s` renderer" % mode)
    a("")
    a("> **%s**" % FICTION_BANNER)
    a("")
    a("Every page was checked **geometrically**: the box of every placed glyph "
      "run on every page was measured against the printable content box. "
      "**No human has visually inspected these pages.** That step is "
      "outstanding — see README.md.")
    a("")
    a("| | |")
    a("|---|---|")
    a("| renderer | `%s` |" % mode)
    a("| pages | %d |" % len(pages))
    a("| glyph runs checked | %d |" % sum(len(p) for p in pages))
    a("| defects found | **%d** |" % len(defects))
    a("| PDF structurally valid | %s |" % pdf_info["structurally_valid"])
    a("| all characters encodable | %s%s |"
      % (pdf_info["all_characters_encodable"],
         "" if pdf_info["all_characters_encodable"] else
         " — %s would be replaced in the PDF"
         % ", ".join("%r" % c for c in pdf_info["unencodable_characters"])))
    a("| no text lost | %s (%d source chars, %d placed; +%d from deliberately "
      "repeated table headers) |"
      % (audit["no_text_lost"], audit["source_chars"], audit["placed_chars"],
         audit["added_chars"]))
    a("")

    tr = (doc or {}).get("_transliterations") or {}
    if tr:
        a("### Characters substituted before rendering")
        a("")
        a("These typographic characters cannot be carried by the base-14 font "
          "encoding. They were replaced once, at load, with a recorded ASCII "
          "equivalent, so the substitution is visible here rather than "
          "appearing as `?` in the PDF.")
        a("")
        a("| Character | Replaced with | Occurrences |")
        a("|---|---|---|")
        for ch, n in tr.items():
            a("| `%s` (U+%04X) | `%s` | %d |"
              % (ch, ord(ch), TRANSLITERATE[ch], n))
        a("")

    counts = OrderedDict((k, 0) for k in DEFECT_MEANINGS)
    for d in defects:
        counts[d["defect"]] += 1
    a("## Defects by class")
    a("")
    a("| Defect | Count | What it does to a reader |")
    a("|---|---|---|")
    for name, meaning in DEFECT_MEANINGS.items():
        a("| `%s` | %d | %s |" % (name, counts[name], meaning))
    a("")

    if defects:
        a("## Every defect, with its page")
        a("")
        a("| Page | Defect | Block | Detail |")
        a("|---|---|---|---|")
        for d in defects:
            a("| %d | `%s` | `%s` | %s |"
              % (d["page"], d["defect"], d["block_id"],
                 d["detail"].replace("|", "\\|")))
    else:
        a("## No defects found")
        a("")
        a("Every glyph run on all %d pages sits inside the content box; no "
          "heading is separated from its body; every page carrying table rows "
          "also carries that table's header row; no citation straddles a page "
          "break." % len(pages))
    a("")
    return "\n".join(out)


def run(doc_path, out_dir, stem=None):
    doc = load_document(doc_path)
    os.makedirs(out_dir, exist_ok=True)
    if stem is None:
        stem = os.path.splitext(os.path.basename(doc_path))[0]
    results = OrderedDict()
    for mode in ("naive", "fixed"):
        pages, defects, audit = render(doc, mode)
        pdf_path = os.path.join(out_dir, "%s_%s.pdf" % (stem, mode))
        n = write_pdf(pages, pdf_path, "%s (%s)" % (doc["title"], mode))
        pdf_info = verify_pdf(pdf_path, n, pages)
        with open(os.path.join(out_dir, "inspection_%s_%s.md" % (stem, mode)),
                  "w", encoding="utf-8") as fh:
            fh.write(inspection_report_md(mode, pages, defects, audit,
                                          pdf_info, doc))
        payload = OrderedDict([
            ("fiction_notice", FICTION_BANNER), ("renderer", mode),
            ("pages", len(pages)),
            ("runs_checked", sum(len(p) for p in pages)),
            ("defects", defects), ("defect_meanings", DEFECT_MEANINGS),
            ("text_conservation", audit), ("pdf", pdf_info),
            ("transliterations", doc.get("_transliterations", {})),
            ("visual_check_by_human", "OUTSTANDING - not performed"),
        ])
        with open(os.path.join(out_dir, "inspection_%s_%s.json" % (stem, mode)),
                  "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        results[mode] = OrderedDict([
            ("pages", len(pages)), ("defects", defects), ("audit", audit),
            ("pdf", pdf_info),
        ])
    return results


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--document", action="append", default=None,
                    help="document JSON; repeatable. Default: all three fixtures.")
    ap.add_argument("--out", default=os.path.join(here, "sample"))
    args = ap.parse_args(argv)
    docs = args.document or [
        os.path.join(here, "fixtures", name) for name in
        ("report_document.json", "boundary_orphan_heading.json",
         "boundary_citation_split.json")]

    print(FICTION_BANNER)
    header = ("%-26s %-6s %5s %8s  %s"
              % ("document", "render", "pages", "defects",
                 "  ".join(k[:5] for k in DEFECT_MEANINGS)))
    print(header)
    print("-" * len(header))
    total_fixed_defects = 0
    for doc_path in docs:
        stem = os.path.splitext(os.path.basename(doc_path))[0]
        try:
            results = run(doc_path, args.out, stem)
        except DocumentError as exc:
            print("DOCUMENT ERROR: %s" % exc, file=sys.stderr)
            return 2
        for mode, res in results.items():
            counts = OrderedDict((k, 0) for k in DEFECT_MEANINGS)
            for d in res["defects"]:
                counts[d["defect"]] += 1
            if mode == "fixed":
                total_fixed_defects += len(res["defects"])
            print("%-26s %-6s %5d %8d  %s   no_text_lost=%s pdf_valid=%s"
                  % (stem[:26], mode, res["pages"], len(res["defects"]),
                     "  ".join("%5d" % counts[k] for k in DEFECT_MEANINGS),
                     res["audit"]["no_text_lost"],
                     res["pdf"]["structurally_valid"]))
    print("")
    print("fixed-renderer defects across all documents: %d" % total_fixed_defects)
    print("VISUAL CHECK BY A HUMAN: OUTSTANDING - not performed. Every page was "
          "checked geometrically; nobody has looked at the PDFs. They are in %s "
          "so that it can be done." % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
