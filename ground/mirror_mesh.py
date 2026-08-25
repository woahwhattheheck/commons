#!/usr/bin/env python3
"""Thin wrapper. Canonical core lives in mesh/core.py."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mesh.core import run_fixture

if __name__ == "__main__":
    raise SystemExit(run_fixture())
