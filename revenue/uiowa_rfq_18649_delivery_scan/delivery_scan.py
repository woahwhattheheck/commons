#!/usr/bin/env python3
"""Cross-lane scope-boundary screen over the delivered RFQ 18649 tree.

STATUS: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.

Why this exists
---------------
UIOWA-082 shipped a scope guard for the three deliverables this RFQ forbids:
audit/compliance verdicts, individual performance evaluation, product
procurement. Forty-plus lanes from two vendors' swarms have since shipped prose
under that same constraint, and the guard had only ever run against its own
fixtures. Nobody had screened the delivered tree.

What running it actually found
------------------------------
The first scan of 161 delivered markdown files produced 42 flags across 11
lanes. Reading all 42 by hand: **41 were false positives.** The guard's
precision on a real corpus was about 2%.

That was a finding about the tool, not about anyone's lane, and it is the reason
this module exists as a lane of its own rather than as a one-off command. Two
classes accounted for nearly all of it:

1. **Lanes declaring the boundary correctly, in list form.** "Excludes ... formal
   compliance audit, performance evaluation of any individual", "there is no
   average, maturity score, confidence score, or employee ranking",
   "(facilitator prompts, not employee scoring keys)". Six seats were flagged for
   doing exactly the right thing, because the negation sat in a comma list, a
   table cell, or a lead-in line above a bullet.

2. **The guard reading its own test data.** Ten flags were the literal string
   from 082's own CLI test, captured into two lanes' verification transcripts
   when they executed that suite.

After hardening (fenced blocks, inline code spans, markdown emphasis, negated
enumerations, lead-in inheritance for list items, and a person-required gate on
IE-02) the same corpus yields **2 flags**, and both are a single genuine wording
note. 082's own 55 tests still pass unchanged.

Honesty constraint
------------------
This is a **screen, not a proof**. A clean result means the screen found nothing
it knows how to look for. It cannot read intent, it does not understand a
sentence, and a determined author can write drift it will not catch. It emits no
score, no percentage, no pass/fail per lane, and it makes no compliance claim
about anybody's code. Findings go to the lane's owner to judge.

It is strictly read-only: it opens files to scan them and writes only into its
own output directory.

Python 3 standard library only. No network.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Iterable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))

# The guard lives in the 082 lane. Both lanes are this seat's own work, so the
# coupling is deliberate rather than a reach into someone else's code.
_GUARD_LANE = os.path.abspath(os.path.join(HERE, "..", "uiowa_rfq_18649_report_structure"))
if _GUARD_LANE not in sys.path:
    sys.path.insert(0, _GUARD_LANE)

try:
    import scope_guard  # noqa: E402
except ImportError as exc:  # pragma: no cover - environment problem, not logic
    raise SystemExit(
        f"cannot import scope_guard from {_GUARD_LANE}: {exc}\n"
        "This screen reuses the UIOWA-082 guard rather than reimplementing it.") from exc


DEFAULT_PATTERNS = ("*.md",)

# Directories whose contents are this screen's OWN output. A findings report
# necessarily quotes the sentences it flagged, so scanning it re-flags every
# finding and inflates the next run - the cry-wolf problem arriving by
# recursion. A report about drift is not delivery prose.
DEFAULT_EXCLUDE_DIRS = ("out", "__pycache__")


@dataclass
class LaneResult:
    lane: str
    files_scanned: int = 0
    flagged: list = field(default_factory=list)
    neutralized: int = 0

    @property
    def flag_count(self) -> int:
        return len(self.flagged)


@dataclass
class ScanResult:
    root: str
    lanes: dict = field(default_factory=dict)
    files_scanned: int = 0
    files_unreadable: list = field(default_factory=list)

    @property
    def total_flags(self) -> int:
        return sum(l.flag_count for l in self.lanes.values())

    @property
    def total_neutralized(self) -> int:
        return sum(l.neutralized for l in self.lanes.values())

    @property
    def flagged_lanes(self) -> list:
        return sorted((l for l in self.lanes.values() if l.flag_count), key=lambda l: l.lane)


def iter_files(root: str, lane_glob: str = "uiowa_rfq_18649_*",
               patterns: Sequence[str] = DEFAULT_PATTERNS,
               exclude_dirs: Sequence[str] = DEFAULT_EXCLUDE_DIRS) -> list[tuple[str, str]]:
    """(lane, path) for every matching file. Sorted, so a run is reproducible."""
    import fnmatch
    out: list[tuple[str, str]] = []
    if not os.path.isdir(root):
        return out
    for lane in sorted(os.listdir(root)):
        lane_dir = os.path.join(root, lane)
        if not os.path.isdir(lane_dir) or not fnmatch.fnmatch(lane, lane_glob):
            continue
        for dirpath, dirnames, filenames in os.walk(lane_dir):
            dirnames[:] = sorted(d for d in dirnames if d not in exclude_dirs)
            for fn in sorted(filenames):
                if any(fnmatch.fnmatch(fn, p) for p in patterns):
                    out.append((lane, os.path.join(dirpath, fn)))
    return out


def scan_tree(root: str, lane_glob: str = "uiowa_rfq_18649_*",
              patterns: Sequence[str] = DEFAULT_PATTERNS,
              exclude_dirs: Sequence[str] = DEFAULT_EXCLUDE_DIRS) -> ScanResult:
    res = ScanResult(root=root)
    for lane, path in iter_files(root, lane_glob, patterns, exclude_dirs):
        lr = res.lanes.setdefault(lane, LaneResult(lane=lane))
        rel = os.path.relpath(path, root)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            # An unreadable file is reported, never counted as clean.
            res.files_unreadable.append({"path": rel, "error": str(exc)})
            continue
        hits = scope_guard.scan_text(text, source_id=rel)
        flags = scope_guard.flagged(hits)
        lr.flagged.extend(flags)
        lr.neutralized += len(hits) - len(flags)
        lr.files_scanned += 1
        res.files_scanned += 1
    return res


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_DISCLAIMER = (
    "This is a **screen, not a proof.** A lane with no flags means the screen found "
    "nothing it knows how to look for -- it cannot read intent, and a determined author "
    "can write drift it will not catch. No score, percentage or pass/fail is assigned to "
    "any lane, and nothing here is a compliance claim about anybody's code. Every flag is "
    "a question for that lane's owner, not a defect ruling."
)


def render_markdown(res: ScanResult) -> str:
    L: list[str] = []
    L.append("# Cross-lane scope-boundary screen -- RFQ 18649 delivered tree")
    L.append("")
    L.append("**Status: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.**")
    L.append("")
    L.append(_DISCLAIMER)
    L.append("")
    L.append(f"- lanes scanned: **{len(res.lanes)}**")
    L.append(f"- files scanned: **{res.files_scanned}**")
    L.append(f"- flagged: **{res.total_flags}**")
    L.append(f"- neutralized (scope-boundary language, correctly not flagged): "
             f"**{res.total_neutralized}**")
    L.append(f"- lanes with at least one flag: **{len(res.flagged_lanes)}**")
    if res.files_unreadable:
        L.append(f"- files that could not be read: **{len(res.files_unreadable)}** "
                 f"(listed below; not counted as clean)")
    L.append("")

    if not res.flagged_lanes:
        L.append("No flags. See the disclaimer above for what that does and does not mean.")
    else:
        L.append("## Flags by lane")
        L.append("")
        for lr in sorted(res.flagged_lanes, key=lambda x: (-x.flag_count, x.lane)):
            L.append(f"### `{lr.lane}` -- {lr.flag_count}")
            L.append("")
            for h in lr.flagged:
                L.append(f"- **[{h.rule_id}] {h.guard_class}** in `{h.source_id}:{h.line}`")
                L.append(f"  - matched: `{h.matched}`")
                L.append(f"  - sentence: {h.sentence[:220]}")
                L.append(f"  - why: {h.why}")
                L.append(f"  - suggested rewrite: {h.suggested_rewrite}")
            L.append("")

    if res.files_unreadable:
        L.append("## Files that could not be read")
        L.append("")
        for u in res.files_unreadable:
            L.append(f"- `{u['path']}` -- {u['error']}")
        L.append("")

    L.append("## Lanes with no flags")
    L.append("")
    clean = sorted(l.lane for l in res.lanes.values() if not l.flag_count)
    L.append(", ".join(f"`{c}`" for c in clean) if clean else "_none_")
    L.append("")
    return "\n".join(L)


CSV_HEADERS = ["lane", "file", "line", "rule_id", "guard_class", "matched", "sentence"]


def write_outputs(res: ScanResult, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []

    md = os.path.join(out_dir, "scope_screen.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(render_markdown(res))
    written.append(md)

    rows = [[lr.lane, h.source_id, h.line, h.rule_id, h.guard_class, h.matched,
             h.sentence[:300]]
            for lr in sorted(res.lanes.values(), key=lambda x: x.lane) for h in lr.flagged]
    path = os.path.join(out_dir, "scope_screen.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADERS)
        w.writerows(rows)
    written.append(path)

    payload = {
        "status": "READ_ONLY_SCREEN_NOT_A_COMPLIANCE_CLAIM",
        "disclaimer": _DISCLAIMER,
        "lanes_scanned": len(res.lanes),
        "files_scanned": res.files_scanned,
        "total_flags": res.total_flags,
        "total_neutralized": res.total_neutralized,
        "files_unreadable": res.files_unreadable,
        "flags": [h.as_dict() | {"lane": lr.lane}
                  for lr in sorted(res.lanes.values(), key=lambda x: x.lane)
                  for h in lr.flagged],
    }
    path = os.path.join(out_dir, "scope_screen.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    written.append(path)
    return written


def render_console(res: ScanResult) -> str:
    L = ["CROSS-LANE SCOPE SCREEN -- RFQ 18649", "=" * 62,
         f"root            : {res.root}",
         f"lanes scanned   : {len(res.lanes)}",
         f"files scanned   : {res.files_scanned}",
         f"FLAGGED         : {res.total_flags}",
         f"neutralized     : {res.total_neutralized}",
         f"lanes flagged   : {len(res.flagged_lanes)}"]
    if res.files_unreadable:
        L.append(f"unreadable      : {len(res.files_unreadable)} (not counted as clean)")
    L.append("")
    for lr in sorted(res.flagged_lanes, key=lambda x: (-x.flag_count, x.lane)):
        L.append(f"{lr.lane}  ({lr.flag_count})")
        for h in lr.flagged:
            L.append(f"    [{h.rule_id}] {h.guard_class}  {h.source_id}:{h.line}")
            L.append(f"        matched : {h.matched!r}")
            L.append(f"        in      : {h.sentence[:140]}")
    if not res.flagged_lanes:
        L.append("no flags -- a screen result, not a proof of anything")
    return "\n".join(L)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Read-only scope-boundary screen across the delivered RFQ 18649 lanes.")
    ap.add_argument("--root", default=os.path.abspath(os.path.join(HERE, "..")),
                    help="directory holding the uiowa_rfq_18649_* lanes")
    ap.add_argument("--lane-glob", default="uiowa_rfq_18649_*")
    ap.add_argument("--pattern", action="append", default=None,
                    help="filename glob to scan (repeatable; default *.md)")
    ap.add_argument("--out", default=None, help="write the report artifacts into this directory")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the console report")
    ap.add_argument("--fail-on-flag", action="store_true",
                    help="exit 1 when any flag is found (off by default: this screens other "
                         "people's lanes and should not break their builds)")
    a = ap.parse_args(argv)

    res = scan_tree(a.root, a.lane_glob, tuple(a.pattern) if a.pattern else DEFAULT_PATTERNS)

    if a.json:
        print(json.dumps({"lanes_scanned": len(res.lanes), "files_scanned": res.files_scanned,
                          "total_flags": res.total_flags,
                          "total_neutralized": res.total_neutralized,
                          "flags": [h.as_dict() for lr in res.lanes.values() for h in lr.flagged]},
                         indent=2))
    else:
        print(render_console(res))

    if a.out:
        for p in write_outputs(res, a.out):
            print(f"wrote {p}")

    return 1 if (a.fail_on_flag and res.total_flags) else 0


if __name__ == "__main__":
    raise SystemExit(main())
