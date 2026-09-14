from __future__ import annotations

import copy
from typing import Any

from .constants import INPUT_SCHEMA, OUTPUT_SCHEMA, STATES
from .lineage import _generation_conflicts
from .model import normalize_input
from .resolve import _resolve_requirement
from .strict import RegistryError, _parse_utc, canonical_json, load_json_strict, sha256_hex

def compile_registry(payload: Any) -> dict[str, Any]:
    normalized = normalize_input(copy.deepcopy(payload))
    as_of = _parse_utc(normalized["as_of"], "root.as_of")
    assert as_of is not None
    conflicts, superseded_by, _ = _generation_conflicts(normalized["evidence"])
    results = [
        _resolve_requirement(req, normalized["evidence"], normalized["entity_id"], as_of, conflicts, superseded_by)
        for req in normalized["requirements"]
    ]
    counts = {state: 0 for state in sorted(STATES)}
    for result in results:
        counts[result["state"]] += 1
    output: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "generation_id": normalized["generation_id"],
        "entity_id": normalized["entity_id"],
        "as_of": normalized["as_of"],
        "registry_sha256": sha256_hex(normalized),
        "requirements": results,
        "counts": counts,
        "ready_for_bid_consumption": all(r["state"] == "CURRENT_VERIFIED" for r in results),
        "authority": {
            "external_contact_authorized": False,
            "submission_authorized": False,
            "signature_authorized": False,
            "pricing_authorized": False,
            "payment_authorized": False,
            "award_or_revenue_claim_authorized": False,
        },
    }
    output["receipt_sha256"] = sha256_hex(output)
    return output


def verify_receipt(payload: Any, receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    try:
        expected = compile_registry(payload)
    except RegistryError:
        return False
    return canonical_json(expected) == canonical_json(receipt)


def render_markdown(receipt: dict[str, Any]) -> str:
    if receipt.get("schema") != OUTPUT_SCHEMA:
        raise RegistryError("receipt.schema:UNSUPPORTED")
    lines = [
        "# Bid Evidence Authority Manifest",
        "",
        f"- Generation: `{receipt['generation_id']}`",
        f"- Entity: `{receipt['entity_id']}`",
        f"- As of: `{receipt['as_of']}`",
        f"- Registry SHA-256: `{receipt['registry_sha256']}`",
        f"- Receipt SHA-256: `{receipt['receipt_sha256']}`",
        f"- Ready for bid consumption: `{'YES' if receipt['ready_for_bid_consumption'] else 'NO'}`",
        "",
        "| Requirement | Category | Stage | State | Evidence | Evidence SHA-256 | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in receipt["requirements"]:
        evidence = row["evidence_id"] or "—"
        evidence_sha = row["evidence_sha256"] or "—"
        lines.append(
            f"| `{row['requirement_id']}` | `{row['category']}` | `{row['stage']}` | "
            f"`{row['state']}` | `{evidence}` | `{evidence_sha}` | `{row['reason']}` |"
        )
    lines.extend([
        "",
        "> Evidence descriptors and private document contents are intentionally absent from this manifest. "
        "A manifest is evidence truth for human/bid tooling only; it grants no contact, signature, pricing, submission, payment, award, or revenue authority.",
        "",
    ])
    return "\n".join(lines)
