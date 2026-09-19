#!/usr/bin/env python3
"""CLI for the filesystem-safety screen.

    python3 fs_safety.py --root /path/to/revenue --lane-prefix uiowa_rfq_18649 \
        --output-dir examples

Exit codes:
    0  no REVIEW_REQUIRED finding
    1  at least one REVIEW_REQUIRED finding -- a human must look
    2  the scan could not run

Writes only inside --output-dir, through the single writer below. Reads
everything else.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

import fsaudit
from fsaudit import (
    CLEAN, REVIEW_REQUIRED, SELF_SCOPED, TEST_CONTEXT, UNDETERMINED, UNPARSEABLE,
    WRITE_TO_CALLER_PATH,
)

DISCLAIMER = (
    "This is a SCREEN, not a proof. CLEAN means the screen found nothing it "
    "could see -- it does not mean the module is safe. Dynamic dispatch, "
    "getattr, C extensions and anything inside a subprocess are invisible to "
    "an AST. No safety score is produced and no lane is marked compliant."
)

CSV_COLUMNS = ["lane", "module", "line", "kind", "call", "classification", "target", "why"]


def write_output(output_dir: str, relative_path: str, text: str) -> str:
    """The only writer. Refuses any target outside output_dir."""
    if os.path.isabs(relative_path):
        raise ValueError(f"refusing absolute output path {relative_path!r}")
    root = os.path.realpath(output_dir)
    target = os.path.realpath(os.path.join(root, relative_path))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError(f"refusing to write outside the output directory: {relative_path!r}")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return target


def render_csv(reports: list) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for report in reports:
        for f in report.findings:
            row = f.to_json()
            writer.writerow({k: row[k] for k in CSV_COLUMNS})
    return buf.getvalue()


def render_markdown(reports: list, summary: dict, root: str) -> str:
    lines = [
        "# Filesystem-safety screen",
        "",
        f"> {DISCLAIMER}",
        "",
        f"Scanned: `{root}`",
        "",
        f"- modules scanned: **{summary['modules_scanned']}** across "
        f"**{summary['lanes_scanned']}** lanes",
        f"- findings: **{summary['findings']}**",
        f"- `REVIEW_REQUIRED`: **{summary['review_required']}**",
        f"- `UNDETERMINED`: **{summary['undetermined']}**",
        "",
        "`REVIEW_REQUIRED` means exactly one thing here: **this tool can remove, "
        "move, rename or truncate a path the caller names.** Writing where you "
        "asked it to write is reported separately.",
        "",
        "## Module status counts",
        "",
        "| status | modules |",
        "| --- | --- |",
    ]
    for status, count in summary["modules_by_status"].items():
        lines.append(f"| `{status}` | {count} |")

    lines += [
        "",
        "`UNPARSEABLE` is listed separately and is never counted as CLEAN: a "
        "module the screen could not read is not a module it cleared.",
        "",
        "## Lanes needing a human look",
        "",
    ]
    flagged = [(lane, st) for lane, st in summary["lanes_by_status"].items()
               if st in (REVIEW_REQUIRED, UNDETERMINED, UNPARSEABLE)]
    if not flagged:
        lines.append("None.")
    else:
        lines += ["| lane | worst status |", "| --- | --- |"]
        for lane, status in flagged:
            lines.append(f"| `{lane}` | `{status}` |")

    for level, heading, note in (
        (REVIEW_REQUIRED, "REVIEW_REQUIRED - the target comes from outside the module",
         "Each of these removes, moves or overwrites a path chosen by the caller, "
         "by argv, by the environment, or by a config value. That is not "
         "automatically wrong -- it is what a human has to confirm is intended."),
        (UNDETERMINED, "UNDETERMINED - the screen could not trace the target",
         "Reported as its own class on purpose. A screen that cannot tell does "
         "not get to report clean."),
        (WRITE_TO_CALLER_PATH,
         "WRITE_TO_CALLER_PATH - writes where the caller pointed it",
         "Normal for every CLI here: they all take an output option. Listed so "
         "an operator can confirm none of them can be aimed at evidence that "
         "must be kept. These do not delete anything."),
        (TEST_CONTEXT, "TEST_CONTEXT - inside a test module",
         "Test suites legitimately create and remove their own temp trees. "
         "Listed for completeness, not as a concern."),
        (SELF_SCOPED, "SELF_SCOPED - the module created the path it removes",
         "A verifier cleaning up its own scratch copy lands here. This is the "
         "shape you want."),
    ):
        rows = [f for r in reports for f in r.findings if f.classification == level]
        lines += ["", f"## {heading}", "", note, ""]
        if not rows:
            lines.append("None.")
            continue
        lines += ["| lane | module:line | call | target | why |", "| --- | --- | --- | --- | --- |"]
        for f in rows:
            target = f.target_expr.replace("|", "\\|")
            if len(target) > 48:
                target = target[:45] + "..."
            lines.append(
                f"| `{f.lane}` | `{f.module}:{f.line}` | `{f.call}` | `{target}` | {f.why} |"
            )

    unparseable = [r for r in reports if not r.parsed]
    lines += ["", "## Modules the screen could not read", ""]
    if not unparseable:
        lines.append("None.")
    else:
        lines += ["| lane | module | reason |", "| --- | --- | --- |"]
        for r in unparseable:
            lines.append(f"| `{r.lane}` | `{r.module}` | {r.parse_error} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def run(args) -> int:
    if not os.path.isdir(args.root):
        print(f"ERROR: not a directory: {args.root}", file=sys.stderr)
        return 2
    reports = fsaudit.scan_tree(args.root, args.lane_prefix)
    summary = fsaudit.summarize(reports)

    payload = {
        "disclaimer": DISCLAIMER,
        "root": os.path.abspath(args.root),
        "lane_prefix": args.lane_prefix,
        "summary": summary,
        "findings": [f.to_json() for r in reports for f in r.findings],
        "unparseable": [
            {"lane": r.lane, "module": r.module, "reason": r.parse_error}
            for r in reports if not r.parsed
        ],
    }
    write_output(args.output_dir, "FILESYSTEM_SAFETY_SCREEN.md",
                 render_markdown(reports, summary, os.path.abspath(args.root)))
    write_output(args.output_dir, "findings.csv", render_csv(reports))
    write_output(args.output_dir, "screen.json",
                 json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"root            {os.path.abspath(args.root)}")
    print(f"modules         {summary['modules_scanned']} across "
          f"{summary['lanes_scanned']} lane(s)")
    print(f"findings        {summary['findings']}")
    for status in (REVIEW_REQUIRED, UNDETERMINED, WRITE_TO_CALLER_PATH,
                   TEST_CONTEXT, SELF_SCOPED, CLEAN, UNPARSEABLE):
        count = summary["modules_by_status"].get(status)
        if count:
            print(f"  modules {status:<16} {count}")
    print()
    for f in (f for r in reports for f in r.findings
              if f.classification == REVIEW_REQUIRED):
        print(f"  REVIEW_REQUIRED  {f.lane}/{f.module}:{f.line}  {f.call}({f.target_expr})")
        print(f"                   {f.why}")
    print()
    print(f"wrote           3 file(s) under {os.path.abspath(args.output_dir)}")
    print(f"note            {DISCLAIMER}")
    return 1 if summary["review_required"] else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", required=True, help="directory to scan (read-only)")
    p.add_argument("--lane-prefix", default="",
                   help="only scan lanes whose directory name starts with this")
    p.add_argument("--output-dir", default="examples",
                   help="where the report is written; nothing is written outside it")
    args = p.parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
