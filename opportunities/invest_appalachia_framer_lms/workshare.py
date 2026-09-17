from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "invest_appalachia_framer_lms.partner_workshare.v1"
OPPORTUNITY_ID = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
QUALIFICATION_GENERATION_SHA256 = "13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
WORKSHARE_SHA256 = "9825e29c23028dffb23158f7b1db8fb751ba45c0ecedad681764d77bc5ac3b4d"
PRICE_USD = 24000
BUYER_CAP_USD = 60000

class WorkshareError(ValueError):
    pass

def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise WorkshareError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out

def _reject_constant(token: str) -> Any:
    raise WorkshareError(f"invalid JSON constant: {token}")

def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise WorkshareError(f"cannot canonicalize: {exc}") from exc

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()

def load_json(path: Path) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
        canonical_json(value)
        return value
    except WorkshareError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError, OverflowError) as exc:
        raise WorkshareError(f"invalid JSON: {exc}") from exc

def _exact(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise WorkshareError(f"{where}: exact object contract mismatch")
    return value

def validate_qualification_generation(current_packet: Any) -> None:
    if digest(current_packet) != QUALIFICATION_GENERATION_SHA256:
        raise WorkshareError("qualification generation changed; workshare requires review")

def validate_workshare(value: Any) -> dict[str, Any]:
    if digest(value) != WORKSHARE_SHA256:
        raise WorkshareError("workshare does not match reviewed commercial generation")
    ws = _exact(value, {
        "schema", "opportunity_id", "qualification_generation_sha256", "commercial",
        "scope", "excludes", "qualified_prime_must_own", "single_writer_gate", "authority",
    }, "workshare")
    if ws["schema"] != SCHEMA or ws["opportunity_id"] != OPPORTUNITY_ID:
        raise WorkshareError("workshare identity mismatch")
    if ws["qualification_generation_sha256"] != QUALIFICATION_GENERATION_SHA256:
        raise WorkshareError("qualification-generation binding mismatch")

    commercial = _exact(ws["commercial"], {"price_usd", "commercial_status", "buyer_budget_integration_state"}, "commercial")
    if commercial != {
        "price_usd": PRICE_USD,
        "commercial_status": "PROPOSED_NOT_ACCEPTED",
        "buyer_budget_integration_state": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
    }:
        raise WorkshareError("commercial truth mismatch")

    gate = _exact(ws["single_writer_gate"], {
        "fresh_opportunity_and_route_census_required", "muse_dm_clearance_required", "maximum_external_messages_if_cleared",
    }, "single_writer_gate")
    if gate != {
        "fresh_opportunity_and_route_census_required": True,
        "muse_dm_clearance_required": True,
        "maximum_external_messages_if_cleared": 1,
    }:
        raise WorkshareError("single-writer gate mismatch")

    authority = _exact(ws["authority"], {
        "partner_contact_authorized", "buyer_contact_authorized", "submission_authorized",
        "signature_authorized", "contract_acceptance_authorized", "payment_authorized", "award_or_revenue_asserted",
    }, "authority")
    if any(item is not False for item in authority.values()):
        raise WorkshareError("external/commercial authority must remain all false")
    return ws

def evaluate(current_packet: Any, workshare: Any) -> dict[str, Any]:
    validate_qualification_generation(current_packet)
    ws = validate_workshare(workshare)
    receipt = {
        "schema": "invest_appalachia_framer_lms.partner_workshare_receipt.v1",
        "opportunity_id": OPPORTUNITY_ID,
        "qualification_generation_sha256": QUALIFICATION_GENERATION_SHA256,
        "workshare_sha256": WORKSHARE_SHA256,
        "prime_posture": "NO_CHANGE_PRIME_HOLD",
        "workshare_posture": "READY_FOR_INTERNAL_QUALIFIED_PRIME_SELECTION",
        "specialist_price_usd": PRICE_USD,
        "buyer_budget_cap_usd": BUYER_CAP_USD,
        "buyer_budget_fit": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
        "commercial_status": "PROPOSED_NOT_ACCEPTED",
        "money_state": "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE",
        "fresh_opportunity_and_route_census_required": True,
        "muse_dm_clearance_required": True,
        "maximum_external_messages_if_cleared": 1,
        **{key: False for key in ws["authority"]},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-packet", required=True, type=Path)
    parser.add_argument("--workshare", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(load_json(args.current_packet), load_json(args.workshare)), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
