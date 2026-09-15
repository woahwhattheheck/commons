"""Permission-state compiler and deterministic proof renderer."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from .core import (CompiledProof, POLICY_VERSION, STATUSES, ProofError, _canonical_json, _money, _public_proof_id, _redacted_customer_id, strict_json_loads)
from .validation import validate_and_normalize

def compile_proof(raw: dict[str, Any]) -> CompiledProof:
    record = validate_and_normalize(raw)
    blockers: list[str] = []
    withheld: list[str] = []

    payment_verified = record["payment"]["status"] == "SETTLED" and bool(record["payment"]["evidence_refs"])
    delivery_accepted = record["delivery"]["status"] == "ACCEPTED" and bool(record["delivery"]["evidence_refs"])
    revoked = record["revocation"]["revoked"]
    p = record["permissions"]

    if not payment_verified:
        blockers.append("settled_payment_not_verified")
    if revoked:
        blockers.append("publication_permission_revoked")

    public_requested = p["public_proof"]["granted"]
    public_payment_allowed = public_requested and p["payment_fact"]["granted"]
    if payment_verified and not public_requested:
        withheld.append("all_public_projection:no_public_proof_permission")
    elif payment_verified and public_requested and not p["payment_fact"]["granted"]:
        withheld.append("payment_fact:no_payment_fact_permission")

    if not payment_verified or revoked:
        status = "HOLD"
    elif not public_payment_allowed:
        status = "PRIVATE_VERIFIED"
    elif p["customer_identity"]["granted"]:
        status = "PUBLIC_NAMED"
    else:
        status = "PUBLIC_ANONYMOUS"
    if status not in STATUSES:
        raise ProofError("internal status invariant failed")

    public_enabled = status in {"PUBLIC_ANONYMOUS", "PUBLIC_NAMED"}
    named = status == "PUBLIC_NAMED"

    if named:
        customer_label = record["customer"]["display_name"]
    elif public_enabled:
        customer_label = _redacted_customer_id(record["engagement_id"])
        if record["customer"]["display_name"] is not None:
            withheld.append("customer_identity")
    else:
        customer_label = None

    exact_amount: str | None = None
    if public_enabled:
        if p["exact_amount"]["granted"]:
            pay = record["payment"]
            exact_amount = _money(pay["amount_minor"], pay["currency"], pay["currency_decimals"])
        else:
            withheld.append("exact_amount")

    public_delivery = False
    if delivery_accepted:
        if public_enabled and p["delivery_acceptance"]["granted"]:
            public_delivery = True
        else:
            withheld.append("delivery_acceptance")

    public_quote: str | None = None
    if record["quote"]["text"] is not None:
        if public_enabled and p["quote"]["granted"]:
            public_quote = record["quote"]["text"]
        else:
            withheld.append("quote")

    public_logo_ref: str | None = None
    if record["customer"]["logo_ref"] is not None:
        if public_enabled and named and p["logo"]["granted"]:
            public_logo_ref = record["customer"]["logo_ref"]
        else:
            withheld.append("logo")

    public_outcomes: list[dict[str, Any]] = []
    private_outcomes: list[dict[str, Any]] = []
    for outcome in record["outcomes"]:
        private_outcomes.append({"claim": outcome["claim"], "evidence_refs": outcome["evidence_refs"]})
        if public_enabled and outcome["publication_permission"]["granted"]:
            public_outcomes.append({"claim": outcome["claim"], "evidence_refs": outcome["evidence_refs"]})
        else:
            withheld.append(f"outcome:{outcome['claim']}")

    permission_refs = {
        scope: p[scope]["evidence_refs"]
        for scope in sorted(p)
        if p[scope]["granted"]
    }

    public_projection = {
        "status": status,
        # Never expose the internal engagement identifier in a public projection; it may itself
        # contain buyer-identifying metadata. A domain-separated digest is stable without disclosure.
        "proof_id": _public_proof_id(record["engagement_id"]) if public_enabled else None,
        "customer": customer_label,
        "paid_engagement": True if public_enabled and payment_verified else None,
        "exact_amount": exact_amount,
        "delivery_accepted": True if public_delivery else None,
        "quote": public_quote,
        "logo_ref": public_logo_ref,
        "outcomes": public_outcomes,
    }

    private_evidence = {
        "payment_verified": payment_verified,
        "payment": record["payment"],
        "delivery_accepted": delivery_accepted,
        "delivery": record["delivery"],
        "customer": record["customer"],
        "quote": record["quote"],
        "outcomes": private_outcomes,
        "permission_evidence_refs": permission_refs,
        "revocation": record["revocation"],
    }

    proof_without_receipt = {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "status": status,
        "engagement_id": record["engagement_id"],
        "blockers": sorted(set(blockers)),
        "withheld": sorted(set(withheld)),
        "public_projection": public_projection,
        "private_evidence": private_evidence,
    }
    markdown = render_markdown(proof_without_receipt)
    receipt_payload = {
        "policy_version": POLICY_VERSION,
        "normalized_input": record,
        "proof": proof_without_receipt,
        "markdown": markdown,
    }
    receipt = hashlib.sha256(_canonical_json(receipt_payload).encode("utf-8")).hexdigest()
    proof = dict(proof_without_receipt)
    proof["receipt_sha256"] = receipt
    return CompiledProof(proof=proof, markdown=markdown, receipt_sha256=receipt)


def render_markdown(proof: dict[str, Any]) -> str:
    status = proof["status"]
    public = proof["public_projection"]
    lines = ["# Verified Paid Proof", "", f"**Status:** `{status}`", f"**Policy:** `{proof['policy_version']}`"]

    if status == "HOLD":
        lines += ["", "No public or private paid-proof claim is releasable from this record."]
    elif status == "PRIVATE_VERIFIED":
        lines += [
            "",
            "Settled payment is verified internally. No public sales claim is authorized by this record.",
            "",
            "**Important:** payment does not imply satisfaction, endorsement, delivery acceptance, or outcome success.",
        ]
    else:
        lines += ["", "## Sales-safe public projection", ""]
        lines.append(f"- Customer: **{public['customer']}**")
        lines.append("- Commercial fact: **Paid engagement verified**")
        if public["exact_amount"] is not None:
            lines.append(f"- Settled amount: **{public['exact_amount']}**")
        else:
            lines.append("- Settled amount: withheld")
        if public["delivery_accepted"]:
            lines.append("- Delivery: **explicit acceptance verified**")
        if public["outcomes"]:
            lines.append("- Permissioned outcome facts:")
            for outcome in public["outcomes"]:
                lines.append(f"  - {outcome['claim']}")
        if public["quote"] is not None:
            quote = public["quote"].replace("\n", " ")
            lines.append(f"- Permissioned customer quote: “{quote}”")
        if public["logo_ref"] is not None:
            lines.append(f"- Permissioned logo reference: `{public['logo_ref']}`")
        lines += [
            "",
            "Payment is represented only as payment. No unstated satisfaction, endorsement, recommendation, recurring-customer, or performance claim is implied.",
        ]

    if proof["withheld"]:
        lines += ["", "## Withheld from public projection", ""]
        for item in proof["withheld"]:
            lines.append(f"- `{item}`")
    if proof["blockers"]:
        lines += ["", "## Blockers", ""]
        for item in proof["blockers"]:
            lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)


def compile_text(text: str) -> CompiledProof:
    return compile_proof(strict_json_loads(text))


def write_outputs(compiled: CompiledProof, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "proof.json").write_text(compiled.proof_json(), encoding="utf-8")
    (out_dir / "proof.md").write_text(compiled.markdown, encoding="utf-8")
    (out_dir / "receipt.sha256").write_text(compiled.receipt_sha256 + "\n", encoding="utf-8")


