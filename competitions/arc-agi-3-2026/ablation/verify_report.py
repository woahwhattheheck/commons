"""Offline verifier for ARC3 SAGE ablation report receipts."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from harness import verify_report


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_report.py REPORT.json", file=sys.stderr)
        return 2
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ok = isinstance(raw, dict) and verify_report(raw)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
