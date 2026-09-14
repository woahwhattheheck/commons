"""Hardened public facade for the bidder qualification evidence vault.

The shipped v1 engine is preserved byte-for-byte in ``_core_v1``.  This facade
adds trust anchors that cannot be supplied by an opportunity query itself:
subject identity and coherent snapshot chronology.  It does not add any action
authority.
"""
from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from . import _core_v1 as _core

AUTHORITY_SCHEMA = _core.AUTHORITY_SCHEMA
REGISTRY_SCHEMA = _core.REGISTRY_SCHEMA
QUERY_SCHEMA = _core.QUERY_SCHEMA
RESULT_SCHEMA = _core.RESULT_SCHEMA
RECEIPT_SCHEMA = _core.RECEIPT_SCHEMA
BUNDLE_SCHEMA = _core.BUNDLE_SCHEMA
KINDS = _core.KINDS
STATES = _core.STATES
RELEASE_RANK = _core.RELEASE_RANK
ACTION_AUTHORITY_KEYS = _core.ACTION_AUTHORITY_KEYS
VaultError = _core.VaultError
load_json = _core.load_json
canonical = _core.canonical
canonical_sha256 = _core.canonical_sha256
normalize_authority = _core.normalize_authority
normalize_registry = _core.normalize_registry
normalize_query = _core.normalize_query
roots = _core.roots


def _trusted_subject(value: Any) -> str:
    return _core._str(value, "expected_subject_id", token=True)


def _hardened_bind(
    authority_value: dict[str, Any],
    registry_value: dict[str, Any],
    query_value: dict[str, Any],
    *,
    expected_subject_id: str,
) -> str:
    """Validate host-owned subject identity and snapshot chronology."""
    expected = _trusted_subject(expected_subject_id)
    authority = normalize_authority(deepcopy(authority_value))
    registry = normalize_registry(deepcopy(registry_value))
    query = normalize_query(deepcopy(query_value))

    if query["subject_id"] != expected:
        raise VaultError("query.subject_id: trusted subject mismatch")

    authority_issued = _core._parse_ts(authority["issued_at"])
    registry_generated = _core._parse_ts(registry["generated_at"])
    if registry_generated < authority_issued:
        raise VaultError("registry.generated_at: predates bound authority generation")

    for item in registry["items"]:
        if _core._parse_ts(item["observed_at"]) > registry_generated:
            raise VaultError(
                f"registry item {item['evidence_id']}: observation postdates registry generation"
            )
    return expected


def compile_vault(
    authority_value: dict[str, Any],
    registry_value: dict[str, Any],
    query_value: dict[str, Any],
    *,
    expected_subject_id: str,
    expected_authority_sha256: str,
    expected_registry_sha256: str,
    evaluated_at: datetime | str,
) -> dict[str, Any]:
    _hardened_bind(
        authority_value,
        registry_value,
        query_value,
        expected_subject_id=expected_subject_id,
    )
    return _core.compile_vault(
        authority_value,
        registry_value,
        query_value,
        expected_authority_sha256=expected_authority_sha256,
        expected_registry_sha256=expected_registry_sha256,
        evaluated_at=evaluated_at,
    )


def verify_bundle(
    authority_value: dict[str, Any],
    registry_value: dict[str, Any],
    query_value: dict[str, Any],
    bundle_value: dict[str, Any],
    *,
    expected_subject_id: str,
    expected_authority_sha256: str,
    expected_registry_sha256: str,
    verified_at: datetime | str,
) -> dict[str, Any]:
    _hardened_bind(
        authority_value,
        registry_value,
        query_value,
        expected_subject_id=expected_subject_id,
    )
    return _core.verify_bundle(
        authority_value,
        registry_value,
        query_value,
        bundle_value,
        expected_authority_sha256=expected_authority_sha256,
        expected_registry_sha256=expected_registry_sha256,
        verified_at=verified_at,
    )


def _required(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        raise VaultError(
            f"{where}: keys mismatch missing={sorted(keys-set(obj))} extra={sorted(set(obj)-keys)}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-only bidder qualification vault")
    parser.add_argument("command", choices=("roots", "compile", "verify"))
    args = parser.parse_args(argv)
    try:
        env = load_json(sys.stdin.buffer.read(), "stdin")
        if args.command == "roots":
            _required(env, {"authority", "registry", "subject_id"}, "roots envelope")
            subject = _trusted_subject(env["subject_id"])
            a_sha, r_sha = roots(env["authority"], env["registry"])
            out = {
                "authority_sha256": a_sha,
                "expected_subject_id": subject,
                "registry_sha256": r_sha,
                "warning": (
                    "SETUP_ONLY: supplied bytes do not establish trust; production consumers "
                    "must independently retain this subject ID together with both expected roots"
                ),
            }
            sys.stdout.buffer.write(canonical(out))
            return 0

        now = datetime.now(timezone.utc).replace(microsecond=0)
        if args.command == "compile":
            _required(
                env,
                {
                    "authority",
                    "registry",
                    "query",
                    "expected_subject_id",
                    "expected_authority_sha256",
                    "expected_registry_sha256",
                },
                "compile envelope",
            )
            bundle = compile_vault(
                env["authority"],
                env["registry"],
                env["query"],
                expected_subject_id=env["expected_subject_id"],
                expected_authority_sha256=env["expected_authority_sha256"],
                expected_registry_sha256=env["expected_registry_sha256"],
                evaluated_at=now,
            )
            sys.stdout.buffer.write(canonical(bundle))
            return 0 if bundle["result"]["status"] == "EVIDENCE_READY" else 2

        _required(
            env,
            {
                "authority",
                "registry",
                "query",
                "expected_subject_id",
                "expected_authority_sha256",
                "expected_registry_sha256",
                "bundle",
            },
            "verify envelope",
        )
        proof = verify_bundle(
            env["authority"],
            env["registry"],
            env["query"],
            env["bundle"],
            expected_subject_id=env["expected_subject_id"],
            expected_authority_sha256=env["expected_authority_sha256"],
            expected_registry_sha256=env["expected_registry_sha256"],
            verified_at=now,
        )
        sys.stdout.buffer.write(canonical(proof))
        return 0 if proof["current_status"] == "EVIDENCE_READY" else 2
    except VaultError as exc:
        sys.stderr.write(f"HOLD: {exc}\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
