#!/usr/bin/env python3
"""Public fail-closed qualification boundary for Jersey procurement DN827803."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import _qualify_engine as _engine

# Preserve the implementation surface for existing imports while replacing the
# authority-bearing entry points below. Python is not a sandbox; `_qualify_engine`
# is intentionally private and exists for implementation/tests, not production
# trust-anchor injection.
for _name in dir(_engine):
    if not _name.startswith("__") and _name not in {
        "evaluate",
        "evaluate_historical",
        "main",
    }:
        globals()[_name] = getattr(_engine, _name)

TRUSTED_ROOT_PATH = Path(__file__).with_name("trusted_root.json")


def load_retained_root() -> dict[str, Any]:
    """Load the repository-retained trust anchor; public callers cannot replace it."""
    return _engine.load_json_bytes(TRUSTED_ROOT_PATH.read_bytes(), "trusted_root")


def evaluate(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    trusted_as_of: datetime,
    tender_pack_bytes: bytes | None = None,
    extraction_raw: bytes | None = None,
    evidence_raw: bytes | None = None,
):
    return _engine.evaluate(
        manifest,
        source,
        source_raw,
        load_retained_root(),
        trusted_as_of=trusted_as_of,
        tender_pack_bytes=tender_pack_bytes,
        extraction_raw=extraction_raw,
        evidence_raw=evidence_raw,
    )


def evaluate_historical(
    manifest: dict[str, Any],
    source: dict[str, Any],
    source_raw: bytes,
    *,
    replay_as_of: datetime,
    tender_pack_bytes: bytes | None = None,
    extraction_raw: bytes | None = None,
    evidence_raw: bytes | None = None,
):
    return _engine.evaluate_historical(
        manifest,
        source,
        source_raw,
        load_retained_root(),
        replay_as_of=replay_as_of,
        tender_pack_bytes=tender_pack_bytes,
        extraction_raw=extraction_raw,
        evidence_raw=evidence_raw,
    )


def main(argv: list[str] | None = None) -> int:
    # The private engine CLI also loads trusted_root.json from its own directory
    # and exposes no root override, so delegating parsing preserves the same
    # retained boundary for command-line use.
    return _engine.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
