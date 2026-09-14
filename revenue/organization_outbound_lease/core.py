from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol

from .strict import parse_json_strict

READY_STATE = "READY_FOR_SINGLE_WRITER_REVIEW"
LEASE_SCHEMA = "commons.organization-outbound-lease/v1"
ATTESTATION_SCHEMA = "commons.organization-pressure-attestation/v1"
OUTCOME_SCHEMA = "commons.organization-outbound-outcome/v1"
TERMINAL_STATES = frozenset({"SENT", "OUTCOME_UNKNOWN", "REJECTED", "HELD_AUTHORITY", "UNSENT_RELEASED"})
BLOCKING_TERMINALS = frozenset({"SENT", "OUTCOME_UNKNOWN", "REJECTED", "HELD_AUTHORITY"})
MAX_PREFLIGHT_AGE_SECONDS = 300
MAX_OUTCOME_AGE_SECONDS = 600
MAX_FUTURE_SKEW_SECONDS = 5
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


class LeaseStore(Protocol):
    def get_active(self, org_fingerprint: str) -> tuple[bytes, str] | None: ...
    def get_outcome(self, org_fingerprint: str, lease_id: str) -> tuple[bytes, str] | None: ...
    def create_active(self, org_fingerprint: str, content: bytes) -> str: ...
    def create_outcome(self, org_fingerprint: str, lease_id: str, content: bytes) -> str: ...
    def delete_active(self, org_fingerprint: str, expected_generation: str) -> None: ...


@dataclass(frozen=True)
class AcquireResult:
    state: str
    lease: dict[str, Any]
    active_generation: str | None
    replay: bool


@dataclass(frozen=True)
class FinalizeResult:
    state: str
    outcome: dict[str, Any]
    outcome_generation: str
    active_released: bool
    replay: bool


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_secret(key: bytes, label: str) -> bytes:
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ValueError(f"{label} must be at least 32 bytes")
    return bytes(key)


def fingerprint_organization(canonical_identity: bytes, key: bytes) -> str:
    key = _require_secret(key, "organization fingerprint key")
    if not isinstance(canonical_identity, (bytes, bytearray)):
        raise TypeError("canonical organization identity must be bytes")
    raw = bytes(canonical_identity)
    if not (1 <= len(raw) <= 4096):
        raise ValueError("canonical organization identity must be 1..4096 bytes")
    return hmac.new(key, b"org-v1\x00" + raw, hashlib.sha256).hexdigest()


def _utc(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{label} must be canonical UTC seconds")
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label} must be canonical UTC seconds") from exc
    rendered = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if rendered != value:
        raise ValueError(f"{label} must be canonical UTC seconds")
    return value


def _dt(value: str, label: str) -> datetime:
    _utc(value, label)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _process_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _require_fresh(event_time: str, *, now: datetime, max_age_seconds: int, label: str) -> None:
    dt = _dt(event_time, label)
    if dt > now + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        raise ValueError(f"{label} is from the future")
    age = (now - dt).total_seconds()
    if age > max_age_seconds:
        raise ValueError(f"{label} is stale")


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError(f"{label} must be lower-case sha256 hex")
    return value


def _opaque(value: Any, label: str) -> str:
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise ValueError(f"{label} must be a bounded opaque token")
    return value


def _exact_keys(obj: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if type(obj) is not dict:
        raise ValueError(f"{label} must be an object")
    got = set(obj)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise ValueError(f"{label} keys mismatch missing={missing} extra={extra}")
    return obj


def pressure_attestation_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema",
        "organizationFingerprint",
        "pressureReceiptSha256",
        "authorityCommitment",
        "ledgerCommitment",
        "verifiedState",
        "verifiedAt",
    }
    obj = _exact_keys(payload, expected, "pressure attestation body")
    if obj["schema"] != ATTESTATION_SCHEMA:
        raise ValueError("unsupported pressure attestation schema")
    return {
        "schema": ATTESTATION_SCHEMA,
        "organizationFingerprint": _hex64(obj["organizationFingerprint"], "organizationFingerprint"),
        "pressureReceiptSha256": _hex64(obj["pressureReceiptSha256"], "pressureReceiptSha256"),
        "authorityCommitment": _hex64(obj["authorityCommitment"], "authorityCommitment"),
        "ledgerCommitment": _hex64(obj["ledgerCommitment"], "ledgerCommitment"),
        "verifiedState": obj["verifiedState"] if obj["verifiedState"] == READY_STATE else _raise("upstream state is not positive"),
        "verifiedAt": _utc(obj["verifiedAt"], "verifiedAt"),
    }


def _raise(message: str):
    raise ValueError(message)


def mint_pressure_attestation_for_host(body: Mapping[str, Any], host_key: bytes) -> dict[str, Any]:
    """Host-only integration helper.

    The host MUST call the landed organization-pressure verifier itself before invoking
    this helper. There is intentionally no CLI command that turns caller JSON into an
    attestation.
    """
    key = _require_secret(host_key, "host attestation key")
    normalized = pressure_attestation_body(body)
    mac = hmac.new(key, b"pressure-v1\x00" + canonical_json(normalized), hashlib.sha256).hexdigest()
    return {"body": normalized, "hmacSha256": mac}


def verify_pressure_attestation(attestation: Any, host_key: bytes, *, organization_fingerprint: str) -> dict[str, Any]:
    key = _require_secret(host_key, "host attestation key")
    obj = _exact_keys(attestation, {"body", "hmacSha256"}, "pressure attestation")
    body = pressure_attestation_body(obj["body"])
    mac = _hex64(obj["hmacSha256"], "pressure attestation hmac")
    expected = hmac.new(key, b"pressure-v1\x00" + canonical_json(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("invalid pressure attestation HMAC")
    if body["organizationFingerprint"] != _hex64(organization_fingerprint, "organization_fingerprint"):
        raise ValueError("pressure attestation organization transplant")
    return body


def normalize_request(request: Any) -> dict[str, Any]:
    expected = {
        "schema",
        "claimId",
        "organizationFingerprint",
        "prospectFingerprint",
        "routeCommitment",
        "opportunityCommitment",
        "claimantCommitment",
        "requestedAt",
        "pressureAttestation",
    }
    obj = _exact_keys(request, expected, "acquire request")
    if obj["schema"] != "commons.organization-outbound-acquire/v1":
        raise ValueError("unsupported acquire schema")
    return {
        "schema": obj["schema"],
        "claimId": _opaque(obj["claimId"], "claimId"),
        "organizationFingerprint": _hex64(obj["organizationFingerprint"], "organizationFingerprint"),
        "prospectFingerprint": _hex64(obj["prospectFingerprint"], "prospectFingerprint"),
        "routeCommitment": _hex64(obj["routeCommitment"], "routeCommitment"),
        "opportunityCommitment": _hex64(obj["opportunityCommitment"], "opportunityCommitment"),
        "claimantCommitment": _hex64(obj["claimantCommitment"], "claimantCommitment"),
        "requestedAt": _utc(obj["requestedAt"], "requestedAt"),
        "pressureAttestation": obj["pressureAttestation"],
    }


def _lease_document(request: dict[str, Any], pressure: dict[str, Any], nonce_key: bytes) -> dict[str, Any]:
    nonce_key = _require_secret(nonce_key, "lease nonce key")
    intent = {
        "claimId": request["claimId"],
        "organizationFingerprint": request["organizationFingerprint"],
        "prospectFingerprint": request["prospectFingerprint"],
        "routeCommitment": request["routeCommitment"],
        "opportunityCommitment": request["opportunityCommitment"],
        "claimantCommitment": request["claimantCommitment"],
        "requestedAt": request["requestedAt"],
        "pressureReceiptSha256": pressure["pressureReceiptSha256"],
        "authorityCommitment": pressure["authorityCommitment"],
        "ledgerCommitment": pressure["ledgerCommitment"],
        "pressureVerifiedAt": pressure["verifiedAt"],
    }
    intent_sha = sha256_hex(canonical_json(intent))
    nonce = hmac.new(nonce_key, b"lease-nonce-v1\x00" + canonical_json(intent), hashlib.sha256).hexdigest()
    lease_id = sha256_hex(b"lease-id-v1\x00" + bytes.fromhex(intent_sha) + bytes.fromhex(nonce))
    body = {
        "schema": LEASE_SCHEMA,
        "leaseId": lease_id,
        "intentSha256": intent_sha,
        "leaseNonce": nonce,
        **intent,
        "externalSendAuthorized": False,
    }
    body["leaseSha256"] = sha256_hex(canonical_json(body))
    return body


def verify_lease_document(value: Any) -> dict[str, Any]:
    expected = {
        "schema", "leaseId", "intentSha256", "leaseNonce", "claimId",
        "organizationFingerprint", "prospectFingerprint", "routeCommitment",
        "opportunityCommitment", "claimantCommitment", "requestedAt",
        "pressureReceiptSha256", "authorityCommitment", "ledgerCommitment",
        "pressureVerifiedAt", "externalSendAuthorized", "leaseSha256",
    }
    obj = dict(_exact_keys(value, expected, "lease"))
    if obj["schema"] != LEASE_SCHEMA:
        raise ValueError("unsupported lease schema")
    for k in ["leaseId", "intentSha256", "leaseNonce", "organizationFingerprint", "prospectFingerprint", "routeCommitment", "opportunityCommitment", "claimantCommitment", "pressureReceiptSha256", "authorityCommitment", "ledgerCommitment", "leaseSha256"]:
        _hex64(obj[k], k)
    _opaque(obj["claimId"], "claimId")
    _utc(obj["requestedAt"], "requestedAt")
    _utc(obj["pressureVerifiedAt"], "pressureVerifiedAt")
    if obj["externalSendAuthorized"] is not False:
        raise ValueError("lease can never authorize external send")
    claimed = obj.pop("leaseSha256")
    actual = sha256_hex(canonical_json(obj))
    obj["leaseSha256"] = claimed
    if not hmac.compare_digest(claimed, actual):
        raise ValueError("lease digest mismatch")
    return obj


def acquire_lease(store: LeaseStore, request: Any, *, host_attestation_key: bytes, lease_nonce_key: bytes) -> AcquireResult:
    req = normalize_request(request)
    pressure = verify_pressure_attestation(req["pressureAttestation"], host_attestation_key, organization_fingerprint=req["organizationFingerprint"])
    if _dt(pressure["verifiedAt"], "pressure verifiedAt") > _dt(req["requestedAt"], "requestedAt"):
        raise ValueError("pressure verification cannot postdate acquire request")
    if (_dt(req["requestedAt"], "requestedAt") - _dt(pressure["verifiedAt"], "pressure verifiedAt")).total_seconds() > MAX_PREFLIGHT_AGE_SECONDS:
        raise ValueError("pressure verification is stale relative to acquire request")
    lease = _lease_document(req, pressure, lease_nonce_key)
    content = canonical_json(lease)

    # Read before the freshness gate so an exact already-held lease can be recovered
    # after the original acquisition window without minting any new authority. A stale
    # request may observe a conflicting holder but may never create a new lease.
    existing = store.get_active(req["organizationFingerprint"])
    if existing is not None:
        raw, generation = existing
        existing_lease = verify_lease_document(parse_json_strict(raw.decode("utf-8")))
        if existing_lease["leaseSha256"] == lease["leaseSha256"]:
            return AcquireResult("LEASE_ACQUIRED", existing_lease, generation, True)
        return AcquireResult("ORGANIZATION_ALREADY_LEASED", existing_lease, generation, False)

    now = _process_now()
    _require_fresh(req["requestedAt"], now=now, max_age_seconds=MAX_PREFLIGHT_AGE_SECONDS, label="requestedAt")
    _require_fresh(pressure["verifiedAt"], now=now, max_age_seconds=MAX_PREFLIGHT_AGE_SECONDS, label="pressure verifiedAt")

    try:
        generation = store.create_active(req["organizationFingerprint"], content)
        return AcquireResult("LEASE_ACQUIRED", lease, generation, False)
    except Exception as exc:
        # StoreConflict/StoreUncertain are intentionally not imported here; any create
        # failure is reconciled by authoritative read before deciding whether to retry.
        existing = store.get_active(req["organizationFingerprint"])
        if existing is None:
            raise RuntimeError("acquire outcome uncertain; reconciliation required") from exc
        raw, generation = existing
        existing_lease = verify_lease_document(parse_json_strict(raw.decode("utf-8")))
        if existing_lease["leaseSha256"] == lease["leaseSha256"]:
            return AcquireResult("LEASE_ACQUIRED", existing_lease, generation, True)
        return AcquireResult("ORGANIZATION_ALREADY_LEASED", existing_lease, generation, False)


def normalize_finalize_request(value: Any) -> dict[str, Any]:
    expected = {"schema", "organizationFingerprint", "leaseId", "leaseNonce", "claimId", "outcomeId", "outcome", "observedAt", "evidenceCommitment"}
    obj = _exact_keys(value, expected, "finalize request")
    if obj["schema"] != "commons.organization-outbound-finalize/v1":
        raise ValueError("unsupported finalize schema")
    if obj["outcome"] not in TERMINAL_STATES:
        raise ValueError("unsupported terminal outcome")
    return {
        "schema": obj["schema"],
        "organizationFingerprint": _hex64(obj["organizationFingerprint"], "organizationFingerprint"),
        "leaseId": _hex64(obj["leaseId"], "leaseId"),
        "leaseNonce": _hex64(obj["leaseNonce"], "leaseNonce"),
        "claimId": _opaque(obj["claimId"], "claimId"),
        "outcomeId": _opaque(obj["outcomeId"], "outcomeId"),
        "outcome": obj["outcome"],
        "observedAt": _utc(obj["observedAt"], "observedAt"),
        "evidenceCommitment": _hex64(obj["evidenceCommitment"], "evidenceCommitment"),
    }


def _outcome_doc(req: dict[str, Any], lease: dict[str, Any]) -> dict[str, Any]:
    if req["organizationFingerprint"] != lease["organizationFingerprint"]:
        raise ValueError("cross-organization finalization")
    if req["leaseId"] != lease["leaseId"] or req["leaseNonce"] != lease["leaseNonce"] or req["claimId"] != lease["claimId"]:
        raise ValueError("finalization does not bind exact lease generation")
    if req["observedAt"] < lease["requestedAt"]:
        raise ValueError("outcome predates acquire request")
    body = {
        "schema": OUTCOME_SCHEMA,
        "organizationFingerprint": req["organizationFingerprint"],
        "leaseId": req["leaseId"],
        "leaseNonce": req["leaseNonce"],
        "leaseSha256": lease["leaseSha256"],
        "claimId": req["claimId"],
        "outcomeId": req["outcomeId"],
        "outcome": req["outcome"],
        "observedAt": req["observedAt"],
        "evidenceCommitment": req["evidenceCommitment"],
        "externalSendAuthorized": False,
        "cashOrRevenueClaimed": False,
    }
    body["outcomeSha256"] = sha256_hex(canonical_json(body))
    return body


def verify_outcome_document(value: Any) -> dict[str, Any]:
    expected = {
        "schema", "organizationFingerprint", "leaseId", "leaseNonce",
        "leaseSha256", "claimId", "outcomeId", "outcome", "observedAt",
        "evidenceCommitment", "externalSendAuthorized", "cashOrRevenueClaimed",
        "outcomeSha256",
    }
    obj = dict(_exact_keys(value, expected, "outcome"))
    if obj["schema"] != OUTCOME_SCHEMA:
        raise ValueError("unsupported outcome schema")
    for key in ("organizationFingerprint", "leaseId", "leaseNonce", "leaseSha256", "evidenceCommitment", "outcomeSha256"):
        _hex64(obj[key], key)
    _opaque(obj["claimId"], "claimId")
    _opaque(obj["outcomeId"], "outcomeId")
    if obj["outcome"] not in TERMINAL_STATES:
        raise ValueError("unsupported terminal outcome")
    _utc(obj["observedAt"], "observedAt")
    if obj["externalSendAuthorized"] is not False or obj["cashOrRevenueClaimed"] is not False:
        raise ValueError("outcome exceeds authority ceiling")
    claimed = obj.pop("outcomeSha256")
    actual = sha256_hex(canonical_json(obj))
    obj["outcomeSha256"] = claimed
    if not hmac.compare_digest(claimed, actual):
        raise ValueError("outcome digest mismatch")
    return obj


def _outcome_matches_request(outcome: dict[str, Any], req: dict[str, Any]) -> bool:
    return all((
        outcome["organizationFingerprint"] == req["organizationFingerprint"],
        outcome["leaseId"] == req["leaseId"],
        outcome["leaseNonce"] == req["leaseNonce"],
        outcome["claimId"] == req["claimId"],
        outcome["outcomeId"] == req["outcomeId"],
        outcome["outcome"] == req["outcome"],
        outcome["observedAt"] == req["observedAt"],
        outcome["evidenceCommitment"] == req["evidenceCommitment"],
    ))


def _release_unsent_if_needed(store: LeaseStore, req: dict[str, Any]) -> bool:
    """Release only the exact finalized lease generation; never a successor."""
    active = store.get_active(req["organizationFingerprint"])
    if active is None:
        return True
    raw, active_generation = active
    lease = verify_lease_document(parse_json_strict(raw.decode("utf-8")))
    if (lease["leaseId"], lease["leaseNonce"], lease["claimId"]) != (req["leaseId"], req["leaseNonce"], req["claimId"]):
        # A different active generation proves the finalized lease was already released.
        return True
    try:
        store.delete_active(req["organizationFingerprint"], active_generation)
        return True
    except Exception as exc:
        # Conditional delete may have succeeded while its response was lost, or another
        # exact finalizer may have deleted first. Re-read before escalating uncertainty.
        current = store.get_active(req["organizationFingerprint"])
        if current is None:
            return True
        current_raw, _ = current
        current_lease = verify_lease_document(parse_json_strict(current_raw.decode("utf-8")))
        if (current_lease["leaseId"], current_lease["leaseNonce"], current_lease["claimId"]) != (req["leaseId"], req["leaseNonce"], req["claimId"]):
            return True
        raise RuntimeError("lease release uncertain; reconciliation required") from exc


def finalize_lease(store: LeaseStore, request: Any) -> FinalizeResult:
    req = normalize_finalize_request(request)

    # Exact replay is checked before freshness/active-state gates. Replaying a retained
    # terminal outcome creates no new authority and must remain recoverable after an
    # UNSENT release removed the active lease or after the original time window elapsed.
    existing = store.get_outcome(req["organizationFingerprint"], req["leaseId"])
    if existing is not None:
        prior_raw, outcome_generation = existing
        outcome = verify_outcome_document(parse_json_strict(prior_raw.decode("utf-8")))
        if not _outcome_matches_request(outcome, req):
            raise ValueError("conflicting outcome already exists")
        released = False
        if req["outcome"] == "UNSENT_RELEASED":
            released = _release_unsent_if_needed(store, req)
        return FinalizeResult(req["outcome"], outcome, outcome_generation, released, True)

    _require_fresh(req["observedAt"], now=_process_now(), max_age_seconds=MAX_OUTCOME_AGE_SECONDS, label="observedAt")
    active = store.get_active(req["organizationFingerprint"])
    if active is None:
        raise ValueError("no active organization lease; reconcile before finalization")
    raw, _active_generation = active
    lease = verify_lease_document(parse_json_strict(raw.decode("utf-8")))
    outcome = _outcome_doc(req, lease)
    content = canonical_json(outcome)
    try:
        outcome_generation = store.create_outcome(req["organizationFingerprint"], req["leaseId"], content)
        replay = False
    except Exception as exc:
        # Outcome stores make create-if-absent atomic. A conflict or uncertain response
        # is reconciled by exact retained bytes rather than by retrying the mutation.
        existing = store.get_outcome(req["organizationFingerprint"], req["leaseId"])
        if existing is None:
            raise RuntimeError("outcome persistence uncertain; reconciliation required") from exc
        prior_raw, outcome_generation = existing
        prior = verify_outcome_document(parse_json_strict(prior_raw.decode("utf-8")))
        if not _outcome_matches_request(prior, req) or not hmac.compare_digest(prior_raw, content):
            raise ValueError("conflicting outcome already exists") from exc
        outcome = prior
        replay = True

    released = False
    if req["outcome"] == "UNSENT_RELEASED":
        # Critical ordering: immutable outcome is committed before conditional release.
        released = _release_unsent_if_needed(store, req)
    return FinalizeResult(req["outcome"], outcome, outcome_generation, released, replay)
