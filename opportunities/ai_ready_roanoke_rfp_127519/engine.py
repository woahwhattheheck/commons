from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

SCHEMA = "commons.ai-ready-roanoke/v1"
OUTPUT_SCHEMA = "commons.ai-ready-roanoke-decision/v1"

AUTHORITY = {"OFFICIAL_BYTES", "BUYER_DOCUMENT_MIRROR", "SECONDARY"}
DOC_KINDS = {"RFP", "ADDENDUM", "QA"}
GATE_STATES = {"PASS", "PARTNER_CURABLE", "MISSING", "HOLD", "NOT_APPLICABLE"}
ROUTES = {"PRIME", "TEAM"}
OUTREACH_STATES = {"NOT_CONTACTED", "SENT_NOT_ACCEPTED", "PARTNER_REPLIED", "DECLINED"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+#/-]{0,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_GATES = (
    "regional_feasibility_experience",
    "primary_employer_research",
    "real_estate_program_cost_modeling",
    "governance_design",
    "in_region_interview_capacity",
    "similar_references",
    "key_personnel",
    "virginia_scc_or_valid_exception",
    "required_insurance",
    "proposal_budget_approved",
    "signature_authority",
)

SCORED_SECTIONS = {
    "approach_methodology": 30,
    "relevant_experience_references": 25,
    "team_qualifications": 15,
    "cost_value": 15,
    "topic_region_knowledge": 15,
}

class PursuitError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def strict_json_loads(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise PursuitError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    def bad_constant(value: str) -> None:
        raise PursuitError(f"non-finite JSON number: {value}")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    except PursuitError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise PursuitError(f"invalid JSON: {exc}") from exc


def _exact(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        raise PursuitError(f"{where}: keys mismatch missing={sorted(keys-set(obj))} extra={sorted(set(obj)-keys)}")


def _s(value: Any, name: str, max_len: int = 300, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len or any(ord(c) < 32 for c in value):
        raise PursuitError(f"{name}: invalid string")
    if pattern and not pattern.fullmatch(value):
        raise PursuitError(f"{name}: invalid format")
    return value


def _b(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise PursuitError(f"{name}: bool required")
    return value


def _t(value: Any, name: str) -> datetime:
    text = _s(value, name, 30)
    if not text.endswith("Z"):
        raise PursuitError(f"{name}: UTC Z required")
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PursuitError(f"{name}: invalid timestamp") from exc
    if dt.microsecond:
        raise PursuitError(f"{name}: whole seconds required")
    return dt


def _source(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PursuitError(f"sources[{idx}] must be object")
    keys = {"source_id","doc_kind","generation","authority","source_ref","content_sha256","captured_at","current","supersedes"}
    _exact(raw, keys, f"sources[{idx}]")
    out = {
        "source_id": _s(raw["source_id"], f"sources[{idx}].source_id", 100, SAFE_ID),
        "doc_kind": _s(raw["doc_kind"], f"sources[{idx}].doc_kind", 20),
        "generation": _s(raw["generation"], f"sources[{idx}].generation", 80, SAFE_ID),
        "authority": _s(raw["authority"], f"sources[{idx}].authority", 30),
        "source_ref": _s(raw["source_ref"], f"sources[{idx}].source_ref", 260),
        "content_sha256": raw["content_sha256"],
        "captured_at": _s(raw["captured_at"], f"sources[{idx}].captured_at", 30),
        "current": _b(raw["current"], f"sources[{idx}].current"),
        "supersedes": raw["supersedes"],
    }
    if out["doc_kind"] not in DOC_KINDS or out["authority"] not in AUTHORITY:
        raise PursuitError(f"sources[{idx}]: enum invalid")
    if out["content_sha256"] is not None:
        out["content_sha256"] = _s(out["content_sha256"], f"sources[{idx}].content_sha256", 64, SHA256)
    if out["authority"] == "OFFICIAL_BYTES" and out["content_sha256"] is None:
        raise PursuitError(f"sources[{idx}]: official bytes require digest")
    if out["supersedes"] is not None:
        out["supersedes"] = _s(out["supersedes"], f"sources[{idx}].supersedes", 100, SAFE_ID)
    _t(out["captured_at"], f"sources[{idx}].captured_at")
    return out


def _gate(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PursuitError(f"gates[{idx}] must be object")
    _exact(raw, {"gate_id","route","state","evidence_refs"}, f"gates[{idx}]")
    gid = _s(raw["gate_id"], f"gates[{idx}].gate_id", 100, SAFE_ID)
    route = _s(raw["route"], f"gates[{idx}].route", 10)
    state = _s(raw["state"], f"gates[{idx}].state", 30)
    if route not in ROUTES or state not in GATE_STATES:
        raise PursuitError(f"gates[{idx}]: enum invalid")
    refs = raw["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 20:
        raise PursuitError(f"gates[{idx}].evidence_refs invalid")
    clean_refs = [_s(v, f"gates[{idx}].evidence_refs", 140, SAFE_ID) for v in refs]
    if len(set(clean_refs)) != len(clean_refs):
        raise PursuitError(f"gates[{idx}]: duplicate evidence ref")
    if state == "PASS" and not clean_refs:
        raise PursuitError(f"gates[{idx}]: PASS requires evidence")
    return {"gate_id":gid,"route":route,"state":state,"evidence_refs":sorted(clean_refs)}


def evaluate(packet: Any, as_of: str) -> dict[str, Any]:
    now = _t(as_of, "as_of")
    if not isinstance(packet, dict):
        raise PursuitError("packet must be object")
    _exact(packet, {"schema","opportunity_id","buyer","sources","source_set_complete","deadlines","gates","partner","outreach","budget","owner_release"}, "packet")
    if packet["schema"] != SCHEMA:
        raise PursuitError("unsupported schema")
    opportunity_id = _s(packet["opportunity_id"], "opportunity_id", 100, SAFE_ID)
    buyer = _s(packet["buyer"], "buyer", 180)
    source_set_complete = _b(packet["source_set_complete"], "source_set_complete")

    raw_sources = packet["sources"]
    if not isinstance(raw_sources, list) or not raw_sources or len(raw_sources) > 50:
        raise PursuitError("sources invalid")
    sources = [_source(v, i) for i,v in enumerate(raw_sources)]
    source_ids: dict[str, str] = {}
    for src in sources:
        d = digest(src)
        if src["source_id"] in source_ids and source_ids[src["source_id"]] != d:
            raise PursuitError(f"changed source_id: {src['source_id']}")
        if src["source_id"] in source_ids:
            raise PursuitError(f"duplicate source_id: {src['source_id']}")
        source_ids[src["source_id"]] = d
    for src in sources:
        if src["supersedes"] is not None and src["supersedes"] not in source_ids:
            raise PursuitError(f"unknown supersedes: {src['supersedes']}")
        if _t(src["captured_at"], src["source_id"] + ".captured_at") > now:
            raise PursuitError(f"future source: {src['source_id']}")

    deadlines = packet["deadlines"]
    if not isinstance(deadlines, dict):
        raise PursuitError("deadlines must be object")
    _exact(deadlines, {"questions_due","proposal_due","deadline_source_id"}, "deadlines")
    question_due = _t(deadlines["questions_due"], "deadlines.questions_due")
    proposal_due = _t(deadlines["proposal_due"], "deadlines.proposal_due")
    deadline_source_id = _s(deadlines["deadline_source_id"], "deadlines.deadline_source_id", 100, SAFE_ID)
    if deadline_source_id not in source_ids:
        raise PursuitError("deadline source missing")
    deadline_src = next(s for s in sources if s["source_id"] == deadline_source_id)
    if deadline_src["doc_kind"] != "ADDENDUM" or not deadline_src["current"]:
        raise PursuitError("proposal deadline must bind current addendum")
    if proposal_due <= question_due:
        raise PursuitError("proposal deadline must follow question deadline")

    raw_gates = packet["gates"]
    if not isinstance(raw_gates, list) or len(raw_gates) > 100:
        raise PursuitError("gates invalid")
    gates = [_gate(v,i) for i,v in enumerate(raw_gates)]
    seen_gate_route: set[tuple[str,str]] = set()
    for gate in gates:
        key=(gate["gate_id"],gate["route"])
        if key in seen_gate_route: raise PursuitError(f"duplicate gate route: {key}")
        seen_gate_route.add(key)

    partner = packet["partner"]
    if not isinstance(partner, dict): raise PursuitError("partner must be object")
    _exact(partner, {"candidate_id","confirmed","commercial_workshare_agreed","evidence_refs"}, "partner")
    candidate_id = partner["candidate_id"]
    if candidate_id is not None: candidate_id = _s(candidate_id, "partner.candidate_id", 100, SAFE_ID)
    confirmed = _b(partner["confirmed"], "partner.confirmed")
    workshare = _b(partner["commercial_workshare_agreed"], "partner.commercial_workshare_agreed")
    if workshare and not confirmed: raise PursuitError("workshare cannot precede confirmed partner")
    pref = partner["evidence_refs"]
    if not isinstance(pref, list) or len(pref)>20: raise PursuitError("partner.evidence_refs invalid")
    pref = [_s(v,"partner.evidence_refs",140,SAFE_ID) for v in pref]
    if confirmed and (candidate_id is None or not pref): raise PursuitError("confirmed partner needs identity and evidence")

    outreach = packet["outreach"]
    if not isinstance(outreach, dict): raise PursuitError("outreach must be object")
    _exact(outreach,{"state","provider_receipt_id"},"outreach")
    outreach_state=_s(outreach["state"],"outreach.state",30)
    if outreach_state not in OUTREACH_STATES: raise PursuitError("outreach state invalid")
    provider_receipt=outreach["provider_receipt_id"]
    if provider_receipt is not None: provider_receipt=_s(provider_receipt,"outreach.provider_receipt_id",120,SAFE_ID)
    if outreach_state != "NOT_CONTACTED" and provider_receipt is None: raise PursuitError("observed outreach needs provider receipt")

    budget = packet["budget"]
    if not isinstance(budget, dict): raise PursuitError("budget must be object")
    _exact(budget,{"math_valid","owner_approved","total_cents"},"budget")
    budget_math=_b(budget["math_valid"],"budget.math_valid")
    budget_approved=_b(budget["owner_approved"],"budget.owner_approved")
    total=budget["total_cents"]
    if type(total) is not int or total < 0 or total > 25_000_000: raise PursuitError("budget.total_cents invalid or above buyer ceiling")
    if budget_approved and not budget_math: raise PursuitError("owner cannot approve invalid budget math")

    owner_release=_b(packet["owner_release"],"owner_release")
    if now >= proposal_due:
        disposition="EXPIRED"
    else:
        current_docs=[s for s in sources if s["current"]]
        current_rfp=[s for s in current_docs if s["doc_kind"]=="RFP"]
        current_add=[s for s in current_docs if s["doc_kind"]=="ADDENDUM"]
        if not source_set_complete or not current_rfp or not current_add:
            disposition="SOURCE_REFRESH_REQUIRED"
        else:
            team = {g["gate_id"]:g for g in gates if g["route"]=="TEAM"}
            prime = {g["gate_id"]:g for g in gates if g["route"]=="PRIME"}
            missing_team=[gid for gid in REQUIRED_GATES if gid not in team or team[gid]["state"] not in {"PASS","NOT_APPLICABLE"}]
            missing_prime=[gid for gid in REQUIRED_GATES if gid not in prime or prime[gid]["state"] not in {"PASS","NOT_APPLICABLE"}]
            official_complete=all(s["authority"]=="OFFICIAL_BYTES" for s in current_docs if s["doc_kind"] in {"RFP","ADDENDUM"})
            if not missing_prime and official_complete and budget_math and budget_approved and owner_release:
                disposition="PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW"
            elif confirmed and workshare and not missing_team and official_complete and budget_math and budget_approved and owner_release:
                disposition="TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW"
            elif confirmed and not missing_team:
                disposition="TEAMING_RESPONSE_BUILD_READY"
            else:
                disposition="PARTNER_OUTREACH_READY"

    current_docs=[s for s in sources if s["current"]]
    output={
        "schema":OUTPUT_SCHEMA,
        "opportunity_id":opportunity_id,
        "buyer":buyer,
        "as_of":as_of,
        "disposition":disposition,
        "deadlines":{"questions_due":deadlines["questions_due"],"proposal_due":deadlines["proposal_due"]},
        "days_to_proposal":max(0,(proposal_due-now).total_seconds()/86400),
        "scoring":SCORED_SECTIONS,
        "source_posture":{
            "source_set_complete":source_set_complete,
            "current_source_ids":sorted(s["source_id"] for s in current_docs),
            "official_submission_bytes_complete":all(s["authority"]=="OFFICIAL_BYTES" for s in current_docs if s["doc_kind"] in {"RFP","ADDENDUM"}) and bool(current_docs),
        },
        "partner_posture":{"candidate_id":candidate_id,"confirmed":confirmed,"commercial_workshare_agreed":workshare},
        "outreach":{"state":outreach_state,"provider_receipt_id":provider_receipt},
        "budget":{"total_cents":total,"math_valid":budget_math,"owner_approved":budget_approved,"buyer_ceiling_cents":25_000_000,"contingent_funding_cents":9_259_000},
        "authority":{"contact_new_partner":False,"contact_buyer":False,"submit":False,"sign":False,"commit_price":False,"accept_contract":False,"spend":False,"claim_award":False,"claim_payment":False,"recognize_revenue":False},
        "packet_sha256":digest(packet),
    }
    output["receipt_sha256"]=digest(output)
    return output


def verify(packet: Any, as_of: str, candidate: Any) -> bool:
    if not isinstance(candidate, dict): return False
    try: return canonical_bytes(evaluate(packet,as_of)) == canonical_bytes(candidate)
    except PursuitError: return False
