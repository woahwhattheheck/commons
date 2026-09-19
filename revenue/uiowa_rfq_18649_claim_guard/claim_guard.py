#!/usr/bin/env python3
"""Cross-lane prohibited-claim and fiction-labelling guard (OPS-CLAIM-GUARD).

WHY THIS EXISTS
---------------
Every lane in this engagement is bound by the same promises: missing evidence
stays UNKNOWN; no certification, compliance or conformance claim; no maturity
score; no peer percentile; no individual performance scoring; fiction labelled
as fiction; no finding asserted about the real University.

Each lane's own tests prove that lane is internally consistent. None of them
can see across the kit. This tool reads every landed lane and asks one
question: does any delivered file actually make a claim we all said we would
not make?

THE HARD PART -- AND IT IS THE WHOLE PROBLEM
--------------------------------------------
A lane that REFUSES to make a claim contains the same words as a lane that
MAKES one. A file saying

    "no maturity level, readiness level, or tier is computed"

contains every word a naive scanner looks for, and is the *opposite* of a
violation -- it is a lane naming the rule in order to decline it. A word
search flags it. This is not hypothetical: the author's own UIOWA-074 lane
shipped a test that matched the substring "percent" inside its own refusal
text and failed. The assertion was wrong, not the code.

So every match is classified into THREE outcomes, never two:

    ASSERTION  -- the claim is being made. A finding.
    REFUSAL    -- the text names the rule in order to decline it. Reported as
                  positive evidence that the lane knows the rule, not silence.
    AMBIGUOUS  -- the classifier cannot tell. Stays UNKNOWN and is listed for
                  a human. It is NEVER auto-cleared.

That third bucket is the point. A guard that resolves its own uncertainty in
the favourable direction is worse than no guard, because it manufactures
confidence. AMBIGUOUS is a result, not a failure to produce one.

WHAT THIS TOOL REFUSES TO DO
----------------------------
* It does not score, grade, rank or rate a lane. No compliance percentage, no
  per-lane verdict. That would be the same sin one level up. Findings carry an
  exact file:line and the offending text; a human reads them.
* It never writes to a scanned lane. Read-only, and proved rather than
  promised: a test hashes the entire scanned tree before and after a full scan
  and asserts it is byte-identical.
* It does not attempt UNKNOWN-propagation checking. Another seat's lane
  (OPS-UNKNOWN-PROPAGATION) covers that, and duplicating it would be noise.

Python 3 standard library only. No network. Deterministic.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict

# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
# Each pattern is deliberately narrow. A broad pattern produces a pile of
# AMBIGUOUS noise that nobody reads, which is how a guard gets switched off.

RULES = OrderedDict([
    ("CG-01", {
        "name": "CERTIFICATION_CLAIM",
        "patterns": [
            r"\bcertif(y|ied|ication|ies)\b",
            r"\bcompliant\s+with\b",
            r"\bcompliance\s+(status|verdict|determination)\b",
            r"\bconformance\b",
            r"\bconforms?\s+to\b",
            r"\baccredit(ed|ation)\b",
        ],
        "means": "Asserting that the assessed organization is certified, "
                 "compliant or conformant with a standard.",
        "why": "This engagement is an assessment, not a certification body. "
               "The NIST AI RMF is voluntary guidance with nothing to be "
               "conformant to.",
    }),
    ("CG-02", {
        "name": "MATURITY_LEVEL",
        "patterns": [
            r"\bmaturity\s+(level|score|tier|rating|index)\b",
            r"\breadiness\s+(level|score|tier|rating|index)\b",
            r"\b(level|tier)\s+[1-5]\s+(maturity|readiness)\b",
            r"\bmaturity\s+is\s+[1-5]\b",
        ],
        "means": "Reducing the organization to a maturity or readiness "
                 "number.",
        "why": "A single number destroys the distinction between what is "
               "written, what is practised, and what was never assessed.",
    }),
    ("CG-03", {
        "name": "PEER_COMPARISON",
        "patterns": [
            r"\bpercentile\b",
            r"\bbenchmarked\s+against\b",
            r"\bcompared\s+(to|with)\s+(peer|other\s+(institution|universit))",
            r"\bpeer\s+(institution|average|percentile|comparison)\b",
            r"\bindustry\s+average\b",
            r"\btypical\s+(institution|university)\b",
            r"\babove\s+average\s+for\b",
        ],
        "means": "Placing the organization against peers or an industry norm.",
        "why": "No peer dataset was collected. A comparison with no "
               "comparator is an invented number.",
    }),
    ("CG-04", {
        "name": "INDIVIDUAL_SCORING",
        "patterns": [
            r"\b(staff|employee|individual|person|analyst|developer|engineer)s?"
            r"\s+(performance\s+)?(score|rating|ranked|ranking)\b",
            r"\bscore\s+(each|per|every)\s+"
            r"(staff|employee|individual|person|developer)\b",
            r"\brate\s+(individual|staff|employee)s?\b",
            r"\bper-?person\s+(score|rating|metric)\b",
        ],
        "means": "Scoring or ranking a named person rather than a role or a "
                 "capability.",
        "why": "The unit of accountability in this engagement is a ROLE. "
               "Individual performance scoring was excluded from scope.",
    }),
    ("CG-05", {
        "name": "REAL_UNIVERSITY_FINDING",
        "patterns": [
            r"\bthe\s+University\s+of\s+Iowa\b",
        ],
        "means": "Stating something about the real University as though it "
                 "were an observed finding.",
        "why": "No fieldwork has been performed. Every record in this kit is "
               "synthetic, and a synthetic record presented as a real finding "
               "is the most damaging thing this kit could ship.",
    }),
])

# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
# Markers that turn a clause from a claim into a declination of a claim.
# Ordered longest-first only for readability; membership is what matters.
REFUSAL_MARKERS = (
    "must not", "does not", "do not", "did not", "is not", "are not",
    "was not", "were not", "will not", "cannot", "can not", "could not",
    "should not", "shall not", "never", "no ", "not ", "n't",
    "refus", "declin", "prohibit", "forbid", "disallow", "exclude",
    "excluded", "without", "rather than", "instead of", "out of scope",
    "not attempted", "deliberately", "avoid", "makes no", "make no",
    "produces no", "produce no", "reports no", "report no", "free of",
    "absent", "nothing", "none", "neither", "no such", "not a",
    "free from", "stripped of", "omit",
)

# Markers that make a clause read as a statement OF FACT about the subject.
ASSERTION_MARKERS = (
    " is ", " are ", " was ", " were ", " has ", " have ", " achieved",
    " scored", " rated", " assessed as", " determined to be", " found to be",
    " meets ", " satisfies ", " demonstrates ", " ranks ", " places ",
)

# A number sitting next to the match is strong evidence of a real claim:
# nobody quantifies a thing they are declining to say. Only consulted when no
# refusal marker is present, so it cannot override a negation.
QUANTIFIER_WINDOW = 30
# A standalone number, not a digit inside an identifier. Without the guard on
# the left, rule ids like "CG-01" in a heading read as a quantified claim.
QUANTITY = re.compile(r"(?<![A-Za-z0-9_-])\d+")

# Negation that attaches to the VERB governing the match, e.g. "maturity level
# is not computed". Needed because a negation sitting after the match does not
# necessarily govern it: in "the University of Iowa has no retention schedule"
# the "no" negates the schedule, not the claim about the University. Treating
# any later negation as a refusal let a real assertion through -- caught by the
# planted-assertion fixture, where CG-05 silently classified as REFUSAL.
VERBAL_NEGATION = re.compile(
    r"\b(is|are|was|were|be|been|being|will|shall|can|could|would|may|might|"
    r"do|does|did|has|have|had)\s+(not|never)\b")
AFTER_WINDOW = 60

ASSERTION, REFUSAL, AMBIGUOUS = "ASSERTION", "REFUSAL", "AMBIGUOUS"
CLASSIFICATIONS = (ASSERTION, REFUSAL, AMBIGUOUS)

FICTION_MARKERS = ("fiction", "fictional", "synthetic", "invented",
                   "illustrative", "not real", "made up", "fabricated",
                   "example state university", "sample data")


def classify(clause, match_span=None):
    """Classify one clause containing a rule match.

    Conservative on purpose: REFUSAL requires an explicit marker, ASSERTION
    requires an explicit statement-of-fact marker, and anything else lands in
    AMBIGUOUS for a person to read. The classifier never resolves its own
    uncertainty in the direction that produces a clean report.
    """
    low = clause.lower()
    if match_span is None:
        before, after = low, ""
    else:
        before = low[:match_span[0]]
        after = low[match_span[1]:match_span[1] + AFTER_WINDOW]

    # A negation governs the claim if it comes BEFORE it ("no maturity level
    # is computed") or is a verbal negation just after it ("maturity level is
    # not computed"). A negation later in the clause attached to some other
    # noun does not clear the claim.
    if any(m in before for m in REFUSAL_MARKERS):
        return REFUSAL
    if VERBAL_NEGATION.search(after):
        return REFUSAL
    if any(m in low for m in ASSERTION_MARKERS):
        return ASSERTION
    if match_span is not None:
        lo = max(0, match_span[0] - QUANTIFIER_WINDOW)
        hi = min(len(clause), match_span[1] + QUANTIFIER_WINDOW)
        if QUANTITY.search(clause[lo:hi]):
            return ASSERTION
    return AMBIGUOUS


PROSE_SUFFIXES = (".md", ".txt", ".rst")

# Markdown emphasis has to come off before matching. "**not** as a
# certification checklist" is a refusal, but the marker "not " never matches
# because the text is literally "not**". This tool's own scan of the author's
# UIOWA-074 lane classified that line as an ASSERTION until this existed.
EMPHASIS = re.compile(r"[*_`~]+")
WS = re.compile(r"\s+")


def normalize(clause):
    return WS.sub(" ", EMPHASIS.sub("", clause)).strip()


CLAUSE_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n|\|")


def blocks_of(lines, prose):
    """Yield (start_line_number, text) blocks to be clause-split.

    For prose, consecutive non-blank lines are JOINED first. A sentence wrapped
    across two source lines would otherwise be cut in half, and the half
    carrying the negation would be lost -- which turns "Nothing is benchmarked
    against peer institutions" into an apparent assertion. This was a real
    false positive on the planted-refusal fixture before the join existed.
    Markdown headings and table rows stay on their own so a heading does not
    absorb the paragraph under it.
    """
    if not prose:
        for i, line in enumerate(lines, start=1):
            yield i, line
        return
    buf, start = [], None
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        standalone = (not stripped or stripped.startswith("#")
                      or stripped.startswith("|") or stripped.startswith("```")
                      or stripped.startswith("- ") or stripped.startswith("* "))
        if standalone:
            if buf:
                yield start, " ".join(buf)
                buf, start = [], None
            if stripped:
                yield i, line
            continue
        if not buf:
            start = i
        buf.append(stripped)
    if buf:
        yield start, " ".join(buf)


def clauses_of(line):
    """Split a line into clauses. Table cells (|) are separate clauses --
    a Markdown row can hold a claim and its refusal in different cells."""
    parts = [c.strip() for c in CLAUSE_SPLIT.split(line) if c and c.strip()]
    return parts or [line.strip()]


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

TEXT_SUFFIXES = (".md", ".py", ".json", ".csv", ".txt", ".rst", ".html")
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "dist", "build"}

# This tool's own rule table necessarily contains every prohibited phrase.
# Excluding it is standard for a linter, but the exclusion is PRINTED in every
# output rather than left implicit, so nothing is hidden by it.
SELF_EXCLUDED = ("claim_guard.py", "test_claim_guard.py")


def source_context(rel):
    """Objective context for a match. NOT a suppression list -- every finding
    is still reported. It exists because the same word means different things
    in different files: a prohibited phrase inside a test file is very often a
    PLANTED negative-control fixture (several lanes, including this one, ship
    exactly that), and a phrase in a .py file is often an identifier. Grouping
    by context lets a reader start where real prose claims live instead of
    abandoning the report.
    """
    base = os.path.basename(rel)
    if base.startswith("test_") or os.sep + "tests" + os.sep in rel:
        return "test"
    if rel.endswith(".py"):
        return "code"
    if rel.endswith((".json", ".csv")):
        return "data"
    return "prose"


def _iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(TEXT_SUFFIXES):
                yield os.path.join(dirpath, name)


def scan_file(path, rel):
    findings = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        return [OrderedDict([
            ("rule", "CG-00"), ("rule_name", "UNREADABLE_FILE"),
            ("classification", AMBIGUOUS), ("file", rel), ("line", 0),
            ("context", source_context(rel)),
            ("match", ""), ("clause", "could not be read: %s" % exc)])]

    prose = path.endswith(PROSE_SUFFIXES)
    for lineno, block in blocks_of(lines, prose):
        for raw_clause in clauses_of(block):
            clause = normalize(raw_clause)
            if not clause:
                continue
            for rule_id, rule in RULES.items():
                for pat in rule["patterns"]:
                    m = re.search(pat, clause, re.IGNORECASE)
                    if not m:
                        continue
                    findings.append(OrderedDict([
                        ("rule", rule_id),
                        ("rule_name", rule["name"]),
                        ("classification", classify(clause, m.span())),
                        ("file", rel),
                        ("line", lineno),
                        ("context", source_context(rel)),
                        ("match", m.group(0)),
                        ("clause", clause[:220]),
                    ]))
                    break  # one finding per rule per clause
    return findings


def lane_fiction_check(lane_dir, rel_lane):
    """CG-06, structural rather than textual.

    A lane carrying data fixtures must label them as fiction somewhere a
    reader will reach. Absence of a label is reported as a finding to CHECK,
    not as proof the data is passed off as real -- the tool cannot know that.
    """
    has_fixtures = False
    for dirpath, dirnames, filenames in os.walk(lane_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        base = os.path.basename(dirpath).lower()
        if base in ("fixtures", "sample", "examples", "data", "out"):
            if any(f.endswith((".json", ".csv", ".txt", ".md"))
                   for f in filenames):
                has_fixtures = True
    if not has_fixtures:
        return None

    labelled = False
    for path in _iter_files(lane_dir):
        if os.path.basename(path) in SELF_EXCLUDED:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                low = fh.read().lower()
        except OSError:
            continue
        if any(m in low for m in FICTION_MARKERS):
            labelled = True
            break
    if labelled:
        return None
    return OrderedDict([
        ("rule", "CG-06"), ("rule_name", "UNLABELLED_FICTION"),
        ("classification", AMBIGUOUS), ("file", rel_lane), ("line", 0),
        ("context", "prose"), ("match", ""),
        ("clause", "lane carries data fixtures but no file mentions fiction, "
                   "synthetic or invented data -- a reader could take these "
                   "records as real. Needs a human check."),
    ])


def scan_tree(root, lane_glob_prefix="uiowa_rfq_18649_"):
    """Scan every lane under `root`. Returns (findings, meta)."""
    if not os.path.isdir(root):
        raise ValueError("not a directory: %s" % root)

    lanes = sorted(d for d in os.listdir(root)
                   if d.startswith(lane_glob_prefix)
                   and os.path.isdir(os.path.join(root, d)))

    findings, excluded, scanned = [], [], 0
    for lane in lanes:
        lane_dir = os.path.join(root, lane)
        for path in _iter_files(lane_dir):
            rel = os.path.relpath(path, root)
            if os.path.basename(path) in SELF_EXCLUDED:
                excluded.append(rel)
                continue
            scanned += 1
            findings.extend(scan_file(path, rel))
        fiction = lane_fiction_check(lane_dir, lane)
        if fiction:
            findings.append(fiction)

    findings.sort(key=lambda f: (f["file"], f["line"], f["rule"]))
    meta = OrderedDict([
        ("root", os.path.abspath(root)),
        ("lanes_scanned", len(lanes)),
        ("files_scanned", scanned),
        ("files_excluded", sorted(excluded)),
        ("exclusion_note",
         "This tool's own rule table necessarily contains every prohibited "
         "phrase, so its source and tests are excluded from pattern matching. "
         "The exclusion is listed here rather than left implicit."),
    ])
    return findings, meta


def tree_digest(root):
    """sha256 over every file's path and bytes. Used to prove the scan wrote
    nothing -- the promise is checked, not asserted."""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            h.update(os.path.relpath(path, root).encode("utf-8"))
            try:
                with open(path, "rb") as fh:
                    h.update(fh.read())
            except OSError:
                h.update(b"<unreadable>")
    return h.hexdigest()


# --------------------------------------------------------------------------
# Summary -- counts only, never a score
# --------------------------------------------------------------------------

def summarize(findings, meta):
    by_rule = OrderedDict()
    for rule_id, rule in list(RULES.items()) + [
            ("CG-06", {"name": "UNLABELLED_FICTION"}),
            ("CG-00", {"name": "UNREADABLE_FILE"})]:
        by_rule[rule_id] = OrderedDict(
            [("name", rule["name"])] +
            [(c, 0) for c in CLASSIFICATIONS])
    for f in findings:
        by_rule[f["rule"]][f["classification"]] += 1

    totals = OrderedDict((c, sum(1 for f in findings
                                 if f["classification"] == c))
                         for c in CLASSIFICATIONS)

    by_context = OrderedDict()
    for f in findings:
        if f["classification"] != ASSERTION:
            continue
        by_context[f["context"]] = by_context.get(f["context"], 0) + 1
    by_context = OrderedDict(sorted(by_context.items()))

    notes = []
    notes.append(
        "ASSERTION means the clause READS AS a statement of fact containing "
        "the prohibited concept. It is a candidate finding for a person to "
        "confirm, not a proven violation. The scan cannot tell a claim about "
        "the assessed organization from the same word used as a document "
        "name ('certified cost rate schedule'), an identifier "
        "('check_conformance'), or a deliberately planted test fixture.")
    if totals[AMBIGUOUS]:
        notes.append(
            "%d matches could not be classified and are listed as AMBIGUOUS. "
            "They are NOT cleared. Each needs a person to read the clause and "
            "decide. Treating them as clean would manufacture confidence the "
            "scan does not have." % totals[AMBIGUOUS])
    if not totals[ASSERTION]:
        notes.append(
            "Zero ASSERTION findings. This is only meaningful alongside the "
            "planted-violation fixtures, which prove the detector still fires: "
            "run the tests. A guard that has never gone red is not evidence.")
    if totals[REFUSAL]:
        notes.append(
            "%d REFUSAL matches were found. These are positive evidence: lanes "
            "naming a prohibited claim in order to decline it." % totals[REFUSAL])

    return OrderedDict([
        ("scanned", meta),
        ("totals_by_classification", totals),
        ("assertions_by_source_context", by_context),
        ("by_rule", by_rule),
        ("notes", notes),
        ("refusals_of_this_tool", [
            "No lane is scored, graded, ranked or rated. Findings carry an "
            "exact file and line; a human reads them.",
            "No compliance percentage or pass/fail verdict per lane is "
            "produced.",
            "AMBIGUOUS is never resolved automatically in the clean "
            "direction.",
            "Nothing in a scanned lane is modified. The scan is read-only and "
            "a test proves it by hashing the tree before and after.",
            "UNKNOWN-propagation checking is deliberately not attempted here; "
            "another lane (OPS-UNKNOWN-PROPAGATION) covers it.",
        ]),
    ])


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

COLUMNS = ["rule", "rule_name", "classification", "context", "file", "line",
           "match", "clause"]


def write_csv(findings, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for f in findings:
            w.writerow(f)


def _esc(text):
    return str(text).replace("|", "\\|")


def write_md(findings, summary, path):
    out = []
    a = out.append
    a("# Cross-lane claim guard")
    a("")
    a("Scanned `%s` — **%d lanes, %d files**."
      % (summary["scanned"]["root"], summary["scanned"]["lanes_scanned"],
         summary["scanned"]["files_scanned"]))
    a("")
    a("Read-only. Nothing in any scanned lane was modified.")
    a("")
    a("## Three outcomes, not two")
    a("")
    a("| Outcome | Meaning |")
    a("|---|---|")
    a("| `ASSERTION` | The prohibited claim is being made. A finding. |")
    a("| `REFUSAL` | The text names the rule in order to decline it. Positive "
      "evidence, not silence. |")
    a("| `AMBIGUOUS` | The classifier cannot tell. **UNKNOWN** — needs a "
      "person. Never auto-cleared. |")
    a("")
    a("A lane that refuses a claim contains the same words as a lane that "
      "makes one. That is why classification exists and why a word search "
      "would be worse than useless here.")
    a("")

    t = summary["totals_by_classification"]
    a("## Totals")
    a("")
    a("| Outcome | Count |")
    a("|---|---|")
    for k in CLASSIFICATIONS:
        a("| `%s` | %d |" % (k, t[k]))
    a("")
    a("Raw counts. No lane is scored, graded or ranked.")
    a("")
    if summary["assertions_by_source_context"]:
        a("### ASSERTION findings by source context")
        a("")
        a("| Context | Count |")
        a("|---|---|")
        for k, v in summary["assertions_by_source_context"].items():
            a("| `%s` | %d |" % (k, v))
        a("")
        a("Context is reported, not filtered. A match in a `test` file is "
          "frequently a planted negative-control fixture; a match in `code` "
          "is frequently an identifier. Start with `prose`.")
        a("")

    if summary["notes"]:
        a("### Read before quoting the totals")
        a("")
        for n in summary["notes"]:
            a("- %s" % n)
        a("")

    a("## By rule")
    a("")
    a("| Rule | Name | ASSERTION | REFUSAL | AMBIGUOUS | What it catches |")
    a("|---|---|---|---|---|---|")
    for rid, row in summary["by_rule"].items():
        meaning = RULES.get(rid, {}).get("means", "—")
        a("| `%s` | %s | **%d** | %d | %d | %s |"
          % (rid, row["name"], row[ASSERTION], row[REFUSAL], row[AMBIGUOUS],
             _esc(meaning)))
    a("")

    for cls in (ASSERTION, AMBIGUOUS):
        rows = [f for f in findings if f["classification"] == cls]
        a("## %s (%d)" % (cls, len(rows)))
        a("")
        if not rows:
            a("None.")
            a("")
            continue
        a("| File | Line | Rule | Context | Matched | Clause |")
        a("|---|---|---|---|---|---|")
        for f in rows:
            a("| `%s` | %d | `%s` | `%s` | `%s` | %s |"
              % (_esc(f["file"]), f["line"], f["rule"], f["context"],
                 _esc(f["match"]), _esc(f["clause"])))
        a("")

    a("## What this tool refuses to do")
    a("")
    for item in summary["refusals_of_this_tool"]:
        a("- %s" % item)
    a("")
    a("## Files excluded from pattern matching")
    a("")
    a(summary["scanned"]["exclusion_note"])
    a("")
    for f in summary["scanned"]["files_excluded"]:
        a("- `%s`" % f)
    a("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def run(root, out_dir):
    before = tree_digest(root)
    findings, meta = scan_tree(root)
    after = tree_digest(root)
    meta["scanned_tree_unmodified"] = (before == after)
    meta["tree_digest"] = before
    summary = summarize(findings, meta)
    os.makedirs(out_dir, exist_ok=True)
    write_csv(findings, os.path.join(out_dir, "claim_findings.csv"))
    write_md(findings, summary, os.path.join(out_dir, "claim_findings.md"))
    with open(os.path.join(out_dir, "claim_findings.json"), "w",
              encoding="utf-8") as fh:
        json.dump(OrderedDict([("summary", summary), ("findings", findings)]),
                  fh, indent=2)
        fh.write("\n")
    return findings, summary


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(here),
                    help="directory holding the lane directories")
    ap.add_argument("--out", default=os.path.join(here, "sample"))
    args = ap.parse_args(argv)
    try:
        findings, summary = run(args.root, args.out)
    except ValueError as exc:
        print("SCAN ERROR: %s" % exc, file=sys.stderr)
        return 2
    t = summary["totals_by_classification"]
    print("scanned %d lanes / %d files under %s"
          % (summary["scanned"]["lanes_scanned"],
             summary["scanned"]["files_scanned"], summary["scanned"]["root"]))
    print("ASSERTION=%d  REFUSAL=%d  AMBIGUOUS=%d"
          % (t[ASSERTION], t[REFUSAL], t[AMBIGUOUS]))
    print("scanned tree unmodified: %s"
          % summary["scanned"]["scanned_tree_unmodified"])
    for n in summary["notes"]:
        print("NOTE: %s" % n)
    print("wrote claim_findings.{csv,md,json} -> %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
