#!/usr/bin/env python3
"""Numeric claims in delivery documentation vs. measured reality.

STATUS: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.

The gap
-------
UIOWA-117 checks that a report's outputs agree with each other: a summary saying
"three priority findings" over a matrix holding five is a COUNT_MISMATCH. The
same defect class exists one level up, in the delivery's own documentation. A
README says "41 tests"; the suite runs 47, because six were added afterwards and
the sentence was never touched. Nobody is checking that.

This is not a duplicate of the run sweep. `uiowa_rfq_18649_run_sweep/` (OP5-
IRONWOOD) already measured every lane by executing it, and this module
**consumes that landed artifact** rather than re-running anybody's suite. The run
sweep answers "does it run". This answers "does the prose match what ran".

Why the extraction is careful
-----------------------------
A first, naive pass over the tree produced 50 "mismatches". Almost all were
artefacts of how this repository is laid out, and shipping that number would
have been a false alarm on nine other seats:

- **Sample packets embed other lanes' documents.** `acceptance_map/output/
  sample_packet/uiowa_rfq_18649_intake_rehearsal__README.md` is intake
  rehearsal's README, sitting in acceptance map's directory. Attributing a claim
  to the directory it is stored in is wrong; the filename says whose it is.
- **Verification logs quote other lanes' runs.** One lane's log produced 20+
  hits, each a different number, because it records what other suites printed.
  Those are captured transcripts inside fenced blocks, not self-claims.
- **A lane can hold two implementations.** `recovery_evidence` carries two, so a
  README describing one suite legitimately disagrees with the lane's total.
- **Not every "N tests" is a test count**, and not every number near the word
  is a claim about this lane.

So a claim is only compared when it can be attributed to a lane and to a
measurable quantity. Everything else is `UNVERIFIABLE` - reported as its own
class, never silently dropped and never counted as agreement.

Python 3 standard library only. No network. Executes nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
_GUARD_LANE = os.path.abspath(os.path.join(HERE, "..", "uiowa_rfq_18649_report_structure"))
if _GUARD_LANE not in sys.path:
    sys.path.insert(0, _GUARD_LANE)

try:
    # Reused for fenced-block / code-span / quote stripping. Captured transcripts
    # are not self-claims, and that logic already exists rather than being
    # written twice.
    from scope_guard import strip_non_prose
except ImportError:  # pragma: no cover
    def strip_non_prose(text: str) -> str:  # type: ignore
        return text


LANE_PREFIX = "uiowa_rfq_18649_"

# Verdicts. UNVERIFIABLE is a first-class outcome, not a quiet pass.
AGREES = "AGREES"
CONTRADICTED = "CONTRADICTED"
UNVERIFIABLE = "UNVERIFIABLE"

# "41 tests", "Ran 41 tests", "41 unittest cases", "41 test cases".
#
# Two exclusions, both from real false positives in the first pass over the tree:
#   - `(?<!UIOWA-)` : "the UIOWA-136 tests assert ..." is an ORDER ID followed by
#     the word tests, not a count of 136 tests.
#   - the lookahead  : "1 test file(s) failed" counts FILES, not tests. So does
#     "2 test suites". Those are a different quantity and must not be compared
#     against a test count.
_TEST_CLAIM = re.compile(
    r"(?<!UIOWA-)(?<!uiowa-)\b(\d{1,4})\s+(?:"
    r"unittest\s+cases?"                      # "55 unittest cases"
    r"|(?:unittest\s+)?tests?(?:\s+cases?)?"  # "41 tests", "22 unittest tests"
    r")"
    r"(?!\s+(?:file|files|script|scripts|suite|suites|module|modules|dir))\b", re.I)
# A sentence naming a specific suite file lets the claim be checked against that
# suite rather than the lane total.
_SUITE_NAME = re.compile(r"\b(test_[A-Za-z0-9_]+\.py)\b")


@dataclass
class Claim:
    lane: str
    stored_in: str
    file: str
    line: int
    claimed: int
    measured: object
    verdict: str
    basis: str
    reason: str
    sentence: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftResult:
    root: str
    claims: list = field(default_factory=list)
    lanes_with_measurement: int = 0
    files_examined: int = 0
    files_skipped_non_root: int = 0
    sweep_path: str = ""

    def by_verdict(self, v: str) -> list:
        return [c for c in self.claims if c.verdict == v]


def load_measurements(root: str) -> tuple[dict, str]:
    """Per-lane measured test counts from the landed run sweep."""
    path = os.path.join(root, "uiowa_rfq_18649_run_sweep", "out", "run_sweep.json")
    if not os.path.exists(path):
        return {}, ""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict] = {}
    for lane in data.get("lanes", []):
        out[lane["lane"]] = lane
    return out, path


def attribute_lane(root: str, path: str, stored_lane: str) -> str:
    """Whose document is this?

    A sample packet embeds other lanes' files, naming the source lane in the
    filename (`uiowa_rfq_18649_intake_rehearsal__README.md`). The directory it
    sits in is not the author.
    """
    base = os.path.basename(path)
    if LANE_PREFIX in base:
        m = re.match(rf"({re.escape(LANE_PREFIX)}[a-z0-9_]+?)__", base)
        if m:
            return m.group(1)
    return stored_lane


# A bare short name is not a lane reference. "the 022 handoff" contains
# "handoff", which is also a lane directory name - matching on the short name
# attributed that sentence to `uiowa_rfq_18649_handoff` and compared a claim
# against a completely unrelated lane's total. Full directory names only.
def _mentions_other_lane(sentence: str, lane: str, known: Sequence[str]) -> str:
    for other in known:
        if other != lane and other in sentence:
            return other
    return ""


# Markers that make a sentence ambiguous: it is talking about some other piece of
# work, so a number in it cannot be confidently read as this lane's own count.
_AMBIGUOUS_REF = re.compile(r"\bUIOWA-\d+\b|\bPR\s*#\d+\b|\bcommit\b", re.I)


def _ambiguous(sentence: str, lane: str, known: Sequence[str]) -> str:
    m = _AMBIGUOUS_REF.search(sentence)
    if m:
        return m.group(0)
    for other in known:
        if other == lane:
            continue
        short = other[len(LANE_PREFIX):]
        if len(short) > 5 and short in sentence:
            return short
    return ""


def extract_claims(root: str, measurements: dict,
                   skip_dir_names: Sequence[str] = ("out", "__pycache__")) -> DriftResult:
    res = DriftResult(root=root)
    known = sorted(measurements)
    res.lanes_with_measurement = len(known)
    if not os.path.isdir(root):
        return res

    for stored_lane in sorted(os.listdir(root)):
        lane_dir = os.path.join(root, stored_lane)
        if not os.path.isdir(lane_dir) or not stored_lane.startswith(LANE_PREFIX):
            continue
        # Only a lane's ROOT-level markdown is its documentation of itself.
        #
        # Files under sample/, output/ and examples/ are operational records and
        # embedded copies: one lane's `sample/verification_log.md` records what
        # OTHER lanes' suites printed, and `output/sample_packet/` holds verbatim
        # copies of other lanes' READMEs. Treating those as self-claims produced
        # dozens of accusations against seats who had written nothing wrong.
        res.files_skipped_non_root += sum(
            len([f for f in files if f.endswith(".md")])
            for dp, dn, files in os.walk(lane_dir)
            if os.path.abspath(dp) != os.path.abspath(lane_dir)
            and not any(part in skip_dir_names for part in dp.split(os.sep)))
        for dirpath, dirnames, filenames in [(lane_dir, [], sorted(os.listdir(lane_dir)))]:
            for fn in sorted(f for f in filenames
                             if os.path.isfile(os.path.join(lane_dir, f))):
                if not fn.endswith(".md"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root)
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        raw = f.read()
                except OSError:
                    continue
                res.files_examined += 1
                lane = attribute_lane(root, path, stored_lane)
                # Captured transcripts and code samples are not claims.
                # Claims are read from prose with code/transcripts stripped, but
                # a suite filename is normally written as `test_x.py` - inside a
                # code span, which the stripper blanks. So the raw line is kept
                # and used for the suite/lane-name lookups only.
                body = strip_non_prose(raw)
                raw_lines = {i + 1: ln for i, ln in enumerate(raw.split("\n"))}
                for line_no, sentence in _lines(body):
                    for m in _TEST_CLAIM.finditer(sentence):
                        res.claims.append(
                            _judge(lane, stored_lane, rel, line_no, int(m.group(1)),
                                   sentence, measurements, known,
                                   raw_sentence=raw_lines.get(line_no, sentence)))
    return res


def _lines(text: str) -> list[tuple[int, str]]:
    return [(i + 1, ln.strip()) for i, ln in enumerate(text.split("\n")) if ln.strip()]


def _judge(lane: str, stored_lane: str, rel: str, line_no: int, claimed: int,
           sentence: str, measurements: dict, known: Sequence[str],
           raw_sentence: str | None = None) -> Claim:
    lookup = raw_sentence if raw_sentence is not None else sentence
    def mk(measured, verdict, basis, reason):
        return Claim(lane=lane, stored_in=stored_lane, file=rel, line=line_no,
                     claimed=claimed, measured=measured, verdict=verdict,
                     basis=basis, reason=reason, sentence=sentence[:240])

    other = _mentions_other_lane(lookup, lane, known)
    if other:
        # A claim about a different lane is checked against THAT lane.
        target = measurements.get(other, {})
        if target.get("category") != "TESTED":
            return mk(None, UNVERIFIABLE, "cross_reference",
                      f"sentence refers to {other}, which the run sweep did not measure")
        measured = target.get("tests_run_total")
        if measured == claimed:
            return mk(measured, AGREES, "cross_reference_total",
                      f"matches the measured total for {other}")
        return mk(measured, CONTRADICTED, "cross_reference_total",
                  f"states {claimed} for {other}; the run sweep measured {measured}")

    lane_m = measurements.get(lane)
    if not lane_m:
        return mk(None, UNVERIFIABLE, "no_measurement",
                  f"{lane} does not appear in the run sweep")
    if lane_m.get("category") != "TESTED":
        return mk(None, UNVERIFIABLE, "lane_not_tested",
                  f"run sweep category is {lane_m.get('category')!r}, so there is no "
                  f"measured count to compare against")

    suites = lane_m.get("suites", [])
    named = _SUITE_NAME.search(lookup)
    if named:
        hit = next((s for s in suites if s.get("suite") == named.group(1)), None)
        if hit is None:
            return mk(None, UNVERIFIABLE, "named_suite_not_measured",
                      f"sentence names {named.group(1)}, which the run sweep did not measure")
        measured = hit.get("tests_run")
        basis = f"suite:{named.group(1)}"
    elif len(suites) > 1:
        # Two implementations in one lane: a README describing one of them
        # legitimately disagrees with the lane total. Reporting that as drift
        # would be an accusation the evidence does not support.
        totals = {s.get("tests_run") for s in suites} | {lane_m.get("tests_run_total")}
        if claimed in totals:
            return mk(sorted(x for x in totals if x is not None), AGREES, "multi_suite",
                      "matches one of the lane's measured suites")
        return mk(sorted(x for x in totals if x is not None), UNVERIFIABLE, "multi_suite",
                  f"lane has {len(suites)} suites and the sentence names none; "
                  f"cannot attribute the claim to one")
    else:
        measured = lane_m.get("tests_run_total")
        basis = "lane_total"

    if measured is None:
        return mk(None, UNVERIFIABLE, basis, "run sweep recorded no count")
    if measured == claimed:
        return mk(measured, AGREES, basis, "matches the measured run")
    amb = _ambiguous(lookup, lane, known)
    if amb:
        # The sentence references other work, so the number may not be this
        # lane's own count. Disagreement here is not evidence of drift.
        return mk(measured, UNVERIFIABLE, "ambiguous_reference",
                  f"sentence references {amb!r}, so the count cannot be attributed "
                  f"to this lane with confidence (measured {measured})")
    return mk(measured, CONTRADICTED, basis,
              f"documentation states {claimed}; the run sweep measured {measured}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_DISCLAIMER = (
    "Numeric claims are compared against the measured run recorded in "
    "`uiowa_rfq_18649_run_sweep/out/run_sweep.json`. This screen executes nothing. A "
    "CONTRADICTED row means the sentence and that measurement disagree -- most often "
    "because tests were added after the sentence was written. It is a documentation "
    "question for the lane's owner, not a defect in their code and not a compliance "
    "claim. UNVERIFIABLE means there is no measurement this claim can be checked "
    "against; it is never treated as agreement."
)


def render_markdown(res: DriftResult) -> str:
    bad = res.by_verdict(CONTRADICTED)
    ok = res.by_verdict(AGREES)
    unk = res.by_verdict(UNVERIFIABLE)
    L = ["# Documentation claim drift -- RFQ 18649 delivered tree", "",
         "**Status: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.**",
         "", _DISCLAIMER, "",
         f"- lanes with a measured run: **{res.lanes_with_measurement}**",
         f"- lane-root markdown files examined: **{res.files_examined}**",
         f"- non-root markdown files skipped (operational records / embedded "
         f"copies): **{res.files_skipped_non_root}**",
         f"- claims found: **{len(res.claims)}**",
         f"- agrees: **{len(ok)}**",
         f"- contradicted: **{len(bad)}**",
         f"- unverifiable: **{len(unk)}**", ""]
    if bad:
        L += ["## Contradicted", "",
              "| lane | file:line | documentation says | measured | basis |",
              "|---|---|---|---|---|"]
        for c in sorted(bad, key=lambda x: (x.lane, x.file, x.line)):
            L.append(f"| `{c.lane}` | `{c.file}:{c.line}` | {c.claimed} | {c.measured} "
                     f"| {c.basis} |")
        L.append("")
    if unk:
        L += ["## Unverifiable", "",
              "Reported rather than dropped. None of these is counted as agreement.", "",
              "| lane | file:line | claim | why |", "|---|---|---|---|"]
        for c in sorted(unk, key=lambda x: (x.lane, x.file, x.line)):
            L.append(f"| `{c.lane}` | `{c.file}:{c.line}` | {c.claimed} | {c.reason} |")
        L.append("")
    return "\n".join(L)


def render_console(res: DriftResult) -> str:
    bad = res.by_verdict(CONTRADICTED)
    L = ["DOCUMENTATION CLAIM DRIFT -- RFQ 18649", "=" * 62,
         f"root                    : {res.root}",
         f"lanes with measurement  : {res.lanes_with_measurement}",
         f"lane-root files examined: {res.files_examined}",
         f"non-root files skipped  : {res.files_skipped_non_root}",
         f"claims found            : {len(res.claims)}",
         f"agrees                  : {len(res.by_verdict(AGREES))}",
         f"CONTRADICTED            : {len(bad)}",
         f"unverifiable            : {len(res.by_verdict(UNVERIFIABLE))}", ""]
    for c in sorted(bad, key=lambda x: (x.lane, x.file, x.line)):
        L.append(f"  {c.lane}")
        L.append(f"      {c.file}:{c.line}  says {c.claimed}, measured {c.measured} "
                 f"({c.basis})")
        L.append(f"      {c.sentence[:120]}")
    if not bad:
        L.append("  no contradicted claims")
    return "\n".join(L)


CSV_HEADERS = ["lane", "stored_in", "file", "line", "claimed", "measured", "verdict",
               "basis", "reason"]


def write_outputs(res: DriftResult, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    p = os.path.join(out_dir, "doc_claim_drift.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(render_markdown(res))
    written.append(p)
    p = os.path.join(out_dir, "doc_claim_drift.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADERS)
        for c in sorted(res.claims, key=lambda x: (x.verdict, x.lane, x.file, x.line)):
            w.writerow([c.lane, c.stored_in, c.file, c.line, c.claimed, c.measured,
                        c.verdict, c.basis, c.reason])
    written.append(p)
    p = os.path.join(out_dir, "doc_claim_drift.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"status": "READ_ONLY_SCREEN_NOT_A_COMPLIANCE_CLAIM",
                   "disclaimer": _DISCLAIMER,
                   "sweep_source": res.sweep_path,
                   "lanes_with_measurement": res.lanes_with_measurement,
                   "files_examined": res.files_examined,
                   "counts": {v: len(res.by_verdict(v))
                              for v in (AGREES, CONTRADICTED, UNVERIFIABLE)},
                   "claims": [c.as_dict() for c in res.claims]}, f, indent=2)
    written.append(p)
    return written


def run(root: str) -> DriftResult:
    measurements, sweep_path = load_measurements(root)
    res = extract_claims(root, measurements)
    res.sweep_path = sweep_path
    return res


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Compare numeric documentation claims against the measured run sweep.")
    ap.add_argument("--root", default=os.path.abspath(os.path.join(HERE, "..")))
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-contradiction", action="store_true",
                    help="exit 1 when a claim is contradicted (off by default: this "
                         "screens other people's documentation)")
    a = ap.parse_args(argv)

    res = run(a.root)
    if not res.sweep_path:
        print("NOTE: run_sweep.json not found; every claim will be UNVERIFIABLE. "
              "This screen does not execute suites of its own.")
    if a.json:
        print(json.dumps({"counts": {v: len(res.by_verdict(v))
                                     for v in (AGREES, CONTRADICTED, UNVERIFIABLE)},
                          "claims": [c.as_dict() for c in res.claims]}, indent=2))
    else:
        print(render_console(res))
    if a.out:
        for p in write_outputs(res, a.out):
            print(f"wrote {p}")
    return 1 if (a.fail_on_contradiction and res.by_verdict(CONTRADICTED)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
