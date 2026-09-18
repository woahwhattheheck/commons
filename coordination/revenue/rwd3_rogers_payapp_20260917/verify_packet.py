#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PUBLIC_PATH = HERE / "public_facts.json"
HANDOFF_PATH = HERE / "owner_handoff.json"
MAX_BYTES = 262_144

OP = "RWD3-ROGERS-PAYAPP-RETAINAGE-OWNER-PACKET-ZSOL-20260917"
SOURCES = (
    "https://rwd3rogers.com/agenda-and-minutes",
    "https://rwd3rogers.com/personnel",
    "https://rwd3rogers.com/contact-us",
)
AGENDA = (
    ("RWD3-KEETONVILLE-TANK", "Crossland Heavy Contractors, Inc.", "1", 12290625, False, False),
    ("RWD3-TACORA-WTP-PUMP", "Beytco, Inc.", "5-Final", 3576203, True, True),
    ("RWD3-TACORA-MB-II", "Cunningham Construction", "3", 15281933, False, False),
    ("RWD3-GARDNER-POND-WATER-LINE", "King Excavating, Inc.", "2-Final", 3352381, True, True),
)
CANDIDATES = (
    ("RWD3-TACORA-WTP-PR5-FINAL", "RWD3-TACORA-WTP-PUMP", "5-Final", 3576203),
    ("RWD3-GARDNER-POND-PR2-FINAL", "RWD3-GARDNER-POND-WATER-LINE", "2-Final", 3352381),
)
REQUIRED_INPUTS = (
    "COMPLETE_SCHEDULE_OF_VALUES",
    "CURRENT_WORK_EVIDENCE",
    "APPROVED_CHANGE_ORDER_EVIDENCE",
    "PRIOR_CERTIFICATION_EVIDENCE",
    "PRIOR_PAYMENT_EVIDENCE",
    "PREDECESSOR_LINEAGE_EVIDENCE",
    "RETAINAGE_POLICY_EVIDENCE",
    "SOV_LINE_COUNT",
    "COMBINED_APPLICATION_EVIDENCE_PAYMENT_ROW_COUNT",
)

class PacketError(ValueError):
    pass

def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PacketError(f"duplicate JSON key: {key}")
        out[key] = value
    return out

def _reject_float(_: str) -> None:
    raise PacketError("floats are forbidden")

def _reject_constant(value: str) -> None:
    raise PacketError(f"non-finite JSON number is forbidden: {value}")

def load(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise PacketError(f"symlink input forbidden: {path.name}")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise PacketError(f"input too large: {path.name}")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise PacketError(f"input too large: {path.name}")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except PacketError:
        raise
    except Exception as exc:
        raise PacketError(f"invalid JSON {path.name}: {exc}") from exc
    if type(value) is not dict:
        raise PacketError(f"top level must be object: {path.name}")
    return value

def exact_keys(obj: Any, expected: set[str], where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise PacketError(f"{where}: expected object")
    actual = set(obj)
    if actual != expected:
        raise PacketError(
            f"{where}: keys mismatch missing={sorted(expected-actual)} unknown={sorted(actual-expected)}"
        )
    return obj

def exact(value: Any, typ: type, where: str) -> Any:
    if type(value) is not typ:
        raise PacketError(f"{where}: expected exact {typ.__name__}")
    return value

def all_false(obj: Any, expected: set[str], where: str) -> None:
    row = exact_keys(obj, expected, where)
    for key in sorted(expected):
        if exact(row[key], bool, f"{where}.{key}") is not False:
            raise PacketError(f"{where}.{key}: must remain false")

def validate_public(p: dict[str, Any]) -> None:
    exact_keys(
        p,
        {"schema_version","operation_id","observed_on","source_urls","district","agenda_items","assertions","authority"},
        "public",
    )
    if exact(p["schema_version"], int, "public.schema_version") != 1:
        raise PacketError("public schema")
    if exact(p["operation_id"], str, "public.operation_id") != OP:
        raise PacketError("public operation")
    if exact(p["observed_on"], str, "public.observed_on") != "2026-09-17":
        raise PacketError("public observation date drift")
    urls = exact(p["source_urls"], list, "public.source_urls")
    if tuple(urls) != SOURCES or any(type(item) is not str for item in urls):
        raise PacketError("public source drift")
    district = exact_keys(
        p["district"],
        {"name","district_manager","contact_surface_class"},
        "public.district",
    )
    if district != {
        "name": "Rural Water District #3 Rogers County",
        "district_manager": "Kelly King",
        "contact_surface_class": "GENERAL_PUBLIC_CONTACT_SURFACE_NOT_SELECTED",
    }:
        raise PacketError("district truth drift")

    items = exact(p["agenda_items"], list, "public.agenda_items")
    if len(items) != 4:
        raise PacketError("agenda item count")
    got: list[tuple[Any, ...]] = []
    for index, item in enumerate(items):
        row = exact_keys(
            item,
            {"project_ref","contractor","pay_request","amount_minor_usd","final","retainage_release_explicit"},
            f"agenda[{index}]",
        )
        got.append((
            exact(row["project_ref"], str, "project_ref"),
            exact(row["contractor"], str, "contractor"),
            exact(row["pay_request"], str, "pay_request"),
            exact(row["amount_minor_usd"], int, "amount_minor_usd"),
            exact(row["final"], bool, "final"),
            exact(row["retainage_release_explicit"], bool, "retainage_release_explicit"),
        ))
    if tuple(got) != AGENDA:
        raise PacketError("agenda truth drift")

    assertions = exact_keys(
        p["assertions"],
        {
            "two_final_retainage_release_items_observed","defect_observed","buyer_need_observed",
            "budget_observed","savings_observed","intent_to_buy_observed"
        },
        "public.assertions",
    )
    if exact(
        assertions["two_final_retainage_release_items_observed"],
        bool,
        "public.assertions.two_final_retainage_release_items_observed",
    ) is not True:
        raise PacketError("retainage observation must be true")
    for key in ("defect_observed","buyer_need_observed","budget_observed","savings_observed","intent_to_buy_observed"):
        if exact(assertions[key], bool, f"public.assertions.{key}") is not False:
            raise PacketError(f"unsupported commercial assertion: {key}")

    all_false(
        p["authority"],
        {
            "buyer_selected","route_selected","muse_requested","outbound_contact",
            "provider_mutation","contract_acceptance","payment","revenue"
        },
        "public.authority",
    )

def validate_handoff(h: dict[str, Any]) -> None:
    exact_keys(
        h,
        {
            "schema_version","operation_id","product","candidate_scopes","scope_policy",
            "required_owner_inputs_before_fixed_scope_review","external_action_state",
            "customer_surface_url","commercial_claims_observed"
        },
        "handoff",
    )
    if exact(h["schema_version"], int, "handoff.schema_version") != 1:
        raise PacketError("handoff schema")
    if exact(h["operation_id"], str, "handoff.operation_id") != OP:
        raise PacketError("handoff operation")

    product = exact_keys(
        h["product"],
        {"repository","carrier_pr","name","offer_status","price_minor_usd","target_business_days","scope"},
        "handoff.product",
    )
    if product != {
        "repository":"woahwhattheheck/smb-showcase-inventory",
        "carrier_pr":1043,
        "name":"Pay Application + Retainage Sprint",
        "offer_status":"PROPOSED_NOT_ACCEPTED",
        "price_minor_usd":1250000,
        "target_business_days":10,
        "scope":"ONE_LEGAL_ENTITY_ONE_PROJECT_ONE_PAY_CYCLE",
    }:
        raise PacketError("product truth drift")

    scopes = exact(h["candidate_scopes"], list, "handoff.candidate_scopes")
    if len(scopes) != 2:
        raise PacketError("candidate count")
    got: list[tuple[Any, ...]] = []
    for index, scope in enumerate(scopes):
        row = exact_keys(
            scope,
            {"candidate_id","project_ref","public_pay_request","public_amount_minor_usd","public_retainage_release_explicit"},
            f"candidate[{index}]",
        )
        if exact(
            row["public_retainage_release_explicit"],
            bool,
            f"candidate[{index}].public_retainage_release_explicit",
        ) is not True:
            raise PacketError("candidate must be an explicit retainage-release item")
        got.append((
            exact(row["candidate_id"], str, "candidate_id"),
            exact(row["project_ref"], str, "project_ref"),
            exact(row["public_pay_request"], str, "public_pay_request"),
            exact(row["public_amount_minor_usd"], int, "public_amount_minor_usd"),
        ))
    if tuple(got) != CANDIDATES:
        raise PacketError("candidate truth drift")

    policy = exact_keys(
        h["scope_policy"],
        {"must_not_combine_projects","selected_candidate"},
        "handoff.scope_policy",
    )
    if exact(policy["must_not_combine_projects"], bool, "must_not_combine_projects") is not True:
        raise PacketError("projects must remain separate fixed scopes")
    if policy["selected_candidate"] is not None:
        raise PacketError("candidate must remain unselected")

    required = exact(
        h["required_owner_inputs_before_fixed_scope_review"],
        list,
        "required_owner_inputs_before_fixed_scope_review",
    )
    if tuple(required) != REQUIRED_INPUTS or any(type(item) is not str for item in required):
        raise PacketError("required owner input drift")
    if exact(h["external_action_state"], str, "external_action_state") != "NOT_SELECTED_OR_AUTHORIZED":
        raise PacketError("external action state escalated")
    if h["customer_surface_url"] is not None:
        raise PacketError("customer surface must remain unset")
    all_false(
        h["commercial_claims_observed"],
        {"error","savings","buyer_need","budget","urgency","intent_to_buy"},
        "handoff.commercial_claims_observed",
    )

def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

def compile_receipt(public: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    validate_public(public)
    validate_handoff(handoff)
    return {
        "schema_version": 1,
        "operation_id": OP,
        "status": "OWNER_PACKET_READY_NO_OUTBOUND",
        "public_facts_sha256": hashlib.sha256(canonical(public)).hexdigest(),
        "owner_handoff_sha256": hashlib.sha256(canonical(handoff)).hexdigest(),
        "candidate_count": 2,
        "selected_candidate": None,
        "external_action_state": "NOT_SELECTED_OR_AUTHORIZED",
        "payment_or_revenue": False,
    }

def main() -> int:
    try:
        public = load(PUBLIC_PATH)
        handoff = load(HANDOFF_PATH)
        print(json.dumps(compile_receipt(public,handoff),sort_keys=True,separators=(",",":")))
        return 0
    except PacketError as exc:
        print(json.dumps({"ok":False,"error":str(exc)},sort_keys=True,separators=(",",":")))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
