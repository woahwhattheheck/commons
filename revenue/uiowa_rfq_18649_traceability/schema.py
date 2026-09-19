#!/usr/bin/env python3
"""Field contract and rule registry for the UIOWA-093 traceability checker.

Why this file exists: the checker's value is that a rule has a stable id you can
cite in a review comment ("S-002 failed T301"). Rule text lives here, once, so
the CLI, the Markdown report and the tests all name a failure the same way.

Field names are deliberately inherited from the already-merged bundle at
revenue/uiowa_rfq_18649_traceability_rehearsal/ (statement_id, finding_id,
evidence_id, locator, evidence_state, limitation, linked_findings) so the two
lanes compose instead of forking the vocabulary. Columns added here are
additive: source_id, quantities, asserts_polarity, asserts_quantity,
limitation_ack, finding_digest, statement_digest.
"""
import csv
import hashlib
import re

UNKNOWN = "UNKNOWN"

# Columns a bundle must carry. A missing column is a structural failure, not a
# blank value -- silently reading a missing column as "" is how an absent input
# becomes a pass.
REQUIRED_COLUMNS = {
    "sources.csv": ["source_id", "title", "path", "sha256", "captured", "synthetic"],
    "evidence.csv": ["evidence_id", "service", "source_type", "source_id", "locator",
                     "observation", "evidence_state", "quantities"],
    "findings.csv": ["finding_id", "service", "type", "title", "statement",
                     "evidence_ids", "confidence", "limitation"],
    "recommendations.csv": ["recommendation_id", "title", "linked_findings", "action",
                            "expected_outcome", "effort", "dependency"],
    "trace-map.csv": ["statement_id", "report_location", "statement_summary",
                      "recommendation_ids", "finding_ids", "evidence_ids",
                      "asserts_polarity", "asserts_quantity", "limitation_ack",
                      "finding_digest", "statement_digest"],
}

ID_PATTERNS = {
    "source_id": re.compile(r"^SRC-\d{3}$"),
    "evidence_id": re.compile(r"^E-\d{3}$"),
    "finding_id": re.compile(r"^F-\d{3}$"),
    "recommendation_id": re.compile(r"^R-\d{3}$"),
    "statement_id": re.compile(r"^S-\d{3}$"),
}

FINDING_TYPES = {"strength", "gap", "mixed", "unknown"}
POLARITIES = FINDING_TYPES

# The fields a report statement actually rests on. The digest covers exactly
# these: reflowing a CSV or re-quoting a cell must not fire drift, but changing
# what a finding says must.
FINDING_DIGEST_FIELDS = ("finding_id", "type", "statement", "limitation", "evidence_ids")

RULES = {
    # -- forward integrity: every level resolves downward -------------------
    "T101": "statement cites a finding id that does not exist",
    "T102": "statement cites a recommendation id that does not exist",
    "T103": "finding cites an evidence id that does not exist",
    "T104": "recommendation links a finding id that does not exist",
    "T105": "evidence cites a source id that is not in the source register",
    "T106": "registered source record is missing from disk",
    "T107": "source record on disk does not match its registered sha256",
    "T108": "evidence locator does not resolve to an anchor inside its source record",
    "T109": "evidence quantity is not declared by its source record",
    "T110": "report prose and trace map disagree about a statement's links",
    "T111": "statement is registered but absent from the report file it names",
    "T112": "the same statement id carries different text in two report locations",
    # -- reverse integrity: nothing in the report is unaccounted for --------
    "T201": "a paragraph marked {narrative} asserts a quantity or a universal claim",
    "T202": "report paragraph is neither a registered statement nor marked {narrative}",
    "T203": "finding is supported by evidence but reaches no report statement",
    "T204": "evidence is registered but cited by no finding",
    "T205": "source is registered but cited by no evidence",
    "T206": "recommendation reaches no report statement",
    # -- agreement: the report still says what the records say --------------
    "T301": "statement asserts a polarity the finding does not carry",
    "T302": "statement asserts a quantity the evidence does not carry",
    "T303": "finding carries a limitation the statement does not acknowledge",
    "T304": "statement asserts a value where the record says UNKNOWN",
    "T305": "report paragraph changed after it was registered",
    "T306": "finding changed after the statement that rests on it was registered",
    "T307": "recommendation rests only on findings recorded as strengths",
    # -- structural --------------------------------------------------------
    "T001": "required file is missing from the bundle",
    "T002": "required column is missing from a bundle file",
    "T003": "duplicate id in a bundle file",
    "T004": "id does not match its required format",
    "T005": "source path escapes the bundle directory",
}

# T201 is a lexical tripwire, not a semantic judge, and it is reported as a
# WARNING for a reason discovered on its first run: the bare quantifier pattern
# flagged this bundle's own disclaimer ("Every claim paragraph carries the
# statement id...", "All records referenced here are fabricated"). Those are
# statements about the document, not about the assessed subject. A heuristic
# that blocks the build on prose like that gets silenced by its users within a
# week, which is strictly worse than an advisory that still gets read. So the
# quantifier patterns now require an assessment SUBJECT next to the quantifier,
# and T202 -- which is exact -- carries the error.
ASSESSMENT_SUBJECT = (r"(services?|teams?|groups?|applications?|consumers?|"
                      r"workflows?|systems?|environments?|controls?|criteria|"
                      r"findings?|gaps?|recommendations?)")
CLAIM_MARKERS = [
    re.compile(r"\b\d+(\.\d+)?\s*(%|percent)\b", re.I),
    re.compile(r"\b(all|every|each of the|no other)\b[^.]{0,40}\b" + ASSESSMENT_SUBJECT + r"\b", re.I),
    re.compile(r"\bnone of the\b[^.]{0,40}\b" + ASSESSMENT_SUBJECT + r"\b", re.I),
    re.compile(r"\bno (further|additional|remaining|outstanding)\b", re.I),
    re.compile(r"\b(adequate|sufficient|compliant|fully (covered|tested|documented))\b", re.I),
    re.compile(r"\b(is|are|was|were) (not )?required\b", re.I),
    re.compile(r"\b\d+\s+(of|out of)\s+\d+\b", re.I),
]

def norm(text):
    """Collapse whitespace so formatting churn is not mistaken for drift."""
    return re.sub(r"\s+", " ", (text or "").strip())


def digest(payload):
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_digest(row, fields=FINDING_DIGEST_FIELDS):
    return digest("\n".join("%s=%s" % (f, norm(row.get(f, ""))) for f in fields))


def paragraph_digest(text):
    return digest(norm(text))


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def split_ids(value):
    """Accept ';' or ',' separated id lists; order is never significant."""
    return [x.strip() for x in (value or "").replace(",", ";").split(";") if x.strip()]


def parse_quantities(value):
    """'name=value unit;name2=UNKNOWN count' -> {name: (value, unit)}."""
    out = {}
    for part in (value or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            out[part] = (None, None)
            continue
        name, rest = part.split("=", 1)
        bits = rest.strip().split(None, 1)
        out[name.strip()] = (bits[0], bits[1] if len(bits) > 1 else "")
    return out


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), (reader.fieldnames or [])
