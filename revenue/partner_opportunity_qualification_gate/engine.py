from __future__ import annotations

import hashlib as _hashlib
import json as _json
from datetime import date as _date, timedelta as _timedelta_type
from typing import Any

from .validation import QualificationError, SCHEMA, digest, normalize_input

OUTPUT_SCHEMA = "partner-opportunity-qualification-output/v1"
RECEIPT_SCHEMA = "partner-opportunity-qualification-receipt/v1"
READY = {"READY_FOR_MUSE_ELECTION_ONLY", "READY_FOR_CAPACITY_MUSE_ELECTION_ONLY"}
RUNWAY_DONOR_BLOB_SHA256 = "f254a8afca9d1255e8afa5bf111cb808c04036d7"


def _build_sealed_runway_api(
    _json_dumps=_json.dumps,
    _sha256=_hashlib.sha256,
    _date_fromisoformat=_date.fromisoformat,
    _timedelta=_timedelta_type,
):
    SCHEMA = "procurement-runway-gate-input/v1"
    OUTPUT_SCHEMA = "procurement-runway-gate-output/v1"
    RECEIPT_SCHEMA = "procurement-runway-gate-receipt/v1"
    RUNWAY_STATES = {"READY", "ASK_CAPACITY_FIRST", "TOO_LATE", "UNKNOWN"}
    CAPACITY_STATES = {"EXPLICIT_EARLIEST_DATE", "EXPLICIT_LEAD_TIME_DAYS", "UNVERIFIED"}
    RELATIONSHIP_STATES = {"CLEAR", "DNR", "INBOUND_ONLY", "UNKNOWN"}
    COLLISION_STATES = {"CLEAR", "CLAIMED_ELSEWHERE", "UNKNOWN"}
    AUTHORITY_FALSE = {
        "external_send_authorized": False,
        "provider_mutation_authorized": False,
        "submission_authorized": False,
        "payment_or_revenue_inferred": False,
    }
    
    
    class GateError(ValueError):
        pass
    
    
    def canonical_json_bytes(value: Any) -> bytes:
        return (_json_dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    
    
    def _require_dict(value: Any, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise GateError(f"{field} must be an object")
        return value
    
    
    def _require_list(value: Any, field: str) -> list[Any]:
        if not isinstance(value, list):
            raise GateError(f"{field} must be an array")
        return value
    
    
    def _require_str(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise GateError(f"{field} must be a non-empty string")
        return value.strip()
    
    
    def _require_int(value: Any, field: str, minimum: int | None = None) -> int:
        if type(value) is not int:
            raise GateError(f"{field} must be an integer")
        if minimum is not None and value < minimum:
            raise GateError(f"{field} must be >= {minimum}")
        return value
    
    
    def _parse_date(value: Any, field: str) -> date:
        text = _require_str(value, field)
        try:
            parsed = _date_fromisoformat(text)
        except ValueError as exc:
            raise GateError(f"{field} must be YYYY-MM-DD") from exc
        if parsed.isoformat() != text:
            raise GateError(f"{field} must use canonical YYYY-MM-DD")
        return parsed
    
    
    def _urls(value: Any, field: str, *, required: bool = True) -> list[str]:
        rows = _require_list(value, field)
        out: list[str] = []
        seen: set[str] = set()
        for idx, raw in enumerate(rows):
            url = _require_str(raw, f"{field}[{idx}]")
            if not (url.startswith("https://") or url.startswith("http://")):
                raise GateError(f"{field}[{idx}] must be http(s)")
            if url in seen:
                raise GateError(f"{field} contains duplicate URL")
            seen.add(url)
            out.append(url)
        if required and not out:
            raise GateError(f"{field} must contain evidence")
        return sorted(out)
    
    
    def _date_fact(raw: Any, field: str, *, required: bool = False) -> dict[str, Any] | None:
        if raw is None:
            if required:
                raise GateError(f"{field} is required")
            return None
        obj = _require_dict(raw, field)
        allowed = {"date", "label", "evidence_urls"}
        unknown = set(obj) - allowed
        if unknown:
            raise GateError(f"{field} has unknown keys: {sorted(unknown)}")
        parsed = _parse_date(obj.get("date"), f"{field}.date")
        label = _require_str(obj.get("label"), f"{field}.label")
        urls = _urls(obj.get("evidence_urls"), f"{field}.evidence_urls")
        return {"date": parsed.isoformat(), "label": label, "evidence_urls": urls}
    
    
    def _validate_partner(raw: Any, field: str) -> dict[str, Any]:
        obj = _require_dict(raw, field)
        allowed = {"name", "capability_evidence_urls", "capacity", "conflicts_dnr"}
        unknown = set(obj) - allowed
        if unknown:
            raise GateError(f"{field} has unknown keys: {sorted(unknown)}")
        name = _require_str(obj.get("name"), f"{field}.name")
        capability = _urls(obj.get("capability_evidence_urls"), f"{field}.capability_evidence_urls")
        conflicts = [
            _require_str(v, f"{field}.conflicts_dnr[{i}]")
            for i, v in enumerate(_require_list(obj.get("conflicts_dnr", []), f"{field}.conflicts_dnr"))
        ]
        capacity = _require_dict(obj.get("capacity"), f"{field}.capacity")
        allowed_capacity = {"state", "earliest_date", "lead_time_days", "evidence_urls"}
        unknown_capacity = set(capacity) - allowed_capacity
        if unknown_capacity:
            raise GateError(f"{field}.capacity has unknown keys: {sorted(unknown_capacity)}")
        state = _require_str(capacity.get("state"), f"{field}.capacity.state")
        if state not in CAPACITY_STATES:
            raise GateError(f"{field}.capacity.state invalid")
        earliest: str | None = None
        lead: int | None = None
        evidence = _urls(
            capacity.get("evidence_urls", []),
            f"{field}.capacity.evidence_urls",
            required=state != "UNVERIFIED",
        )
        if state == "EXPLICIT_EARLIEST_DATE":
            earliest = _parse_date(capacity.get("earliest_date"), f"{field}.capacity.earliest_date").isoformat()
            if "lead_time_days" in capacity and capacity.get("lead_time_days") is not None:
                raise GateError(f"{field}.capacity.lead_time_days forbidden for EXPLICIT_EARLIEST_DATE")
        elif state == "EXPLICIT_LEAD_TIME_DAYS":
            lead = _require_int(capacity.get("lead_time_days"), f"{field}.capacity.lead_time_days", 0)
            if "earliest_date" in capacity and capacity.get("earliest_date") is not None:
                raise GateError(f"{field}.capacity.earliest_date forbidden for EXPLICIT_LEAD_TIME_DAYS")
        else:
            if capacity.get("earliest_date") is not None or capacity.get("lead_time_days") is not None:
                raise GateError(f"{field}.capacity UNVERIFIED cannot carry invented timing")
            if evidence:
                raise GateError(f"{field}.capacity UNVERIFIED cannot label evidence as capacity evidence")
        return {
            "name": name,
            "capability_evidence_urls": capability,
            "capacity": {
                "state": state,
                "earliest_date": earliest,
                "lead_time_days": lead,
                "evidence_urls": evidence,
            },
            "conflicts_dnr": sorted(set(conflicts)),
        }
    
    
    def _validate_workshare(raw: Any, field: str) -> dict[str, Any]:
        obj = _require_dict(raw, field)
        allowed = {"fixed_fee_minor", "currency", "scope", "acceptance_criteria", "exclusions"}
        unknown = set(obj) - allowed
        if unknown:
            raise GateError(f"{field} has unknown keys: {sorted(unknown)}")
        fee = _require_int(obj.get("fixed_fee_minor"), f"{field}.fixed_fee_minor", 1)
        currency = _require_str(obj.get("currency"), f"{field}.currency")
        if len(currency) != 3 or currency.upper() != currency or not currency.isalpha():
            raise GateError(f"{field}.currency must be uppercase ISO-like 3-letter code")
        scope = _require_str(obj.get("scope"), f"{field}.scope")
        acceptance = [
            _require_str(v, f"{field}.acceptance_criteria[{i}]")
            for i, v in enumerate(_require_list(obj.get("acceptance_criteria"), f"{field}.acceptance_criteria"))
        ]
        if not acceptance:
            raise GateError(f"{field}.acceptance_criteria must not be empty")
        exclusions = [
            _require_str(v, f"{field}.exclusions[{i}]")
            for i, v in enumerate(_require_list(obj.get("exclusions", []), f"{field}.exclusions"))
        ]
        return {
            "fixed_fee_minor": fee,
            "currency": currency,
            "scope": scope,
            "acceptance_criteria": acceptance,
            "exclusions": exclusions,
        }
    
    
    def validate_input(raw: Any) -> dict[str, Any]:
        doc = _require_dict(raw, "input")
        allowed = {"schema", "as_of", "opportunities"}
        unknown = set(doc) - allowed
        if unknown:
            raise GateError(f"input has unknown keys: {sorted(unknown)}")
        if doc.get("schema") != SCHEMA:
            raise GateError(f"schema must be {SCHEMA}")
        as_of = _parse_date(doc.get("as_of"), "as_of")
        rows = _require_list(doc.get("opportunities"), "opportunities")
        if not rows:
            raise GateError("opportunities must not be empty")
        normalized: list[dict[str, Any]] = []
        ids: set[str] = set()
        for idx, raw_opp in enumerate(rows):
            field = f"opportunities[{idx}]"
            opp = _require_dict(raw_opp, field)
            allowed_opp = {
                "id", "buyer", "source_urls", "dates", "mandatory_delivery_window_days",
                "partners", "workshare", "relationship_state", "collision_state",
            }
            unknown_opp = set(opp) - allowed_opp
            if unknown_opp:
                raise GateError(f"{field} has unknown keys: {sorted(unknown_opp)}")
            oid = _require_str(opp.get("id"), f"{field}.id")
            if oid in ids:
                raise GateError(f"duplicate opportunity id: {oid}")
            ids.add(oid)
            buyer = _require_str(opp.get("buyer"), f"{field}.buyer")
            source_urls = _urls(opp.get("source_urls"), f"{field}.source_urls")
            dates = _require_dict(opp.get("dates"), f"{field}.dates")
            allowed_dates = {
                "issue", "questions_due", "prebid", "proposal_due",
                "anticipated_award", "start", "go_live",
            }
            unknown_dates = set(dates) - allowed_dates
            if unknown_dates:
                raise GateError(f"{field}.dates has unknown keys: {sorted(unknown_dates)}")
            norm_dates = {
                "issue": _date_fact(dates.get("issue"), f"{field}.dates.issue"),
                "questions_due": _date_fact(dates.get("questions_due"), f"{field}.dates.questions_due"),
                "prebid": _date_fact(dates.get("prebid"), f"{field}.dates.prebid"),
                "proposal_due": _date_fact(dates.get("proposal_due"), f"{field}.dates.proposal_due", required=True),
                "anticipated_award": _date_fact(dates.get("anticipated_award"), f"{field}.dates.anticipated_award"),
                "start": _date_fact(dates.get("start"), f"{field}.dates.start"),
                "go_live": _date_fact(dates.get("go_live"), f"{field}.dates.go_live"),
            }
            mdw = opp.get("mandatory_delivery_window_days")
            if mdw is not None:
                mdw = _require_int(mdw, f"{field}.mandatory_delivery_window_days", 1)
            partners = [
                _validate_partner(v, f"{field}.partners[{i}]")
                for i, v in enumerate(_require_list(opp.get("partners"), f"{field}.partners"))
            ]
            partner_names = [p["name"].casefold() for p in partners]
            if len(partner_names) != len(set(partner_names)):
                raise GateError(f"{field}.partners contains duplicate names")
            relationship = _require_str(opp.get("relationship_state"), f"{field}.relationship_state")
            if relationship not in RELATIONSHIP_STATES:
                raise GateError(f"{field}.relationship_state invalid")
            collision = _require_str(opp.get("collision_state"), f"{field}.collision_state")
            if collision not in COLLISION_STATES:
                raise GateError(f"{field}.collision_state invalid")
            normalized.append({
                "id": oid,
                "buyer": buyer,
                "source_urls": source_urls,
                "dates": norm_dates,
                "mandatory_delivery_window_days": mdw,
                "partners": sorted(partners, key=lambda p: (p["name"].casefold(), p["name"])),
                "workshare": _validate_workshare(opp.get("workshare"), f"{field}.workshare"),
                "relationship_state": relationship,
                "collision_state": collision,
            })
        return {
            "schema": SCHEMA,
            "as_of": as_of.isoformat(),
            "opportunities": sorted(normalized, key=lambda r: r["id"]),
        }
    
    
    def _target_date(opp: dict[str, Any]) -> date | None:
        for key in ("start", "go_live"):
            fact = opp["dates"].get(key)
            if fact:
                return _date_fromisoformat(fact["date"])
        award = opp["dates"].get("anticipated_award")
        days = opp.get("mandatory_delivery_window_days")
        if award and days is not None:
            return _date_fromisoformat(award["date"]) + _timedelta(days=days)
        return None
    
    
    def _partner_timing(partner: dict[str, Any], as_of: date, target: date | None) -> tuple[str, str]:
        cap = partner["capacity"]
        state = cap["state"]
        if state == "UNVERIFIED":
            return "UNKNOWN_CAPACITY", "public capability evidence does not establish delivery availability"
        if state == "EXPLICIT_EARLIEST_DATE":
            earliest = _date_fromisoformat(cap["earliest_date"])
        else:
            earliest = as_of + _timedelta(days=cap["lead_time_days"])
        if target is not None and earliest > target:
            return "EXPLICIT_MISS", f"evidenced earliest feasible date {earliest.isoformat()} is after target {target.isoformat()}"
        if target is None:
            return "EXPLICIT_NO_KNOWN_CONFLICT", f"capacity evidence implies earliest {earliest.isoformat()}; no mandatory target date is evidenced"
        return "EXPLICIT_FIT", f"capacity evidence implies earliest {earliest.isoformat()} on/before target {target.isoformat()}"
    
    
    def _contact_state(opp: dict[str, Any]) -> str:
        if opp["relationship_state"] == "DNR":
            return "HOLD_DNR"
        if opp["relationship_state"] == "INBOUND_ONLY":
            return "WAIT_INBOUND"
        if opp["relationship_state"] != "CLEAR":
            return "HOLD_RELATIONSHIP_UNKNOWN"
        if opp["collision_state"] == "CLAIMED_ELSEWHERE":
            return "HOLD_COLLISION"
        if opp["collision_state"] != "CLEAR":
            return "HOLD_COLLISION_UNKNOWN"
        return "ELIGIBLE_FOR_SEPARATE_MUSE_ELECTION_ONLY"
    
    
    def _score_opportunity(opp: dict[str, Any], as_of: date) -> dict[str, Any]:
        proposal_due = _date_fromisoformat(opp["dates"]["proposal_due"]["date"])
        target = _target_date(opp)
        partner_rows: list[dict[str, Any]] = []
        statuses: list[str] = []
        for p in opp["partners"]:
            status, reason = _partner_timing(p, as_of, target)
            statuses.append(status)
            partner_rows.append({
                "name": p["name"],
                "timing_status": status,
                "timing_reason": reason,
                "capability_evidence_urls": p["capability_evidence_urls"],
                "capacity": p["capacity"],
                "conflicts_dnr": p["conflicts_dnr"],
            })
    
        if proposal_due <= as_of:
            runway = "TOO_LATE"
            reason = f"proposal due {proposal_due.isoformat()} is not after as_of {as_of.isoformat()}"
        elif not partner_rows:
            runway = "UNKNOWN"
            reason = "no plausible partner is bound to evidence"
        elif any(s in {"EXPLICIT_FIT", "EXPLICIT_NO_KNOWN_CONFLICT"} for s in statuses):
            runway = "READY"
            reason = "at least one partner has explicit capacity evidence with no known timing conflict"
        elif any(s == "UNKNOWN_CAPACITY" for s in statuses):
            runway = "ASK_CAPACITY_FIRST"
            reason = "partner capability is evidenced but public availability is not"
        else:
            runway = "TOO_LATE"
            reason = "all evidenced partner capacity misses the known delivery target"
    
        selected = partner_rows[:3] if runway in {"READY", "ASK_CAPACITY_FIRST"} else []
        return {
            "id": opp["id"],
            "buyer": opp["buyer"],
            "runway_state": runway,
            "runway_reason": reason,
            "proposal_due": opp["dates"]["proposal_due"],
            "target_date": target.isoformat() if target else None,
            "known_dates": opp["dates"],
            "source_urls": opp["source_urls"],
            "selected_partners": selected,
            "contact_state": _contact_state(opp),
            "workshare": opp["workshare"],
            **AUTHORITY_FALSE,
        }
    
    
    def compile_gate(raw: Any) -> dict[str, Any]:
        doc = validate_input(raw)
        as_of = _date_fromisoformat(doc["as_of"])
        rows = [_score_opportunity(opp, as_of) for opp in doc["opportunities"]]
        counts = {state: 0 for state in sorted(RUNWAY_STATES)}
        for row in rows:
            counts[row["runway_state"]] += 1
        return {
            "schema": OUTPUT_SCHEMA,
            "input_schema": SCHEMA,
            "as_of": doc["as_of"],
            "opportunities": rows,
            "summary": counts,
            **AUTHORITY_FALSE,
        }
    
    
    def make_receipt(output: dict[str, Any]) -> dict[str, Any]:
        output_bytes = canonical_json_bytes(output)
        return {
            "schema": RECEIPT_SCHEMA,
            "output_sha256": _sha256(output_bytes).hexdigest(),
            "output_bytes": len(output_bytes),
            **AUTHORITY_FALSE,
        }
    
    
    def verify_bundle(raw_input: Any, output: Any, receipt: Any) -> None:
        expected = compile_gate(raw_input)
        if output != expected:
            raise GateError("output does not match deterministic recompilation")
        expected_receipt = make_receipt(expected)
        if receipt != expected_receipt:
            raise GateError("receipt does not match output")

    return validate_input, compile_gate, make_receipt, verify_bundle, canonical_json_bytes


(
    _sealed_normalize_runway,
    _sealed_compile_runway,
    _sealed_runway_receipt,
    _sealed_verify_runway,
    _sealed_runway_bytes,
) = _build_sealed_runway_api()
del _build_sealed_runway_api

def _build_public_api():
    _qualification_error = QualificationError
    def _state(partner, gates, sources, runway, as_of, selected_timing, controls_current):
        timing_status = selected_timing.get(partner["name"])
        if runway["runway_state"] not in {"_ready_states", "ASK_CAPACITY_FIRST"} or timing_status is None:
            return "HOLD_RUNWAY", [f"runway state/selection does not admit partner: {runway['runway_state']}"]
        if timing_status == "EXPLICIT_MISS":
            return "HOLD_RUNWAY", ["candidate upstream timing status is EXPLICIT_MISS"]
        if timing_status not in {"EXPLICIT_FIT", "EXPLICIT_NO_KNOWN_CONFLICT", "UNKNOWN_CAPACITY"}:
            return "HOLD_RUNWAY", [f"candidate upstream timing status is unsupported: {timing_status}"]
        if runway["contact_state"] != "ELIGIBLE_FOR_SEPARATE_MUSE_ELECTION_ONLY":
            return "HOLD_CONTACT_POLICY", [f"upstream contact policy is {runway['contact_state']}"]
        if not controls_current:
            return "HOLD_SOURCE", ["one or more solicitation-control sources are not CURRENT"]
        reg = partner["registration"]
        if reg["state"] in {"UNKNOWN", "CLOSED"}:
            return "HOLD_REGISTRATION", [f"registration state is {reg['state']}"]
        if any(sources[r["source_id"]]["status"] != "CURRENT" for r in reg["requirement_refs"] + reg["evidence_refs"]):
            return "HOLD_REGISTRATION", ["registration evidence is not CURRENT"]
        if reg["state"] == "OPEN" and reg["deadline"] is not None and reg["deadline"] <= as_of:
            return "HOLD_REGISTRATION", [f"registration deadline {reg['deadline']} is not after as_of {as_of}"]
    
        blocking, later = [], []
        for disp in partner["gate_dispositions"]:
            gate = gates[disp["gate_id"]]
            stale = any(sources[r["source_id"]]["status"] != "CURRENT" for r in disp["evidence_refs"])
            if disp["state"] != "SATISFIED" or stale:
                token = f"{disp['gate_id']}:{'STALE_EVIDENCE' if stale else disp['state']}"
                (blocking if gate["phase"] == "PRE_OUTREACH" else later).append(token)
        later = [f"later:{x}" for x in sorted(later)]
        if blocking:
            return "HOLD_HARD_GATE", sorted(blocking) + later
        if partner["paid_workshare"]["state"] != "DEFINED":
            return "HOLD_NO_PAID_SEAM", ["paid TJLabs workshare is undefined"] + later
        if timing_status == "UNKNOWN_CAPACITY":
            return "READY_FOR_CAPACITY_MUSE_ELECTION_ONLY", ["qualification gates clear; this candidate upstream capacity remains unverified"] + later
        return "READY_FOR_MUSE_ELECTION_ONLY", ["runway, contact policy, registration, pre-outreach gates, and paid seam are bounded"] + later
    
    
    def _validate_disposition_source_binding(partner: dict[str, Any], gates: dict[str, dict[str, Any]]) -> None:
        for disposition in partner["gate_dispositions"]:
            if disposition["state"] == "UNKNOWN":
                continue
            gate = gates[disposition["gate_id"]]
            gate_sources = {(ref["source_id"], ref["source_sha256"]) for ref in gate["source_refs"]}
            disposition_sources = {(ref["source_id"], ref["source_sha256"]) for ref in disposition["evidence_refs"]}
            if not disposition_sources or not disposition_sources.issubset(gate_sources):
                raise _qualification_error(
                    f"partner {partner['name']} gate {disposition['gate_id']} disposition evidence "
                    "must be wholly bound in that gate's source_refs"
                )
    # Capture the exact imported runway API generation once. Public compile/verify
    # paths below no longer resolve mutable module aliases for these trust roots.
    _normalize_runway = _sealed_normalize_runway
    _compile_runway = _sealed_compile_runway
    _runway_receipt = _sealed_runway_receipt
    _verify_runway = _sealed_verify_runway
    _runway_bytes = _sealed_runway_bytes
    _normalize_input = normalize_input
    _digest = digest
    _state_impl = _state
    _binding_impl = _validate_disposition_source_binding
    _qualification_error = QualificationError
    _input_schema = SCHEMA
    _output_schema = OUTPUT_SCHEMA
    _receipt_schema = RECEIPT_SCHEMA
    _ready_states = frozenset(READY)
    _sha256 = _hashlib.sha256
    _authority_keys = (
        "partner_contact_authorized",
        "buyer_contact_authorized",
        "muse_election_granted",
        "account_registration_authorized",
        "eligibility_certified",
        "portal_submission_authorized",
        "signature_authorized",
        "contract_authorized",
        "award_inferred",
        "payment_authorized",
        "cash_received",
        "revenue_recognized",
    )

    def _authority():
        return {key: False for key in _authority_keys}

    def compile_qualification(raw: Any) -> dict[str, Any]:
        doc = _normalize_input(raw)
        try:
            runway_doc = _normalize_runway(doc["runway_input"])
            upstream = _compile_runway(runway_doc)
            upstream_receipt = _runway_receipt(upstream)
            _verify_runway(runway_doc, upstream, upstream_receipt)
        except Exception as exc:
            raise _qualification_error("runway bundle failed semantic recompilation") from exc
        rows = upstream.get("opportunities")
        if type(rows) is not list or len(rows) != 1 or rows[0].get("id") != doc["opportunity_id"] or upstream.get("as_of") != doc["as_of"]:
            raise _qualification_error("runway output identity/as_of mismatch")
        runway = rows[0]
        selected_rows = runway.get("selected_partners")
        if type(selected_rows) is not list:
            raise _qualification_error("runway selected_partners malformed")
        selected_timing = {}
        for index, row in enumerate(selected_rows):
            if type(row) is not dict or type(row.get("name")) is not str or type(row.get("timing_status")) is not str:
                raise _qualification_error(f"runway selected_partners[{index}] malformed")
            if row["name"] in selected_timing:
                raise _qualification_error("runway selected_partners contains duplicate partner name")
            selected_timing[row["name"]] = row["timing_status"]
        sources = {s["source_id"]: s for s in doc["sources"]}
        controls = [s for s in doc["sources"] if s["kind"] == "SOLICITATION_CONTROL"]
        if not controls:
            raise _qualification_error("at least one SOLICITATION_CONTROL source is required")
        if not all(s["url"] in set(runway.get("source_urls", [])) for s in controls):
            raise _qualification_error("solicitation-control source URL is not bound by upstream runway source_urls")
        gates = {g["gate_id"]: g for g in doc["hard_gates"]}
        partner_rows = []
        for partner in doc["partners"]:
            _binding_impl(partner, gates)
            state, reasons = _state_impl(
                partner,
                gates,
                sources,
                runway,
                doc["as_of"],
                selected_timing,
                all(s["status"] == "CURRENT" for s in controls),
            )
            partner_rows.append({
                "name": partner["name"],
                "state": state,
                "reasons": reasons,
                "registration": partner["registration"],
                "gate_dispositions": partner["gate_dispositions"],
                "paid_workshare": partner["paid_workshare"],
                **_authority(),
            })
        binding = {
            "runway_input_sha256": _sha256(_runway_bytes(runway_doc)).hexdigest(),
            "runway_output_schema": upstream.get("schema"),
            "runway_output_sha256": _sha256(_runway_bytes(upstream)).hexdigest(),
            "runway_receipt_sha256": _digest(upstream_receipt),
            "runway_state": runway["runway_state"],
            "contact_state": runway["contact_state"],
        }
        return {
            "schema": _output_schema,
            "input_schema": _input_schema,
            "as_of": doc["as_of"],
            "opportunity_id": doc["opportunity_id"],
            "runway_binding": binding,
            "sources": doc["sources"],
            "hard_gates": doc["hard_gates"],
            "partners": partner_rows,
            "ready_partner_names": sorted(
                (r["name"] for r in partner_rows if r["state"] in _ready_states),
                key=lambda n: (n.casefold(), n),
            ),
            **_authority(),
        }

    def make_receipt(raw_input: Any, output: dict[str, Any]) -> dict[str, Any]:
        doc = _normalize_input(raw_input)
        semantic = {k: v for k, v in doc.items() if k != "runway_input"}
        semantic["runway_binding"] = output["runway_binding"]
        return {
            "schema": _receipt_schema,
            "semantic_input_sha256": _digest(semantic),
            "output_sha256": _digest(output),
            "opportunity_id": doc["opportunity_id"],
            "as_of": doc["as_of"],
            "runway_input_sha256": output["runway_binding"]["runway_input_sha256"],
            "runway_output_sha256": output["runway_binding"]["runway_output_sha256"],
            "runway_receipt_sha256": output["runway_binding"]["runway_receipt_sha256"],
            **_authority(),
        }

    def verify_bundle(raw_input: Any, output: Any, receipt: Any) -> None:
        if type(output) is not dict or type(receipt) is not dict:
            raise _qualification_error("bundle objects must be exact dicts")
        rows = output.get("partners")
        if type(rows) is not list:
            raise _qualification_error("output partners must be an exact list")
        for where, row in [("output", output), ("receipt", receipt)] + [
            (f"partner[{index}]", row) for index, row in enumerate(rows)
        ]:
            if type(row) is not dict:
                raise _qualification_error(f"{where} must be an exact dict")
            for key in _authority_keys:
                if key not in row or type(row[key]) is not bool or row[key] is not False:
                    raise _qualification_error(f"{where} authority {key} must be exact false")
        expected = compile_qualification(raw_input)
        if output != expected:
            raise _qualification_error("output does not match deterministic recompilation")
        if receipt != make_receipt(raw_input, expected):
            raise _qualification_error("receipt does not match deterministic recompilation")

    return compile_qualification, make_receipt, verify_bundle


compile_qualification, make_receipt, verify_bundle = _build_public_api()
del _build_public_api
# Remove mutable module aliases after capture. Reintroducing attributes with these
# names later cannot alter the captured compile/verify generation.
del _sealed_normalize_runway, _sealed_compile_runway, _sealed_runway_receipt, _sealed_verify_runway, _sealed_runway_bytes


del _hashlib, _json, _date, _timedelta_type
