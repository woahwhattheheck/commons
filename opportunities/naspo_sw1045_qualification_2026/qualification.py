#!/usr/bin/env python3
"""Public NASPO SW1045 qualification v1 entrypoint.

There is one executable/import authority: ``qualification_core``.  That module
installs the metadata-only fail-closed packet ceiling before exporting any
compiler API.  This wrapper is intentionally only a compatibility re-export;
it contains no monkeypatch and no second policy generation.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from opportunities.naspo_sw1045_qualification_2026 import qualification_core as _core
from opportunities.naspo_sw1045_qualification_2026.qualification_core import *  # noqa: F401,F403,E402


if __name__ == "__main__":
    raise SystemExit(_core.main())
