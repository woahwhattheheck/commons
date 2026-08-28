#!/usr/bin/env python3
"""Exact-host launcher for the owner-context display service.

Stdlib HTTP. Display only. Never a gate. GitHub Actions is not an
always-on host. Secrets never belong in this tree.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "host") not in sys.path:
    sys.path.insert(0, str(ROOT / "host"))

import owner_context as oc


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["serve"]
    bind = os.environ.get("OWNER_CONTEXT_BIND", "0.0.0.0:8789")
    if argv[0] == "serve" and "--bind" not in argv:
        argv = ["serve", "--bind", bind, *argv[1:]]
    return oc.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
