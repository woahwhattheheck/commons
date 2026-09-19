#!/usr/bin/env python3
"""Audit an assessment deliverable for unsourced claims and promotional language.

    python3 claim_audit.py --doc fixtures/exec_summary_BAD.md  --register fixtures/register.json
    python3 claim_audit.py --doc fixtures/exec_summary_GOOD.md --register fixtures/register.json
    python3 claim_audit.py --corpus /path/to/tree --rules language --format json

WHAT THIS CATCHES THAT A LINK CHECKER DOES NOT.

A citation verifier answers "does this reference resolve?". This answers two
different questions: "does this statement have a reference AT ALL?" and "is the
thing it references actually capable of supporting it?" A citation that resolves
perfectly to a finding whose state is UNKNOWN does not support a number, and
that is the failure this exists to catch.

Exit status: 0 clean, 1 findings at error severity, 2 could not run.

Python 3 standard library only. No network. No clock, sorted traversal:
two runs over the same input are byte-identical.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys

import rules as R

_CITATION_RE = re.compile(r"\[([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\s*,\s*[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)*)\](?!\()")
_SUPPRESS_RE = re.compile(r"<!--\s*audit-ok\s*:(?P<reason>.*?)-->", re.I | re.S)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_DIGIT_RE = re.compile(r"\d")
_ABBREV = (("e.g.", "e<dot>g<dot>"), ("i.e.", "i<dot>e<dot>"), ("etc.", "etc<dot>"),
           ("vs.", "vs<dot>"), ("approx.", "approx<dot>"), ("No.", "No<dot>"))

LANGUAGE_RULES = ("PROMOTIONAL_LANGUAGE", "UNQUANTIFIED_COMPARATIVE")


@dataclasses.dataclass
class Finding:
    code: str
    severity: str
    doc: str
    line_no: int
    message: str
    excerpt: str
    term: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def sort_key(self):
        return (self.doc, self.line_no, self.code, self.term)


@dataclasses.dataclass
class Unit:
    """One statement, bound to the line it came from."""
    doc: str
    line_no: int
    text: str
    suppressed_reason: str | None = None


def _term_re(term: str) -> re.Pattern:
    # Both boundaries, always. An earlier version anchored only the right-hand
    # side for multi-word terms, which made the absolute "all" match the tail of
    # "small" -- a false positive that would have discredited the whole tool on
    # its first real document.
    return re.compile(r"\b" + re.escape(term.strip()) + r"\b", re.I)


_TIER_A_RE = {t: _term_re(t) for t in R.TIER_A}
_TIER_B_RE = {t: _term_re(t) for t in R.TIER_B}
_TIER_C_RE = {t: _term_re(t) for t in R.TIER_C}
_COMPARATIVE_RE = {t: _term_re(t) for t in R.COMPARATIVES}
_ABSOLUTE_RE = {t: _term_re(t) for t in R.ABSOLUTES}
_SUPPORT_RE = {t: _term_re(t) for t in R.SUPPORT_FRAMING}


def split_sentences(text: str) -> list[str]:
    protected = text
    for real, token in _ABBREV:
        protected = protected.replace(real, token)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    out = []
    for part in parts:
        for real, token in _ABBREV:
            part = part.replace(token, real)
        if part.strip():
            out.append(part.strip())
    return out


def segment(doc_id: str, text: str) -> tuple[list[Unit], list[Finding]]:
    """Markdown -> statements. Skips code, headings and table rules."""
    units: list[Unit] = []
    problems: list[Finding] = []
    in_fence = False

    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        # Headings name a topic; they do not assert anything.
        if stripped.startswith("#"):
            continue
        # Table rule rows carry no content.
        if set(stripped) <= set("|-: "):
            continue
        # Indented code block.
        if raw.startswith("    ") and not stripped.startswith(("-", "*", "|", ">", "1.")):
            continue

        suppressed = None
        match = _SUPPRESS_RE.search(raw)
        if match:
            reason = match.group("reason").strip()
            if len(reason) < 8:
                problems.append(Finding(
                    code="EMPTY_SUPPRESSION", severity=R.ERROR, doc=doc_id,
                    line_no=line_no,
                    message=("this line suppresses the audit without giving a reason; "
                             "a suppression with no recorded justification is an "
                             "unaudited claim wearing a green check"),
                    excerpt=stripped[:140]))
            else:
                suppressed = reason

        body = _COMMENT_RE.sub("", raw).strip()
        if not body or set(body) <= set("|-: "):
            continue

        # A table row is one statement; splitting cells produces fragments that
        # read as claims but are not sentences.
        if body.startswith("|"):
            units.append(Unit(doc_id, line_no, body, suppressed))
            continue

        body = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", body)
        body = re.sub(r"^\s*>\s*", "", body)
        for sentence in split_sentences(body):
            units.append(Unit(doc_id, line_no, sentence, suppressed))

    return units, problems


def load_register(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not raw.get("synthetic"):
        raise ValueError("the register must be explicitly marked synthetic:true")
    index = {}
    for record in raw.get("findings", []) + raw.get("recommendations", []):
        index[record["id"]] = record
    return index


def audit_units(units: list[Unit], register: dict[str, dict] | None,
                enabled: tuple[str, ...] | None = None) -> list[Finding]:
    out: list[Finding] = []

    def on(code: str) -> bool:
        return enabled is None or code in enabled

    for unit in units:
        citations: list[str] = []
        for m in _CITATION_RE.finditer(unit.text):
            citations.extend(i.strip() for i in m.group(1).split(","))
        body = _CITATION_RE.sub("", unit.text)
        has_number = bool(_DIGIT_RE.search(body))
        has_citation = bool(citations)
        excerpt = unit.text.strip()[:160]

        comparative_hit = next((t for t, rx in _COMPARATIVE_RE.items()
                                if rx.search(body)), None)

        if unit.suppressed_reason is None:
            if on("PROMOTIONAL_LANGUAGE"):
                for tier_name, table, lexicon, fires in (
                    ("A", _TIER_A_RE, R.TIER_A, True),
                    ("B", _TIER_B_RE, R.TIER_B, not has_number),
                    ("C", _TIER_C_RE, R.TIER_C, not has_number and not has_citation),
                ):
                    if not fires:
                        continue
                    hits = [t for t, rx in table.items() if rx.search(body)]
                    # "best practice" and "industry best practice" both match the
                    # same words. Reporting both is two findings for one defect
                    # and makes the count untrustworthy, so keep only the longest
                    # match of any overlapping pair.
                    hits = [t for t in hits
                            if not any(t != o and t in o for o in hits)]
                    for term in sorted(hits):
                        out.append(Finding(
                            code="PROMOTIONAL_LANGUAGE", severity=R.ERROR,
                            doc=unit.doc, line_no=unit.line_no, term=term,
                            message=(f"tier {tier_name} term {term!r}: "
                                     f"{lexicon[term]}"),
                            excerpt=excerpt))

            if on("UNQUANTIFIED_COMPARATIVE") and comparative_hit and not has_number:
                out.append(Finding(
                    code="UNQUANTIFIED_COMPARATIVE", severity=R.ERROR,
                    doc=unit.doc, line_no=unit.line_no, term=comparative_hit,
                    message=(f"{comparative_hit!r} claims a difference without stating "
                             "its size; a delta with no number cannot be checked"),
                    excerpt=excerpt))

            if on("UNSOURCED_CLAIM") and (has_number or comparative_hit) and not has_citation:
                out.append(Finding(
                    code="UNSOURCED_CLAIM", severity=R.ERROR,
                    doc=unit.doc, line_no=unit.line_no,
                    message=("this statement asserts a quantity or a difference and "
                             "cites no finding; it cannot be traced to anything"),
                    excerpt=excerpt))

            if on("ABSOLUTE_WITHOUT_SOURCE") and not has_citation:
                for term, rx in _ABSOLUTE_RE.items():
                    if rx.search(body):
                        out.append(Finding(
                            code="ABSOLUTE_WITHOUT_SOURCE", severity=R.WARN,
                            doc=unit.doc, line_no=unit.line_no, term=term.strip(),
                            message=(f"absolute {term.strip()!r} with no citation; "
                                     "absolutes are the cheapest statement to "
                                     "disprove and the most expensive to withdraw"),
                            excerpt=excerpt))
                        break

        if register is None:
            continue

        for ref in citations:
            record = register.get(ref)
            if record is None:
                if on("DANGLING_CITATION"):
                    out.append(Finding(
                        code="DANGLING_CITATION", severity=R.ERROR, doc=unit.doc,
                        line_no=unit.line_no, term=ref,
                        message=f"{ref!r} is cited but is not in the register",
                        excerpt=excerpt))
                continue
            state = str(record.get("state", "")).upper()
            if (on("UNKNOWN_PRESENTED_AS_FINDING") and has_number
                    and state in R.UNSUPPORTING_STATES):
                out.append(Finding(
                    code="UNKNOWN_PRESENTED_AS_FINDING", severity=R.ERROR,
                    doc=unit.doc, line_no=unit.line_no, term=ref,
                    message=(f"this statement asserts a figure while citing {ref}, "
                             f"whose recorded state is {state}; the citation "
                             "resolves but cannot support a number"),
                    excerpt=excerpt))
            if on("CONTRADICTED_FINDING_CITED_AS_SUPPORT") and state in R.CONTRADICTING_STATES:
                if any(rx.search(body) for rx in _SUPPORT_RE.values()):
                    out.append(Finding(
                        code="CONTRADICTED_FINDING_CITED_AS_SUPPORT", severity=R.ERROR,
                        doc=unit.doc, line_no=unit.line_no, term=ref,
                        message=(f"{ref} is recorded as CONTRADICTED and is cited here "
                                 "in a sentence framed as support"),
                        excerpt=excerpt))

    return sorted(out, key=lambda f: f.sort_key())


def audit_document(path: str, register: dict[str, dict] | None,
                   enabled: tuple[str, ...] | None = None,
                   doc_id: str | None = None) -> tuple[list[Finding], int]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    units, problems = segment(doc_id or os.path.basename(path), text)
    return sorted(problems + audit_units(units, register, enabled),
                  key=lambda f: f.sort_key()), len(units)


def render_text(findings: list[Finding], statements: int, label: str) -> str:
    errors = [f for f in findings if f.severity == R.ERROR]
    warns = [f for f in findings if f.severity == R.WARN]
    lines = [
        f"claim audit -- {label}",
        "=" * 72,
        f"statements examined : {statements}",
        f"result              : {'FAIL' if errors else 'PASS'}"
        f"  ({len(errors)} error, {len(warns)} warning)",
        "",
    ]
    for finding in findings:
        lines.append(f"  [{finding.severity}] {finding.code}  {finding.doc}:{finding.line_no}"
                     + (f"  ({finding.term})" if finding.term else ""))
        lines.append(f"      {finding.message}")
        lines.append(f"      > {finding.excerpt}")
    if not findings:
        lines.append("  Every substantive statement carries a citation that resolves to a")
        lines.append("  record able to support it, and no promotional term was found.")
    lines.append("")
    return "\n".join(lines)


def scan_corpus(root: str, enabled: tuple[str, ...]) -> dict:
    """Advisory sweep over a tree of markdown. No register, so only the rules
    that need no register are run -- see --rules."""
    per_rule: dict[str, int] = {}
    per_term: dict[str, int] = {}
    per_file: dict[str, int] = {}
    files = 0
    statements = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__"))
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            try:
                found, count = audit_document(path, None, enabled, doc_id=rel)
            except (OSError, UnicodeDecodeError):
                continue
            files += 1
            statements += count
            if found:
                per_file[rel] = len(found)
            for f in found:
                per_rule[f.code] = per_rule.get(f.code, 0) + 1
                if f.term:
                    per_term[f.term] = per_term.get(f.term, 0) + 1
    return {
        "root": root,
        "files_scanned": files,
        "statements_examined": statements,
        "files_with_findings": len(per_file),
        "findings_by_rule": dict(sorted(per_rule.items())),
        "top_terms": dict(sorted(per_term.items(), key=lambda kv: (-kv[1], kv[0]))[:15]),
        "advisory_note": (
            "Corpus mode runs only the rules that need no finding register. These "
            "are REVIEW CANDIDATES, not defects. An engineering README is not a "
            "client deliverable and should not be held to a leadership-paper "
            "standard; the rules are calibrated for the latter."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--doc", help="a single markdown deliverable to audit")
    src.add_argument("--corpus", help="walk a tree of .md files (advisory sweep)")
    p.add_argument("--register", help="finding/recommendation register JSON")
    p.add_argument("--rules", default="all", choices=["all", "language"],
                   help="'language' runs only the rules that need no register")
    p.add_argument("--format", default="text", choices=["text", "json"])
    p.add_argument("--out", help="write the report to this file as well")
    args = p.parse_args(argv)

    enabled = LANGUAGE_RULES if args.rules == "language" else None

    if args.corpus:
        payload = scan_corpus(args.corpus, LANGUAGE_RULES)
        body = (json.dumps(payload, indent=2) + "\n" if args.format == "json"
                else "\n".join([f"corpus sweep -- {payload['root']}", "=" * 72,
                                f"files scanned        : {payload['files_scanned']}",
                                f"statements examined  : {payload['statements_examined']}",
                                f"files with findings  : {payload['files_with_findings']}",
                                "", "findings by rule:"]
                               + [f"  {k:34s} {v}" for k, v in payload["findings_by_rule"].items()]
                               + ["", "most frequent terms:"]
                               + [f"  {k:34s} {v}" for k, v in payload["top_terms"].items()]
                               + ["", payload["advisory_note"], ""]))
        sys.stdout.write(body)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(body)
        return 0

    register = None
    if args.register:
        try:
            register = load_register(args.register)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"error: could not load register: {exc}", file=sys.stderr)
            return 2
    try:
        findings, statements = audit_document(args.doc, register, enabled)
    except OSError as exc:
        print(f"error: could not read document: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        body = json.dumps({
            "document": args.doc,
            "statements_examined": statements,
            "passed": not any(f.severity == R.ERROR for f in findings),
            "findings": [f.to_dict() for f in findings],
        }, indent=2) + "\n"
    else:
        body = render_text(findings, statements, args.doc)
    sys.stdout.write(body)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(body)

    return 1 if any(f.severity == R.ERROR for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
