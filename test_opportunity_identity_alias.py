#!/usr/bin/env python3
"""Bridge opportunity-identity hostiles into the retained Commons root battery.

The canonical battery discovers root test_*.py files. Keep the package-local
suite modular, but make both ordinary and -O executions part of the retained
workflow without adding another active Actions workflow.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MODULES = (
    "revenue.opportunity_identity_alias.test_resolution",
    "revenue.opportunity_identity_alias.test_transition",
    "revenue.opportunity_identity_alias.test_io",
)


def run(optimized: bool) -> int:
    argv = [sys.executable]
    if optimized:
        argv.append("-O")
    argv.extend(["-m", "unittest", "-v", *MODULES])
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(argv, cwd=ROOT, env=env)
    return completed.returncode


def main() -> int:
    ordinary = run(False)
    optimized = run(True)
    if ordinary or optimized:
        print(
            f"opportunity identity hostiles failed: normal={ordinary} optimized={optimized}",
            file=sys.stderr,
        )
        return 1
    print("opportunity identity hostiles passed: normal + python -O")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
