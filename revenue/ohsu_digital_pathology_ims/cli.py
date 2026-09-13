# SPDX-License-Identifier: Apache-2.0
"""CLI for offline OHSU RFP-2027-2012 qualification evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from qualification import QualificationError, evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate OHSU RFP-2027-2012 qualification evidence")
    parser.add_argument("bundle", type=Path, help="JSON qualification bundle")
    parser.add_argument("--evaluated-at", required=True, help="trusted UTC verifier time, e.g. 2026-09-13T09:30:00Z")
    parser.add_argument("--output", type=Path, help="write receipt atomically instead of stdout")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.bundle.read_text(encoding="utf-8"))
        receipt = evaluate(payload, evaluated_at=args.evaluated_at)
    except (OSError, json.JSONDecodeError, QualificationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_name(args.output.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(args.output)
    return 0 if receipt["decision"] == "READY_FOR_INTERNAL_BID_REVIEW" else 3


if __name__ == "__main__":
    raise SystemExit(main())
