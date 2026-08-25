#!/usr/bin/env python3
"""Deterministic, secret-free receipts for the GGUF diagnostic revenue lane.

This instrument reads exact public Commons artifacts and explicit external
private evidence. It never writes by default and never upgrades purchase intent
into legal acceptance, delivery, payment, or cash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes

OFFER_ID = "gguf-diagnostic-10d-12k"
SUBJECT = "GGUF DIAGNOSTIC PURCHASE INTENT"
PACK_PATH = "revenue/payment_ready/pack.json"
RECOVERY_PATH = "revenue/payment_ready/recovery.json"
EXPECTED_TERMS_SHA256 = "1c0756062563415e551587a5f1ab22147366d406135de6c45ccbd3a562985730"

FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]{1,40}):\s*(.*)$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
HTTPS_RE = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OPAQUE_REFERENCE_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9._-]{0,31}:[A-Za-z0-9][A-Za-z0-9._-]{0,126}$"
)
PERCENT_DECODE_LAYERS = 4
SENSITIVE_FIELD_NAMES = frozenset({
    "authorization",
    "aws_access_key_id",
    "password",
    "passwd",
    "passphrase",
    "api_key",
    "access_token",
    "auth_token",
    "client_secret",
    "secret",
    "token",
    "private_buyer",
    "private_customer",
    "buyer_private",
    "model_bytes",
    "model_weights",
    "gguf_bytes",
    "gguf_file",
    "weights",
    "base64",
    "b64",
    "tax_id",
    "taxpayer_id",
    "taxpayer_identification",
    "ein",
    "tin",
    "email",
    "email_address",
    "customer_email",
    "private_email",
    "contact_email",
    "buyer_email",
    "work_email",
    "contact",
    "private_contact",
    "customer_contact",
    "buyer_contact",
    "phone",
    "phone_number",
    "telephone",
    "mobile",
    "mobile_phone",
    "customer_phone",
    "private_phone",
    "contact_phone",
    "buyer_phone",
    "name",
    "full_name",
    "first_name",
    "last_name",
    "legal_name",
    "customer_name",
    "private_name",
    "contact_name",
    "buyer_name",
    "address",
    "street_address",
    "address_line_1",
    "address_line_2",
    "mailing_address",
    "postal_address",
    "customer_address",
    "private_address",
    "contact_address",
    "postal_code",
    "zip_code",
    "postcode",
    "routing_number",
    "account_number",
    "bank_account",
    "bank_account_number",
    "bank_routing_number",
    "aba_routing_number",
    "iban",
    "swift",
    "swift_code",
    "bic",
    "sort_code",
})
FIELD_ASSIGNMENT_RE = re.compile(
    r'''["']?([A-Za-z][A-Za-z0-9_. -]{1,60})["']?\s*[:=]\s*'''
    r'''(?:["']([^"'\r\n]*)["']|([^\s,}\r\n]+))''',
    re.IGNORECASE,
)
PERCENT_ESCAPE_RE = re.compile(r"%[0-9A-Fa-f]{2}")
HTTPS_TOKEN_RE = re.compile(r"\bhttps://[^\s]+", re.IGNORECASE)
SENSITIVE_PATTERNS = (
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:routing|account)\s*(?:number)?\s*:\s*\d", re.IGNORECASE),
    re.compile(r"\b(?:tax[_ -]?id|taxpayer[_ -]?(?:id|identification)|ein|tin)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b\d{2}-\d{7}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])\d{10}(?![A-Za-z0-9])"),
    re.compile(r"(?<!\w)(?:\+?[1-9]\d{0,2}[ .-]*)?(?:\(\d{2,4}\)|\d{2,4})[ .-]+\d{3,4}[ .-]+\d{4}(?!\w)"),
    re.compile(
        r"\b\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,5}\s+"
        r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|way|parkway|pkwy)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]+\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bauthorization\s*[:=]\s*['\"]?Bearer\s+\S+", re.IGNORECASE),
    re.compile(
        r"(?:[?&](?:access[_-]?token|api[_-]?key|key|password|secret|token)=)[^&#\s]+",
        re.IGNORECASE,
    ),
    re.compile(r"\bhttps://[^/?#\s@]+@[^/?#\s]+", re.IGNORECASE),
    re.compile(
        r"\b(?:password|passwd|passphrase|api[_ -]?key|access[_ -]?token|auth[_ -]?token|client[_ -]?secret|secret|token|bearer)"
        r"\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:private[_ -]?(?:buyer|customer)|buyer[_ -]?private)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(
        r"\b(?:weights?|model|gguf)(?:[_ -]?(?:bytes|weights|file|data|payload|base64|b64))?\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:base64|b64)\s*[:=]\s*[A-Za-z0-9+/=_-]{8,}", re.IGNORECASE),
    re.compile(r"\bdata:[^\s;,]+;base64,[A-Za-z0-9+/=]+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{80,}={0,2}(?![A-Za-z0-9+/])"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_canonical_text_file(path: Path) -> str:
    """Hash UTF-8 text with every platform newline canonicalized to LF."""
    with path.open("r", encoding="utf-8", newline=None) as source:
        return sha256_bytes(source.read().encode("utf-8"))


def terms_record(pack: dict[str, Any]) -> dict[str, Any]:
    offer = pack["offer"]
    return {
        "acceptance_rule": offer["acceptance_rule"],
        "acceptance_tests": [row["id"] for row in pack["acceptance_tests"]],
        "currency": offer["currency"],
        "fixed_amount": offer["fixed_amount"],
        "milestones": [
            {"amount": row["amount"], "due": row["due"], "id": row["id"]}
            for row in offer["milestones"]
        ],
        "offer_id": offer["offer_id"],
        "term_calendar_days": offer["term_calendar_days"],
    }


def terms_sha256(pack: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(terms_record(pack)))


def safe_inbound_path(root: Path, inbound_id: str) -> Path:
    if not SAFE_ID_RE.fullmatch(inbound_id) or "/" in inbound_id or "\\" in inbound_id or inbound_id in {".", ".."}:
        raise ValueError("inbound id must be a single safe Commons post id")
    candidate = (root / "p" / f"{inbound_id}.md").resolve()
    expected_parent = (root / "p").resolve()
    if candidate.parent != expected_parent:
        raise ValueError("inbound path escaped p/")
    return candidate


def safe_repo_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("evidence path must be a POSIX-style relative path")
    path = Path(relative)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError("evidence path must stay inside the Commons root")
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("evidence path escaped Commons root") from error
    if not candidate.is_file():
        raise ValueError(f"evidence file missing: {relative}")
    return candidate


def validate_evidence_root(root: Path, evidence_root: Path) -> Path:
    """Resolve a private evidence root that is disjoint from Commons."""
    commons = root.resolve(strict=True)
    private = evidence_root.resolve(strict=True)
    if not private.is_dir():
        raise ValueError("evidence root must be an existing directory")
    try:
        private.relative_to(commons)
    except ValueError:
        pass
    else:
        raise ValueError("evidence root must be outside the Commons root")
    try:
        commons.relative_to(private)
    except ValueError:
        pass
    else:
        raise ValueError("evidence root must be disjoint from the Commons root")
    return private


def safe_external_evidence_file(root: Path, evidence_root: Path, relative: str) -> Path:
    """Resolve exact private bytes beneath a disjoint external evidence root."""
    private = validate_evidence_root(root, evidence_root)
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("private evidence path must be a POSIX-style relative path")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("private evidence path must stay inside the external evidence root")
    candidate = (private / path).resolve(strict=True)
    try:
        candidate.relative_to(private)
    except ValueError as error:
        raise ValueError("private evidence path escaped the external evidence root") from error
    try:
        candidate.relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise ValueError("private evidence path resolved inside the Commons root")
    if not candidate.is_file():
        raise ValueError(f"private evidence file missing: {relative}")
    return candidate


def parse_post(text: str) -> tuple[dict[str, str], dict[str, str]]:
    headers: dict[str, str] = {}
    fields: dict[str, str] = {}
    phase = "PREAMBLE"
    for raw in text.splitlines():
        line = raw.strip()
        if line == "---":
            phase = "HEADER" if phase == "PREAMBLE" else "BODY"
            continue
        match = FIELD_RE.match(line)
        if not match:
            continue
        key, value = match.groups()
        upper_key = key.upper()
        if phase == "BODY" or upper_key in {
            "PLAIN", "OFFER_ID", "TERMS_SHA256", "PURCHASE_INTENT", "GGUF_CONTROL",
            "HARNESS_READY", "PUBLIC_CONTACT_URL", "START_WINDOW", "PUBLIC_OBJECTIVE",
        }:
            fields[upper_key] = value.strip()
        else:
            headers[key.lower()] = value.strip()
    return headers, fields


def canonical_field_name(name: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", str(name))
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def is_sensitive_field_name(name: str) -> bool:
    canonical = canonical_field_name(name)
    return canonical in SENSITIVE_FIELD_NAMES or canonical.startswith("aws_secret_")


def _json_has_sensitive_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if is_sensitive_field_name(str(key)) and child not in (None, "", [], {}):
                return True
            if _json_has_sensitive_field(child):
                return True
    elif isinstance(value, list):
        return any(_json_has_sensitive_field(child) for child in value)
    return False


def _decode_percent_once(value: str) -> tuple[str, bool, bool]:
    """Decode one percent layer with strict UTF-8; preserve literal percent."""
    if not PERCENT_ESCAPE_RE.search(value):
        return value, False, False
    try:
        decoded = unquote_to_bytes(value).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return value, False, True
    return decoded, decoded != value, False


def decode_percent_layers(value: Any) -> tuple[str, bool]:
    """Decode bounded URL layers; flag overflow or invalid UTF-8 fail closed."""
    decoded = str(value)
    for _ in range(PERCENT_DECODE_LAYERS):
        next_value, changed, invalid = _decode_percent_once(decoded)
        if invalid:
            return decoded, True
        if not changed:
            return decoded, False
        decoded = next_value
    _next_value, changed, invalid = _decode_percent_once(decoded)
    return decoded, invalid or changed


def _has_sensitive_assignment(text: str) -> bool:
    for match in FIELD_ASSIGNMENT_RE.finditer(text):
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if is_sensitive_field_name(match.group(1)) and str(value or "").strip():
            return True
    return False


def contains_sensitive_value(text: str) -> bool:
    source, decoding_overflow = decode_percent_layers(text)
    if decoding_overflow:
        return True
    if any(pattern.search(source) for pattern in SENSITIVE_PATTERNS):
        return True
    if _has_sensitive_assignment(source):
        return True
    for url in HTTPS_TOKEN_RE.findall(source):
        if any(_has_sensitive_assignment(part) for part in re.split(r"[/?#&;]", url)[1:]):
            return True
    try:
        return _json_has_sensitive_field(json.loads(source))
    except (TypeError, ValueError, json.JSONDecodeError):
        return False


def base_facts() -> dict[str, Any]:
    return {
        "purchase_intent": "UNKNOWN",
        "gguf_control": "UNKNOWN",
        "harness_ready": "UNKNOWN",
        "public_contact_url_present": False,
        "legal_acceptance": "NOT_LANDED",
        "delivery": "NOT_LANDED",
        "processor_reference": "NOT_LANDED",
        "processor_payment": "NOT_LANDED",
        "payout": "NOT_LANDED",
        "bank_available": "NOT_LANDED",
        "cash_evidence": "NOT_LANDED",
        "collected_cash_usd": 0,
    }


def validate_contract(root: Path) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    pack_path = root / PACK_PATH
    recovery_path = root / RECOVERY_PATH
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    term_hash = terms_sha256(pack)
    pack_hash = sha256_canonical_text_file(pack_path)
    if term_hash != EXPECTED_TERMS_SHA256:
        raise ValueError(f"term hash mismatch: {term_hash}")
    if recovery["offer"]["offer_id"] != OFFER_ID:
        raise ValueError("recovery offer id mismatch")
    if recovery["offer"]["source_sha256"] != pack_hash:
        raise ValueError("recovery pack hash mismatch")
    if recovery["offer"]["terms_sha256"] != term_hash:
        raise ValueError("recovery terms hash mismatch")
    return pack, recovery, pack_hash, term_hash


def purchase_intent_receipt(root: Path, inbound_id: str | None) -> dict[str, Any]:
    _, _, pack_hash, term_hash = validate_contract(root)
    pack_evidence = {
        "kind": "OFFER_SOURCE",
        "reference": PACK_PATH,
        "sha256": pack_hash,
        "status": "VERIFIED",
    }
    facts = base_facts()
    if inbound_id is None:
        return {
            "schema_version": "revenue-recovery/v1",
            "kind": "REVENUE_RECOVERY_RECEIPT",
            "receipt_id": "rr-intent-awaiting-buyer",
            "offer_id": OFFER_ID,
            "stage": "PURCHASE_INTENT",
            "state": "NEEDS_BUYER",
            "source": {"path": None, "sha256": None, "terms_sha256": term_hash},
            "evidence": [pack_evidence],
            "facts": facts,
            "next_stage": "PURCHASE_INTENT",
            "cash_claimed": False,
        }

    path = safe_inbound_path(root, inbound_id)
    if not path.is_file():
        return purchase_intent_receipt(root, None)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    content_hash = sha256_bytes(raw)
    headers, fields = parse_post(text)
    required = {
        "OFFER_ID": OFFER_ID,
        "TERMS_SHA256": term_hash,
        "PURCHASE_INTENT": "YES",
        "GGUF_CONTROL": "YES",
        "HARNESS_READY": "YES",
    }
    valid = (
        headers.get("to") == "OFFER"
        and headers.get("board") == "OFFER"
        and headers.get("subject") == SUBJECT
        and all(fields.get(key) == value for key, value in required.items())
        and bool(HTTPS_RE.fullmatch(fields.get("PUBLIC_CONTACT_URL", "")))
        and not contains_sensitive_value(text)
    )
    if valid:
        facts.update({
            "purchase_intent": "YES",
            "gguf_control": "YES",
            "harness_ready": "YES",
            "public_contact_url_present": True,
        })
    receipt_seed = canonical_json({"id": inbound_id, "sha256": content_hash, "terms_sha256": term_hash})
    return {
        "schema_version": "revenue-recovery/v1",
        "kind": "REVENUE_RECOVERY_RECEIPT",
        "receipt_id": "rr-intent-" + sha256_bytes(receipt_seed)[:24],
        "offer_id": OFFER_ID,
        "stage": "PURCHASE_INTENT",
        "state": "RECORDED" if valid else "INCOMPLETE",
        "source": {"path": f"p/{inbound_id}.md", "sha256": content_hash, "terms_sha256": term_hash},
        "evidence": [
            pack_evidence,
            {"kind": "PUBLIC_POST", "reference": f"p/{inbound_id}.md", "sha256": content_hash, "status": "VALID" if valid else "INCOMPLETE"},
        ],
        "facts": facts,
        "next_stage": "QUOTE" if valid else "PURCHASE_INTENT",
        "cash_claimed": False,
    }


STAGE_CONTRACT = {
    "QUOTE": {
        "prior_stage": "PURCHASE_INTENT",
        "prior_state": "RECORDED",
        "state": "OFFERED",
        "next_stage": "ACCEPTANCE",
    },
    "ACCEPTANCE": {
        "prior_stage": "QUOTE",
        "prior_state": "OFFERED",
        "state": "ACCEPTED",
        "next_stage": "DELIVERY",
    },
    "DELIVERY": {
        "prior_stage": "ACCEPTANCE",
        "prior_state": "ACCEPTED",
        "state": "DELIVERED",
        "next_stage": "PROCESSOR_REFERENCE",
    },
    "PROCESSOR_REFERENCE": {
        "prior_stage": "DELIVERY",
        "prior_state": "DELIVERED",
        "state": "REFERENCE_RECORDED",
        "next_stage": "OWNER_PRIVATE_CASH_EVIDENCE",
    },
}


def _checked_artifact(root: Path, evidence_root: Path, artifact: Any, expected_kind: str) -> dict[str, Any]:
    """Verify an artifact digest against exact local bytes, then emit no path.

    The manifest path is relative to an explicit evidence root outside Commons.
    It is an input to verification only: receipts expose the opaque reference
    and verified digest, never the private path, root, or bytes.
    """
    if not isinstance(artifact, dict):
        raise ValueError(f"{expected_kind} artifact missing")
    reference = artifact.get("reference")
    digest = artifact.get("sha256")
    relative_path = artifact.get("path")
    if artifact.get("kind") != expected_kind:
        raise ValueError(f"artifact kind must be {expected_kind}")
    if not isinstance(reference, str) or not OPAQUE_REFERENCE_RE.fullmatch(reference) or ".." in reference:
        raise ValueError("artifact reference must be an opaque, secret-free reference")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ValueError("artifact sha256 must be exact")
    if not isinstance(relative_path, str):
        raise ValueError("artifact path must identify exact local bytes")
    artifact_path = safe_external_evidence_file(root, evidence_root, relative_path)
    if sha256_file(artifact_path) != digest:
        raise ValueError(f"{expected_kind} sha256 does not match artifact bytes")
    return {"kind": expected_kind, "reference": reference, "sha256": digest, "status": "VERIFIED"}


def _checked_timestamp(value: Any, field: str) -> tuple[datetime, str]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an RFC3339 timestamp with timezone")
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
    except ValueError as error:
        raise ValueError(f"{field} must be an RFC3339 timestamp with timezone") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    canonical = parsed.astimezone(timezone.utc).isoformat(timespec="auto").replace("+00:00", "Z")
    return parsed.astimezone(timezone.utc), canonical


def _require_zero_cash_lineage(receipt: dict[str, Any]) -> None:
    facts = receipt.get("facts", {})
    if receipt.get("cash_claimed") is not False:
        raise ValueError("previous receipt may not claim cash")
    for field in ("processor_payment", "payout", "bank_available", "cash_evidence"):
        if facts.get(field) != "NOT_LANDED":
            raise ValueError(f"previous receipt {field} contradicts zero-cash lineage")
    if facts.get("collected_cash_usd") != 0:
        raise ValueError("cash_claimed false requires collected_cash_usd to be zero")


PREDECESSOR_STATE = {
    "PURCHASE_INTENT": ("RECORDED", "QUOTE"),
    "QUOTE": ("OFFERED", "ACCEPTANCE"),
    "ACCEPTANCE": ("ACCEPTED", "DELIVERY"),
    "DELIVERY": ("DELIVERED", "PROCESSOR_REFERENCE"),
}
RECEIPT_KEYS = frozenset({
    "schema_version", "kind", "receipt_id", "offer_id", "stage", "state",
    "source", "evidence", "facts", "next_stage", "cash_claimed",
})
SOURCE_KEYS = frozenset({"path", "sha256", "terms_sha256"})


def _expected_predecessor_facts(stage: str) -> dict[str, Any]:
    facts = base_facts()
    facts.update({
        "purchase_intent": "YES",
        "gguf_control": "YES",
        "harness_ready": "YES",
        "public_contact_url_present": True,
    })
    if stage in {"ACCEPTANCE", "DELIVERY"}:
        facts["legal_acceptance"] = "OWNER_REPORTED"
    if stage == "DELIVERY":
        facts["delivery"] = "OWNER_REPORTED"
    return facts


def _validate_previous_receipt(
    root: Path,
    evidence_root: Path,
    previous: Any,
    expected_stage: str,
    term_hash: str,
    previous_receipt_path: str,
    depth: int = 0,
) -> dict[str, Any]:
    if depth >= len(PREDECESSOR_STATE):
        raise ValueError("previous receipt chain exceeds the bounded stage count")
    if not isinstance(previous, dict) or set(previous) != RECEIPT_KEYS:
        raise ValueError("previous receipt envelope fields mismatch")
    expected_state, expected_next = PREDECESSOR_STATE[expected_stage]
    immutable = {
        "schema_version": "revenue-recovery/v1",
        "kind": "REVENUE_RECOVERY_RECEIPT",
        "offer_id": OFFER_ID,
        "stage": expected_stage,
        "state": expected_state,
        "next_stage": expected_next,
    }
    for field, expected in immutable.items():
        if previous.get(field) != expected:
            raise ValueError(f"previous receipt immutable {field} mismatch")
    receipt_id = previous.get("receipt_id")
    if not isinstance(receipt_id, str) or not SAFE_ID_RE.fullmatch(receipt_id):
        raise ValueError("previous receipt id mismatch")
    source = previous.get("source")
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise ValueError("previous receipt source envelope mismatch")
    if not isinstance(source.get("path"), str) or not source["path"]:
        raise ValueError("previous receipt source path mismatch")
    if not isinstance(source.get("sha256"), str) or not SHA256_RE.fullmatch(source["sha256"]):
        raise ValueError("previous receipt source sha256 mismatch")
    if source.get("terms_sha256") != term_hash:
        raise ValueError("previous receipt terms hash mismatch")
    if not isinstance(previous.get("evidence"), list) or not previous["evidence"]:
        raise ValueError("previous receipt evidence mismatch")
    if previous.get("facts") != _expected_predecessor_facts(expected_stage):
        raise ValueError("previous receipt stage-specific facts mismatch")
    _require_zero_cash_lineage(previous)

    source_path = safe_repo_file(root, source["path"])
    if sha256_file(source_path) != source["sha256"]:
        raise ValueError("previous receipt source sha256 does not match source bytes")
    if expected_stage == "PURCHASE_INTENT":
        source_reference = source["path"]
        if not source_reference.startswith("p/") or not source_reference.endswith(".md"):
            raise ValueError("purchase-intent predecessor must bind a p/<id>.md source")
        inbound_id = source_reference[2:-3]
        if safe_inbound_path(root, inbound_id) != source_path:
            raise ValueError("purchase-intent predecessor source path mismatch")
        reconstructed = purchase_intent_receipt(root, inbound_id)
    else:
        first = previous["evidence"][0]
        if not isinstance(first, dict) or set(first) != {"kind", "reference", "sha256", "status"}:
            raise ValueError("previous receipt lineage evidence envelope mismatch")
        if first.get("kind") != "PREVIOUS_RECEIPT" or first.get("status") != "VERIFIED":
            raise ValueError("previous receipt lineage evidence mismatch")
        prior_reference = first.get("reference")
        prior_digest = first.get("sha256")
        if not isinstance(prior_reference, str) or not isinstance(prior_digest, str) or not SHA256_RE.fullmatch(prior_digest):
            raise ValueError("previous receipt lineage reference mismatch")
        prior_path = safe_repo_file(root, prior_reference)
        if sha256_file(prior_path) != prior_digest:
            raise ValueError("previous receipt lineage sha256 does not match prior bytes")
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        prior_stage = STAGE_CONTRACT[expected_stage]["prior_stage"]
        _validate_previous_receipt(root, evidence_root, prior, prior_stage, term_hash, prior_reference, depth + 1)
        reconstructed = advance_receipt(root, evidence_root, expected_stage, prior_reference, source["path"])
    if previous != reconstructed:
        raise ValueError("previous receipt does not exactly match deterministic source replay")
    return previous


def advance_receipt(
    root: Path,
    evidence_root: Path,
    stage: str,
    previous_receipt_path: str,
    evidence_path: str,
) -> dict[str, Any]:
    """Build a deterministic later-stage receipt from secret-free evidence metadata.

    The referenced quote, signed acceptance, delivery evidence, and processor
    payload stay owner-private. Commons records only opaque references and exact
    hashes. These receipts are owner reports; they are not independent cash proof.
    """
    if stage not in STAGE_CONTRACT:
        raise ValueError("stage must be QUOTE, ACCEPTANCE, DELIVERY, or PROCESSOR_REFERENCE")
    private_root = validate_evidence_root(root, evidence_root)
    _, _, _, term_hash = validate_contract(root)
    previous_path = safe_repo_file(root, previous_receipt_path)
    manifest_path = safe_repo_file(root, evidence_path)
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    if contains_sensitive_value(manifest_text):
        raise ValueError("evidence manifest contains a forbidden sensitive value")
    contract = STAGE_CONTRACT[stage]
    _validate_previous_receipt(root, private_root, previous, contract["prior_stage"], term_hash, previous_receipt_path)
    if manifest.get("schema_version") != "revenue-recovery-evidence/v1" or manifest.get("stage") != stage:
        raise ValueError("evidence manifest contract mismatch")

    evidence = [{
        "kind": "PREVIOUS_RECEIPT",
        "reference": previous_receipt_path.replace("\\", "/"),
        "sha256": sha256_file(previous_path),
        "status": "VERIFIED",
    }]
    facts = dict(previous["facts"])
    if stage == "QUOTE":
        evidence.append(_checked_artifact(root, private_root, manifest.get("artifact"), "QUOTE_ARTIFACT"))
    elif stage == "ACCEPTANCE":
        required_artifacts = (
            ("nda", "SIGNED_NDA"),
            ("sow", "SIGNED_SOW"),
            ("m1", "M1_PAYMENT_REFERENCE"),
        )
        checked_artifacts = [
            _checked_artifact(root, private_root, manifest.get(field), kind)
            for field, kind in required_artifacts
        ]
        nda_at, nda_canonical = _checked_timestamp(manifest["nda"].get("signed_at"), "NDA signed_at")
        sow_at, sow_canonical = _checked_timestamp(manifest["sow"].get("signed_at"), "SOW signed_at")
        m1_at, m1_canonical = _checked_timestamp(manifest["m1"].get("reference_at"), "M1 reference_at")
        if not (nda_at < m1_at and sow_at < m1_at):
            raise ValueError("NDA and SOW signature timestamps must precede the M1 reference timestamp")
        for identity_field in ("reference", "path", "sha256"):
            identities = [manifest[field].get(identity_field) for field, _ in required_artifacts]
            if len(set(identities)) != len(identities):
                raise ValueError(f"NDA, SOW, and M1 evidence {identity_field} values must be distinct")
        for checked, owner_reported_at in zip(checked_artifacts, (nda_canonical, sow_canonical, m1_canonical)):
            checked["owner_reported_at"] = owner_reported_at
        evidence.extend(checked_artifacts)
        facts["legal_acceptance"] = "OWNER_REPORTED"
    elif stage == "DELIVERY":
        tests = manifest.get("acceptance_tests")
        if not isinstance(tests, list) or [row.get("id") for row in tests if isinstance(row, dict)] != [f"AT{i}" for i in range(1, 7)]:
            raise ValueError("delivery requires ordered AT1-AT6 evidence")
        for row in tests:
            if row.get("status") != "PASS":
                raise ValueError("every delivery acceptance test must be PASS")
            checked = _checked_artifact(root, private_root, {
                "kind": "ACCEPTANCE_TEST",
                "reference": row.get("reference"),
                "sha256": row.get("sha256"),
                "path": row.get("path"),
            }, "ACCEPTANCE_TEST")
            checked["kind"] = row["id"]
            evidence.append(checked)
        facts["legal_acceptance"] = "OWNER_REPORTED"
        facts["delivery"] = "OWNER_REPORTED"
    else:
        provider = manifest.get("provider")
        reference = manifest.get("opaque_reference")
        digest = manifest.get("payload_sha256")
        payload_path = manifest.get("payload_path")
        if provider not in {"Stripe", "PayPal"}:
            raise ValueError("processor provider must be Stripe or PayPal")
        if not isinstance(reference, str) or not OPAQUE_REFERENCE_RE.fullmatch(reference) or ".." in reference:
            raise ValueError("processor reference must be opaque")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("processor payload sha256 must be exact")
        if not isinstance(payload_path, str):
            raise ValueError("processor payload path must identify exact local bytes")
        if sha256_file(safe_external_evidence_file(root, private_root, payload_path)) != digest:
            raise ValueError("processor payload sha256 does not match payload bytes")
        evidence.append({"kind": f"{provider.upper()}_REFERENCE", "reference": reference, "sha256": digest, "status": "REFERENCE_ONLY"})
        facts["legal_acceptance"] = "OWNER_REPORTED"
        facts["delivery"] = "OWNER_REPORTED"
        facts["processor_reference"] = "REFERENCE_RECORDED"
        facts["processor_payment"] = "NOT_LANDED"
        facts["payout"] = "NOT_LANDED"
        facts["bank_available"] = "NOT_LANDED"
        facts["cash_evidence"] = "NOT_LANDED"
        facts["collected_cash_usd"] = 0

    manifest_hash = sha256_file(manifest_path)
    previous_hash = sha256_file(previous_path)
    receipt_seed = canonical_json({
        "stage": stage,
        "previous_sha256": previous_hash,
        "manifest_sha256": manifest_hash,
        "terms_sha256": term_hash,
    })
    return {
        "schema_version": "revenue-recovery/v1",
        "kind": "REVENUE_RECOVERY_RECEIPT",
        "receipt_id": f"rr-{stage.lower()}-" + sha256_bytes(receipt_seed)[:24],
        "offer_id": OFFER_ID,
        "stage": stage,
        "state": contract["state"],
        "source": {
            "path": evidence_path.replace("\\", "/"),
            "sha256": manifest_hash,
            "terms_sha256": term_hash,
        },
        "evidence": evidence,
        "facts": facts,
        "next_stage": contract["next_stage"],
        "cash_claimed": False,
    }


def measure(root: Path) -> dict[str, Any]:
    _, recovery, pack_hash, term_hash = validate_contract(root)
    public_path = root / recovery["public_surface"]["path"]
    prospects = json.loads((root / "revenue/payment_ready/prospects.json").read_text(encoding="utf-8"))
    receipt = purchase_intent_receipt(root, None)
    return {
        "kind": "REVENUE_RECOVERY_MEASUREMENT",
        "offer_id": OFFER_ID,
        "pack_sha256": pack_hash,
        "terms_sha256": term_hash,
        "public_surface": "READY" if public_path.is_file() else "MISSING",
        "purchase_intent": receipt["state"],
        "prospects_not_contacted": sum(1 for row in prospects["prospects"] if row["state"] == "PROSPECT_NOT_CONTACTED"),
        "buyer": recovery["truth"]["buyer"],
        "demand": recovery["truth"]["demand"],
        "contact_sent": recovery["truth"]["contact_sent"],
        "collected_cash_usd": recovery["truth"]["collected_cash_usd"],
        "cash_state": recovery["offer"]["cash_state"],
        "cursor_used": recovery["resource_recovery"]["cursor_used_for_this_pipeline"],
    }


def self_test() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    validate_contract(root)
    waiting = purchase_intent_receipt(root, None)
    assert waiting["state"] == "NEEDS_BUYER"
    assert waiting["facts"]["collected_cash_usd"] == 0
    assert waiting["cash_claimed"] is False
    try:
        safe_inbound_path(root, "../escape")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe id was accepted")
    with tempfile.TemporaryDirectory() as tmp:
        container = Path(tmp)
        temp_root = container / "commons"
        evidence_root = container / "private-evidence"
        (temp_root / "revenue/payment_ready").mkdir(parents=True)
        (temp_root / "p").mkdir()
        (temp_root / "receipts").mkdir()
        (temp_root / "evidence").mkdir()
        evidence_root.mkdir()
        for relative in (PACK_PATH, RECOVERY_PATH):
            (temp_root / relative).write_bytes((root / relative).read_bytes())
        post = "\n".join([
            "TO: OFFER", "BOARD: OFFER", f"SUBJECT: {SUBJECT}", "---",
            "PLAIN: Public, non-confidential purchase intent.", f"OFFER_ID: {OFFER_ID}",
            f"TERMS_SHA256: {EXPECTED_TERMS_SHA256}", "PURCHASE_INTENT: YES",
            "GGUF_CONTROL: YES", "HARNESS_READY: YES", "PUBLIC_CONTACT_URL: https://example.com/contact",
        ])
        (temp_root / "p/example.md").write_text(post, encoding="utf-8")
        first = purchase_intent_receipt(temp_root, "example")
        second = purchase_intent_receipt(temp_root, "example")
        assert first == second and first["state"] == "RECORDED"
        assert "example.com" not in json.dumps(first)
        (temp_root / "receipts/intent.json").write_text(json.dumps(first, sort_keys=True), encoding="utf-8")
        quote_bytes = b"self-test quote\n"
        (evidence_root / "quote.bin").write_bytes(quote_bytes)
        quote_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "QUOTE",
            "artifact": {
                "kind": "QUOTE_ARTIFACT",
                "reference": "owner-private:self-test-quote",
                "path": "quote.bin",
                "sha256": sha256_bytes(quote_bytes),
            },
        }
        (temp_root / "evidence/quote.json").write_text(json.dumps(quote_manifest, sort_keys=True), encoding="utf-8")
        quote = advance_receipt(temp_root, evidence_root, "QUOTE", "receipts/intent.json", "evidence/quote.json")
        rendered_quote = json.dumps(quote, sort_keys=True)
        assert "quote.bin" not in rendered_quote and str(evidence_root) not in rendered_quote
        try:
            validate_evidence_root(temp_root, temp_root)
        except ValueError:
            pass
        else:
            raise AssertionError("inside-repo evidence root was accepted")
    return {"kind": "REVENUE_RECOVERY_SELF_TEST", "status": "PASS"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("intent", "advance", "measure"), default="measure")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--inbound-id")
    parser.add_argument("--stage", choices=tuple(STAGE_CONTRACT))
    parser.add_argument("--previous-receipt")
    parser.add_argument("--evidence-json")
    parser.add_argument("--evidence-root")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if args.self_test:
            result = self_test()
        elif args.command == "intent":
            result = purchase_intent_receipt(root, args.inbound_id)
        elif args.command == "advance":
            if not args.stage or not args.previous_receipt or not args.evidence_json or not args.evidence_root:
                raise ValueError("advance requires --stage, --previous-receipt, --evidence-json, and --evidence-root")
            result = advance_receipt(root, Path(args.evidence_root), args.stage, args.previous_receipt, args.evidence_json)
        else:
            result = measure(root)
    except (KeyError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"kind": "REVENUE_RECOVERY_ERROR", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
