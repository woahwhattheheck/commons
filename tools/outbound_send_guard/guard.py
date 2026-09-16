"""Compatibility facade for the outbound send guard.

All supported evaluation and CLI entrypoints are verifier-clock current. The
deterministic v1 engine is retained only as an underscore-private implementation
dependency for reconstruction and composed controls.
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

from . import _guard_core as _legacy_core

# Preserve parsing/canonicalization/helper compatibility, but do not re-export
# the historical positive evaluator or its CLI.
for _name in dir(_legacy_core):
    if not _name.startswith("__") and _name not in {"evaluate", "main"}:
        globals()[_name] = getattr(_legacy_core, _name)


def evaluate(intent_raw: dict[str, Any], evidence_raw: dict[str, Any]) -> dict[str, Any]:
    """Evaluate only at verifier-owned current process time."""
    from .current import compile_current

    return compile_current(intent_raw, evidence_raw)


def evaluate_bytes(intent_bytes: bytes, evidence_bytes: bytes) -> dict[str, Any]:
    """Evaluate exact consumed bytes only at verifier-owned current time."""
    from .current import compile_current_bytes

    return compile_current_bytes(intent_bytes, evidence_bytes)


def evaluate_historical_at(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    *,
    historical_at: datetime,
) -> dict[str, Any]:
    """Explicit historical replay; outward result is permanently HOLD."""
    from .current import compile_historical_at

    return compile_historical_at(
        intent_raw,
        evidence_raw,
        historical_at=historical_at,
    )


def main(argv: list[str] | None = None) -> int:
    """Route old and new CLI syntax through the current verifier-clock boundary."""
    from .current import main as current_main

    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"compile", "verify"}:
        return current_main(args)
    return current_main(["compile", *args])


if __name__ == "__main__":
    raise SystemExit(main())
