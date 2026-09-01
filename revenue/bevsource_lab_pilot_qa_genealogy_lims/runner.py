#!/usr/bin/env python3
"""Thin pack door over the BevSource lab pilot QA genealogy runner."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bevsource_lab_pilot_qa_genealogy_lims as gate


def main(argv: list[str] | None = None) -> int:
    del argv
    return int(gate.main())


if __name__ == "__main__":
    raise SystemExit(main())
