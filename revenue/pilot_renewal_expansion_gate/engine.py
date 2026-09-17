from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .common import (
    AUTHORITY, GateError, RECEIPT_SCHEMA, SCHEMA, TERMINAL_STATES, TRUTH_CEILING,
    _dt, _exact_keys, _obj, _sha, _z, canonical_json, sha256,
)
from .schema import normalize

def evaluate(doc: dict[str, Any], verified_at: datetime) -> dict[str, Any]:
    now = verified_at.astimezone(timezone.utc)
    evidence = {row["id"]: row for row in doc["evidence"]}
    sources = {row["id"]: row for row in doc["sources"]}
    reasons: list[dict[str, str]] = []

    def check(eid: str, kind: str, subject_id: str) -> bool:
        row = evidence[eid]
        ok = True
        detail: list[str] = []
        if row["kind"] != kind:
            ok = False; detail.append(f"kind={row['kind']} expected={kind}")
        if row["subject_id"] != subject_id:
            ok = False; detail.append("subject mismatch")
        if row["status"] != "VERIFIED":
            ok = False; detail.append(f"status={row['status']}")
        observed = _dt(row["observed_at"], "evidence.observed_at")
        source_observed = _dt(sources[row["source_id"]]["observed_at"], "source.observed_at")
        if source_observed > now:
            ok = False; detail.append("future source observation")
        if observed < source_observed:
            ok = False; detail.append("evidence predates retained source observation")
        if observed > now:
            ok = False; detail.append("future evidence")
        if row.get("valid_through") is not None and _dt(row["valid_through"], "evidence.valid_through") < now:
            ok = False; detail.append("expired evidence")
        if not ok:
            reasons.append({"code": "EVIDENCE_INVALID", "ref": eid, "detail": "; ".join(detail)})
        return ok

    dnr_rows = [row for row in doc["evidence"] if row["kind"] == "DNR" and row["subject_id"] == doc["engagement"]["id"]]
    if any(check(row["id"], "DNR", doc["engagement"]["id"]) for row in dnr_rows):
        decision = "DNR"
    else:
        acceptance_bad = False
        base = doc["commercial_baseline"]
        if not check(base["acceptance_evidence_id"], "BASELINE_ACCEPTANCE", base["id"]):
            acceptance_bad = True
            reasons.append({"code": "BASELINE_NOT_ACCEPTED", "ref": base["id"], "detail": "current verified baseline acceptance missing"})

        for co in doc["change_orders"]:
            if co["state"] == "APPROVED" and not check(co["approval_evidence_id"], "CHANGE_ORDER_APPROVAL", co["id"]):
                acceptance_bad = True
                reasons.append({"code": "CHANGE_ORDER_APPROVAL_MISSING", "ref": co["id"], "detail": "APPROVED state lacks matching current verified approval"})
            elif co["state"] != "APPROVED":
                reasons.append({"code": "CHANGE_ORDER_NOT_IN_BASELINE", "ref": co["id"], "detail": f"state={co['state']} remains outside accepted commercial lineage"})

        for ms in doc["milestones"]:
            if ms["required"]:
                if ms["state"] != "ACCEPTED":
                    acceptance_bad = True
                    reasons.append({"code": "MILESTONE_NOT_ACCEPTED", "ref": ms["id"], "detail": f"state={ms['state']} is not buyer acceptance"})
                elif not check(ms["acceptance_evidence_id"], "MILESTONE_ACCEPTANCE", ms["id"]):
                    acceptance_bad = True
                    reasons.append({"code": "MILESTONE_ACCEPTANCE_EVIDENCE_MISSING", "ref": ms["id"], "detail": "ACCEPTED state lacks matching current verified evidence"})

        payment_bad = False
        for payment in doc["payments"]:
            if payment["required_for_renewal"]:
                if payment["state"] != "SETTLED":
                    payment_bad = True
                    reasons.append({"code": "PAYMENT_NOT_SETTLED", "ref": payment["id"], "detail": f"state={payment['state']} does not establish payment"})
                elif not check(payment["settlement_evidence_id"], "PAYMENT_SETTLED", payment["id"]):
                    payment_bad = True
                    reasons.append({"code": "PAYMENT_EVIDENCE_MISSING", "ref": payment["id"], "detail": "SETTLED state lacks matching current verified evidence"})

        evidence_bad = False
        window = doc["renewal_window"]
        if not check(window["evidence_id"], "RENEWAL_WINDOW", doc["engagement"]["id"]):
            evidence_bad = True
            reasons.append({"code": "WINDOW_EVIDENCE_INVALID", "ref": doc["engagement"]["id"], "detail": "renewal window requires current verified evidence"})
        for finding in doc["support_findings"]:
            if not check(finding["evidence_id"], "SUPPORT_FINDING", finding["id"]):
                evidence_bad = True
                reasons.append({"code": "SUPPORT_FINDING_UNBOUND", "ref": finding["id"], "detail": "support finding lacks current verified evidence"})
        for gap in doc["gaps"]:
            if not check(gap["evidence_id"], "GAP_STATUS", gap["id"]):
                evidence_bad = True
                reasons.append({"code": "GAP_EVIDENCE_INVALID", "ref": gap["id"], "detail": "gap status lacks current verified evidence"})
            if gap["blocking"] and gap["state"] == "OPEN":
                evidence_bad = True
                reasons.append({"code": "BLOCKING_GAP_OPEN", "ref": gap["id"], "detail": f"{gap['kind']} gap remains open"})
        for hypothesis in doc["expansion_hypotheses"]:
            for eid in hypothesis["supporting_evidence_ids"]:
                row = evidence[eid]
                if row["status"] != "VERIFIED" or _dt(row["observed_at"], "evidence.observed_at") > now:
                    evidence_bad = True
                    reasons.append({"code": "EXPANSION_SUPPORT_UNVERIFIED", "ref": hypothesis["id"], "detail": f"support {eid} is not current VERIFIED evidence"})

        open_at = _dt(window["open_at"], "renewal_window.open_at")
        close_at = _dt(window["close_at"], "renewal_window.close_at")
        window_bad = not (open_at <= now <= close_at)
        if window_bad:
            reasons.append({"code": "OUTSIDE_RENEWAL_WINDOW", "ref": doc["engagement"]["id"], "detail": f"verifier time {_z(now)} not within [{_z(open_at)}, {_z(close_at)}]"})

        if acceptance_bad:
            decision = "HOLD_ACCEPTANCE"
        elif payment_bad:
            decision = "HOLD_PAYMENT"
        elif evidence_bad:
            decision = "HOLD_EVIDENCE"
        elif window_bad:
            decision = "HOLD_WINDOW"
        else:
            decision = "READY_FOR_RENEWAL_REVIEW"

    if decision not in TERMINAL_STATES:
        raise AssertionError("unreachable decision")
    return {
        "schema": SCHEMA,
        "decision": decision,
        "verified_at": _z(now),
        "truth_ceiling": TRUTH_CEILING,
        "engagement_id": doc["engagement"]["id"],
        "organization_id": doc["engagement"]["organization_id"],
        "commercial_baseline": doc["commercial_baseline"],
        "approved_change_orders": [x for x in doc["change_orders"] if x["state"] == "APPROVED"],
        "milestones": doc["milestones"],
        "payments": doc["payments"],
        "support_findings": doc["support_findings"],
        "gaps": doc["gaps"],
        "renewal_window": doc["renewal_window"],
        "expansion_hypotheses": doc["expansion_hypotheses"],
        "communication": doc["communication"],
        "reasons": reasons,
        "authority": dict(AUTHORITY),
    }


def compile_packet(raw: Any, verified_at: datetime) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    doc = normalize(raw)
    packet = evaluate(doc, verified_at)
    normalized_hash = sha256(canonical_json(doc))
    packet_hash = sha256(canonical_json(packet))
    receipt_core = {
        "schema": RECEIPT_SCHEMA,
        "normalized_input_sha256": normalized_hash,
        "packet_sha256": packet_hash,
        "decision": packet["decision"],
        "verified_at": packet["verified_at"],
        "valid_until": doc["renewal_window"]["close_at"],
        "authority": dict(AUTHORITY),
    }
    receipt = dict(receipt_core)
    receipt["receipt_sha256"] = sha256(canonical_json(receipt_core))
    return doc, packet, receipt


def verify_current(raw: Any, packet: Any, receipt: Any, verified_at: datetime) -> dict[str, Any]:
    doc = normalize(raw)
    packet_obj = _obj(packet, "packet")
    receipt_obj = _obj(receipt, "receipt")
    expected_receipt_fields = {"schema", "normalized_input_sha256", "packet_sha256", "decision", "verified_at", "valid_until", "authority", "receipt_sha256"}
    _exact_keys(receipt_obj, expected_receipt_fields, "receipt", expected_receipt_fields)
    if receipt_obj["schema"] != RECEIPT_SCHEMA:
        raise GateError("receipt.schema mismatch")
    core = {k: receipt_obj[k] for k in expected_receipt_fields - {"receipt_sha256"}}
    if _sha(receipt_obj["receipt_sha256"], "receipt.receipt_sha256") != sha256(canonical_json(core)):
        raise GateError("receipt digest mismatch")
    if receipt_obj["normalized_input_sha256"] != sha256(canonical_json(doc)):
        raise GateError("input digest mismatch")
    if receipt_obj["packet_sha256"] != sha256(canonical_json(packet_obj)):
        raise GateError("packet digest mismatch")
    if receipt_obj["decision"] != packet_obj.get("decision"):
        raise GateError("receipt/packet decision mismatch")
    if receipt_obj["authority"] != AUTHORITY or packet_obj.get("authority") != AUTHORITY:
        raise GateError("authority block mismatch")
    if receipt_obj["valid_until"] != doc["renewal_window"]["close_at"]:
        raise GateError("receipt valid_until is not bound to renewal window")
    if receipt_obj["verified_at"] != packet_obj.get("verified_at"):
        raise GateError("receipt/packet verifier timestamp mismatch")

    compiled_at = _dt(receipt_obj["verified_at"], "receipt.verified_at")
    expected_packet = evaluate(doc, compiled_at)
    if canonical_json(expected_packet) != canonical_json(packet_obj):
        raise GateError("packet does not reproduce from bound input and verifier timestamp")

    current = evaluate(doc, verified_at)
    now = verified_at.astimezone(timezone.utc)
    if compiled_at > now:
        raise GateError("receipt is future-dated relative to verifier")
    valid_until = _dt(receipt_obj["valid_until"], "receipt.valid_until")
    same_decision = current["decision"] == receipt_obj["decision"]
    current_valid = same_decision and now <= valid_until and current["decision"] == "READY_FOR_RENEWAL_REVIEW"
    return {
        "schema": "pilot-renewal-expansion-current-verification/v1",
        "integrity_valid": True,
        "current_valid": current_valid,
        "compiled_decision": receipt_obj["decision"],
        "current_decision": current["decision"],
        "verified_at": _z(now),
        "valid_until": receipt_obj["valid_until"],
        "authority": dict(AUTHORITY),
    }

