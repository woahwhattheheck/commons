#!/usr/bin/env python3
"""Check that time-bounded claims agree with the dates of their evidence.

    python3 check_window.py --claims fixtures/claims_UNSOUND.json
    python3 check_window.py --claims fixtures/claims_SOUND.json --format json

Exit status: 0 no errors, 1 errors present, 2 the input could not be read.

The assessment date comes from the input's `as_of`, never from the system
clock, so the same input gives the same answer on any day. Stdlib only, no
network.
"""
from __future__ import annotations

import argparse
import json
import sys

import window


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--claims", required=True)
    p.add_argument("--format", default="text", choices=["text", "json"])
    p.add_argument("--out")
    args = p.parse_args(argv)

    try:
        as_of, evidence, claims, settings = window.load(args.claims)
    except (OSError, window.WindowError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: could not load claims: {exc}", file=sys.stderr)
        return 2

    findings = window.check(as_of, evidence, claims, settings)
    if args.format == "json":
        body = json.dumps({
            "as_of": as_of.isoformat(),
            "claims_checked": len(claims),
            "settings": settings,
            "passed": not any(f.severity == window.ERROR for f in findings),
            "findings": [f.to_dict() for f in findings],
        }, indent=2) + "\n"
    else:
        body = window.render_text(as_of, claims, findings, settings)
    sys.stdout.write(body)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(body)
    return 1 if any(f.severity == window.ERROR for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
