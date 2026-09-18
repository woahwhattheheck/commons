"""Offline CLI for deterministic TPRM assessment and verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from .qualification import compile_qualification, verify_receipt
    from .tprm import (
        compile_assessment,
        compile_portfolio,
        verify_assessment_packet,
        verify_portfolio_packet,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from revenue.nm_ocs_tprm.qualification import compile_qualification, verify_receipt
    from revenue.nm_ocs_tprm.tprm import (
        compile_assessment,
        compile_portfolio,
        verify_assessment_packet,
        verify_portfolio_packet,
    )


def _strict_load(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be an ordinary non-symlink file")
    if path.stat().st_size > 4_000_000:
        raise ValueError("input too lare")

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in values:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def bad_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=bad_constant,
    )


def _write(path: Path, value: Any) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite output")
    encoded = (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    path.write_bytes(encoded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("assessment", "portfolio", "qualification"):
        p = sub.add_parser(name)
        p.add_argument("input")
        p.add_argument("output")

    for name in ("verify-assessment", "verify-portfolio", "verify-qualification"):
        p = sub.add_parser(name)
        p.add_argument("input")

    args = parser.parse_args(argv)
    data = _strict_load(Path(args.input))

    if args.cmd == "assessment":
        _write(Path(args.output), compile_assessment(data))
    elif args.cmd == "portfolio":
        _write(Path(args.output), compile_portfolio(data))
    elif args.cmd == "qualification":
        _write(Path(args.output), compile_qualification(data))
    elif args.cmd == "verify-assessment":
        return 0 if verify_assessment_packet(data) else 2
    elif args.cmd == "verify-portfolio":
        return 0 if verify_portfolio_packet(data) else 2
    elif args.cmd == "verify-qualification":
        return 0 if verify_receipt(data) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
