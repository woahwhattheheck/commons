"""Uncertainty-language lint for the delivery kit's own Markdown output.

What this checks, and what it deliberately does not
---------------------------------------------------
UIOWA-089C ships the rule: "we found no evidence of X" is a statement about our
search; "X does not happen" is a claim about the organisation. This lints the
kit's *own shipped artifacts* for the second form.

The naive version of this tool is a grep for "there is no", "has no", "lacks".
Run over the 45 landed lanes it produces 132 hits, and reading them shows why
that number is worthless:

    "There is no HTTP field, CLI switch, or browser control that..."   <- software
    "Item 'X-09' has no phase."                                        <- a record
    "The checked-in rehearsal intentionally lacks ownership evidence." <- a fixture
    "A cell reading UNKNOWN records that the assessment lacks evidence."
                                                     <- the CORRECT form, flagged

Those are correct English and none of them is the failure. **A linter with that
false-positive rate is worse than no linter**, because the first person who runs
it turns it off, and then the real instances ship too. So precision is the whole
design problem here, not detection.

The narrow thing that is actually wrong
---------------------------------------
An absence predicate whose subject is an **assessed entity** -- a service, a
group, a team -- rather than the evidence, the assessment, a tool or a record:

    FLAG  "SVC-DIRSYNC has no backup record."
    OK    "We found no backup record for SVC-DIRSYNC in the material supplied."

Both may describe the same situation. The first reads as a property of the
service and survives being quoted out of context; the second stays a property of
the search. In a findings table, under a heading, next to a rating, the first one
is how an absence of evidence becomes a finding of absence.

This is advisory. It emits a suggested rewrite and a class, never a score, never
a per-lane or per-author ranking -- ranking authors here would violate the same
boundary the 089C kit ships (B-002), and the irony is the point. Each lane owner
decides; nothing here edits another lane.

Precision is measured, not claimed. `fixtures/labelled_lines.json` holds lines
from the real corpus that were read and hand-labelled, and `test_lint.py` fails
if precision falls below the declared floor -- so this cannot quietly rot into
the noisy grep it was built to avoid.
"""

import json
import os
import re

# The absence predicates worth looking at. Narrower than the 089C claim checker:
# that one runs against a claim whose type is already known to be an absence
# claim, so it can afford to be broad. This one runs against arbitrary prose and
# has to earn every flag.
# NOTE ON A CHECK THAT WAS REMOVED.
# "there is/are no X" is deliberately NOT here, and it was the single most
# common candidate in the corpus (21 of 107). It is an existential: its subject
# follows the predicate rather than preceding it, so the backward subject scan
# that works for every other form reads whatever happened to be earlier in the
# sentence. On "IAM AI readiness was not assessed; there is no finding in
# either direction" it read "IAM" and flagged a sentence that is exactly
# right. Scanning forward instead just moves the ambiguity: in "there is no
# incident review practice at ESS" the entity is the scope, while in "there is
# no evidence that the path works" the following noun is the evidence.
# Separating those needs a parser, not a window.
#
# So it is left out, and the limitation is documented rather than papered over.
# A narrow check people trust beats a broad one they switch off -- which is the
# same argument this whole tool is built on, applied to itself.
ABSENCE_PREDICATES = [
    (r"\bhas no\b", "has no"),
    (r"\bhave no\b", "have no"),
    (r"\blacks\b", "lacks"),
    (r"\bdoes not (?:exist|happen|occur)\b", "does not exist/happen"),
    (r"\bdo not (?:exist|happen|occur)\b", "do not exist/happen"),
    (r"\bnever (?:happens|occurs|tested|tests)\b", "never happens"),
    (r"\bis not (?:done|performed|carried out)\b", "is not done"),
    (r"\bare not (?:done|performed|carried out)\b", "are not done"),
]

# Classes. Only FLAG_ASSESSED_ENTITY is reported as a finding.
FLAG_ASSESSED_ENTITY = "ABSENCE_ABOUT_ASSESSED_ENTITY"
OK_EVIDENCE_SUBJECT = "ok_subject_is_evidence_or_assessment"
OK_TOOL_SUBJECT = "ok_subject_is_tool_record_or_artifact"
OK_HEDGED = "ok_hedged_or_conditional"
OK_QUOTED = "ok_quoted_as_an_example"
OK_UNCLASSIFIED = "ok_no_assessed_subject_found"

# The correct form: the sentence is about what we looked at.
_EVIDENCE_SUBJECT = re.compile(
    r"\b(?:assessment|evidence|packet|material|materials|document|documents|"
    r"record|records|register|manifest|export|report|engagement|review|"
    r"search|sample|we|i|our|this kit|the kit|the checker|the analysis|"
    r"the finding|the cell|the matrix|the source|the supplied)\b", re.I)

# Software, records, fixtures and process objects. Not assessment claims.
_TOOL_SUBJECT = re.compile(
    r"\b(?:checker|linter|form|template|field|fields|endpoint|cli|switch|"
    r"flag|flags|script|tool|module|function|test|tests|fixture|column|"
    r"cell|row|file|files|directory|path|schema|key|item|items|node|level|"
    r"levels|phase|page|slide|api|json|csv|markdown|html|build|commit|"
    r"branch|pr|repo|repository|rate|fee|travel|invoice|clause|exhibit|"
    r"payment|dependency|chain|packet|run|output|input|header|table|"
    r"section|heading|line|entry|id|identifier|argument|parameter|"
    r"option|command|process|workflow|step|rule|check|gate|note|notes|"
    r"procedure|procedures|policy|policies|standard|standards|runbook|"
    r"runbooks|guide|log|logs|ticket|issue|plan|draft|version|criterion|"
    r"criteria|objective|objectives|definition|description|summary)\b", re.I)

_HEDGE = re.compile(
    r"\b(?:may|might|would|could|should|if|when|where|whether|assume|"
    r"assuming|suppose|hypothetical|example|e\.g\.|imagine|were to)\b", re.I)

# An assessed entity: a synthetic service/system id, a group code, or an
# explicit "the <name> team/service/group".
#
# The group codes are guarded with (?![-\w]) and (?<![-\w]) after a real
# measurement: without it, `RIS-AI-002` and `EC-IAM-007` -- row identifiers in
# a findings table, not subjects of anything -- matched as assessed entities
# and drove precision to 0.29. A hyphen is a word boundary to `\b`, so `\bIAM\b`
# happily matches inside `SLO-IAM-AUTH-1`.
# Two patterns, because case matters for one half and not the other. Group
# codes and service ids are case-SENSITIVE: lowercasing them would match "ris"
# and "iam" inside ordinary prose. The "the <name> service" form is
# case-INSENSITIVE, and was case-sensitive by accident until the labelled set
# caught it -- "The identity service lacks a documented escalation path" is a
# textbook true positive and sailed straight through.
_ASSESSED_ENTITY_ID = re.compile(
    r"(?:\b(?:SVC|SYS|APP|TEAM|GRP)-[A-Z0-9][A-Z0-9_-]*\b"
    r"|(?<![-\w])(?:ESS|RIS|IAM)(?![-\w])"
    # A proper-noun entity name: "Directory Synchronization Service". Stays
    # case-sensitive because the capitals are what make it a name rather than
    # a common noun -- "the backup service" is already covered by the phrase
    # pattern below, and lowercasing this one would swallow it.
    r"|\b[A-Z][\w-]*\s+(?:Service|Team|Group|Unit|Department)\b)")
_ASSESSED_ENTITY_PHRASE = re.compile(
    r"\bthe\s+[A-Za-z][\w-]*\s+(?:team|group|service|unit|department|"
    r"function|office)\b", re.I)


def _assessed_entity_finditer(text):
    for m in _ASSESSED_ENTITY_ID.finditer(text):
        yield m
    for m in _ASSESSED_ENTITY_PHRASE.finditer(text):
        yield m

# How far back the subject is looked for. A subject further away than this is
# not reliably the subject of the predicate, and guessing produces exactly the
# noise this tool exists to avoid.
SUBJECT_WINDOW = 90

SUGGESTION = (
    "rewrite as a statement about the search, naming the scope: "
    "\"we found no <thing> for <subject> in <what was examined>\" -- "
    "or, if nothing was examined, mark it NOT_ASSESSED instead"
)


class Finding:
    def __init__(self, path, line_no, predicate, klass, text, subject=None):
        self.path = path
        self.line_no = line_no
        self.predicate = predicate
        self.klass = klass
        self.text = text
        self.subject = subject

    def as_dict(self):
        return {"path": self.path, "line": self.line_no,
                "predicate": self.predicate, "class": self.klass,
                "subject": self.subject, "text": self.text,
                "suggestion": SUGGESTION if self.klass == FLAG_ASSESSED_ENTITY
                else None}


def _inside_quoted_span(line, pos):
    """True if `pos` falls between a matched pair of quotes or backticks."""
    for quote in ('"', "`", "\u201c\u201d"):
        opens = []
        if len(quote) == 2:
            depth = 0
            for i, ch in enumerate(line):
                if ch == quote[0]:
                    depth += 1
                    opens.append(i)
                elif ch == quote[1] and depth:
                    depth -= 1
                    if opens and opens[-1] < pos < i:
                        return True
                    opens.pop()
            continue
        idx = [i for i, ch in enumerate(line) if ch == quote]
        for a, b in zip(idx[0::2], idx[1::2]):
            if a < pos < b:
                return True
    return False


def _cell_of(line, pos):
    """In a Markdown table row, the subject lives in the predicate's own cell.

    Scanning the whole row picked up the row identifier (`RIS-AI-002`) as the
    subject of a predicate three cells away. Narrowing to the cell was worth
    more than any regex change.
    """
    if line.count("|") < 2:
        return line, pos
    start = line.rfind("|", 0, pos)
    end = line.find("|", pos)
    if start == -1:
        start = -1
    if end == -1:
        end = len(line)
    return line[start + 1:end], pos - (start + 1)


def classify(line, match_start, match_text):
    """Decide what an absence predicate in this line is actually about.

    Order matters and is deliberate: the cheapest, most certain exclusions run
    first, and `FLAG` is only reached when nothing else explains the sentence.
    A tool that guesses when it is unsure is the noisy grep again, so the
    default is OK, not FLAG.
    """
    cell, cell_pos = _cell_of(line, match_start)
    before = cell[max(0, cell_pos - SUBJECT_WINDOW):cell_pos]

    # Demonstrating or quoting the wording, not committing it. Several lanes
    # list forbidden phrasings verbatim, and the readout-deck lane quotes a
    # slide's claim in order to criticise it. The first version checked only
    # the two characters either side of the match and missed both, because the
    # quote marks are at the ends of the sentence -- so the whole quoted span
    # is computed instead.
    if _inside_quoted_span(line, match_start):
        return OK_QUOTED, None

    if _HEDGE.search(before):
        return OK_HEDGED, None

    # Nearest subject wins: whichever candidate sits closest to the predicate.
    ev = None
    for m in _EVIDENCE_SUBJECT.finditer(before):
        ev = m
    tool = None
    for m in _TOOL_SUBJECT.finditer(before):
        tool = m
    ent = None
    for m in sorted(_assessed_entity_finditer(before), key=lambda m: m.end()):
        ent = m

    best = max(
        [(ev.end() if ev else -1, OK_EVIDENCE_SUBJECT, ev),
         (tool.end() if tool else -1, OK_TOOL_SUBJECT, tool),
         (ent.end() if ent else -1, FLAG_ASSESSED_ENTITY, ent)],
        key=lambda t: t[0])
    if best[0] < 0:
        return OK_UNCLASSIFIED, None
    return best[1], (best[2].group(0) if best[2] else None)


def scan_text(text, path="<text>"):
    """Findings for one document. Code fences are skipped."""
    findings = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for pattern, label in ABSENCE_PREDICATES:
            m = re.search(pattern, line, re.I)
            if not m:
                continue
            klass, subject = classify(line, m.start(), m.group(0))
            findings.append(Finding(path, line_no, label, klass,
                                    line.strip(), subject))
            break
    return findings


def scan_tree(root, skip_dirs=()):
    """Every Markdown file under root, sorted for a deterministic report."""
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in skip_dirs and d != "__pycache__")
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            try:
                with open(full, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            findings.extend(scan_text(text, os.path.relpath(full, root)))
    return findings


def summarise(findings):
    counts = {}
    for f in findings:
        counts[f.klass] = counts.get(f.klass, 0) + 1
    flagged = [f for f in findings if f.klass == FLAG_ASSESSED_ENTITY]
    return {
        "candidates_examined": len(findings),
        "flagged": len(flagged),
        "by_class": dict(sorted(counts.items())),
        "flag_rate": round(len(flagged) / len(findings), 4) if findings else 0.0,
    }


def load_labelled(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def score_against_labels(labelled):
    """Precision and recall against hand-read labels.

    `label` is TRUE_POSITIVE when the line really does state absence as a
    property of an assessed entity, FALSE_POSITIVE when it does not. Lines the
    tool passes are labelled too, so a false negative is visible rather than
    silently absent.
    """
    tp = fp = fn = tn = 0
    errors = []
    for row in labelled["lines"]:
        findings = scan_text(row["text"], row.get("source", "<labelled>"))
        predicted = any(f.klass == FLAG_ASSESSED_ENTITY for f in findings)
        actual = row["label"] == "TRUE_POSITIVE"
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
            errors.append(("false_positive", row["text"]))
        elif not predicted and actual:
            fn += 1
            errors.append(("false_negative", row["text"]))
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return {"true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "precision": round(precision, 4), "recall": round(recall, 4),
            "errors": errors}
