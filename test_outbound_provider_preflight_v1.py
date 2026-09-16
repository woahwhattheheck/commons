#!/usr/bin/env python3
"""Source-linked battery entrypoint for outbound provider preflight v1."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "tools" / "outbound_send_guard" / "test_provider_preflight_v1.py"


def main() -> int:
    for optimized in (False, True):
        argv = [sys.executable]
        if optimized:
            argv.append("-O")
        argv.append(str(TARGET))
        result = subprocess.run(argv, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
