#!/usr/bin/env python3
"""Regenerate todo.html from DIRECTIVES.md.

BRYCE-1787152126912-tv2s6u: "Enforcers, put together a todo list and make sure no
matter where you are in the commons it directs you to keep todo current and check
grounding docs and anything else important that needs to be known every turn."

The first todo.html was a hand-typed table, so it rotted the way hand-typed tables
always do: it still read "5 NOT BUILT" and "12 SPEC'D" hours after both shipped and
DIRECTIVES.md had been corrected. A stale NOT BUILT is not harmless -- it invites a
rebuild over working code and it reports a stalled board to the owner.

So todo.html stops being a second copy of the truth. DIRECTIVES.md is the list; this
writes a view of it. The page ALSO re-parses DIRECTIVES.md in the browser on load, so
it is current even between runs of this script; what this bakes is the fallback that
shows when that fetch cannot run (file://, offline, Pages lag).

Run: python3 todo_gen.py   (writes todo.html, prints the row count)
"""
import html
import re
import sys

SRC = "DIRECTIVES.md"
OUT = "todo.html"

# "### 7. Profile pictures, player-selected, with a default"
HEAD = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
# Status may start a line or sit inline after "**Asked:** ... ·". Both shapes are in
# the file today and neither is wrong, so match the marker anywhere.
STATUS = re.compile(r"\*\*Status:\*\*\s*(.+)")
SECTION = re.compile(r"^##\s+(.+?)\s*$")

# The word that decides the colour. status_word() chooses the earliest bounded token,
# so OPEN wins in "OPEN. Not LANDED" and NOT BUILT is never read as BUILT.
WORDS = ["NOT BUILT", "LANDED", "BUILT", "MEASURED", "PARTIAL", "SPLIT", "HALF",
         "OPEN", "SPEC'D", "CLOSED", "DONE"]


def status_word(status):
    """Return the first status token, not a later negated token.

    A status such as ``OPEN. Not LANDED.`` must stay OPEN. The old fixed-order
    substring scan found LANDED later in that sentence and painted an unfinished
    directive green.
    """
    up = status.upper()
    hits = []
    for word in WORDS:
        match = re.search(r"(?<![A-Z])%s(?![A-Z])" % re.escape(word), up)
        if match:
            hits.append((match.start(), -len(word), word))
    return min(hits)[2] if hits else "OPEN"


def parse(text):
    rows, section, cur = [], "", None
    for line in text.split("\n"):
        m = SECTION.match(line)
        if m:
            section = m.group(1).split("(")[0].strip()
            continue
        m = HEAD.match(line)
        if m:
            cur = {"n": int(m.group(1)), "title": m.group(2),
                   "status": "", "word": "OPEN", "section": section}
            rows.append(cur)
            continue
        if cur is None:
            continue
        if cur.get("done"):
            continue
        if cur["status"]:
            # A status sentence can wrap. Keep pulling continuation lines until a blank
            # line or the next bolded field, or item 11 truncates at "published titles, byte".
            if line.strip() and not line.startswith(("**", ">", "#", "-")):
                cur["status"] += " " + line.strip()
                continue
            cur["done"] = True
            continue
        m = STATUS.search(line)
        if m:
            cur["status"] = m.group(1).strip()
    for r in rows:
        s = re.sub(r"\s+", " ", r["status"]).strip()
        # one sentence of it -- the rest is receipts, which belong in the file
        s = re.split(r"(?<=[a-z0-9`)])\.\s", s)[0].strip().rstrip(".")
        up = s.upper()
        r["word"] = status_word(s)
        # do not print "BUILT BUILT 2026-08-19 -- ..."; the badge already says the word
        if up.startswith(r["word"]):
            s = s[len(r["word"]):].lstrip(" .,:\u2014-")
        r["status"] = s
        r.pop("done", None)
    return rows


def strip_md(s):
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    return s


def render(rows):
    out = []
    for r in rows:
        cls = r["word"].lower().replace(" ", "-").replace("'", "")
        out.append(
            '<tr><td>%d</td><td>%s</td><td><b class="s-%s">%s</b> %s</td><td>%s</td></tr>'
            % (r["n"], html.escape(strip_md(r["title"])), cls, html.escape(r["word"]),
               html.escape(strip_md(r["status"])[:200]), html.escape(r["section"])))
    return "\n".join(out)


def project(page, directives):
    rows = parse(directives)
    if not rows:
        raise ValueError("parsed 0 directives -- refusing to write an empty todo")
    if '<tbody id="rows">' not in page:
        raise ValueError('todo.html has no <tbody id="rows"> to fill')
    new, replacements = re.subn(r'(<tbody id="rows">).*?(</tbody>)',
                                lambda m: m.group(1) + "\n" + render(rows) + "\n" + m.group(2),
                                page, count=1, flags=re.S)
    if replacements != 1:
        raise ValueError("todo.html has no closing </tbody> for rows")
    return new, rows


def main():
    page = open(OUT, encoding="utf-8").read()
    try:
        new, rows = project(page, open(SRC, encoding="utf-8").read())
    except ValueError as exc:
        print("todo_gen: %s" % exc, file=sys.stderr)
        return 1
    open(OUT, "w", encoding="utf-8").write(new)
    print("todo_gen: %d directives baked into %s" % (len(rows), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
