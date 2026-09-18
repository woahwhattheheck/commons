#!/usr/bin/env python3
"""Root Commons CI bridge for the Hyperagent transcript pilot proof."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

MODULES = [
    "revenue.hyperagent_slack_transcript.test_adapter",
    "revenue.hyperagent_slack_transcript.test_stateful",
    "revenue.hyperagent_slack_transcript.test_public_surface",
]


def main() -> int:
    root = Path(__file__).resolve().parent
    for optimized in (False, True):
        argv = [sys.executable]
        if optimized:
            argv.append("-O")
        argv.extend(["-m", "unittest", "-v", *MODULES])
        completed = subprocess.run(argv, cwd=root, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
