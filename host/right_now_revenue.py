#!/usr/bin/env python3
"""Canonical entrypoint for current-safe right-now revenue control."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.right_now_revenue_current import *  # noqa: F401,F403,E402
from host.right_now_revenue_current import main as _main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(_main())
