from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATES = {"PAID", "HOLD_SPONSOR_ADJUDICATION", "HOLD_SPONSOR_AUTH", "WAIT_SPONSOR"}


class ValidationError(ValueError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def dec(value):
    if not isinstance(value, str):
        fail("amounts must be strings")
    try:
        result = Decimal(value)
    except InvalidOperation:
        fail("invalid decimal")
    if not result.is_finite() or result < 0:
        fail("invalid amount")
    return result


def validate(doc):
    if not isinstance(doc, dict) or doc.get("schema") != "open-pr-cash-claim-recovery/v1":
        fail("schema")
    authority = doc.get("authority")
    if not isinstance(authority, dict):
        fail("authority")
    for key in (
        "new_outbound_authorized",
        "cash_or_revenue_recognition_computed",
        "merge_implies_award",
        "cross_denomination_conversion_authorized",
    ):
        if authority.get(key) is not False:
            fail(f"{key} must be false")
    if authority.get("last_inch_external_mutation_requires_muse") is not True:
        fail("Muse fence")

    rows = doc.get("rows")
    if not isinstance(rows, list) or len(rows) != 5:
        fail("five canonical rows required")
    seen = set()
    paid = {}
    ready = 0
    for row in rows:
        if not isinstance(row, dict):
            fail("row")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            fail("row id")
        seen.add(rid)
        state = row.get("settlement_state")
        if state not in STATES:
            fail(f"{rid}: state")
        if row.get("new_outbound_authorized") is not False:
            fail(f"{rid}: outbound must remain false")
        if row.get("next_action") == "READY_FOR_MUSE":
            ready += 1

        private = row.get("private_evidence")
        if private is not None:
            if (
                not isinstance(private, dict)
                or not str(private.get("ref", "")).startswith("private:")
                or not HEX64.fullmatch(str(private.get("sha256", "")))
            ):
                fail(f"{rid}: private evidence")

        advertised = row.get("advertised")
        awarded = row.get("awarded")
        paid_claim = row.get("paid")
        if state == "PAID":
            if row.get("proof_level") != "SPONSOR_PAYMENT_CONFIRMATION":
                fail(f"{rid}: paid proof")
            if not isinstance(awarded, dict) or not isinstance(paid_claim, dict):
                fail(f"{rid}: award/payment required")
            if private is None:
                fail(f"{rid}: sponsor private evidence required")
            for claim in (awarded, paid_claim):
                dec(claim.get("amount"))
                if claim.get("denomination") not in {"USD", "RTC"}:
                    fail(f"{rid}: denomination")
            if (awarded["denomination"], awarded["amount"]) != (
                paid_claim["denomination"],
                paid_claim["amount"],
            ):
                fail(f"{rid}: paid must match sponsor award in snapshot")
            denomination = paid_claim["denomination"]
            paid[denomination] = paid.get(denomination, Decimal("0")) + dec(
                paid_claim["amount"]
            )
        else:
            if awarded is not None or paid_claim is not None:
                fail(f"{rid}: nonpaid row cannot claim award/payment")

        if advertised is not None:
            dec(advertised.get("amount"))
            if advertised.get("truth") not in {"ADVERTISED", "ADVERTISED_LOW_TIER"}:
                fail(f"{rid}: advertised truth")

        proposed = row.get("proposed_by_us")
        if proposed is not None:
            dec(proposed.get("amount"))
            if proposed.get("truth") != "PROPOSED_BY_US_NOT_ADVERTISED":
                fail(f"{rid}: proposal truth")
            if advertised is not None or awarded is not None or paid_claim is not None:
                fail(f"{rid}: proposal amplified")

        contact = row.get("contact")
        if not isinstance(contact, dict) or not isinstance(contact.get("human_reply_count"), int):
            fail(f"{rid}: contact")
        if paid_claim and paid_claim["denomination"] == "RTC" and (
            "usd_equivalent" in paid_claim or "usd_value" in row
        ):
            fail(f"{rid}: RTC conversion forbidden")

    expected = {"USD": "1.00", "RTC": "25"}
    actual = {key: format(value, "f") for key, value in paid.items()}
    if actual != expected:
        fail(f"paid totals {actual}")
    summary = doc.get("summary")
    if summary != {
        "rows": 5,
        "paid_rows": 2,
        "nonpaid_rows": 3,
        "paid_by_denomination": expected,
        "ready_for_muse_rows": 0,
    }:
        fail("summary drift")
    if ready != 0:
        fail("snapshot has no outbound-ready row")
    return {"valid": True, "rows": 5, "paid_by_denomination": expected}


def load(path=ROOT / "ledger.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(validate(load()), sort_keys=True))
