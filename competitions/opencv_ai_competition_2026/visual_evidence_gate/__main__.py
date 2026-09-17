from __future__ import annotations

import argparse
import json

from .aws_boundary import inactive_aws_plan
from .core import compile_synthetic_run, evaluate_synthetic_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenCV 2026 deterministic Visual Evidence Gate")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="compile one synthetic trace")
    run.add_argument("--scenario", required=True)
    run.add_argument("--evaluated-at", default="2026-09-17T08:00:00Z")
    run.add_argument("--compatibility-mode", action="store_true")

    evaluate = sub.add_parser("evaluate", help="run the deterministic synthetic evaluation suite")
    evaluate.add_argument("--evaluated-at", default="2026-09-17T08:00:00Z")
    evaluate.add_argument("--compatibility-mode", action="store_true")

    sub.add_parser("aws-plan", help="render the inactive AWS deployment boundary")

    args = parser.parse_args()
    if args.command == "run":
        payload = compile_synthetic_run(
            args.scenario,
            evaluated_at=args.evaluated_at,
            compatibility_mode=args.compatibility_mode,
        )
    elif args.command == "evaluate":
        payload = evaluate_synthetic_suite(
            evaluated_at=args.evaluated_at,
            compatibility_mode=args.compatibility_mode,
        )
    else:
        payload = inactive_aws_plan()

    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
