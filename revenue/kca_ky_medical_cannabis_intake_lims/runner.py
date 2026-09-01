#!/usr/bin/env python3
"""Thin pack entrypoint for the KCA synthetic intake engine."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import kca_ky_medical_cannabis_intake_lims as intake


def main(argv: list[str] | None = None) -> int:
    return int(intake.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
