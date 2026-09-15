#!/usr/bin/env python3
"""CLI and public API for the deterministic, permission-safe paid-proof compiler."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Iterable
from .core import ProofError, strict_json_loads
from .validation import validate_and_normalize
from .compiler import CompiledProof, compile_proof, compile_text, public_json, render_markdown, write_outputs


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="strict JSON commercial-evidence record")
    parser.add_argument("--out-dir", type=Path, help="write internal proof.json, public.json, public-safe proof.md, and receipt.sha256")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="print INTERNAL audit JSON (contains private evidence)")
    output.add_argument("--public-json", action="store_true", help="print fail-closed public JSON only")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        compiled = compile_text(args.input.read_text(encoding="utf-8"))
        if args.out_dir:
            write_outputs(compiled, args.out_dir)
    except (OSError, ProofError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        sys.stdout.write(compiled.proof_json())
    elif args.public_json:
        sys.stdout.write(public_json(compiled))
    elif not args.out_dir:
        sys.stdout.write(compiled.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
