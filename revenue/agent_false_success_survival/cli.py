"""CLI for compiling and verifying false-success survival proofs."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .proof import MAX_INPUT_BYTES, ProofError, canonical_bytes, compile_proof, loads_strict, verify_proof


def _read_regular(path: str, *, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    p = Path(path)
    try:
        before = os.lstat(p)
    except OSError as exc:
        raise ProofError(f"cannot stat input file: {path}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ProofError(f"input must be a regular non-symlink file: {path}")
    if before.st_size > max_bytes:
        raise ProofError(f"input exceeds {max_bytes} bytes: {path}")
    try:
        with open(p, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ProofError(f"input changed before open: {path}")
            data = handle.read(max_bytes + 1)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise ProofError(f"cannot read input file: {path}") from exc
    if len(data) > max_bytes:
        raise ProofError(f"input exceeds {max_bytes} bytes: {path}")
    if (opened.st_dev, opened.st_ino, opened.st_size) != (after.st_dev, after.st_ino, after.st_size):
        raise ProofError(f"input changed while reading: {path}")
    return data


def _write_exclusive(path: str, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ProofError(f"refusing to overwrite or follow output: {path}") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _emit(value: Any) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile/verify an agent false-success survival proof")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile", help="compile a capture bundle into a deterministic proof")
    compile_p.add_argument("bundle")
    compile_p.add_argument("--out", required=True)
    verify_p = sub.add_parser("verify", help="recompute a proof from the original capture bundle")
    verify_p.add_argument("bundle")
    verify_p.add_argument("proof")
    demo_p = sub.add_parser("demo", help="compile and verify a fixture without publishing a file")
    demo_p.add_argument("bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bundle = loads_strict(_read_regular(args.bundle))
        if args.command == "compile":
            proof = compile_proof(bundle)
            _write_exclusive(args.out, canonical_bytes(proof) + b"\n")
            _emit({"ok": True, "decision": proof["proof"]["decision"], "proof_sha256": proof["proof_sha256"], "output": args.out})
            return 0
        if args.command == "verify":
            proof = loads_strict(_read_regular(args.proof))
            ok = verify_proof(bundle, proof)
            _emit({"ok": ok, "decision": proof.get("proof", {}).get("decision") if isinstance(proof, dict) else None})
            return 0 if ok else 1
        proof = compile_proof(bundle)
        ok = verify_proof(bundle, proof)
        _emit({"ok": ok, "decision": proof["proof"]["decision"], "proof_sha256": proof["proof_sha256"]})
        return 0 if ok else 1
    except ProofError as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
