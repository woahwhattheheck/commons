#!/usr/bin/env python3
"""Materialize the exact-current receipt_profile executable-prefix repair.

This carrier does not edit the canonical scheduler. It verifies the exact
scheduler and official interpreter blobs, applies one source-local helper and
one call-site replacement, compiles the result, and writes it atomically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

OPERATION = "TITAN-V3-RECEIPT-PROFILE-EXECUTABLE-PREFIX-CLOSURE-20260910-01"
SOURCE_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"

ENGINE_LIMIT_ANCHOR = (
    'max_orders = max(1, int(get(env.configuration, '
    '"maxMarketOrdersPerTurn", 10)))'
)
ENGINE_SLICE_ANCHOR = "queues.append(q[:max_orders])"

HELPER_ANCHOR = "\n\nclass SellScheduler:\n"
HELPER = """\

def _engine_market_prefix(action, config):
    # Match the official raw queue truncation before any order is interpreted.
    market=action.get('market',[]) if isinstance(action,dict) else []
    q=list(market) if isinstance(market,list) else []
    return q[:max(1,int(config.get('maxMarketOrdersPerTurn',10)))]


class SellScheduler:
"""

CALLSITE_PREIMAGE = """\
            orders=base['market'] if t==now else (route[t].get('market',[]) if t<len(route) else [])
            for o in orders:
"""
CALLSITE_REPLACEMENT = """\
            market_action=base if t==now else (route[t] if t<len(route) else parent.PASS)
            orders=_engine_market_prefix(market_action,config)
            for o in orders:
"""


class MaterializationError(RuntimeError):
    """The exact source/engine or output boundary is not safe to transform."""


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_count(text: str, needle: str, count: int, label: str) -> None:
    actual = text.count(needle)
    if actual != count:
        raise MaterializationError(f"{label}: expected {count}, found {actual}")


def materialize_bytes(source_bytes: bytes, engine_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
    source_blob = git_blob_sha(source_bytes)
    engine_blob = git_blob_sha(engine_bytes)
    if source_blob != SOURCE_GIT_BLOB:
        raise MaterializationError(
            f"scheduler blob mismatch: expected {SOURCE_GIT_BLOB}, got {source_blob}"
        )
    if engine_blob != ENGINE_GIT_BLOB:
        raise MaterializationError(
            f"engine blob mismatch: expected {ENGINE_GIT_BLOB}, got {engine_blob}"
        )
    try:
        source = source_bytes.decode("utf-8")
        engine = engine_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterializationError("source and engine must be strict UTF-8") from exc

    _require_exact_count(engine, ENGINE_LIMIT_ANCHOR, 1, "engine prefix-limit anchor")
    _require_exact_count(engine, ENGINE_SLICE_ANCHOR, 1, "engine prefix-slice anchor")
    _require_exact_count(source, HELPER_ANCHOR, 1, "scheduler helper anchor")
    _require_exact_count(source, CALLSITE_PREIMAGE, 1, "receipt_profile market loop")
    _require_exact_count(source, "def _engine_market_prefix(", 0, "preexisting helper")

    candidate = source.replace(HELPER_ANCHOR, HELPER, 1)
    candidate = candidate.replace(CALLSITE_PREIMAGE, CALLSITE_REPLACEMENT, 1)
    _require_exact_count(candidate, "def _engine_market_prefix(", 1, "materialized helper")
    _require_exact_count(candidate, CALLSITE_REPLACEMENT, 1, "materialized call site")
    _require_exact_count(candidate, CALLSITE_PREIMAGE, 0, "retired call site")

    candidate_bytes = candidate.encode("utf-8")
    compile(candidate, "<materialized-scheduler>", "exec")

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "source": {
            "git_blob": SOURCE_GIT_BLOB,
            "bytes": len(source_bytes),
            "sha256": sha256(source_bytes),
        },
        "engine": {
            "git_blob": ENGINE_GIT_BLOB,
            "bytes": len(engine_bytes),
            "sha256": sha256(engine_bytes),
            "prefix_limit_anchor_count": engine.count(ENGINE_LIMIT_ANCHOR),
            "prefix_slice_anchor_count": engine.count(ENGINE_SLICE_ANCHOR),
        },
        "candidate": {
            "git_blob": git_blob_sha(candidate_bytes),
            "bytes": len(candidate_bytes),
            "sha256": sha256(candidate_bytes),
        },
        "patch": {
            "helper_insertions": candidate.count("def _engine_market_prefix("),
            "receipt_profile_callsite_replacements": candidate.count(
                CALLSITE_REPLACEMENT
            ),
            "retired_preimages": candidate.count(CALLSITE_PREIMAGE),
        },
        "claim": "SOURCE_REAL_ACTION_UNMEASURED",
    }
    return candidate_bytes, receipt


def _aliases(left: Path, right: Path) -> bool:
    if left.resolve(strict=False) == right.resolve(strict=False):
        return True
    if left.exists() and right.exists():
        try:
            return os.path.samefile(left, right)
        except OSError:
            return False
    return False


def _validate_input(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise MaterializationError(f"{label} must be a regular non-symlink file")


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise MaterializationError("output must not be a symlink")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def materialize(source: Path, engine: Path, output: Path) -> dict[str, Any]:
    _validate_input(source, "scheduler")
    _validate_input(engine, "engine")
    if _aliases(source, engine):
        raise MaterializationError("scheduler and engine paths alias")
    if _aliases(output, source) or _aliases(output, engine):
        raise MaterializationError("output aliases a bound input")

    source_before = source.read_bytes()
    engine_before = engine.read_bytes()
    candidate, receipt = materialize_bytes(source_before, engine_before)
    _write_atomic(output, candidate)

    if source.read_bytes() != source_before:
        output.unlink(missing_ok=True)
        raise MaterializationError("scheduler changed during materialization")
    if engine.read_bytes() != engine_before:
        output.unlink(missing_ok=True)
        raise MaterializationError("engine changed during materialization")
    if output.read_bytes() != candidate:
        raise MaterializationError("candidate readback mismatch")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scheduler", type=Path)
    parser.add_argument("engine", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    receipt = materialize(args.scheduler, args.engine, args.output)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
