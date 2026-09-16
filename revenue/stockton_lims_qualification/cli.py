from __future__ import annotations

import argparse
import os
import sys

from .engine import compile_at, compile_current, render_markdown, verify_current, verify_historical
from .schema import QualificationError, canonical_bytes, loads_strict
from .source_binding import bind_source_file, read_regular_file

MAX_INPUT_BYTES = 1_000_000


def _read_regular(path: str, maximum: int = MAX_INPUT_BYTES) -> bytes:
    return read_regular_file(path, maximum=maximum, label="input")


def _write_exclusive(path: str, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise QualificationError("output must be a new regular path") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockton-lims-qualify")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("input")
    compile_cmd.add_argument("report")
    compile_cmd.add_argument("markdown")
    compile_cmd.add_argument("--as-of")

    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("input")
    verify_cmd.add_argument("report")
    verify_cmd.add_argument("--current", action="store_true")

    bind_cmd = sub.add_parser("bind-source")
    bind_cmd.add_argument("source_id", choices=["RFP_PDF", "REQUIREMENTS_XLSX"])
    bind_cmd.add_argument("source_path")
    bind_cmd.add_argument("captured_at")
    bind_cmd.add_argument("output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "bind-source":
            row = bind_source_file(args.source_id, args.source_path, args.captured_at)
            _write_exclusive(args.output, canonical_bytes(row) + b"\n")
            return 0

        packet = loads_strict(_read_regular(args.input))
        if args.command == "compile":
            report = compile_at(packet, args.as_of) if args.as_of else compile_current(packet)
            _write_exclusive(args.report, canonical_bytes(report) + b"\n")
            _write_exclusive(args.markdown, render_markdown(report).encode("utf-8"))
            return 0

        report = loads_strict(_read_regular(args.report))
        valid = verify_current(packet, report) if args.current else verify_historical(packet, report)
        return 0 if valid else 1
    except QualificationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
