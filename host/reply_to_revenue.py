#!/usr/bin/env python3
"""Chronology-safe reply-to-revenue entrypoint.

All observation identity, contact-state, and positive-surface authority lives in
``reply_to_revenue_core.py``. This wrapper intentionally contains no policy of
its own: wrapper imports, direct-core imports, and both CLI paths must execute
the same retained implementation graph.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_CORE_PATH = Path(__file__).with_name("reply_to_revenue_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "_commons_reply_to_revenue_core",
    _CORE_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load reply-to-revenue core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_core.main())
