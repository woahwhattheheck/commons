#!/usr/bin/env python3
"""CLI: build milestone delivery + billing evidence packets (UIOWA-135).

    python3 milestone_packets.py fixtures/engagement.json \
        --artifact-root fixtures/artifacts \
        --output-dir out \
        --as-of 2026-11-25

Exit codes are distinct on purpose, because "the packet is not ready" and "the
tool broke" need different responses:
    0  every packet is ready to submit as a draft
    1  the completeness report found errors (normal, actionable outcome)
    2  the input could not be read or violated the contract
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import completeness
import packets
import resolve
from schema import Engagement, PacketError

DEFAULT_AS_OF = "2026-11-25"


def load_engagement(path: str) -> Engagement:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        raise PacketError(f"engagement file not found: {path}") from None
    except json.JSONDecodeError as exc:
        # A malformed packet definition gets a diagnostic with a location, not a
        # traceback -- an operator running this at delivery time needs the line.
        raise PacketError(
            f"{path} is not valid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from None
    return Engagement.from_json(raw)


def run(args: argparse.Namespace) -> int:
    engagement = load_engagement(args.engagement)
    resolutions = resolve.resolve_all(engagement, args.artifact_root)
    report = completeness.check(engagement, resolutions, args.as_of)
    written = packets.build(engagement, resolutions, report, args.output_dir, args.as_of)

    print(f"engagement      {engagement.engagement_id} - {engagement.title}")
    print(f"as of           {args.as_of}")
    print(
        f"amounts         {engagement.milestone_total().dollars()} across "
        f"{len(engagement.milestones)} milestones "
        f"({engagement.milestone_total().cents} cents)"
    )
    opened = sum(1 for r in resolutions.values() if r.opens)
    print(f"artifacts       {opened}/{len(resolutions)} cited artifacts opened")
    print()
    for mr in report.milestone_results:
        print(
            f"  {mr.milestone_id:<6} {mr.kind:<18} {mr.amount_display:>10}  "
            f"{mr.submission_state:<14} acceptance={mr.acceptance_state:<18} "
            f"{mr.status}  ({len(mr.errors)}E/{len(mr.warnings)}W)"
        )
    print()
    print(
        f"completeness    {'PASS' if report.passed else 'FAIL'} - "
        f"{report.error_count} error(s), {report.warning_count} warning(s)"
    )
    for f in report.all_findings:
        if f.severity in (completeness.ERROR, completeness.WARN):
            scope = f.milestone_id if f.milestone_id is not None else "-"
            print(f"  {f.severity:<5} {f.code:<32} {scope} {f.message}")
    print()
    print(f"wrote           {len(written)} file(s) under {os.path.abspath(args.output_dir)}")
    return 0 if report.passed else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("engagement", help="path to the engagement/milestone JSON")
    p.add_argument("--artifact-root", default="fixtures/artifacts",
                   help="root the index paths are resolved against (read-only)")
    p.add_argument("--output-dir", default="out",
                   help="directory to write packets into; nothing is written outside it")
    p.add_argument("--as-of", default=DEFAULT_AS_OF,
                   help="YYYY-MM-DD date the report is computed against")
    args = p.parse_args(argv)
    try:
        return run(args)
    except PacketError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
