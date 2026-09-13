"""CLI for the public Steerability Challenge foundation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

try:
    from .experiment_matrix import experiment_matrix
    from .scorecard import ScorecardError, load_jsonl, rank_recipes
    from .submission_plan import PlanError, load_plan
except ImportError:  # direct script execution
    from experiment_matrix import experiment_matrix
    from scorecard import ScorecardError, load_jsonl, rank_recipes
    from submission_plan import PlanError, load_plan


def _write(value: Any, output: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rank = sub.add_parser("rank", help="rank shared recipes from normalized local JSONL evidence")
    rank.add_argument("evaluations")
    rank.add_argument("--model-spread-penalty", type=float, default=0.25)
    rank.add_argument("--run-instability-penalty", type=float, default=0.10)
    rank.add_argument("--output")

    validate = sub.add_parser("validate-plan", help="validate public cross-model submission invariants")
    validate.add_argument("plan")
    validate.add_argument("--require-files", action="store_true")
    validate.add_argument("--output")

    matrix = sub.add_parser("matrix", help="emit the source-bound pre-registration experiment matrix")
    matrix.add_argument("--output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "rank":
            result = rank_recipes(
                load_jsonl(args.evaluations),
                model_spread_penalty=args.model_spread_penalty,
                run_instability_penalty=args.run_instability_penalty,
            )
        elif args.command == "validate-plan":
            result = load_plan(args.plan, require_files=args.require_files)
        elif args.command == "matrix":
            result = experiment_matrix()
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (ScorecardError, PlanError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    _write(result, getattr(args, "output", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
