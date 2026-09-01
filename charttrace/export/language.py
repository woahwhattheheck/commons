"""Export-language sanitizer — scoped non-findings only."""

from __future__ import annotations

import re
from typing import Tuple

_FORBIDDEN = (
    (re.compile(r"\\bthe patient was not told\\b", re.I), "SCOPED_NONFINDING"),
    (re.compile(r"\\bpatient was not told\\b", re.I), "SCOPED_NONFINDING"),
    (re.compile(r"\\bwas never told\\b", re.I), "SCOPED_NONFINDING"),
    (re.compile(r"\\bmalpractice\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bnegligence\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bnegligent\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bstandard[- ]of[- ]care\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bcausation\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bactionability\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bactionable\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
    (re.compile(r"\\bcase value\\b", re.I), "REMOVED_LEGAL_CONCLUSION"),
)


def sanitize_export_text(
    text: str,
    *,
    scope: str = "reviewed materials",
    date_range: str = "the supplied date range",
) -> Tuple[str, bool]:
    if not text:
        return text, False
    out = text
    changed = False
    scoped = (
        f"No documentation of communication was located in the supplied "
        f"{scope} for {date_range}."
    )
    for pat, kind in _FORBIDDEN:
        if pat.search(out):
            changed = True
            if kind == "SCOPED_NONFINDING":
                out = pat.sub(scoped, out)
            else:
                out = pat.sub("[legal conclusion omitted — counsel determination only]", out)
    return out, changed
