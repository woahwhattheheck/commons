from __future__ import annotations

import copy
import json
import unittest

from opportunities.inkomoko_ai_platform.engine import (
    CarrierError,
    QUALIFICATION_GATES,
    SUBMISSION_GATES,
    TECHNICAL_REQUIREMENTS,
    canonical_json,
    compile_carrier,
    strict_json_loads,
    verify_carrier,
)


def row(rid: str, state: str = "SUPPORTED") -> dict:
    return {"id": rid, "state": state, "evidence_sha256": "1" * 64 if state == "SUPPORTED" else None}


def event(eid: str, kind: str, seq: int, *, channel="WEB", language="en", role="LEARNER", ref="CTX-1") -> dict:
    return {"id": eid, "kind": kind, "channel": channel, "language": language, "role": role, "sequence": seq, "payload_ref": ref}


def suite() -> list[dict]:
    return [
        {"scenario_id":"progressive_learning","synthetic":True,"events":[event(f"p{i}",f"STAGE_{i}_COMPLETE",i) for i in range(1,5)]},
        {"scenario_id":"content_revision","synthetic":True,"events":[event("c1","CONTENT_VERSION_OLD",1),event("c2","CONTENT_VERSION_NEW",2),event("c3","STALE_VERSION_REJECTED",3)]},
        {"scenario_id":"rbac","synthetic":True,"events":[event("r1","AUTHORIZED_ACTION",1,role="COACH"),event("r2","UNAUTHORIZED_ACTION_REJECTED",2,role="LEARNER")]},
        {"scenario_id":"multilingual_routing","synthetic":True,"events":[event(f"m{i}","ROUTED_RESPONSE",i,language=lang) for i,lang in enumerate(["en","fr","rw","sw"],1)]},
        {"scenario_id":"channel_continuity","synthetic":True,"events":[event("cc1","SESSION_OPEN",1,channel="WEB",ref="CTX-CONT"),event("cc2","SESSION_RESUME",2,channel="WHATSAPP_SYNTHETIC",ref="CTX-CONT")]},
        {"scenario_id":"human_escalation","synthetic":True,"events":[event("h1","ESCALATION_REQUESTED",1),event("h2","CONTEXT_PRESERVED",2)]},
        {"scenario_id":"adapter_boundaries","synthetic":True,"events":[event("a1","CBS_ADAPTER_STUB",1),event("a2","INKOBOOK_ADAPTER_STUB",2),event("a3","POWERBI_ADAPTER_STUB",3),event("a4","LIVE_CREDENTIAL_REFUSED",4)]},
        {"scenario_id":"replay_idempotency","synthetic":True,"events":[event("i1","DUPLICATE_EFFECT_COLLAPSED",1),event("i2","CONFLICTING_REPLAY_REJECTED",2)]},
        {"scenario_id":"stale_content_policy","synthetic":True,"events":[event("s1","STALE_POLICY_REJECTED",1),event("s2","CURRENT_POLICY_ACCEPTED",2)]},
        {"scenario_id":"analytics_events","synthetic":True,"events":[event("x1","ANALYTICS_EVENT_EMITTED",1),event("x2","ANALYTICS_DUPLICATE_COLLAPSED",2)]},
    ]


def packet(*, official=False, qualification=True, submission=True) -> dict:
    qstate = "SUPPORTED" if qualification else "OWNER_EVIDENCE_REQUIRED"
    sstate = "SUPPORTED" if submission else "OWNER_EVIDENCE_REQUIRED"
    return {
        "opportunity_id":"INKOMOKO-AI-TRAINING-PLATFORM-2026",
        "sources":[{
            "id":"SOURCE-1",
            "authority":"BUYER_OFFICIAL" if official else "PUBLIC_REPRODUCTION",
            "url":"https://example.invalid/inkomoko-source",
            "content_sha256":"2"*64,
            "captured_at":"2026-09-13T10:00:00Z",
            "reviewed":True,
        }],
        "technical":[row(rid) for rid in TECHNICAL_REQUIREMENTS],
        "qualification":[row(rid,qstate) for rid in QUALIFICATION_GATES],
        "submission":[row(rid,sstate) for rid in SUBMISSION_GATES],
    }


class CarrierTests(unittest.TestCase):
    NOW = "2026-09-15T07:30:00Z"

    def test_public_reproduction_never_submission_ready(self):
        report = compile_carrier(packet(official=False), suite(), self.NOW)
        self.assertEqual(report["projection"]["pursuit_posture"], "PRIME_CANDIDATE")
        self.assertEqual(report["projection"]["proposal_state"], "HOLD_CONTROLLING_SOURCE")
        self.assertFalse(report["projection"]["proposal_submission_authorized"])

    def test_prime_requires_every_qualification_gate(self):
        p = packet(official=True)
        p["qualification"][0] = row(QUALIFICATION_GATES[0], "OWNER_EVIDENCE_REQUIRED")
        report = compile_carrier(p, suite(), self.NOW)
        self.assertEqual(report["projection"]["pursuit_posture"], "TEAMING_CANDIDATE")
        self.assertEqual(report["projection"]["proposal_state"], "HOLD_OWNER_EVIDENCE")

    def test_all_gates_and_official_source_can_reach_owner_review_only(self):
        report = compile_carrier(packet(official=True), suite(), self.NOW)
        self.assertEqual(report["projection"]["proposal_state"], "READY_FOR_OWNER_PROPOSAL_REVIEW")
        self.assertFalse(report["projection"]["external_contact_authorized"])
        self.assertFalse(report["projection"]["contract_acceptance_authorized"])

    def test_technical_gap_forces_hold(self):
        p = packet(official=True)
        p["technical"][0] = row(TECHNICAL_REQUIREMENTS[0], "GAP")
        report = compile_carrier(p, suite(), self.NOW)
        self.assertEqual(report["projection"]["pursuit_posture"], "HOLD")

    def test_acceptance_scenario_missing_fails_closed(self):
        with self.assertRaises(CarrierError):
            compile_carrier(packet(official=True), suite()[:-1], self.NOW)

    def test_acceptance_live_credential_evidence_is_required_to_be_refused(self):
        cases = suite()
        target = next(c for c in cases if c["scenario_id"] == "adapter_boundaries")
        target["events"] = [e for e in target["events"] if e["kind"] != "LIVE_CREDENTIAL_REFUSED"]
        report = compile_carrier(packet(official=True), cases, self.NOW)
        self.assertEqual(report["projection"]["pursuit_posture"], "HOLD")
        self.assertFalse(report["projection"]["synthetic_acceptance"]["passed"])

    def test_future_source_capture_rejected(self):
        p = packet()
        p["sources"][0]["captured_at"] = "2026-09-16T00:00:00Z"
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_unknown_requirement_rejected(self):
        p = packet()
        p["technical"][0]["id"] = "INVENTED_REQUIREMENT"
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_supported_gate_requires_digest(self):
        p = packet()
        p["qualification"][0]["evidence_sha256"] = None
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_non_supported_gate_cannot_smuggle_digest(self):
        p = packet()
        p["qualification"][0]["state"] = "GAP"
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_bool_int_alias_rejected_in_acceptance_sequence(self):
        cases = suite()
        cases[0]["events"][0]["sequence"] = True
        with self.assertRaises(CarrierError):
            compile_carrier(packet(), cases, self.NOW)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(CarrierError):
            strict_json_loads('{"x":1,"x":2}')

    def test_nan_rejected(self):
        with self.assertRaises(CarrierError):
            strict_json_loads('{"x":NaN}')

    def test_report_verification_detects_tamper(self):
        p = packet(official=True)
        a = suite()
        report = compile_carrier(p, a, self.NOW)
        self.assertTrue(verify_carrier(p, a, self.NOW, report))
        report["projection"]["qualification_supported"] -= 1
        self.assertFalse(verify_carrier(p, a, self.NOW, report))

    def test_input_order_does_not_change_report(self):
        p1 = packet(official=True)
        p2 = copy.deepcopy(p1)
        p2["technical"].reverse()
        p2["qualification"].reverse()
        p2["submission"].reverse()
        a1 = suite()
        a2 = list(reversed(copy.deepcopy(a1)))
        self.assertEqual(canonical_json(compile_carrier(p1,a1,self.NOW)), canonical_json(compile_carrier(p2,a2,self.NOW)))

    def test_cross_opportunity_rejected(self):
        p = packet()
        p["opportunity_id"] = "OTHER"
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_unknown_source_authority_rejected(self):
        p = packet()
        p["sources"][0]["authority"] = "TRUST_ME"
        with self.assertRaises(CarrierError):
            compile_carrier(p, suite(), self.NOW)

    def test_submission_gap_blocks_ready(self):
        p = packet(official=True)
        p["submission"][3] = row(SUBMISSION_GATES[3], "OWNER_EVIDENCE_REQUIRED")
        report = compile_carrier(p, suite(), self.NOW)
        self.assertEqual(report["projection"]["proposal_state"], "HOLD_OWNER_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
