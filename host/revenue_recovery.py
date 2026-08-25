#!/usr/bin/env python3
"""Deterministic, secret-free receipts for the GGUF diagnostic revenue lane.

This instrument reads exact Commons artifacts. It never writes by default and it
never upgrades purchase intent into legal acceptance, delivery, payment, or cash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

OFFER_ID = "gguf-diagnostic-10d-12k"
SUBJECT = "GGUF DIAGNOSTIC PURCHASE INTENT"
PACK_PATH = "revenue/payment_ready/pack.json"
RECOVERY_PATH = "revenue/payment_ready/recovery.json"
EXPECTED_TERMS_SHA256 = "1c0756062563415e551587a5f1ab22147366d406135de6c45ccbd3a562985730"

FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]{1,40}):\s*(.*)$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
HTTPS_RE = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
SENSITIVE_PATTERNS = (
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:routing|account)\s*(?:number)?\s*:\s*\d", re.IGNORECASE),
    re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]+\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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


def contains_sensitive_value(text: str) -> bool:
    without_urls = URL_RE.sub("", text)
    return any(pattern.search(without_urls) for pattern in SENSITIVE_PATTERNS)


def base_facts() -> dict[str, Any]:
    return {
        "purchase_intent": "UNKNOWN",
        "gguf_control": "UNKNOWN",
        "harness_ready": "UNKNOWN",
        "public_contact_url_present": False,
        "legal_acceptance": "NOT_LANDED",
        "delivery": "NOT_LANDED",
        "processor_payment": "NOT_LANDED",
        "bank_available": "NOT_LANDED",
        "collected_cash_usd": 0,
    }


def validate_contract(root: Path) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    pack_path = root / PACK_PATH
    recovery_path = root / RECOVERY_PATH
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    term_hash = terms_sha256(pack)
    pack_hash = sha256_file(pack_path)
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
        temp_root = Path(tmp)
        (temp_root / "revenue/payment_ready").mkdir(parents=True)
        (temp_root / "p").mkdir()
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
    return {"kind": "REVENUE_RECOVERY_SELF_TEST", "status": "PASS"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("intent", "measure"), default="measure")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--inbound-id")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = self_test() if args.self_test else (
            purchase_intent_receipt(Path(args.root).resolve(), args.inbound_id)
            if args.command == "intent"
            else measure(Path(args.root).resolve())
        )
    except (KeyError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"kind": "REVENUE_RECOVERY_ERROR", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
