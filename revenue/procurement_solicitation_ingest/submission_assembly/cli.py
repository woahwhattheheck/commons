"""CLI for source-bound procurement submission assembly."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import compile_manifest, verify
from .custody import artifact_loader_from_root, _ensure_real_dir, _load_input_file, _read_regular_bounded, _write_exclusive
from .schema import AssemblyError, MAX_JSON_BYTES

def _command_compile(args) -> int:
    raw = _load_input_file(Path(args.input))
    loader = artifact_loader_from_root(Path(args.artifact_root))
    manifest, checklist, receipt = compile_manifest(raw, loader)
    out = Path(args.out_dir)
    _ensure_real_dir(out)
    _write_exclusive(out / "assembly.json", manifest)
    _write_exclusive(out / "assembly.md", checklist)
    _write_exclusive(out / "receipt.json", receipt)
    parsed = json.loads(manifest)
    print(parsed["status"])
    return 0


def _command_verify(args) -> int:
    raw = _load_input_file(Path(args.input))
    loader = artifact_loader_from_root(Path(args.artifact_root))
    manifest = _load_input_file(Path(args.manifest))
    checklist = _read_regular_bounded(Path(args.checklist), MAX_JSON_BYTES)
    receipt = _load_input_file(Path(args.receipt))
    ok = verify(raw, manifest, checklist, receipt, loader)
    print("VALID" if ok else "INVALID")
    return 0 if ok else 2


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("--input", required=True)
    compile_cmd.add_argument("--artifact-root", required=True)
    compile_cmd.add_argument("--out-dir", required=True)
    compile_cmd.set_defaults(func=_command_compile)
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--input", required=True)
    verify_cmd.add_argument("--artifact-root", required=True)
    verify_cmd.add_argument("--manifest", required=True)
    verify_cmd.add_argument("--checklist", required=True)
    verify_cmd.add_argument("--receipt", required=True)
    verify_cmd.set_defaults(func=_command_verify)
    return parser


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except AssemblyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
