"""CLI for deterministic pursuit portfolio allocation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import PortfolioError, load_regular_json, verify_compiled, write_compiled


def _regular_bytes(path: Path, label: str) -> bytes:
    # Reuse strict file semantics by parsing JSON where applicable at call sites.
    if not path.is_file() or path.is_symlink():
        raise PortfolioError(f"{label}: regular non-symlink file required")
    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise PortfolioError(f"{label}: file too large")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pursuit-portfolio")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile", help="compile a current owner-review portfolio")
    compile_p.add_argument("input")
    compile_p.add_argument("output_dir")
    verify_p = sub.add_parser("verify", help="deterministically verify a compiled directory")
    verify_p.add_argument("output_dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            source = load_regular_json(args.input)
            compiled = write_compiled(source, args.output_dir)
            print(json.dumps({
                "output_dir": args.output_dir,
                "receipt_sha256": compiled.receipt["receipt_sha256"],
                "selected_opportunity_ids": compiled.result["selected_opportunity_ids"],
                "selected_priority_units": compiled.result["selected_priority_units"],
            }, sort_keys=True))
            return 0
        root = Path(args.output_dir)
        if not root.is_dir() or root.is_symlink():
            raise PortfolioError("verify: ordinary directory required")
        result = _regular_bytes(root / "portfolio.json", "portfolio.json")
        markdown = _regular_bytes(root / "portfolio.md", "portfolio.md")
        receipt = _regular_bytes(root / "receipt.json", "receipt.json")
        verified = verify_compiled(result, markdown, receipt)
        print(json.dumps(verified, sort_keys=True))
        return 0
    except PortfolioError as exc:
        parser.exit(2, f"error: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
