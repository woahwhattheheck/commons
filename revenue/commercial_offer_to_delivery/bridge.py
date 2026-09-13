from __future__ import annotations

import copy
import hashlib
from decimal import Decimal
from typing import Any, Callable, Mapping

from .contract import ContractVerifier
from .primitives import (
    BRIDGE_KIND, MAX_SHORT, REFUND_CHOICE, SCHEMA_VERSION, SCOPE_ACCEPTANCE_ATTESTATION,
    SCOPE_KIND, SCOPE_SCHEMA, BridgeError, canonical, decimal_amount, digest, exact, fail,
    identifier, load_json_strict, scope_identifier, sha, text,
)
from .verification import create_operator_verification, verify_operator_verification

AgreementValidator = Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]


def default_agreement_validator(agreement: Mapping[str, Any], catalog: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        from host.scope_to_delivery import validate_agreement
    except Exception as exc:  # pragma: no cover
        raise BridgeError("scope-to-delivery validator is unavailable") from exc
    try:
        return validate_agreement(copy.deepcopy(dict(agreement)), copy.deepcopy(dict(catalog)))
    except Exception as exc:
        raise BridgeError(f"scope-to-delivery compatibility failed: {exc}") from exc


def catalog_quote(catalog: Mapping[str, Any], sku_id: str) -> tuple[str, Decimal]:
    if type(catalog) is not dict or type(catalog.get("listings")) is not list:
        fail("catalog.listings must be a list")
    matches = [item for item in catalog["listings"] if type(item) is dict and item.get("id") == sku_id]
    if len(matches) != 1:
        fail("sku_id must resolve to exactly one canonical catalog listing")
    pricing = matches[0].get("pricing")
    if type(pricing) is not dict or pricing.get("currency") != "USD":
        fail("v1 bridge supports only USD catalog listings")
    components = pricing.get("components")
    if type(components) is not list or not components:
        fail("catalog listing requires pricing components")
    total = Decimal("0.00")
    for i, component in enumerate(components):
        if type(component) is not dict:
            fail(f"catalog pricing component {i} is invalid")
        if "amount" in component:
            total += decimal_amount(component["amount"], f"catalog.components[{i}].amount")
        elif "unit_amount" in component:
            total += decimal_amount(component["unit_amount"], f"catalog.components[{i}].unit_amount")
        else:
            fail(f"catalog pricing component {i} has no amount")
    return "USD", total


def scope_buyer_ref(raw_buyer_ref: str) -> str:
    value = hashlib.sha256(("commercial-offer-buyer-v1\0" + raw_buyer_ref).encode()).hexdigest()
    return "buyer_" + value


def acceptance_rows(offer: Mapping[str, Any], offer_sha256: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(offer["deliverables"]):
        item = exact(raw, {"id", "title", "acceptance_criteria", "evidence_sha256"}, f"offer.deliverables[{i}]")
        did = identifier(item["id"], f"offer.deliverables[{i}].id")
        title = text(item["title"], f"offer.deliverables[{i}].title", max_len=MAX_SHORT)
        criteria = text(item["acceptance_criteria"], f"offer.deliverables[{i}].acceptance_criteria")
        evidence_sha = sha(item["evidence_sha256"], f"offer.deliverables[{i}].evidence_sha256")
        row_id = "acc_" + hashlib.sha256((offer["offer_id"] + "\0" + did).encode()).hexdigest()[:24]
        if row_id in seen:
            fail("derived acceptance row collision")
        seen.add(row_id)
        rows.append({
            "id": row_id,
            "given": (
                f"Accepted commercial offer {offer['offer_id']} at {offer_sha256}; "
                f"deliverable {did} evidence commitment {evidence_sha}."
            ),
            "when": title,
            "then": criteria,
            "evidence_required": ["public_ref", "sha256"],
        })
    return rows


def terms_digest(agreement: Mapping[str, Any]) -> str:
    return digest({key: agreement[key] for key in (
        "sku_id", "quote", "window", "intake_sentence", "acceptance_rows", "exclusions", "refund_choice",
    )})


def build_scope_bridge(
    contract: Mapping[str, Any], operator_verification: Mapping[str, Any], owner_secret: bytes,
    verification_secret: bytes, *, catalog: Mapping[str, Any], trusted_now: str,
    contract_verifier: ContractVerifier | None = None,
    agreement_validator: AgreementValidator | None = None,
) -> dict[str, Any]:
    verified, receipt = verify_operator_verification(
        contract, operator_verification, owner_secret, verification_secret,
        trusted_now=trusted_now, contract_verifier=contract_verifier,
    )
    offer = verified["offer"]
    # v1 cannot safely add a post-acceptance classification. The accepted
    # opportunity_id itself must already be the canonical scope SKU.
    sku_id = scope_identifier(offer["opportunity_id"], "offer.opportunity_id")
    catalog_currency, catalog_total = catalog_quote(catalog, sku_id)
    offer_amount = Decimal(offer["total_amount_minor"]) / Decimal(100)
    if catalog_currency != offer["currency"] or catalog_total != offer_amount:
        fail("accepted offer price/currency does not equal canonical catalog listing")

    schedule = receipt["schedule_acceptance"]
    agreement: dict[str, Any] = {
        "schema_version": SCOPE_SCHEMA,
        "kind": SCOPE_KIND,
        "agreement_id": "offer_" + verified["offer_sha256"][:32],
        "sku_id": sku_id,
        "quote": {"currency": "USD", "amount": f"{offer_amount:.2f}"},
        "window": {"start": schedule["start"], "end": schedule["end"], "timezone": schedule["timezone"]},
        "written_acceptance": {
            "status": "PRESENT", "attestation": SCOPE_ACCEPTANCE_ATTESTATION, "terms_digest": "",
            "public_ref": receipt["public_ref"], "accepted_at": schedule["accepted_at"],
        },
        "buyer_ref": scope_buyer_ref(offer["buyer_ref"]),
        "intake_sentence": (
            f"Execute exact accepted commercial offer {offer['offer_id']} "
            f"with offer SHA-256 {verified['offer_sha256']}."
        ),
        "acceptance_rows": acceptance_rows(offer, verified["offer_sha256"]),
        "exclusions": copy.deepcopy(offer["exclusions"]),
        "refund_choice": REFUND_CHOICE,
    }
    agreement["written_acceptance"]["terms_digest"] = terms_digest(agreement)
    validator = agreement_validator or default_agreement_validator
    try:
        validated = validator(copy.deepcopy(agreement), copy.deepcopy(dict(catalog)))
    except BridgeError:
        raise
    except Exception as exc:
        raise BridgeError(f"scope-to-delivery compatibility failed: {exc}") from exc
    if canonical(validated) != canonical(agreement):
        fail("scope-to-delivery validator altered the derived agreement")

    bridge_core = {
        "schema_version": SCHEMA_VERSION,
        "kind": BRIDGE_KIND,
        "state": "SCOPE_AGREEMENT_READY",
        "contract_sha256": digest(verified),
        "operator_verification_sha256": digest(receipt),
        "offer_sha256": verified["offer_sha256"],
        "source_buyer_ref_sha256": hashlib.sha256(offer["buyer_ref"].encode()).hexdigest(),
        "agreement_sha256": digest(agreement),
        "agreement_id": agreement["agreement_id"],
        "sku_id": sku_id,
        "service_window": copy.deepcopy(agreement["window"]),
        "authority": {
            "scope_agreement_ready": True, "external_send_performed": False,
            "fulfillment_performed": False, "payment_collected": False, "revenue_recognized": False,
        },
    }
    return {
        "agreement": agreement,
        "operator_verification": receipt,
        "bridge_receipt": {**bridge_core, "bridge_sha256": digest(bridge_core)},
    }


def verify_scope_bridge(
    bundle: Mapping[str, Any], contract: Mapping[str, Any], owner_secret: bytes,
    verification_secret: bytes, *, catalog: Mapping[str, Any], trusted_now: str,
    contract_verifier: ContractVerifier | None = None,
    agreement_validator: AgreementValidator | None = None,
) -> dict[str, Any]:
    bundle = exact(bundle, {"agreement", "operator_verification", "bridge_receipt"}, "bundle")
    receipt = exact(bundle["bridge_receipt"], {
        "schema_version", "kind", "state", "contract_sha256", "operator_verification_sha256",
        "offer_sha256", "source_buyer_ref_sha256", "agreement_sha256", "agreement_id", "sku_id",
        "service_window", "authority", "bridge_sha256",
    }, "bridge_receipt")
    if receipt["schema_version"] != SCHEMA_VERSION or receipt["kind"] != BRIDGE_KIND or receipt["state"] != "SCOPE_AGREEMENT_READY":
        fail("unsupported bridge receipt")
    core = {key: value for key, value in receipt.items() if key != "bridge_sha256"}
    if sha(receipt["bridge_sha256"], "bridge_receipt.bridge_sha256") != digest(core):
        fail("bridge_sha256 mismatch")
    expected_authority = {
        "scope_agreement_ready": True, "external_send_performed": False,
        "fulfillment_performed": False, "payment_collected": False, "revenue_recognized": False,
    }
    if exact(receipt["authority"], set(expected_authority), "bridge_receipt.authority") != expected_authority:
        fail("bridge receipt contains authority escalation")
    rebuilt = build_scope_bridge(
        contract, bundle["operator_verification"], owner_secret, verification_secret,
        catalog=catalog, trusted_now=trusted_now, contract_verifier=contract_verifier,
        agreement_validator=agreement_validator,
    )
    if canonical(rebuilt) != canonical(bundle):
        fail("bridge bundle does not round-trip to canonical bytes")
    return copy.deepcopy(dict(bundle))
