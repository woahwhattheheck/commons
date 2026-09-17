"""Retained root bridge for procurement submission assembly hostile coverage."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    suite = "revenue.procurement_solicitation_ingest.submission_assembly.test_engine"
    for extra in ([], ["-O"]):
        proc = subprocess.run([sys.executable, *extra, "-m", "unittest", "-v", suite], check=False)
        if proc.returncode:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
