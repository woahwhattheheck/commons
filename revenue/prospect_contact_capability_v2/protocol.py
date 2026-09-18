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


