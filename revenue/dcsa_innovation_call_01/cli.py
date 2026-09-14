"""Command-line interface for the DCSA Innovation Call #01 carrier."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .acceptance import compile_matrix, render_matrix_markdown, verify_matrix
from .concept import render_concept
from .gate import (
    compile_current,
    compile_historical,
    verify_current,
    verify_historical,
    verify_report_shape,
)
from .strict import (
    CustodyError,
    DcsaError,
    ValidationError,
    canonical_json_bytes,
    read_bounded_regular_file,
    strict_json_loads,
    write_exclusive_regular_file,
)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError(f"argument error: {message}")


def _read(path: str) -> bytes:
    return read_bounded_regular_file(path)


def _write_json(path: str, value: Any) -> None:
    write_exclusive_regular_file(path, canonical_json_bytes(value) + b"\n")


def _write_text(path: str, value: str) -> None:
    write_exclusive_regular_file(path, value.encode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="DCSA Innovation Call #01 internal pursuit carrier")
    sub = parser.add_subparsers(dest="command", required=True)

    current = sub.add_parser("compile-current")
    current.add_argument("--candidate", required=True)
    current.add_argument("--source", required=True)
    current.add_argument("--report", required=True)
    current.add_argument("--concept")
    current.add_argument("--acceptance-json")
    current.add_argument("--acceptance-markdown")

    historical = sub.add_parser("compile-historical")
    historical.add_argument("--candidate", required=True)
    historical.add_argument("--source", required=True)
    historical.add_argument("--authority", required=True)
    historical.add_argument("--floor", required=True)
    historical.add_argument("--as-of", required=True)
    historical.add_argument("--report", required=True)

    verify_now = sub.add_parser("verify-current")
    verify_now.add_argument("--candidate", required=True)
    verify_now.add_argument("--source", required=True)
    verify_now.add_argument("--report", required=True)

    verify_old = sub.add_parser("verify-historical")
    verify_old.add_argument("--candidate", required=True)
    verify_old.add_argument("--source", required=True)
    verify_old.add_argument("--authority", required=True)
    verify_old.add_argument("--floor", required=True)
    verify_old.add_argument("--as-of", required=True)
    verify_old.add_argument("--report", required=True)

    concept = sub.add_parser("render-concept")
    concept.add_argument("--candidate", required=True)
    concept.add_argument("--report", required=True)
    concept.add_argument("--output", required=True)

    matrix = sub.add_parser("render-acceptance")
    matrix.add_argument("--json-output", required=True)
    matrix.add_argument("--markdown-output", required=True)
    return parser


def _emit(value: Any, *, stream: Any = None) -> None:
    target = sys.stdout if stream is None else stream
    target.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "compile-current":
            candidate_bytes = _read(args.candidate)
            source_bytes = _read(args.source)
            report = compile_current(candidate_bytes, source_bytes)
            _write_json(args.report, report)
            candidate = strict_json_loads(candidate_bytes)
            if args.concept:
                _write_text(args.concept, render_concept(candidate, report))
            matrix = compile_matrix()
            if args.acceptance_json:
                _write_json(args.acceptance_json, matrix)
            if args.acceptance_markdown:
                _write_text(args.acceptance_markdown, render_matrix_markdown(matrix))
            _emit(
                {
                    "ok": True,
                    "state": report["state"],
                    "mode": report["mode"],
                    "receipt_sha256": report["receipt_sha256"],
                    "external_contact_authorized": False,
                    "external_submission_authorized": False,
                }
            )
            return 0 if report["state"] in {"DIRECT_READY", "TEAMING_REQUIRED"} else 3

        if args.command == "compile-historical":
            report = compile_historical(
                _read(args.candidate),
                _read(args.source),
                _read(args.authority),
                _read(args.floor),
                as_of=args.as_of,
            )
            _write_json(args.report, report)
            _emit(
                {
                    "ok": True,
                    "state": report["state"],
                    "historical_route_projection": report["historical_route_projection"],
                    "mode": report["mode"],
                    "receipt_sha256": report["receipt_sha256"],
                }
            )
            return 0

        if args.command == "verify-current":
            valid = verify_current(_read(args.candidate), _read(args.source), _read(args.report))
            _emit({"ok": valid, "mode": "CURRENT"})
            return 0 if valid else 4

        if args.command == "verify-historical":
            valid = verify_historical(
                _read(args.candidate),
                _read(args.source),
                _read(args.authority),
                _read(args.floor),
                _read(args.report),
                as_of=args.as_of,
            )
            _emit({"ok": valid, "mode": "HISTORICAL_INTEGRITY_ONLY"})
            return 0 if valid else 4

        if args.command == "render-concept":
            candidate = strict_json_loads(_read(args.candidate))
            report = verify_report_shape(strict_json_loads(_read(args.report)))
            _write_text(args.output, render_concept(candidate, report))
            _emit({"ok": True, "output": args.output})
            return 0

        if args.command == "render-acceptance":
            matrix = compile_matrix()
            if not verify_matrix(matrix):
                raise ValidationError("internal acceptance matrix failed verification")
            _write_json(args.json_output, matrix)
            _write_text(args.markdown_output, render_matrix_markdown(matrix))
            _emit({"ok": True, "receipt_sha256": matrix["receipt_sha256"]})
            return 0

        raise ValidationError("unsupported command")
    except (DcsaError, OSError) as exc:
        _emit(
            {
                "ok": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
