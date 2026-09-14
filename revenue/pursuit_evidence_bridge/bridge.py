"""Bind pursuit-local bytes to the shared bidder evidence vault without caller-minted trust."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from revenue.bidder_qualification_vault import VaultError, canonical_sha256, verify_bundle

BINDINGS_SCHEMA = "pursuit-evidence-bridge/bindings/v1"
RESULT_SCHEMA = "pursuit-evidence-bridge/result/v1"
SHA = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ACTION_KEYS = (
    "buyer_contact", "reference_contact", "proposal_submission", "portal_mutation",
    "signature", "certification_claim", "insurance_adequacy_claim", "solvency_claim",
    "pricing_commitment", "staffing_commitment", "contract_acceptance", "spend",
    "payment_mutation", "award_claim", "revenue_claim",
)


class BridgeError(ValueError):
    """Malformed, unbound, or tampered bridge input."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BridgeError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(raw: bytes, label: str = "input") -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)):
        raise BridgeError(f"{label}: bytes required")
    try:
        value = json.loads(bytes(raw).decode("utf-8", "strict"), object_pairs_hook=_pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(BridgeError(f"{label}: non-finite number")),
                           parse_float=lambda x: (_ for _ in ()).throw(BridgeError(f"{label}: floating-point numbers forbidden")))
    except BridgeError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise BridgeError(f"{label}: invalid JSON/UTF-8") from exc
    if type(value) is not dict:
        raise BridgeError(f"{label}: top level must be object")
    return value


def _plain_json(value: Any, label: str) -> Any:
    """Copy exact JSON builtins, rejecting mutable/type-confusing subclasses."""
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is list:
        return [_plain_json(item, f"{label}[]") for item in value]
    if type(value) is dict:
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise BridgeError(f"{label}: object keys must be strings")
            out[key] = _plain_json(item, f"{label}.{key}")
        return out
    raise BridgeError(f"{label}: plain JSON builtins required")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise BridgeError(f"{label}: object required")
    if set(value) != expected:
        raise BridgeError(f"{label}: keys mismatch missing={sorted(expected-set(value))} extra={sorted(set(value)-expected)}")
    return value


def _str(value: Any, label: str, *, token: bool = False, limit: int = 512) -> str:
    if type(value) is not str or not value or len(value) > limit or any(ord(ch) < 32 for ch in value):
        raise BridgeError(f"{label}: safe non-empty string required")
    if token and not TOKEN.fullmatch(value):
        raise BridgeError(f"{label}: invalid token")
    return value


def _sha(value: Any, label: str) -> str:
    text = _str(value, label, limit=64)
    if not SHA.fullmatch(text):
        raise BridgeError(f"{label}: lowercase sha256 required")
    return text


def _optional_sha(value: Any, label: str) -> str | None:
    return None if value is None else _sha(value, label)


def _ts(value: Any, label: str, _strptime=datetime.strptime) -> str:
    """Normalize a registry timestamp with the parser captured at module construction."""
    text = _str(value, label, limit=20)
    if not TS.fullmatch(text):
        raise BridgeError(f"{label}: RFC3339 UTC second timestamp required")
    try:
        _strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise BridgeError(f"{label}: invalid timestamp") from exc
    return text


def _parse_ts(text: str, _strptime=datetime.strptime, _utc=timezone.utc) -> datetime:
    """Parse a pinned registry deadline using immutable captured runtime primitives."""
    return _strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_utc)


def _make_process_clock(now=datetime.now, utc=timezone.utc):
    """Close over the interpreter clock so module-global rebinding cannot backdate current evaluation."""
    def current_utc() -> datetime:
        return now(utc).replace(microsecond=0)
    return current_utc


def _normalize_binding(raw: dict[str, Any], index: int) -> dict[str, Any]:
    where = f"bindings[{index}]"
    raw = _keys(raw, {
        "binding_id", "opportunity_id", "source_ledger_path", "source_ledger_sha256",
        "submission_manifest_path", "submission_manifest_sha256", "deadline_utc",
        "vault_authority_sha256", "vault_registry_sha256", "vault_query_sha256",
        "static_holds",
    }, where)
    holds = raw["static_holds"]
    if type(holds) is not list:
        raise BridgeError(f"{where}.static_holds: array required")
    clean_holds = [_str(x, f"{where}.static_holds", token=True) for x in holds]
    if len(set(clean_holds)) != len(clean_holds):
        raise BridgeError(f"{where}.static_holds: duplicate hold")
    roots = (
        _optional_sha(raw["vault_authority_sha256"], f"{where}.vault_authority_sha256"),
        _optional_sha(raw["vault_registry_sha256"], f"{where}.vault_registry_sha256"),
        _optional_sha(raw["vault_query_sha256"], f"{where}.vault_query_sha256"),
    )
    if any(x is None for x in roots) and any(x is not None for x in roots):
        raise BridgeError(f"{where}: vault roots must be all pinned or all null")
    return {
        "binding_id": _str(raw["binding_id"], f"{where}.binding_id", token=True),
        "opportunity_id": _str(raw["opportunity_id"], f"{where}.opportunity_id", token=True),
        "source_ledger_path": _str(raw["source_ledger_path"], f"{where}.source_ledger_path", limit=512),
        "source_ledger_sha256": _sha(raw["source_ledger_sha256"], f"{where}.source_ledger_sha256"),
        "submission_manifest_path": _str(raw["submission_manifest_path"], f"{where}.submission_manifest_path", limit=512),
        "submission_manifest_sha256": _sha(raw["submission_manifest_sha256"], f"{where}.submission_manifest_sha256"),
        "deadline_utc": _ts(raw["deadline_utc"], f"{where}.deadline_utc"),
        "vault_authority_sha256": roots[0],
        "vault_registry_sha256": roots[1],
        "vault_query_sha256": roots[2],
        "static_holds": sorted(clean_holds),
    }


def _load_binding_registry() -> tuple[str, dict[str, dict[str, Any]]]:
    raw_bytes = Path(__file__).with_name("bindings.json").read_bytes()
    raw = load_json(raw_bytes, "bindings.json")
    raw = _keys(raw, {"schema", "bindings"}, "bindings.json")
    if raw["schema"] != BINDINGS_SCHEMA:
        raise BridgeError("bindings.json: unsupported schema")
    rows = raw["bindings"]
    if type(rows) is not list or not rows:
        raise BridgeError("bindings.json: at least one binding required")
    normalized = [_normalize_binding(deepcopy(row), i) for i, row in enumerate(rows)]
    ids = [row["binding_id"] for row in normalized]
    if len(set(ids)) != len(ids):
        raise BridgeError("bindings.json: duplicate binding_id")
    return _digest(raw), {row["binding_id"]: row for row in normalized}


def _actions() -> dict[str, bool]:
    return {key: False for key in ACTION_KEYS}


def _normalize_vault(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return _keys(value, {"authority", "registry", "query", "bundle"}, "vault")


def _evaluate_at(binding: dict[str, Any], registry_sha256: str, source_ledger: dict[str, Any],
                 submission_manifest: dict[str, Any], vault: dict[str, Any] | None,
                 now: datetime, _utc=timezone.utc, _parse_deadline=_parse_ts) -> dict[str, Any]:
    """Deterministic lower-level evaluator for tests and historical verification only."""
    if type(source_ledger) is not dict or type(submission_manifest) is not dict:
        raise BridgeError("source_ledger and submission_manifest must be objects")
    source_sha = _digest(source_ledger)
    manifest_sha = _digest(submission_manifest)
    if source_sha != binding["source_ledger_sha256"]:
        raise BridgeError("source_ledger root mismatch")
    if manifest_sha != binding["submission_manifest_sha256"]:
        raise BridgeError("submission_manifest root mismatch")
    if now.tzinfo is None or now.utcoffset() is None:
        raise BridgeError("process clock must be timezone-aware")
    now = now.astimezone(_utc).replace(microsecond=0)
    when = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    reasons = list(binding["static_holds"])
    if now >= _parse_deadline(binding["deadline_utc"]):
        reasons.append("PROPOSAL_DEADLINE_EXPIRED")

    vault_proof: dict[str, Any] | None = None
    configured = binding["vault_authority_sha256"] is not None
    if not configured:
        if vault is not None:
            raise BridgeError("binding has no pinned vault roots; runtime vault bytes cannot self-authorize")
        reasons.append("VAULT_ROOTS_NOT_PINNED")
    elif vault is None:
        reasons.append("VAULT_EVIDENCE_NOT_SUPPLIED")
    else:
        if canonical_sha256(vault["query"]) != binding["vault_query_sha256"]:
            raise BridgeError("vault query root mismatch")
        try:
            vault_proof = verify_bundle(
                vault["authority"], vault["registry"], vault["query"], vault["bundle"],
                expected_authority_sha256=binding["vault_authority_sha256"],
                expected_registry_sha256=binding["vault_registry_sha256"],
                verified_at=now,
            )
        except VaultError as exc:
            raise BridgeError(f"vault verification failed: {exc}") from exc
        if vault_proof.get("verified") is not True or vault_proof.get("current_status") != "EVIDENCE_READY":
            reasons.append("BIDDER_EVIDENCE_HOLD")

    reasons = sorted(set(reasons))
    status = "OPPORTUNITY_EVIDENCE_READY" if not reasons else "HOLD"
    return {
        "schema": RESULT_SCHEMA,
        "binding_id": binding["binding_id"],
        "binding_registry_sha256": registry_sha256,
        "opportunity_id": binding["opportunity_id"],
        "evaluated_at": when,
        "deadline_utc": binding["deadline_utc"],
        "status": status,
        "reason_codes": reasons,
        "source_ledger": {"path": binding["source_ledger_path"], "sha256": source_sha},
        "submission_manifest": {"path": binding["submission_manifest_path"], "sha256": manifest_sha},
        "vault": None if vault_proof is None else {
            "verified": True,
            "current_status": vault_proof["current_status"],
            "current_evaluated_at": vault_proof["current_evaluated_at"],
            "current_result_sha256": vault_proof["current_result_sha256"],
        },
        "authority": _actions(),
        "external_submission_authorized": False,
        "semantic_boundary": (
            "OPPORTUNITY_EVIDENCE_READY means only that repo-pinned opportunity bytes and the "
            "repo-pinned bidder-evidence query are current and satisfied. It never authorizes contact, "
            "submission, signature, pricing, contract acceptance, spend, award, payment, or revenue claims."
        ),
    }


def _make_compile_bridge(clock):
    """Construct the public current evaluator around a captured, non-caller clock."""
    def compile_bridge(binding_id: str, source_ledger: dict[str, Any], submission_manifest: dict[str, Any],
                       vault: dict[str, Any] | None = None) -> dict[str, Any]:
        """Evaluate one repo-pinned pursuit binding using only captured process UTC."""
        registry_sha, bindings = _load_binding_registry()
        clean_binding_id = _str(binding_id, "binding_id", token=True)
        if clean_binding_id not in bindings:
            raise BridgeError(f"unknown binding_id: {clean_binding_id}")
        source = _plain_json(source_ledger, "source_ledger")
        manifest = _plain_json(submission_manifest, "submission_manifest")
        frozen_vault = None if vault is None else _plain_json(vault, "vault")
        return _evaluate_at(bindings[clean_binding_id], registry_sha, source, manifest,
                            _normalize_vault(frozen_vault), clock())
    return compile_bridge


# Capture the interpreter's datetime.now + UTC objects at module construction.  Current
# callers cannot inject a clock through compile_bridge's signature, and rebinding
# bridge.datetime / bridge.timezone later cannot change the captured clock.
compile_bridge = _make_compile_bridge(_make_process_clock())


def _parse_envelope(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    value = _keys(value, {"source_ledger", "submission_manifest", "vault"}, "envelope")
    return value["source_ledger"], value["submission_manifest"], _normalize_vault(value["vault"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repo-pinned pursuit evidence bridge")
    parser.add_argument("binding_id")
    args = parser.parse_args(argv)
    try:
        source, manifest, vault = _parse_envelope(load_json(sys.stdin.buffer.read(), "stdin"))
        result = compile_bridge(args.binding_id, source, manifest, vault)
        sys.stdout.buffer.write(_canonical(result))
        return 0 if result["status"] == "OPPORTUNITY_EVIDENCE_READY" else 2
    except BridgeError as exc:
        sys.stderr.write(f"HOLD: {exc}\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
