#!/usr/bin/env python3
"""Thin pack entrypoint for the MGA Alabama materials-program engine."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mga_alabama_materials_program_lims as lineage


def main(argv: list[str] | None = None) -> int:
    return int(lineage.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
