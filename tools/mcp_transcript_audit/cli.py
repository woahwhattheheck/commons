from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .audit import REQUIRED_PROTOCOL_VERSION, audit_transcript, canonical_json_bytes, verify_receipt


def _read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def _write_exclusive(path: str, data: bytes) -> None:
    target = Path(path)
    parent = target.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError(f"output parent does not exist: {parent}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(target), flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            target.unlink(missing_ok=True)
        finally:
            raise


def _emit(value: dict, output: str | None) -> None:
    payload = canonical_json_bytes(value)
    if output:
        _write_exclusive(output, payload)
    else:
        sys.stdout.buffer.write(payload + b"\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-transcript-audit",
        description="Offline byte-bound audit for captured MCP 2025-11-25 JSON-RPC transcripts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="audit a capture and emit a deterministic receipt")
    audit.add_argument("capture")
    audit.add_argument("--output", "-o")
    audit.add_argument("--protocol-version", default=REQUIRED_PROTOCOL_VERSION)

    verify = sub.add_parser("verify", help="recompute a capture and verify a saved receipt")
    verify.add_argument("capture")
    verify.add_argument("receipt")
    verify.add_argument("--output", "-o")
    verify.add_argument("--protocol-version", default=REQUIRED_PROTOCOL_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source = _read_bytes(args.capture)
        if args.command == "audit":
            result = audit_transcript(source, required_protocol_version=args.protocol_version)
            _emit(result, args.output)
            return 0 if result["status"] == "PASS" else 3
        receipt = _read_bytes(args.receipt)
        result = verify_receipt(source, receipt, required_protocol_version=args.protocol_version)
        _emit(result, args.output)
        return 0 if result["valid"] else 3
    except (OSError, ValueError) as exc:
        print(f"mcp-transcript-audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
