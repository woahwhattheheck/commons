#!/usr/bin/env python3
"""CLI for the revenue-lane current-state compiler."""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import sys

try:
    from .core import ContractError, canonical_bytes, compile_from_json, verify_artifact
except ImportError:
    from core import ContractError, canonical_bytes, compile_from_json, verify_artifact


def _read(path: str) -> bytes:
    return Path(path).read_bytes()


def _body(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="strict")


def _write_exclusive(path: str, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.write(b"\n")
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--events", required=True)
    compile_p.add_argument("--body", required=True)
    compile_p.add_argument("--evaluation-time", required=True)
    compile_p.add_argument("--output", required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--events", required=True)
    verify_p.add_argument("--body", required=True)
    verify_p.add_argument("--evaluation-time", required=True)
    verify_p.add_argument("--artifact", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            result = compile_from_json(
                _read(args.events),
                body_text=_body(args.body),
                evaluation_time=args.evaluation_time,
            )
            _write_exclusive(args.output, canonical_bytes(result))
            return 0
        verify_artifact(
            _read(args.events),
            _read(args.artifact),
            body_text=_body(args.body),
            evaluation_time=args.evaluation_time,
        )
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
