#!/usr/bin/env python3
"""Validate and summarize provider-confirmed settled USD cash evidence.

This ledger is intentionally separate from sponsor awards. It records only
provider receipts whose payment state is PAID. It does not infer bank account
availability, withdrawability, processor settlement beyond the provider's own
state, or customer revenue from unrelated offer-specific receipts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SCHEMA_VERSION = "commons-settled-cash/v1"
SUMMARY_SCHEMA_VERSION = "commons-settled-cash-summary/v1"
KIND = "SETTLED_CASH_LEDGER"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
GITHUB_HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
CANONICAL_AMOUNT = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")
FRANTIC_RECEIPT = re.compile(r"^r/[a-f0-9]{8,64}$")
FRANTIC_CLAIM = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
GITHUB_PR_PATH = re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*$")


class CashSettlementError(ValueError):
    """A settled-cash artifact violates the evidence contract."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _reject_constant(value: str) -> None:
    raise CashSettlementError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CashSettlementError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(text: str) -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except CashSettlementError:
        raise
    except json.JSONDecodeError as error:
        raise CashSettlementError(f"invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise CashSettlementError("settled-cash ledger must contain one JSON object")
    return value


def read_ledger(path: Path) -> dict[str, Any]:
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CashSettlementError(f"cannot read {path}: {error}") from error


def _exact_fields(value: Any, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CashSettlementError(f"{where} must be an object")
    if set(value) != expected:
        raise CashSettlementError(f"{where} fields differ from the settled-cash contract")
    return value


def _bounded_text(value: Any, where: str, *, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CashSettlementError(f"{where} must be a non-empty trimmed string")
    if len(value) > limit or any(ord(char) < 32 for char in value):
        raise CashSettlementError(f"{where} is not bounded printable text")
    return value


def _safe_id(value: Any, where: str) -> str:
    text = _bounded_text(value, where, limit=128)
    if SAFE_ID.fullmatch(text) is None:
        raise CashSettlementError(f"{where} must be a lowercase safe identifier")
    return text


def _positive_integer(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise CashSettlementError(f"{where} must be a positive integer")
    return value


def _utc_timestamp(value: Any, where: str) -> datetime:
    text = _bounded_text(value, where, limit=32)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise CashSettlementError(f"{where} must be canonical UTC seconds") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise CashSettlementError(f"{where} must be canonical UTC seconds")
    return parsed


def _amount(value: Any, where: str) -> Decimal:
    if not isinstance(value, str) or CANONICAL_AMOUNT.fullmatch(value) is None:
        raise CashSettlementError(f"{where} must be a canonical positive decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise CashSettlementError(f"{where} must be a canonical positive decimal string") from error
    if not amount.is_finite() or amount <= 0:
        raise CashSettlementError(f"{where} must be greater than zero")
    return amount


def _format_amount(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _public_url(value: Any, where: str, *, host: str, path_pattern: re.Pattern[str]) -> str:
    text = _bounded_text(value, where, limit=300)
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError as error:
        raise CashSettlementError(f"{where} must be a clean public HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or path_pattern.fullmatch(parsed.path) is None
    ):
        raise CashSettlementError(f"{where} must be a clean public HTTPS URL")
    return text


def _provider_url(value: Any, where: str) -> str:
    text = _bounded_text(value, where, limit=64)
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError as error:
        raise CashSettlementError(f"{where} must be the canonical Frantic root") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != "gofrantic.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path != "/"
        or parsed.query
        or parsed.fragment
    ):
        raise CashSettlementError(f"{where} must be the canonical Frantic root")
    return text


def validate_ledger(value: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(value, {"schema_version", "kind", "as_of", "receipts"}, "ledger")
    if value["schema_version"] != SCHEMA_VERSION:
        raise CashSettlementError("unsupported settled-cash schema_version")
    if value["kind"] != KIND:
        raise CashSettlementError("unsupported settled-cash kind")
    as_of = _utc_timestamp(value["as_of"], "as_of")
    receipts = value["receipts"]
    if not isinstance(receipts, list) or not receipts:
        raise CashSettlementError("receipts must be a non-empty list")

    expected = {
        "cash_id",
        "provider",
        "provider_url",
        "bounty_number",
        "program",
        "result_url",
        "claimant",
        "amount_usd",
        "payment_state",
        "evidenced_at",
        "provider_claim_id",
        "provider_receipt_id",
        "idempotency_key",
        "bank_availability_state",
        "withdrawability_state",
        "collection_action",
    }
    seen_cash: set[str] = set()
    seen_claims: set[str] = set()
    seen_receipts: set[str] = set()
    seen_idempotency: set[str] = set()
    order: list[tuple[str, str]] = []

    for index, raw in enumerate(receipts):
        where = f"receipts[{index}]"
        row = _exact_fields(raw, expected, where)
        cash_id = _safe_id(row["cash_id"], f"{where}.cash_id")
        idempotency = _safe_id(row["idempotency_key"], f"{where}.idempotency_key")
        if cash_id in seen_cash:
            raise CashSettlementError(f"duplicate cash_id: {cash_id}")
        if idempotency in seen_idempotency:
            raise CashSettlementError(f"duplicate idempotency_key: {idempotency}")
        seen_cash.add(cash_id)
        seen_idempotency.add(idempotency)

        if row["provider"] != "Frantic":
            raise CashSettlementError(f"{where}.provider is unsupported")
        _provider_url(row["provider_url"], f"{where}.provider_url")
        _positive_integer(row["bounty_number"], f"{where}.bounty_number")
        _bounded_text(row["program"], f"{where}.program", limit=120)
        _public_url(
            row["result_url"],
            f"{where}.result_url",
            host="github.com",
            path_pattern=GITHUB_PR_PATH,
        )
        claimant = _bounded_text(row["claimant"], f"{where}.claimant", limit=39)
        if GITHUB_HANDLE.fullmatch(claimant) is None:
            raise CashSettlementError(f"{where}.claimant must be a GitHub handle")
        _amount(row["amount_usd"], f"{where}.amount_usd")
        if row["payment_state"] != "PAID":
            raise CashSettlementError(f"{where}.payment_state must be PAID")
        evidenced_at = _utc_timestamp(row["evidenced_at"], f"{where}.evidenced_at")
        if evidenced_at > as_of:
            raise CashSettlementError(f"{where}.evidenced_at is later than ledger as_of")
        order.append((row["evidenced_at"], cash_id))

        claim_id = _bounded_text(row["provider_claim_id"], f"{where}.provider_claim_id", limit=36)
        if FRANTIC_CLAIM.fullmatch(claim_id) is None:
            raise CashSettlementError(f"{where}.provider_claim_id must be a Frantic UUID")
        if claim_id in seen_claims:
            raise CashSettlementError(f"duplicate provider_claim_id: {claim_id}")
        seen_claims.add(claim_id)

        receipt_id = _bounded_text(row["provider_receipt_id"], f"{where}.provider_receipt_id", limit=66)
        if FRANTIC_RECEIPT.fullmatch(receipt_id) is None:
            raise CashSettlementError(f"{where}.provider_receipt_id must be a Frantic receipt id")
        if receipt_id in seen_receipts:
            raise CashSettlementError(f"duplicate provider_receipt_id: {receipt_id}")
        seen_receipts.add(receipt_id)

        if row["bank_availability_state"] != "NOT_ASSERTED":
            raise CashSettlementError(f"{where}.bank_availability_state must remain NOT_ASSERTED")
        if row["withdrawability_state"] != "NOT_ASSERTED":
            raise CashSettlementError(f"{where}.withdrawability_state must remain NOT_ASSERTED")
        if row["collection_action"] != "NONE_DO_NOT_RESEND":
            raise CashSettlementError(f"{where}.collection_action must remain NONE_DO_NOT_RESEND")

    if order != sorted(order):
        raise CashSettlementError("receipts must be ordered by evidenced_at then cash_id")
    return value


def summarize_ledger(value: dict[str, Any]) -> dict[str, Any]:
    validate_ledger(value)
    total = Decimal(0)
    public: list[dict[str, Any]] = []
    for row in value["receipts"]:
        total += Decimal(row["amount_usd"])
        public.append(
            {
                "cash_id": row["cash_id"],
                "provider": row["provider"],
                "provider_url": row["provider_url"],
                "bounty_number": row["bounty_number"],
                "program": row["program"],
                "result_url": row["result_url"],
                "claimant": row["claimant"],
                "amount_usd": row["amount_usd"],
                "payment_state": row["payment_state"],
                "evidenced_at": row["evidenced_at"],
                "provider_receipt_id": row["provider_receipt_id"],
                "bank_availability_state": row["bank_availability_state"],
                "withdrawability_state": row["withdrawability_state"],
                "collection_action": row["collection_action"],
            }
        )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "as_of": value["as_of"],
        "settled_receipts": len(public),
        "settled_usd": _format_amount(total),
        "bank_availability_asserted": False,
        "withdrawability_asserted": False,
        "receipts": public,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "summary"))
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        value = read_ledger(args.ledger)
        summary = summarize_ledger(value)
        if args.command == "summary":
            sys.stdout.write(canonical_text(summary))
        else:
            print(
                f"VALID {summary['settled_receipts']} settled receipt(s) · "
                f"USD {summary['settled_usd']} PAID · bank availability and "
                "withdrawability not asserted"
            )
    except CashSettlementError as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
