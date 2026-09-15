#!/usr/bin/env python3
"""Fail-closed validator for the Oregon ODA CRM qualification carrier."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_DECISIONS = {"PARTNER", "PRIME_READY", "NO_BID"}
REQUIRED_FALSE_UNTIL_AUTHORIZED = ("submission_authorized", "contact_authorized")


def fail(message: str) -> None:
    raise SystemExit(f"qualification invalid: {message}")


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(str(exc))
    if not isinstance(data, dict):
        fail("root must be an object")
    return data


def all_true(mapping: dict) -> bool:
    return bool(mapping) and all(value is True for value in mapping.values())


def validate(data: dict) -> None:
    if data.get("solicitation_id") != "S-DASOBO-00017788":
        fail("wrong solicitation_id")

    decision = data.get("decision")
    if decision not in ALLOWED_DECISIONS:
        fail(f"decision must be one of {sorted(ALLOWED_DECISIONS)}")

    for key in ("prime_gates", "partner_gates", "scope", "source_safety"):
        if not isinstance(data.get(key), dict):
            fail(f"{key} must be an object")

    if data.get("source_safety", {}).get("secondary_sources_are_controlling") is not False:
        fail("secondary sources must never be controlling")
    if data.get("source_safety", {}).get("secondary_facts_require_buyer_byte_reconciliation") is not True:
        fail("secondary facts must require buyer-byte reconciliation")
    if data.get("source_safety", {}).get("real_buyer_data_allowed_during_pursuit") is not False:
        fail("real buyer data is forbidden during pursuit")

    include = data.get("scope", {}).get("include")
    exclude = data.get("scope", {}).get("exclude")
    if not isinstance(include, list) or len(include) < 4:
        fail("partner scope must contain at least four included deliverables")
    if not isinstance(exclude, list) or len(exclude) < 4:
        fail("partner scope must contain explicit exclusions")

    prime_gates = data["prime_gates"]
    partner_gates = data["partner_gates"]
    prime_ready = data.get("prime_ready") is True

    # A PRIME_READY label is only legal when every prime gate is proven and the
    # machine state agrees. This makes accidental optimistic edits fail CI/local checks.
    if decision == "PRIME_READY":
        if not prime_ready:
            fail("PRIME_READY requires prime_ready=true")
        if not all_true(prime_gates):
            missing = sorted(k for k, v in prime_gates.items() if v is not True)
            fail(f"PRIME_READY with unproven prime gates: {missing}")
        if data.get("planning_deadline_timezone_verified") is not True:
            fail("PRIME_READY requires verified deadline timezone")
        if data.get("controlling_package_hashed") is not True:
            fail("PRIME_READY requires hashed controlling package")
    elif prime_ready:
        fail("prime_ready=true is inconsistent with a non-PRIME_READY decision")

    # PARTNER can remain a capture state with open partner gates, but it may not
    # silently authorize contact/submission. Those actions need explicit later approval.
    if decision == "PARTNER":
        for key in REQUIRED_FALSE_UNTIL_AUTHORIZED:
            if data.get(key) is not False:
                fail(f"PARTNER capture requires {key}=false")

    # If a future edit claims the partner lane is fully ready, these seven gates are
    # the minimum evidence surface. Keeping them explicit prevents scope laundering.
    if data.get("partner_ready") is True and not all_true(partner_gates):
        missing = sorted(k for k, v in partner_gates.items() if v is not True)
        fail(f"partner_ready with unproven partner gates: {missing}")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("qualification.json")
    data = load(path)
    validate(data)
    print(f"OK {data['solicitation_id']} decision={data['decision']} prime_ready={data['prime_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
