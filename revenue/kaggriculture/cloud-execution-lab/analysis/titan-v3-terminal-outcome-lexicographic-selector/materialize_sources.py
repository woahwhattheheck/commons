#!/usr/bin/env python3
"""Materialize exact source bytes from temporary gzip/base64 carriers."""

from __future__ import annotations

import base64
import gzip
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {
    "terminal_outcome_selector.py": (22786, "e5697a61b977bd08fae59eaa5997514599fc2d14c7c1947ffee63fcd225ccade"),
    "test_terminal_outcome_selector.py": (20518, "d61ff11c3306df179ae94c59ae8ddfa662776149cbcfd7ebd6ba5d20e93a78b1"),
    "fuzz_terminal_outcome_selector.py": (5858, "3d45554d2024cf39eae2be471e0d8b0599c62cec8946a4c53639bf441a3005a7"),
}


def main() -> int:
    for name, (expected_size, expected_sha) in FILES.items():
        carrier = ROOT / f"{name}.gz.b64"
        target = ROOT / name
        if target.exists() or target.is_symlink():
            raise SystemExit(f"refusing existing target: {target}")
        compact = "".join(carrier.read_text(encoding="ascii").split())
        try:
            compressed = base64.b64decode(compact, validate=True)
            data = gzip.decompress(compressed)
        except Exception as exc:
            raise SystemExit(f"invalid carrier {carrier}: {exc}") from exc
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != expected_size or actual_sha != expected_sha:
            raise SystemExit(
                f"payload mismatch {name}: bytes={len(data)} sha256={actual_sha}"
            )
        temporary = target.with_name(f".{target.name}.materializing")
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"MATERIALIZED {name} bytes={expected_size} sha256={expected_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
