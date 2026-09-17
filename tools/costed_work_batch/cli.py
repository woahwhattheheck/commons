#!/usr/bin/env python3
"""CLI for the costed work-batch optimizer."""
from __future__ import annotations

import argparse
import pathlib
import sys

try:
    from .planner import (
        ScenarioError,
        canonical_json,
        load_strict_json,
        optimize,
        parse_scenario,
        render_schedule,
    )
except ImportError:  # direct script execution
    from planner import (  # type: ignore
        ScenarioError,
        canonical_json,
        load_strict_json,
        optimize,
        parse_scenario,
        render_schedule,
    )


MAX_INPUT_BYTES = 2_000_000


def _read_bounded(path: pathlib.Path) -> str:
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ScenarioError(
            f"scenario exceeds {MAX_INPUT_BYTES} byte CLI limit"
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScenarioError("scenario must be UTF-8") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Optimize an advisory batch under owner-entered economics."
    )
    parser.add_argument("scenario", type=pathlib.Path)
    parser.add_argument("--json", action="store_true", help="emit canonical JSON")
    args = parser.parse_args(argv)

    try:
        raw = load_strict_json(_read_bounded(args.scenario))
        result = optimize(parse_scenario(raw))
    except (OSError, ScenarioError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(canonical_json(result))
    else:
        sys.stdout.write(render_schedule(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
