#!/usr/bin/env python3
"""Verify every retained byte and self-sealed report in this packet."""

from __future__ import annotations

import hashlib
from pathlib import Path

import terminal_outcome_selector as selector

ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    receipt = selector.strict_loads((ROOT / "RECEIPT.json").read_text(encoding="utf-8"))
    expected = receipt.pop("receipt_sha256")
    actual = selector.sha256_hex(selector.canonical_bytes(receipt))
    if actual != expected:
        raise SystemExit(f"FAIL receipt seal: {actual} != {expected}")
    for entry in receipt["files"]:
        path = ROOT / entry["path"]
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"FAIL missing/nonregular: {entry['path']}")
        if path.stat().st_size != entry["bytes"]:
            raise SystemExit(f"FAIL size: {entry['path']}")
        if digest(path) != entry["sha256"]:
            raise SystemExit(f"FAIL sha256: {entry['path']}")
    report = selector.strict_loads((ROOT / "WITNESS-REPORT.json").read_text(encoding="utf-8"))
    if not selector.verify_report_seal(report):
        raise SystemExit("FAIL witness report seal")
    print(
        f"PASS receipt={expected} files={len(receipt['files'])} "
        f"selected={report['selected_plan_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
