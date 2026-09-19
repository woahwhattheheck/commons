#!/usr/bin/env python3
"""Integrated AI decision case: quality, lifecycle and economics in one run.

    python3 ai_decision_case.py --case fixtures/beneficial.json
    python3 ai_decision_case.py --case fixtures/unfavourable.json --sweep
    python3 ai_decision_case.py --case fixtures/beneficial.json \
        --set analyst_hourly_cost=40 --diff
    python3 ai_decision_case.py --case fixtures/undecidable.json --format json

Exit status
  0  the case ran and its explanation passed the citation audit
  1  the explanation failed the audit -- an unsourced or dangling quantity was
     emitted, which is a defect in this tool and not something to ship past
  2  the case could not be loaded

Python 3 standard library only. No network. No clock, no RNG, sorted traversal:
two runs on the same case are byte-identical.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import explain
import sensitivity
from case import decide
from model import CaseLoadError, load_case


def _apply_sets(case, assignments):
    for raw in assignments or []:
        if "=" not in raw:
            raise SystemExit(f"--set expects name=value, got {raw!r}")
        name, value = raw.split("=", 1)
        try:
            case = sensitivity.with_assumption(case, name.strip(), float(value))
        except KeyError as exc:
            raise SystemExit(f"--set: {exc}")
        except ValueError:
            raise SystemExit(f"--set: {value!r} is not a number")
    return case


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--case", required=True, help="path to a synthetic case JSON file")
    p.add_argument("--format", default="markdown", choices=["markdown", "json", "text"])
    p.add_argument("--set", action="append", dest="sets", metavar="NAME=VALUE",
                   help="override an assumption and re-run (repeatable)")
    p.add_argument("--sweep", action="store_true",
                   help="classify every assumption and report the break-even margin")
    p.add_argument("--diff", action="store_true",
                   help="with --set, print the line-level explanation diff")
    p.add_argument("--out", help="write explanation.md and decision.json here")
    args = p.parse_args(argv)

    try:
        base_case = load_case(args.case)
    except (CaseLoadError, FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: could not load case: {exc}", file=sys.stderr)
        return 2

    case = _apply_sets(base_case, args.sets)
    decision = decide(case)
    text = explain.render(case, decision)
    problems = explain.audit_explanation(text, case)

    payload = {
        "decision": decision.to_dict(),
        "explanation_audit": {
            "passed": not problems,
            "problems": problems,
            "checked_lines_rule": "every line stating a quantity must cite a record "
                                  "id, and every cited id must resolve to a record "
                                  "in this case",
        },
    }
    if args.sweep:
        payload["assumption_classification"] = sensitivity.classify_assumptions(case)
        payload["verdict_margin"] = sensitivity.find_verdict_flip(case)

    if args.format == "json":
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")
        if args.sweep:
            sys.stdout.write("## Which assumptions can change the answer\n\n")
            sys.stdout.write("| assumption | classification | verdict at low | "
                             "verdict at high |\n|---|---|---|---|\n")
            for row in payload["assumption_classification"]:
                sys.stdout.write(
                    f"| {row['assumption']} | {row['classification']} | "
                    f"{row['verdict_at_low']} | {row['verdict_at_high']} |\n")
            sys.stdout.write("\n" + payload["verdict_margin"]["note"] + "\n\n")
        if problems:
            sys.stdout.write("## Explanation audit: FAILED\n\n")
            for problem in problems:
                sys.stdout.write(f"- {problem}\n")
            sys.stdout.write("\n")
        else:
            sys.stdout.write("Explanation audit: PASSED — every quantity above "
                             "cites a record in this case.\n")

    if args.diff and args.sets:
        before = explain.render(base_case, decide(base_case))
        sys.stdout.write("\n## What changed when the assumption moved\n\n```\n")
        diff = sensitivity.explanation_diff(before, text)
        sys.stdout.write("\n".join(diff) if diff else
                         "(no line of the explanation changed)")
        sys.stdout.write("\n```\n")

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "explanation.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(os.path.join(args.out, "decision.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2) + "\n")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
