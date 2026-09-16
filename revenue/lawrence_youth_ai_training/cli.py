from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .gate import (
    COLLABORATIVE_READY,
    HOLD,
    NO_BID,
    PRIME_READY,
    QualificationInputError,
    evaluate,
    verify,
)


def _read_json(path: str, name: str) -> Any:
    p = Path(path)
    if p.is_symlink():
        raise QualificationInputError(f"{name} must not be a symlink")
    raw = p.read_bytes()
    if len(raw) > 1_048_576:
        raise QualificationInputError(f"{name} exceeds 1 MiB")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QualificationInputError(f"{name} is malformed JSON") from exc


def _emit(value: Any) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lawrence-youth-ai-qualification",
        description="Evaluate source-bound internal bid-readiness evidence without submitting or contacting the buyer.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ev = sub.add_parser("evaluate")
    ev.add_argument("snapshot")
    ev.add_argument("--evaluated-at", required=True)
    ev.add_argument("--expected-rfp-sha256", required=True)

    vr = sub.add_parser("verify")
    vr.add_argument("receipt")
    vr.add_argument("snapshot")
    vr.add_argument("--verified-at", required=True)
    vr.add_argument("--expected-rfp-sha256", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            snapshot = _read_json(args.snapshot, "snapshot")
            result = evaluate(
                snapshot,
                evaluated_at=args.evaluated_at,
                expected_rfp_sha256=args.expected_rfp_sha256,
            )
            _emit(result)
            decision = result["receipt"]["decision"]
            if decision in {PRIME_READY, COLLABORATIVE_READY}:
                return 0
            if decision == HOLD:
                return 3
            if decision == NO_BID:
                return 4
            return 2

        receipt = _read_json(args.receipt, "receipt")
        snapshot = _read_json(args.snapshot, "snapshot")
        ok = verify(
            receipt,
            snapshot=snapshot,
            expected_rfp_sha256=args.expected_rfp_sha256,
            verified_at=args.verified_at,
        )
        _emit({"verified": ok})
        return 0 if ok else 3
    except (QualificationInputError, OSError) as exc:
        _emit({"error": str(exc), "verified": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
