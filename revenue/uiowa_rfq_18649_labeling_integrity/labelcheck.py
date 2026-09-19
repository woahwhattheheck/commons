"""Read-only screen: is every synthetic artifact in the kit labeled as fiction?

The hardest rule on this engagement is that no real University finding appears
anywhere, and nothing synthetic is presented as one. Every lane asserts its
fixtures are fiction. This screen checks whether the generated artifacts
actually say so, and -- more importantly -- tells apart the files where that
matters from the files where it does not.

The distinction is the whole tool. A coarse "does this file contain the word
synthetic" probe over the tree returns dozens of hits that are model configs,
vocabularies and weight tables. Those need no fiction label, and counting them
as violations would overstate the problem by a factor of several, which is the
precise failure this board exists to avoid. So the screen classifies content
shape first and only then asks about the label.

It reads files. It writes only inside an explicit output directory, and it never
modifies an artifact it is screening.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------- vocabularies

# An explicit disclosure. Deliberately narrow: "example" alone is not a
# disclosure, because "for example" appears in ordinary prose.
LABEL_PATTERNS = (
    r"\bsynthetic\b", r"\bfiction(al)?\b", r"\bnot\s+a\s+(real|university)\b",
    r"\binvented\b", r"\bmade[-\s]up\b", r"\billustrative\s+only\b",
    r"\bsample\s+only\b", r"\bexample\s+only\b", r"\bnot\s+real\s+data\b",
    r"\bplaceholder\b", r"\bdemonstration\s+data\b",
)
LABEL_RE = re.compile("|".join(LABEL_PATTERNS), re.I)

# An explicit provenance statement of EITHER kind also satisfies the check. A
# generated report of a real scan must not be labelled "synthetic" -- that would
# be a false statement -- so the requirement is that a record-shaped artifact
# says which it is, not that it claims to be fiction.
PROVENANCE_RE = re.compile(r"\bprovenance\b", re.I)


def disclosure_offset(text):
    """Byte offset of the earliest provenance disclosure, or None."""
    offsets = [m.start() for m in (LABEL_RE.search(text), PROVENANCE_RE.search(text))
               if m is not None]
    return min(offsets) if offsets else None

# Identifier shapes the kit uses for assessment records. A file carrying these
# is holding records, not configuration.
RECORD_ID_RE = re.compile(
    r"\b(EV|F|REC|OBS|IDX|SRC|CELL|M|DEP|C)-[A-Z0-9]{2,}[-0-9]*\b"
)

# Words that make a statement read as an assessment result rather than a schema.
RESULT_WORDS = re.compile(
    r"\b(finding|findings|maturity|assessed|assessment|demonstrated_strength|"
    r"observed_gap|strength|gap|recommendation|observation|evidence)\b", re.I
)

# The engagement's own subjects. Without one of these a file is generic.
SUBJECT_RE = re.compile(r"\b(university of iowa|uiowa|\bAIS\b|\bESS\b|\bRIS\b|\bIAM\b)\b")

# Shapes that mean "this is machinery, not a record".
CONFIG_HINT_RE = re.compile(
    r"\b(schema|weights?|vocabular|indicator|definition|threshold|config|"
    r"taxonomy|rubric|criteria_definition|field_map|crosswalk)\b", re.I
)

EVIDENCE_EXTENSIONS = frozenset({".md", ".csv", ".json", ".txt", ".tsv"})

# Files whose job is to explain, not to present results.
DOC_BASENAMES = frozenset({
    "readme.md", "license", "license.md", "contributing.md", "changelog.md",
    "operator_guide.md", "notes.md",
})

# ------------------------------------------------------------------ result kinds

DISCLOSED = "DISCLOSED"
LABELED = DISCLOSED  # retained name
LABEL_BURIED = "LABEL_BURIED"
UNDISCLOSED_PROVENANCE = "UNDISCLOSED_PROVENANCE"
UNLABELED_CONFIG_SHAPED = "UNLABELED_CONFIG_SHAPED"
NOT_EVIDENCE = "NOT_EVIDENCE"
UNREADABLE = "UNREADABLE"

# Worst first. UNREADABLE sits above LABELED: a file we could not read is not a
# file we cleared.
SEVERITY_ORDER = (
    UNDISCLOSED_PROVENANCE, LABEL_BURIED, UNREADABLE,
    UNLABELED_CONFIG_SHAPED, LABELED, NOT_EVIDENCE,
)

# A disclosure has to be where a reader will actually see it.
DEFAULT_HEADER_BYTES = 1500


@dataclass
class ArtifactResult:
    lane: str
    path: str
    status: str
    shape: str
    label_offset: Any = None
    reason: str = ""
    record_ids: list = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "lane": self.lane, "path": self.path, "status": self.status,
            "shape": self.shape, "label_offset": self.label_offset,
            "reason": self.reason,
            "record_ids_sample": self.record_ids[:5],
        }


# ------------------------------------------------------------------ classifying

def is_documentation(path: str) -> bool:
    return os.path.basename(path).lower() in DOC_BASENAMES


def classify_shape(text: str, path: str) -> tuple:
    """Return (shape, reason). Shape drives whether a label is expected."""
    if is_documentation(path):
        return "DOCUMENTATION", "documentation explains the kit; it presents no records"

    ids = RECORD_ID_RE.findall(text)
    id_count = len(RECORD_ID_RE.findall(text))
    has_subject = bool(SUBJECT_RE.search(text))
    has_result_words = bool(RESULT_WORDS.search(text))

    ext = os.path.splitext(path)[1].lower()
    populated_rows = 0
    if ext in (".csv", ".tsv"):
        try:
            rows = list(csv.reader(io.StringIO(text),
                                   delimiter="\t" if ext == ".tsv" else ","))
            populated_rows = max(0, len([r for r in rows if any(c.strip() for c in r)]) - 1)
        except csv.Error:
            populated_rows = 0

    if id_count >= 2 or populated_rows >= 2:
        if has_result_words or has_subject:
            return "RECORDS", (
                f"carries {id_count} record identifier(s) and "
                f"{populated_rows} populated row(s) with assessment vocabulary"
            )
        return "DATA", "carries identifiers or rows but no assessment vocabulary"

    if CONFIG_HINT_RE.search(text) and id_count == 0:
        return "CONFIGURATION", (
            "reads as schema/vocabulary/weights rather than records; a fiction "
            "label is not expected here"
        )

    if has_result_words and has_subject:
        return "PROSE_RESULT", "prose that states assessment results about the engagement's subjects"

    return "OTHER", "neither record-shaped nor obviously configuration"


def check_text(text: str, lane: str, path: str,
               header_bytes: int = DEFAULT_HEADER_BYTES) -> ArtifactResult:
    shape, reason = classify_shape(text, path)
    offset = disclosure_offset(text)
    match = offset is not None
    ids = sorted(set(RECORD_ID_RE.findall(text)))[:5]

    if shape in ("DOCUMENTATION", "CONFIGURATION", "OTHER", "DATA"):
        if shape == "CONFIGURATION" and not match:
            return ArtifactResult(lane, path, UNLABELED_CONFIG_SHAPED, shape,
                                  None, reason, ids)
        return ArtifactResult(lane, path, NOT_EVIDENCE if not match else DISCLOSED,
                              shape, offset, reason, ids)

    # RECORDS / PROSE_RESULT: a label is expected, near the top.
    if not match:
        return ArtifactResult(
            lane, path, UNDISCLOSED_PROVENANCE, shape, None,
            f"{reason}; the file states nowhere whether its contents are "
            "synthetic or real", ids)
    if offset > header_bytes:
        return ArtifactResult(
            lane, path, LABEL_BURIED, shape, offset,
            f"{reason}; disclosure appears at byte {offset}, past the first "
            f"{header_bytes} bytes a reader sees", ids)
    return ArtifactResult(lane, path, DISCLOSED, shape, offset,
                          f"{reason}; disclosure at byte {offset}", ids)


def scan_tree(root: str, lane_prefix: str = "",
              header_bytes: int = DEFAULT_HEADER_BYTES) -> list:
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in
                             {"__pycache__", ".git", ".pytest_cache", "node_modules"})
        for filename in sorted(filenames):
            if os.path.splitext(filename)[1].lower() not in EVIDENCE_EXTENSIONS:
                continue
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root)
            lane = rel.split(os.sep)[0] if os.sep in rel else os.path.basename(root)
            if lane_prefix and not lane.startswith(lane_prefix):
                continue
            try:
                with open(full, "r", encoding="utf-8") as fh:   # read-only
                    text = fh.read()
            except (OSError, UnicodeDecodeError) as exc:
                results.append(ArtifactResult(
                    lane, rel, UNREADABLE, "UNKNOWN", None,
                    f"could not be read: {exc.__class__.__name__}"))
                continue
            if len(text.strip()) < 40:
                continue
            results.append(check_text(text, lane, rel, header_bytes))
    return results


def summarize(results: list) -> dict:
    by_status = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    lanes = {}
    for r in results:
        current = lanes.get(r.lane)
        if current is None or SEVERITY_ORDER.index(r.status) < SEVERITY_ORDER.index(current):
            lanes[r.lane] = r.status
    needs_label = [r for r in results
                   if r.status in (UNDISCLOSED_PROVENANCE, LABEL_BURIED)]
    return {
        "artifacts_examined": len(results),
        "by_status": dict(sorted(by_status.items())),
        "lanes_by_worst_status": dict(sorted(lanes.items())),
        "needs_a_label": len(needs_label),
        "lanes_needing_a_label": sorted({r.lane for r in needs_label}),
    }
