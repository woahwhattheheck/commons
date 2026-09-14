from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = "tjlabs.ohsu-ap-rfi-evidence/v1"
SOLICITATION_ID = "RFI-2027-0824"
OFFICIAL_TITLE = "Artificial Intelligence-Enabled Accounts Payable Automation Solution"
OFFICIAL_URL = "https://www.ohsu.edu/procurement/bids"
RESPONSE_DUE_UTC = "2026-09-24T00:00:00Z"  # Sep 23, 2026 17:00 Pacific (PDT)

LOCAL_EVIDENCE_FILES = (
    "ap_acceptance.py",
    "run_acceptance_matrix.py",
    "fixtures/ap_cases.json",
    "test_ohsu_carrier.py",
)

CAPABILITIES = (
    "invoice_intake_validation",
    "po_matching",
    "coding",
    "approvals",
    "oracle_transaction_processing",
    "supplier_internal_inquiries",
    "statement_reconciliation",
    "exception_management",
    "reporting",
    "audit_controls",
    "implementation_requirements",
    "automation_outcomes",
    "comparable_customer_experience",
    "indicative_pricing",
)

STATUSES = {
    "EVIDENCED",
    "PROPOSED",
    "PARTNER_REQUIRED",
    "OWNER_REQUIRED",
    "FORBIDDEN",
}
HARD_DIRECT_GATES = {
    "oracle_transaction_processing",
    "comparable_customer_experience",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,95}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SECRET_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|secret|password|authorization\s*:|bearer\s+[A-Za-z0-9._~+/=-]{12,})",
    re.I,
)


class ContractError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ContractError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def strict_loads(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=lambda x: (_ for _ in ()).throw(ContractError(f"non-finite number: {x}")))


def strict_load(path: str | Path) -> Any:
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def _expect_exact_keys(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        missing = sorted(keys - set(obj))
        extra = sorted(set(obj) - keys)
        raise ContractError(f"{where}: key mismatch missing={missing} extra={extra}")


def _text(value: Any, where: str, *, max_len: int = 500) -> str:
    if type(value) is not str:
        raise ContractError(f"{where}: expected string")
    if not value or len(value) > max_len or any(ord(c) < 32 and c not in "\t\n" for c in value):
        raise ContractError(f"{where}: invalid text")
    if SECRET_RE.search(value):
        raise ContractError(f"{where}: secret-shaped material forbidden")
    return value


def _ident(value: Any, where: str) -> str:
    s = _text(value, where, max_len=96)
    if not ID_RE.fullmatch(s):
        raise ContractError(f"{where}: invalid identifier")
    return s


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{where}: expected bool")
    return value


def _int(value: Any, where: str, lo: int = 0, hi: int = 10**15) -> int:
    if type(value) is not int or value < lo or value > hi:
        raise ContractError(f"{where}: invalid integer")
    return value


def _utc(value: Any, where: str) -> datetime:
    s = _text(value, where, max_len=32)
    if not s.endswith("Z"):
        raise ContractError(f"{where}: UTC Z timestamp required")
    try:
        dt = datetime.fromisoformat(s[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{where}: invalid timestamp") from exc
    if dt.tzinfo != timezone.utc:
        raise ContractError(f"{where}: UTC required")
    return dt


def _https(value: Any, where: str) -> str:
    s = _text(value, where, max_len=500)
    p = urlparse(s)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ContractError(f"{where}: canonical HTTPS URL required")
    if p.fragment:
        raise ContractError(f"{where}: fragments forbidden")
    return s


def canonical_json(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def facts_digest(facts: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(facts))


def compute_local_evidence_digest(root: str | Path) -> str:
    base = Path(root).resolve()
    h = hashlib.sha256()
    for rel in LOCAL_EVIDENCE_FILES:
        path = (base / rel).resolve()
        if path.parent != base and base not in path.parents:
            raise ContractError(f"local evidence escapes root: {rel}")
        data = path.read_bytes()
        rel_bytes = rel.encode("utf-8")
        h.update(len(rel_bytes).to_bytes(4, "big"))
        h.update(rel_bytes)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def validate_manifest(manifest: Any, trusted_as_of: str, *, local_root: str | Path | None = None) -> dict[str, Any]:
    if type(manifest) is not dict:
        raise ContractError("manifest: object required")
    _expect_exact_keys(
        manifest,
        {"schema", "solicitation", "source", "evidence", "claims", "commercial_offer"},
        "manifest",
    )
    if manifest["schema"] != SCHEMA:
        raise ContractError("manifest.schema: unsupported")

    solicitation = manifest["solicitation"]
    if type(solicitation) is not dict:
        raise ContractError("solicitation: object required")
    _expect_exact_keys(
        solicitation,
        {"id", "buyer", "title", "response_due_utc", "intent_required"},
        "solicitation",
    )
    if solicitation["id"] != SOLICITATION_ID:
        raise ContractError("solicitation.id: wrong solicitation")
    if solicitation["buyer"] != "Oregon Health & Science University":
        raise ContractError("solicitation.buyer: exact buyer required")
    if _text(solicitation["title"], "solicitation.title", max_len=160) != OFFICIAL_TITLE:
        raise ContractError("solicitation.title: controlling title drift")
    if solicitation["response_due_utc"] != RESPONSE_DUE_UTC:
        raise ContractError("solicitation.response_due_utc: controlling deadline drift")
    if _bool(solicitation["intent_required"], "solicitation.intent_required") is not False:
        raise ContractError("solicitation.intent_required: official listing says not applicable")

    now = _utc(trusted_as_of, "trusted_as_of")
    due = _utc(solicitation["response_due_utc"], "solicitation.response_due_utc")

    source = manifest["source"]
    if type(source) is not dict:
        raise ContractError("source: object required")
    _expect_exact_keys(source, {"authority", "url", "captured_at_utc", "facts", "fact_digest"}, "source")
    if source["authority"] != "OFFICIAL":
        raise ContractError("source.authority: OFFICIAL required")
    if _https(source["url"], "source.url") != OFFICIAL_URL:
        raise ContractError("source.url: controlling OHSU bids page required")
    captured = _utc(source["captured_at_utc"], "source.captured_at_utc")
    if captured > now:
        raise ContractError("source.captured_at_utc: future source")
    facts = source["facts"]
    if type(facts) is not dict:
        raise ContractError("source.facts: object required")
    _expect_exact_keys(
        facts,
        {"solicitation_id", "buyer", "title", "erp_context", "intent_required", "response_due_utc"},
        "source.facts",
    )
    if facts["solicitation_id"] != SOLICITATION_ID:
        raise ContractError("source.facts.solicitation_id: drift")
    if facts["buyer"] != solicitation["buyer"] or facts["title"] != solicitation["title"]:
        raise ContractError("source.facts: buyer/title drift")
    if facts["erp_context"] != "on-premises Oracle E-Business Suite R12":
        raise ContractError("source.facts.erp_context: drift")
    if _bool(facts["intent_required"], "source.facts.intent_required") is not solicitation["intent_required"]:
        raise ContractError("source.facts.intent_required: drift")
    if facts["response_due_utc"] != solicitation["response_due_utc"]:
        raise ContractError("source.facts.response_due_utc: drift")
    digest = _text(source["fact_digest"], "source.fact_digest", max_len=64)
    if not SHA_RE.fullmatch(digest) or digest != facts_digest(facts):
        raise ContractError("source.fact_digest: normalized controlling facts digest mismatch")

    evidence_rows = manifest["evidence"]
    if type(evidence_rows) is not list or not evidence_rows:
        raise ContractError("evidence: non-empty list required")
    evidence: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(evidence_rows):
        if type(row) is not dict:
            raise ContractError(f"evidence[{i}]: object required")
        _expect_exact_keys(row, {"id", "kind", "locator", "digest", "state"}, f"evidence[{i}]")
        eid = _ident(row["id"], f"evidence[{i}].id")
        if eid in evidence:
            raise ContractError(f"evidence[{i}].id: duplicate")
        if row["kind"] not in {"OFFICIAL_SOURCE", "LOCAL_TEST", "REPO_RECEIPT", "PARTNER_ASSERTION"}:
            raise ContractError(f"evidence[{i}].kind: unsupported")
        _text(row["locator"], f"evidence[{i}].locator", max_len=500)
        dg = _text(row["digest"], f"evidence[{i}].digest", max_len=64)
        if not SHA_RE.fullmatch(dg):
            raise ContractError(f"evidence[{i}].digest: sha256 required")
        if row["state"] not in {"VERIFIED", "UNVERIFIED", "UNMERGED"}:
            raise ContractError(f"evidence[{i}].state: unsupported")
        if row["kind"] == "OFFICIAL_SOURCE" and row["state"] == "VERIFIED" and dg != digest:
            raise ContractError(f"evidence[{i}]: official evidence digest must bind source facts")
        if row["kind"] == "LOCAL_TEST" and row["state"] == "VERIFIED":
            if local_root is None:
                raise ContractError(f"evidence[{i}]: VERIFIED local evidence requires local_root")
            if dg != compute_local_evidence_digest(local_root):
                raise ContractError(f"evidence[{i}]: local evidence digest mismatch")
        evidence[eid] = row

    claims_rows = manifest["claims"]
    if type(claims_rows) is not list or len(claims_rows) != len(CAPABILITIES):
        raise ContractError("claims: exactly one row per required capability")
    claims: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(claims_rows):
        if type(row) is not dict:
            raise ContractError(f"claims[{i}]: object required")
        _expect_exact_keys(row, {"capability", "status", "statement", "evidence_refs"}, f"claims[{i}]")
        cap = _ident(row["capability"], f"claims[{i}].capability")
        if cap not in CAPABILITIES or cap in claims:
            raise ContractError(f"claims[{i}].capability: missing/duplicate/unknown")
        if row["status"] not in STATUSES:
            raise ContractError(f"claims[{i}].status: unsupported")
        _text(row["statement"], f"claims[{i}].statement", max_len=900)
        refs = row["evidence_refs"]
        if type(refs) is not list or any(type(x) is not str for x in refs) or len(set(refs)) != len(refs):
            raise ContractError(f"claims[{i}].evidence_refs: unique string list required")
        for ref in refs:
            if ref not in evidence:
                raise ContractError(f"claims[{i}].evidence_refs: unknown {ref}")
        if row["status"] == "EVIDENCED":
            if not refs:
                raise ContractError(f"claims[{i}]: EVIDENCED requires evidence")
            if any(evidence[r]["state"] != "VERIFIED" for r in refs):
                raise ContractError(f"claims[{i}]: EVIDENCED may use only VERIFIED evidence")
        claims[cap] = row
    if set(claims) != set(CAPABILITIES):
        raise ContractError("claims: incomplete capability set")

    offer = manifest["commercial_offer"]
    if type(offer) is not dict:
        raise ContractError("commercial_offer: object required")
    _expect_exact_keys(
        offer,
        {"state", "name", "price_usd_cents", "delivery_business_days", "acceptance", "external_send_authorized"},
        "commercial_offer",
    )
    if offer["state"] != "PROPOSED_NOT_ACCEPTED":
        raise ContractError("commercial_offer.state: must remain PROPOSED_NOT_ACCEPTED")
    _text(offer["name"], "commercial_offer.name", max_len=120)
    _int(offer["price_usd_cents"], "commercial_offer.price_usd_cents", 1, 10_000_000)
    _int(offer["delivery_business_days"], "commercial_offer.delivery_business_days", 1, 20)
    _text(offer["acceptance"], "commercial_offer.acceptance", max_len=700)
    if _bool(offer["external_send_authorized"], "commercial_offer.external_send_authorized") is not False:
        raise ContractError("commercial_offer.external_send_authorized: must be false")

    direct_blockers = []
    for cap in sorted(HARD_DIRECT_GATES):
        if claims[cap]["status"] != "EVIDENCED":
            direct_blockers.append(f"{cap}:{claims[cap]['status']}")
    any_forbidden = [cap for cap in CAPABILITIES if claims[cap]["status"] == "FORBIDDEN"]
    if any_forbidden:
        direct_blockers.extend(f"{cap}:FORBIDDEN" for cap in any_forbidden)
    if now >= due:
        direct_blockers.append("response_window:EXPIRED")

    packet = {
        "schema": SCHEMA,
        "solicitation_id": SOLICITATION_ID,
        "buyer": solicitation["buyer"],
        "response_due_utc": solicitation["response_due_utc"],
        "trusted_as_of": trusted_as_of,
        "source_authority": "OFFICIAL",
        "capability_matrix": [claims[c] for c in CAPABILITIES],
        "direct_response": {
            "state": "READY" if not direct_blockers else "HOLD",
            "blockers": direct_blockers,
        },
        "teaming": {
            "state": "READY" if now < due else "HOLD",
            "reason": "Partner route remains truthful when Oracle EBS R12/customer proof is supplied by the prime; this carrier does not inherit partner credentials.",
        },
        "commercial_offer": offer,
        "authority": {
            "buyer_contact_authorized": False,
            "partner_contact_authorized": False,
            "submission_authorized": False,
            "contract_authorized": False,
            "payment_or_revenue_claim_authorized": False,
        },
    }
    packet["receipt_sha256"] = sha256_hex(canonical_json(packet))
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        f"# OHSU {packet['solicitation_id']} — AP Automation Response Evidence",
        "",
        f"**Direct response:** `{packet['direct_response']['state']}`",
        f"**Teaming:** `{packet['teaming']['state']}`",
        f"**Response due (UTC):** `{packet['response_due_utc']}`",
        f"**Receipt:** `{packet['receipt_sha256']}`",
        "",
        "## Capability truth matrix",
        "",
        "| Capability | State | Statement |",
        "|---|---|---|",
    ]
    for row in packet["capability_matrix"]:
        statement = row["statement"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{row['capability']}` | `{row['status']}` | {statement} |")
    lines += ["", "## Direct-response blockers", ""]
    if packet["direct_response"]["blockers"]:
        lines.extend(f"- `{x}`" for x in packet["direct_response"]["blockers"])
    else:
        lines.append("- None")
    offer = packet["commercial_offer"]
    lines += [
        "",
        "## Proposed specialist offer",
        "",
        f"**{offer['name']}** — ${offer['price_usd_cents']/100:,.0f} fixed price; {offer['delivery_business_days']} business days; `PROPOSED_NOT_ACCEPTED`.",
        "",
        offer["acceptance"],
        "",
        "## Authority ceiling",
        "",
        "This packet is internal decision/evidence support. It does **not** authorize buyer or partner contact, proposal submission, contract acceptance, provider mutation, payment, or revenue recognition.",
        "",
    ]
    return "\n".join(lines)
