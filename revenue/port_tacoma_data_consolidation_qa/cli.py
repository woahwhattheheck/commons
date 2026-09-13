"""Provider-free CLI for evaluating synthetic consolidation evidence receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from .core import (
        ConsolidationEvidenceError,
        canonical_json,
        evaluate,
        load_strict_json,
        verify_receipt,
    )
except ImportError:
    from core import (
        ConsolidationEvidenceError,
        canonical_json,
        evaluate,
        load_strict_json,
        verify_receipt,
    )


def _read_json(path: Path) -> Any:
    return load_strict_json(path.read_text(encoding="utf-8"))


def _emit(value: Any, output: Path | None) -> None:
    payload = canonical_json(value) + b"\n"
    if output is None:
        sys.stdout.write(payload.decode("utf-8"))
        return
    output.write_bytes(payload)


def _error(code: str, detail: str) -> int:
    sys.stderr.write(json.dumps({"error": code, "detail": detail}, sort_keys=True) + "\n")
    return 4


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="port-tacoma-data-consolidation-qa")
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="evaluate one evidence bundle")
    evaluate_parser.add_argument("input", type=Path)
    evaluate_parser.add_argument("--output", type=Path)

    verify_parser = sub.add_parser("verify", help="verify one content-addressed receipt")
    verify_parser.add_argument("receipt", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            result = evaluate(_read_json(args.input))
            _emit(result.receipt, args.output)
            return 0 if result.receipt["status"] == "PASS" else 2
        receipt = _read_json(args.receipt)
        ok = verify_receipt(receipt)
        if ok:
            _emit({"receipt_sha256": receipt["receipt_sha256"], "verified": True}, None)
            return 0
        _emit({"verified": False}, None)
        return 3
    except (ConsolidationEvidenceError, OSError, UnicodeError) as exc:
        return _error(type(exc).__name__, str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
