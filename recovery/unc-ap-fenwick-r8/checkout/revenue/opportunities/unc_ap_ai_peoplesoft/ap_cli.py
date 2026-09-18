"""Read-only local AP evidence intake. Exit 0=internal-ready, 3=held, 2=invalid.

No network, submission, accounting write, send, payment or contract operation.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
from typing import Sequence

from source_custody import ContractError, MAX_JSON_BYTES, canonical_bytes, load_strict_json
from unc_ap_ai import compile_bundle
from review_html import render_html


def read_input(path: Path) -> bytes:
    if not hasattr(os, "O_NOFOLLOW"):
        raise ContractError("local intake requires POSIX no-follow support")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            meta = os.fstat(handle.fileno())
            if not stat.S_ISREG(meta.st_mode) or not 0 < meta.st_size <= MAX_JSON_BYTES:
                raise ContractError("input must be a bounded regular file")
            data = handle.read(MAX_JSON_BYTES + 1)
            if len(data) != meta.st_size:
                raise ContractError("input changed during read")
            return data
    except OSError as exc:
        raise ContractError(f"input unavailable: {exc.strerror}") from exc


def write_new(path: Path, data: bytes) -> None:
    # Exclusive creation never truncates an existing report or follows its link.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ContractError(f"output not written: {exc.strerror}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="new report only; existing paths are refused")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args(argv)
    try:
        value = load_strict_json(read_input(args.input))
        required = {"source", "cases", "partners", "extraction_threshold_basis_points"}
        if type(value) is not dict or set(value) != required:
            raise ContractError("input requires exact source, cases, partners and threshold fields")
        report = compile_bundle(value["source"], value["cases"], value["partners"],
                                extraction_threshold_basis_points=value["extraction_threshold_basis_points"])
        payload = (canonical_bytes(report) + b"\n") if args.format == "json" else render_html(report).encode("utf-8")
        if args.output is None:
            sys.stdout.buffer.write(payload)
        else:
            write_new(args.output, payload)
        return 0 if report["state"] == "INTERNAL_WORKSHARE_READY" else 3
    except (ContractError, BrokenPipeError) as exc:
        print(f"AP evidence intake rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
