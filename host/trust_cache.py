#!/usr/bin/env python3
"""Cache passed checks by artifact hash and count redundant rerun attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "trust_cache" / "receipts.jsonl"
SCHEMA_VERSION = "commons-trust-cache/v1"
RECEIPT_FIELDS = {
    "artifact_sha256",
    "check_id",
    "result",
    "recorded_at",
    "evidence",
}
RESULTS = {"PASS", "FAIL", "WASTE"}
STATES = {"UNVERIFIED", "TRUSTED", "STALE"}


class TrustCacheError(ValueError):
    """The artifact canary or append-only receipt ledger is invalid."""


def now_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise TrustCacheError(f"artifact missing: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise TrustCacheError(f"artifact hash unreadable: {path}: {error}") from error
    return digest.hexdigest()


def _validate_receipt(row: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != RECEIPT_FIELDS:
        raise TrustCacheError(f"ledger line {line_number} has wrong fields")
    if not isinstance(row["artifact_sha256"], str) or len(row["artifact_sha256"]) != 64:
        raise TrustCacheError(f"ledger line {line_number} has invalid artifact_sha256")
    if not isinstance(row["check_id"], str) or not row["check_id"].strip():
        raise TrustCacheError(f"ledger line {line_number} has invalid check_id")
    if row["result"] not in RESULTS:
        raise TrustCacheError(f"ledger line {line_number} has invalid result")
    evidence = row["evidence"]
    if not isinstance(evidence, dict) or evidence.get("schema_version") != SCHEMA_VERSION:
        raise TrustCacheError(f"ledger line {line_number} has wrong schema version")
    return row


def read_receipts(ledger: Path) -> list[dict[str, Any]]:
    if not ledger.exists():
        return []
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise TrustCacheError(f"ledger unreadable: {ledger}: {error}") from error
    receipts = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise TrustCacheError(f"ledger line {number} is not JSON") from error
        receipts.append(_validate_receipt(row, number))
    return receipts


def canary(artifact: Path, ledger: Path) -> tuple[str, list[dict[str, Any]]]:
    """Cheap always-on boundary: existence, readable hash, and ledger schema."""
    digest = sha256_file(artifact)
    return digest, read_receipts(ledger)


def classify(digest: str, check_id: str, receipts: Iterable[dict[str, Any]]) -> str:
    rows = [row for row in receipts if row["check_id"] == check_id]
    if any(row["artifact_sha256"] == digest and row["result"] == "PASS" for row in rows):
        return "TRUSTED"
    passed_other_bytes = any(row["result"] == "PASS" for row in rows)
    return "STALE" if passed_other_bytes else "UNVERIFIED"


def append_receipt(
    ledger: Path,
    artifact_sha256: str,
    check_id: str,
    result: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "artifact_sha256": artifact_sha256,
        "check_id": check_id,
        "result": result,
        "recorded_at": now_ts(),
        "evidence": {"schema_version": SCHEMA_VERSION, **evidence},
    }
    _validate_receipt(row, 1)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(str(ledger), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        written = os.write(fd, payload)
        if written != len(payload):
            raise TrustCacheError("short append to receipt ledger")
        os.fsync(fd)
    finally:
        os.close(fd)
    return row


def status(artifact: Path, check_id: str, ledger: Path) -> dict[str, Any]:
    digest, receipts = canary(artifact, ledger)
    state = classify(digest, check_id, receipts)
    return {
        "artifact": str(artifact),
        "artifact_sha256": digest,
        "check_id": check_id,
        "state": state,
        "waste_count": sum(
            row["result"] == "WASTE"
            and row["artifact_sha256"] == digest
            and row["check_id"] == check_id
            for row in receipts
        ),
    }


def run_check(
    artifact: Path,
    check_id: str,
    command: list[str],
    ledger: Path,
) -> tuple[dict[str, Any], int]:
    if not command:
        raise TrustCacheError("run requires a command after --")
    snapshot = status(artifact, check_id, ledger)
    if snapshot["state"] == "TRUSTED":
        append_receipt(
            ledger,
            snapshot["artifact_sha256"],
            check_id,
            "WASTE",
            {
                "event": "ATTEMPTED_RERUN",
                "executed": False,
                "command": command,
            },
        )
        snapshot.update({"event": "WASTE", "executed": False})
        return snapshot, 0

    completed = subprocess.run(command, capture_output=True, check=False)
    result = "PASS" if completed.returncode == 0 else "FAIL"
    append_receipt(
        ledger,
        snapshot["artifact_sha256"],
        check_id,
        result,
        {
            "event": "CHECK_RUN",
            "executed": True,
            "command": command,
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        },
    )
    snapshot.update(
        {
            "event": result,
            "executed": True,
            "returncode": completed.returncode,
        }
    )
    return snapshot, completed.returncode


def _command_tail(values: list[str]) -> list[str]:
    return values[1:] if values[:1] == ["--"] else values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER,
        help=f"append-only JSONL ledger (default: {DEFAULT_LEDGER})",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    status_parser = commands.add_parser("status")
    status_parser.add_argument("artifact", type=Path)
    status_parser.add_argument("check_id")
    run_parser = commands.add_parser("run")
    run_parser.add_argument("artifact", type=Path)
    run_parser.add_argument("check_id")
    run_parser.add_argument("check_command", nargs=argparse.REMAINDER)
    commands.add_parser("waste-count")
    args = parser.parse_args()

    try:
        if args.command == "status":
            output = status(args.artifact, args.check_id, args.ledger)
            code = 0
        elif args.command == "run":
            output, code = run_check(
                args.artifact,
                args.check_id,
                _command_tail(args.check_command),
                args.ledger,
            )
        else:
            receipts = read_receipts(args.ledger)
            output = {
                "event": "WASTE_COUNT",
                "waste_count": sum(row["result"] == "WASTE" for row in receipts),
            }
            code = 0
        print(json.dumps(output, sort_keys=True))
        return code
    except (OSError, TrustCacheError) as error:
        print(f"TRUST_CACHE_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
