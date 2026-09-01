#!/usr/bin/env python3
"""Official command for mvmtc-aero-fastener-evidence-lims-01.

Thin door over the revenue runner. The program lives at
revenue/mvmtc_aero_fastener_evidence/runner.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "revenue" / "mvmtc_aero_fastener_evidence" / "runner.py"
SPEC = importlib.util.spec_from_file_location("mvmtc_aero_fastener_evidence_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("missing revenue/mvmtc_aero_fastener_evidence/runner.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main(argv: list[str] | None = None) -> int:
    return int(MODULE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
