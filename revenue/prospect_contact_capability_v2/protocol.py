"""Connector-native capability-chain prospect contact custody v2.

This module is an offline planner/verifier.  It never calls GitHub or a provider.
The authority event is create-exclusive deterministic branch creation performed
by a connector executor, then exact readback compiled here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping

SCHEMA = "prospect-contact-custody/v2"
CLAIM_PLAN_SCHEMA = "prospect-contact-custody-claim-plan/v2"
CLAIM_INTENT_SCHEMA = "prospect-contact-custody-claim-intent/v2"
CLAIM_RECEIPT_SCHEMA = "prospect-contact-custody-claim-receipt/v2"
TERMINAL_PLAN_SCHEMA = "prospect-contact-custody-terminal-plan/v2"
TERMINAL_INTENT_SCHEMA = "prospect-contact-custody-terminal-intent/v2"
TERMINAL_RECEIPT_SCHEMA = "prospect-contact-custody-terminal-receipt/v2"
REVEAL_PLAN_SCHEMA = "prospect-contact-custody-release-reveal-plan/v2"
REVEAL_INTENT_SCHEMA = "prospect-contact-custody-release-reveal-intent/v2"
REVEAL_RECEIPT_SCHEMA = "prospect-contact-custody-release-reveal-receipt/v2"
CONTACTED_PLAN_SCHEMA = "prospect-contact-custody-contacted-plan/v2"
CONTACTED_INTENT_SCHEMA = "prospect-contact-custody-contacted-intent/v2"
CONTACTED_RECEIPT_SCHEMA = "prospect-contact-custody-contacted-receipt/v2"

CLAIM_BRANCH_PREFIX = "prospect-contact-v2/claim/"
TERMINAL_BRANCH_PREFIX = "prospect-contact-v2/terminal/"
REVEAL_BRANCH_PREFIX = "prospect-contact-v2/reveal/"
CONTACTED_BRANCH_PREFIX = "prospect-contact-v2/contacted/"
METADATA_PREFIX = ".tjlabs/prospect-contact-v2/"
ZERO64 = "0" * 64
CAPABILITY_BYTES = 32
MAX_TEXT = 500

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$")
PHONE_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_AMOUNT_RE = re.compile(
    r"(?:[$€£]\s*(?P<lead>[0-9][0-9,]*(?:\.[0-9]{1,2})?)|"
    r"(?P<trail>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:usd|eur|gbp|rtc)\b)",
    re.IGNORECASE,
)
_NEGATIVE_COMP_RE = re.compile(
    r"(?:\b(?:unpaid|gratis|volunteer|free)\b|\bpro\s+bono\b|"
    r"\b(?:no|not|without|zero)\s+(?:pay|paid|payment|fee|compensation|bounty|prize|invoice|commission|retainer)\b)",
    re.IGNORECASE,
)
_SIGNAL_PHRASES = (
    "paid", "payment", "bounty", "prize", "invoice", "fee", "commission",
    "award", "purchase order", "retainer", "contract", "subcontract", "bid",
    "pilot", "discovery",
)


class CustodyError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError("value is not canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _text_digest(value: str) -> str:
    if type(value) is not str:
        raise CustodyError("text required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _token(value: Any, field: str) -> str:
    if type(value) is not str:
        raise CustodyError(f"{field} must be text")
    value = unicodedata.normalize("NFKC", value.strip())
    if not TOKEN_RE.fullmatch(value):
        raise CustodyError(f"{field} invalid")
    return value


def _sha40(value: Any, field: str) -> str:
    if type(value) is not str or not HEX40_RE.fullmatch(value):
        raise CustodyError(f"{field} must be lowercase git SHA-1")
    return value


def _sha64(value: Any, field: str) -> str:
    if type(value) is not str or not HEX64_RE.fullmatch(value):
        raise CustodyError(f"{field} must be lowercase SHA-256")
    return value


def _capability(value: Any) -> str:
    return _sha64(value, "capability")


def capability_commitment(capability: str) -> str:
    return hashlib.sha256(bytes.fromhex(_capability(capability))).hexdigest()


def _authority_flags() -> dict[str, bool]:
    return {
        "external_send_authorized": False,
        "provider_send_completed": False,
        "payment_or_revenue_inferred": False,
    }


def _check_authority_flags(raw: Mapping[str, Any]) -> None:
    for key, expected in _authority_flags().items():
        if raw.get(key) is not expected:
            raise CustodyError(f"{key} must remain false")


def _expected_sealed_fields(raw: Mapping[str, Any], seal_field: str) -> set[str]:
    schema = raw.get("schema")
    state = raw.get("state")
    flags = {"external_send_authorized", "provider_send_completed", "payment_or_revenue_inferred"}
    common_claim = {"generation", "key_sha256", "claim_seam_sha256", "claimant", "operation_id", "claim_capability_sha256"}
    if schema == CLAIM_PLAN_SCHEMA:
        fields = common_claim | {"schema", "target_kind", "target_hint", "prior_release_reveal_receipt_sha256", "anchor_sha", "preflight_sha256", "branch_name", "metadata_path", "metadata_sha256", "metadata_json", "plan_sha256"}
    elif schema == CLAIM_INTENT_SCHEMA:
        fields = common_claim | {"schema", "anchor_sha", "branch_name", "metadata_path", "metadata_sha256", "plan_sha256", "claim_commit_sha", "intent_sha256"}
    elif schema == CLAIM_RECEIPT_SCHEMA:
        fields = common_claim | {"schema", "state", "target_kind", "target_hint", "prior_release_reveal_receipt_sha256", "anchor_sha", "preflight_sha256", "branch_name", "metadata_path", "metadata_sha256", "metadata_json", "claim_commit_sha", "plan_sha256", "intent_sha256", "receipt_sha256"}
    elif schema == TERMINAL_PLAN_SCHEMA and state == "RELEASED_UNSENT":
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_receipt_sha256", "claim_receipt", "claim_capability_sha256", "release_reason_sha256", "holder_proof_hmac_sha256", "terminal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "plan_sha256"}
    elif schema == TERMINAL_PLAN_SCHEMA and state == "DISPATCHED_OUTCOME_UNKNOWN":
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_receipt_sha256", "claim_receipt", "claim_capability_sha256", "message_sha256", "channel", "compensation_path_sha256", "compensation_category", "holder_proof_hmac_sha256", "terminal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "plan_sha256"}
    elif schema == TERMINAL_INTENT_SCHEMA and state in {"RELEASED_UNSENT", "DISPATCHED_OUTCOME_UNKNOWN"}:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_receipt_sha256", "claim_receipt", "claim_capability_sha256", "terminal_branch_name", "metadata_path", "metadata_sha256", "plan_sha256", "terminal_commit_sha", "intent_sha256"}
    elif schema == TERMINAL_RECEIPT_SCHEMA and state == "RELEASED_UNSENT":
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_receipt_sha256", "claim_receipt", "claim_capability_sha256", "release_reason_sha256", "holder_proof_hmac_sha256", "terminal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "terminal_commit_sha", "plan_sha256", "intent_sha256", "receipt_sha256"}
    elif schema == TERMINAL_RECEIPT_SCHEMA and state == "DISPATCHED_OUTCOME_UNKNOWN":
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_receipt_sha256", "claim_receipt", "claim_capability_sha256", "message_sha256", "channel", "compensation_path_sha256", "compensation_category", "holder_proof_hmac_sha256", "terminal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "terminal_commit_sha", "plan_sha256", "intent_sha256", "receipt_sha256"}
    elif schema == REVEAL_PLAN_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "terminal_commit_sha", "terminal_receipt_sha256", "terminal_receipt", "claim_capability_sha256", "retired_capability", "reveal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "plan_sha256"}
    elif schema == REVEAL_INTENT_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "terminal_commit_sha", "terminal_receipt_sha256", "reveal_branch_name", "metadata_path", "metadata_sha256", "plan_sha256", "reveal_commit_sha", "intent_sha256"}
    elif schema == REVEAL_RECEIPT_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "terminal_commit_sha", "terminal_receipt_sha256", "terminal_receipt", "claim_capability_sha256", "retired_capability", "reveal_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "reveal_commit_sha", "plan_sha256", "intent_sha256", "receipt_sha256"}
    elif schema == CONTACTED_PLAN_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "terminal_commit_sha", "terminal_receipt_sha256", "claim_capability_sha256", "provider_receipt_sha256", "contacted_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "plan_sha256"}
    elif schema == CONTACTED_INTENT_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "terminal_commit_sha", "terminal_receipt_sha256", "contacted_branch_name", "metadata_path", "metadata_sha256", "plan_sha256", "contacted_commit_sha", "intent_sha256"}
    elif schema == CONTACTED_RECEIPT_SCHEMA:
        fields = {"schema", "state", "generation", "key_sha256", "claim_seam_sha256", "claim_commit_sha", "claim_capability_sha256", "terminal_commit_sha", "terminal_receipt_sha256", "provider_receipt_sha256", "contacted_branch_name", "metadata_path", "metadata_sha256", "metadata_json", "contacted_commit_sha", "plan_sha256", "intent_sha256", "receipt_sha256"}
    else:
        raise CustodyError("unsupported sealed object schema/state")
    fields |= flags
    if seal_field not in fields:
        raise CustodyError("sealed object uses unexpected seal field")
    return fields


def _normalize_domain(raw: str) -> str:
    value = unicodedata.normalize("NFKC", raw.strip()).rstrip(".").casefold()
    if not value or CONTROL_RE.search(value) or any(ch.isspace() for ch in value):
        raise CustodyError("invalid domain")
    try:
        domain = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CustodyError("invalid domain") from exc
    labels = domain.split(".")
    if len(domain) > 253 or len(labels) < 2:
        raise CustodyError("domain must be qualified")
    if any(not x or len(x) > 63 or x[0] == "-" or x[-1] == "-" or not re.fullmatch(r"[a-z0-9-]+", x) for x in labels):
        raise CustodyError("invalid domain labels")
    return domain


def normalize_target(kind: str, raw: str) -> dict[str, str]:
    kind = _token(kind, "kind").casefold()
    if type(raw) is not str:
        raise CustodyError("target must be text")
    value = unicodedata.normalize("NFKC", raw.strip())
    if kind == "email":
        if CONTROL_RE.search(value) or any(ch.isspace() for ch in value) or value.count("@") != 1:
            raise CustodyError("invalid email")
        local, domain = value.rsplit("@", 1)
        local = local.casefold()
        if not local or len(local) > 64:
            raise CustodyError("invalid email local part")
        domain = _normalize_domain(domain)
        canonical = f"{local}@{domain}"
        hint = f"{local[:1]}…@{domain}"
    elif kind == "domain":
        canonical = _normalize_domain(value)
        hint = f"{canonical[:1]}…{canonical[-1:]}"
    elif kind == "phone":
        canonical = re.sub(r"[\s().-]", "", value)
        if not PHONE_RE.fullmatch(canonical):
            raise CustodyError("phone must be E.164")
        hint = canonical[:2] + "…" + canonical[-2:]
    else:
        raise CustodyError("kind must be email, domain, or phone")
    key = hashlib.sha256(b"prospect-contact-custody/v2\0" + kind.encode() + b"\0" + canonical.encode()).hexdigest()
    return {"kind": kind, "key_sha256": key, "target_hint": hint}


def _compensation_category(text: str) -> tuple[str, str]:
    if type(text) is not str:
        raise CustodyError("compensation_path must be text")
    raw = unicodedata.normalize("NFKC", text.strip())
    norm = raw.casefold()
    if not norm or len(norm) > MAX_TEXT or CONTROL_RE.search(norm):
        raise CustodyError("compensation_path invalid")
    if _NEGATIVE_COMP_RE.search(norm):
        raise CustodyError("negative/free compensation language")
    saw_zero = False
    for match in _AMOUNT_RE.finditer(norm):
        value = (match.group("lead") or match.group("trail") or "").replace(",", "")
        try:
            amount = Decimal(value)
        except InvalidOperation:
            continue
        if amount > 0:
            return "priced_service", hashlib.sha256(raw.encode()).hexdigest()
        if amount == 0:
            saw_zero = True
    if saw_zero:
        raise CustodyError("zero-value compensation path")
    tokens = re.findall(r"[a-z0-9]+", norm)
    for phrase in _SIGNAL_PHRASES:
        words = phrase.split()
        if any(tokens[i:i+len(words)] == words for i in range(0, len(tokens)-len(words)+1)):
            if phrase in {"bounty", "prize"}:
                category = "bounty_or_prize"
            elif phrase in {"contract", "subcontract", "bid", "award"}:
                category = "bid_or_contract"
            elif phrase in {"invoice", "fee", "commission", "retainer"}:
                category = "fee_or_invoice"
            else:
                category = "paid_path"
            return category, hashlib.sha256(raw.encode()).hexdigest()
    raise CustodyError("concrete paid/award path required")


def _claim_seam(key_sha256: str, prior_release_reveal_receipt_sha256: str) -> str:
    return _digest({
        "schema": SCHEMA,
        "key_sha256": _sha64(key_sha256, "key_sha256"),
        "prior_release_reveal_receipt_sha256": _sha64(prior_release_reveal_receipt_sha256, "prior_release_reveal_receipt_sha256"),
    })


def claim_branch(key_sha256: str, prior_release_reveal_receipt_sha256: str = ZERO64) -> str:
    return CLAIM_BRANCH_PREFIX + _claim_seam(key_sha256, prior_release_reveal_receipt_sha256)
