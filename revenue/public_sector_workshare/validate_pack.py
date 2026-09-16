from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PACK_SCHEMA = "tjl-public-sector-workshare-pack/v1"
OVERLAY_SCHEMA = "tjl-public-sector-workshare-overlay/v1"
COMMERCIAL_TRUTH = "PROPOSED_NOT_ACCEPTED"
MODULE_IDS = {
    "MIGRATION_EVIDENCE",
    "INTEGRATION_CONFORMANCE",
    "UAT_ACCEPTANCE_EVIDENCE",
    "CUTOVER_REPLAY",
}

class ContractError(ValueError):
    pass


def _load(path: Path) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ContractError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ContractError(f"non-finite JSON value: {x}")))


def _exact_bool(value: Any, label: str) -> None:
    if type(value) is not bool:
        raise ContractError(f"{label} must be bool")


def _nonempty_strings(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value or any(type(v) is not str or not v.strip() for v in value):
        raise ContractError(f"{label} must be a non-empty string list")


def collision_key(opportunity_id: str, target_company: str, route: str) -> str:
    values = (opportunity_id, target_company, route)
    if any(type(v) is not str or not v.strip() for v in values):
        raise ContractError("collision-key values must be non-empty strings")
    canonical = "\n".join(v.strip().lower() for v in values)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_pack(pack: dict[str, Any]) -> None:
    required = {
        "schema","operation","owner_seat","model_family","commercial_truth",
        "buyer_acceptance_asserted","award_asserted","payment_asserted",
        "recognized_revenue_asserted","modules","offers","coordination_contract",
        "proof_refs","authority_ceiling",
    }
    if set(pack) != required:
        raise ContractError(f"pack keys mismatch: {sorted(set(pack) ^ required)}")
    if pack["schema"] != PACK_SCHEMA:
        raise ContractError("wrong pack schema")
    if pack["commercial_truth"] != COMMERCIAL_TRUTH:
        raise ContractError("commercial truth drift")
    for key in ("buyer_acceptance_asserted","award_asserted","payment_asserted","recognized_revenue_asserted"):
        _exact_bool(pack[key], key)
        if pack[key]:
            raise ContractError(f"{key} must remain false absent provider evidence")
    modules = pack["modules"]
    if not isinstance(modules, list) or len(modules) != 4:
        raise ContractError("exactly four modules required")
    seen = set()
    for module in modules:
        expected = {"id","name","required_inputs","outputs","acceptance_tests","exclusions"}
        if not isinstance(module, dict) or set(module) != expected:
            raise ContractError("module keys mismatch")
        mid = module["id"]
        if mid in seen or mid not in MODULE_IDS:
            raise ContractError(f"invalid/duplicate module id: {mid}")
        seen.add(mid)
        for key in ("required_inputs","outputs","acceptance_tests","exclusions"):
            _nonempty_strings(module[key], f"module {mid} {key}")
    if seen != MODULE_IDS:
        raise ContractError("module coverage incomplete")
    offers = pack["offers"]
    if not isinstance(offers, list) or len(offers) < 2:
        raise ContractError("pilot and implementation offers required")
    offer_ids = set()
    for offer in offers:
        expected = {"id","status","price_usd","duration_weeks_min","duration_weeks_max","scope","excludes"}
        if not isinstance(offer, dict) or set(offer) != expected:
            raise ContractError("offer keys mismatch")
        if offer["id"] in offer_ids:
            raise ContractError("duplicate offer id")
        offer_ids.add(offer["id"])
        if offer["status"] != COMMERCIAL_TRUTH:
            raise ContractError("offer status must remain PROPOSED_NOT_ACCEPTED")
        if type(offer["price_usd"]) is not int or offer["price_usd"] <= 0:
            raise ContractError("offer price must be a positive integer USD hypothesis")
        for key in ("duration_weeks_min","duration_weeks_max"):
            if type(offer[key]) is not int or offer[key] <= 0:
                raise ContractError("duration must be positive integer weeks")
        if offer["duration_weeks_min"] > offer["duration_weeks_max"]:
            raise ContractError("duration range inverted")
        _nonempty_strings(offer["excludes"], "offer excludes")
    cc = pack["coordination_contract"]
    expected_cc = {"single_writer_key_formula","required_pre_send_observations","ambiguous_provider_outcome","send_log_fields","security_authority_created","note"}
    if not isinstance(cc, dict) or set(cc) != expected_cc:
        raise ContractError("coordination contract keys mismatch")
    if cc["ambiguous_provider_outcome"] != "DNR_RECONCILE_NEVER_RESEND":
        raise ContractError("ambiguous provider outcome must fail duplicate-send closed")
    _exact_bool(cc["security_authority_created"], "security_authority_created")
    if cc["security_authority_created"]:
        raise ContractError("coordination may not create auth/permission authority")
    _nonempty_strings(cc["required_pre_send_observations"], "pre-send observations")
    _nonempty_strings(cc["send_log_fields"], "send-log fields")
    if not isinstance(pack["proof_refs"], list) or len(pack["proof_refs"]) < 3:
        raise ContractError("proof refs incomplete")
    _nonempty_strings(pack["authority_ceiling"], "authority ceiling")


def validate_overlay(overlay: dict[str, Any], pack: dict[str, Any]) -> None:
    common = {
        "schema","opportunity_id","buyer","solicitation_id","state","primary_source",
        "source_checked_utc","deadline_local","deadline_timezone","prime_owned",
        "workshare_modules","workshare_wedge","qualification_truth","target_archetypes",
        "named_target_status","commercial_offer_ids","outbound_authorized_by_overlay",
        "submission_authorized","buyer_budget_usd","award_asserted","payment_asserted",
    }
    allowed_extra = {"subcontract_structure_evidence"}
    keys = set(overlay)
    if not common.issubset(keys) or keys - common - allowed_extra:
        raise ContractError(f"overlay keys mismatch: {sorted(keys ^ common)}")
    if overlay["schema"] != OVERLAY_SCHEMA:
        raise ContractError("wrong overlay schema")
    if overlay["state"] != "OPEN_CAPTURE_PARTNER_FIRST":
        raise ContractError("overlay must remain partner-first capture")
    if overlay["qualification_truth"] != "PARTNER_FIRST_NOT_PRIME_ASSERTION":
        raise ContractError("prime-readiness drift")
    if overlay["buyer_budget_usd"] is not None:
        raise ContractError("buyer budget is unknown in this carrier")
    for key in ("outbound_authorized_by_overlay","submission_authorized","award_asserted","payment_asserted"):
        _exact_bool(overlay[key], key)
        if overlay[key]:
            raise ContractError(f"{key} must remain false")
    _nonempty_strings(overlay["prime_owned"], "prime_owned")
    _nonempty_strings(overlay["target_archetypes"], "target_archetypes")
    mods = overlay["workshare_modules"]
    _nonempty_strings(mods, "workshare_modules")
    if set(mods) - MODULE_IDS:
        raise ContractError("overlay references unknown workshare module")
    offer_ids = {o["id"] for o in pack["offers"]}
    _nonempty_strings(overlay["commercial_offer_ids"], "commercial_offer_ids")
    if set(overlay["commercial_offer_ids"]) - offer_ids:
        raise ContractError("overlay references unknown offer")
    if not str(overlay["primary_source"]).startswith("https://"):
        raise ContractError("primary source must be HTTPS")


def validate_tree(root: Path) -> dict[str, Any]:
    pack = _load(root / "pack.json")
    if not isinstance(pack, dict):
        raise ContractError("pack must be an object")
    validate_pack(pack)
    overlay_paths = sorted((root / "overlays").glob("*.json"))
    live = [p for p in overlay_paths if p.name != "EXISTING_MERGED_QUALIFICATIONS.json"]
    if {p.name for p in live} != {
        "IL_DOIT_CDB_27_448DOIT_ADMIN_B_52519.json",
        "NC_DHHS_DHB_30_2025_037_DHB.json",
    }:
        raise ContractError("expected exactly the two still-missing live overlays")
    for path in live:
        overlay = _load(path)
        if not isinstance(overlay, dict):
            raise ContractError("overlay must be an object")
        validate_overlay(overlay, pack)
    refs = _load(root / "overlays" / "EXISTING_MERGED_QUALIFICATIONS.json")
    if refs.get("schema") != "tjl-public-sector-existing-qualification-refs/v1":
        raise ContractError("existing-ref schema mismatch")
    expected = {("OR-ODA-S-DASOBO-00017788", 13907), ("NYSED-RFP-144-OCUE", 13547)}
    actual = {(r.get("opportunity_id"), r.get("pr")) for r in refs.get("refs", [])}
    if actual != expected:
        raise ContractError("existing qualification refs drift")
    return {"schema": pack["schema"], "modules": sorted(MODULE_IDS), "overlays": [p.name for p in live], "offers": [o["id"] for o in pack["offers"]]}


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    print(json.dumps(validate_tree(here), sort_keys=True))
