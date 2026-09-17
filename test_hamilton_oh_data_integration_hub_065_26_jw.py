import copy
import unittest

from opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate import (
    GateError,
    compile_pursuit,
    digest,
    loads_strict,
    verify_receipt,
)

BASE_LEDGER = {
    "opportunity_id": "065-26/JW",
    "sources": [
        {
            "id": "portal",
            "authority": "OFFICIAL_PORTAL_ENTRY",
            "retrieved": False,
            "url": "https://hamiltoncountyohio.gob2g.com/",
            "observed_at": "2026-09-17T07:05:00Z",
            "claims": {},
            "controls": [],
        },
        {
            "id": "mirror",
            "authority": "MIRROR",
            "retrieved": True,
            "content_sha256": "a" * 64,
            "url": "https://example.invalid/mirror",
            "observed_at": "2026-09-17T07:05:00Z",
            "claims": {
                "response_deadline": "2099-10-14T11:00:00-04:00",
                "teaming_rules": True,
                "submission_mechanics": "portal",
            },
            "controls": [],
        },
    ],
}

BASE_REQS = {
    "opportunity_id": "065-26/JW",
    "requirements": [
        {"id": "submission_mechanics", "state": "UNKNOWN", "evidence": []},
        {"id": "eligibility", "state": "UNKNOWN", "evidence": []},
        {"id": "security_compliance", "state": "UNKNOWN", "evidence": []},
        {"id": "past_performance", "state": "UNKNOWN", "evidence": []},
        {"id": "insurance_legal", "state": "UNKNOWN", "evidence": []},
        {"id": "pricing", "state": "UNKNOWN", "evidence": []},
        {"id": "integration_engineering", "state": "UNKNOWN", "evidence": []},
        {"id": "validation_evidence", "state": "UNKNOWN", "evidence": []},
        {"id": "delivery_capacity", "state": "UNKNOWN", "evidence": []},
        {"id": "partner_prime", "state": "UNKNOWN", "evidence": []},
    ],
}

BASE_EVIDENCE = {"opportunity_id": "065-26/JW", "evidence": []}


def with_official(ledger, *, deadline="2026-10-14T11:00:00-04:00", teaming=True):
    out = copy.deepcopy(ledger)
    claims = {
        "teaming_rules": teaming,
        "submission_mechanics": "official portal",
    }
    controls = ["teaming_rules", "submission_mechanics"]
    if deadline is not None:
        claims["response_deadline"] = deadline
        controls.append("response_deadline")
    out["sources"].append(
        {
            "id": "packet",
            "authority": "OFFICIAL_CONTROLLING_PACKET",
            "retrieved": True,
            "content_sha256": "b" * 64,
            "url": "https://hamiltoncountyohio.gob2g.com/packet",
            "observed_at": "2026-09-18T00:00:00Z",
            "claims": claims,
            "controls": controls,
        }
    )
    return out


def _row(reqs, rid):
    return next(row for row in reqs["requirements"] if row["id"] == rid)


def bind_evidence(ledger, reqs, manifest, rid, evidence_class, *, eid=None, source_id=None, fill="c"):
    if eid is None:
        eid = f"evidence-{rid}"
    if source_id is None:
        source_id = f"source-{eid}"
        ledger["sources"].append(
            {
                "id": source_id,
                "authority": "INTERNAL_EVIDENCE",
                "retrieved": True,
                "content_sha256": fill * 64,
                "url": f"repo://retained/{eid}",
                "observed_at": "2026-09-18T00:00:00Z",
                "claims": {},
                "controls": [],
            }
        )
        content_sha = fill * 64
    else:
        source = next(source for source in ledger["sources"] if source["id"] == source_id)
        content_sha = source["content_sha256"]
    manifest["evidence"].append(
        {
            "id": eid,
            "opportunity_id": "065-26/JW",
            "requirement_id": rid,
            "evidence_class": evidence_class,
            "content_sha256": content_sha,
            "source_id": source_id,
        }
    )
    row = _row(reqs, rid)
    row["state"] = "PROVEN"
    row["evidence"] = [eid]
    return eid


def prime_inputs(*, deadline="2026-10-14T11:00:00-04:00"):
    ledger = with_official(BASE_LEDGER, deadline=deadline)
    reqs = copy.deepcopy(BASE_REQS)
    manifest = copy.deepcopy(BASE_EVIDENCE)
    official = {
        "submission_mechanics", "eligibility", "security_compliance",
        "insurance_legal", "pricing",
    }
    fills = iter("cdefghijkl")
    for rid in (
        "submission_mechanics", "eligibility", "security_compliance",
        "past_performance", "insurance_legal", "pricing",
    ):
        if rid in official:
            bind_evidence(
                ledger, reqs, manifest, rid, "OFFICIAL_REQUIREMENT",
                eid=f"official-{rid}", source_id="packet",
            )
        else:
            bind_evidence(
                ledger, reqs, manifest, rid, "OWNER_QUALIFICATION",
                fill=next(fills),
            )
    return ledger, reqs, manifest


def teaming_inputs(*, deadline="2026-10-14T11:00:00-04:00", teaming=True):
    ledger = with_official(BASE_LEDGER, deadline=deadline, teaming=teaming)
    reqs = copy.deepcopy(BASE_REQS)
    manifest = copy.deepcopy(BASE_EVIDENCE)
    bind_evidence(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY", fill="c")
    bind_evidence(ledger, reqs, manifest, "validation_evidence", "OWNER_CAPABILITY", fill="d")
    bind_evidence(ledger, reqs, manifest, "delivery_capacity", "OWNER_CAPACITY", fill="e")
    bind_evidence(ledger, reqs, manifest, "partner_prime", "PARTNER_DUE_DILIGENCE", fill="f")
    return ledger, reqs, manifest


class HamiltonPursuitGateTests(unittest.TestCase):
    def test_baseline_missing_packet_is_hold(self):
        packet = compile_pursuit(BASE_LEDGER, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("CONTROLLING_PACKET_NOT_ACQUIRED", packet["reasons"])
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])
        self.assertFalse(packet["authority"]["mirror_can_control_buyer_terms"])
        self.assertTrue(verify_receipt(
            packet, BASE_LEDGER, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z"
        ))

    def test_mirror_cannot_control_buyer_fields(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][1]["controls"] = ["response_deadline"]
        with self.assertRaisesRegex(GateError, "cannot control buyer fields"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_arbitrary_evidence_ref_cannot_mint_proven(self):
        reqs = copy.deepcopy(BASE_REQS)
        _row(reqs, "integration_engineering").update(
            {"state": "PROVEN", "evidence": ["retained-owner-or-official-evidence"]}
        )
        with self.assertRaisesRegex(GateError, "evidence ref not retained"):
            compile_pursuit(BASE_LEDGER, reqs, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_cross_opportunity_evidence_rejected(self):
        ledger, reqs, manifest = teaming_inputs()
        manifest["evidence"][0]["opportunity_id"] = "OTHER"
        with self.assertRaisesRegex(GateError, "opportunity_id mismatch"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_wrong_class_evidence_rejected(self):
        ledger, reqs, manifest = teaming_inputs()
        manifest["evidence"][0]["evidence_class"] = "PARTNER_DUE_DILIGENCE"
        with self.assertRaisesRegex(GateError, "not admissible"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_digest_transplant_rejected(self):
        ledger, reqs, manifest = teaming_inputs()
        manifest["evidence"][0]["content_sha256"] = "9" * 64
        with self.assertRaisesRegex(GateError, "does not bind source"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_requirement_transplant_rejected(self):
        ledger, reqs, manifest = teaming_inputs()
        first = manifest["evidence"][0]
        first["requirement_id"] = "validation_evidence"
        with self.assertRaisesRegex(GateError, "different requirement"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_official_class_must_bind_official_source(self):
        ledger = with_official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        bind_evidence(ledger, reqs, manifest, "eligibility", "OWNER_QUALIFICATION", fill="c")
        manifest["evidence"][0]["evidence_class"] = "OFFICIAL_REQUIREMENT"
        with self.assertRaisesRegex(GateError, "official evidence must bind official"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_retained_evidence_cannot_disappear_behind_unknown_state(self):
        ledger, reqs, manifest = teaming_inputs()
        _row(reqs, "integration_engineering")["state"] = "UNKNOWN"
        _row(reqs, "integration_engineering")["evidence"] = []
        with self.assertRaisesRegex(GateError, "no matching PROVEN requirement"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_prime_requires_bound_evidence_and_future_official_deadline(self):
        ledger, reqs, manifest = prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "PRIME")
        self.assertEqual(packet["gaps"]["prime"], [])
        self.assertEqual(packet["authority"]["response_deadline_source"], "packet")
        self.assertTrue(packet["evidence_bindings"]["past_performance"])
        self.assertTrue(verify_receipt(packet, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"))

    def test_prime_without_controlled_deadline_is_hold(self):
        ledger, reqs, manifest = prime_inputs(deadline=None)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])

    def test_team_requires_permission_partner_specialist_evidence_and_deadline(self):
        ledger, reqs, manifest = teaming_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "TEAMING")
        self.assertIn("PRIME_GATES_UNPROVEN", packet["reasons"])

    def test_team_without_controlled_deadline_is_hold(self):
        ledger, reqs, manifest = teaming_inputs(deadline=None)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])

    def test_team_not_allowed_holds(self):
        ledger, reqs, manifest = teaming_inputs(teaming=False)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY", packet["reasons"])

    def test_official_deadline_pass_is_no_bid(self):
        ledger = with_official(BASE_LEDGER, deadline="2026-09-17T01:00:00-04:00")
        packet = compile_pursuit(ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "NO_BID")
        self.assertIn("OFFICIAL_RESPONSE_DEADLINE_PASSED", packet["reasons"])

    def test_rehashed_forged_prime_and_revenue_receipt_fails_semantic_verify(self):
        ledger, reqs, manifest = teaming_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        forged = copy.deepcopy(packet)
        forged["decision"] = "PRIME"
        forged["external_authority"]["revenue"] = True
        forged.pop("receipt_sha256")
        forged["receipt_sha256"] = digest(forged)
        self.assertFalse(verify_receipt(forged, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"))

    def test_semantic_verify_binds_evaluation_time(self):
        ledger, reqs, manifest = prime_inputs(deadline="2026-09-18T02:00:00Z")
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertFalse(verify_receipt(packet, ledger, reqs, manifest, now="2026-09-18T03:00:00Z"))

    def test_duplicate_json_keys_fail(self):
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            loads_strict('{"opportunity_id":"065-26/JW","opportunity_id":"x"}')

    def test_nonfinite_json_fails(self):
        with self.assertRaisesRegex(GateError, "non-finite"):
            loads_strict('{"x": NaN}')

    def test_bool_int_alias_fails_for_retrieved(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][0]["retrieved"] = 1
        with self.assertRaisesRegex(GateError, "must be a JSON boolean"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_conflicting_official_authority_fails(self):
        ledger = with_official(BASE_LEDGER)
        other = copy.deepcopy(ledger["sources"][-1])
        other["id"] = "addendum"
        other["authority"] = "OFFICIAL_ADDENDUM"
        other["content_sha256"] = "d" * 64
        other["claims"]["response_deadline"] = "2026-10-15T11:00:00-04:00"
        ledger["sources"].append(other)
        with self.assertRaisesRegex(GateError, "conflicting official authority"):
            compile_pursuit(ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-18T01:00:00Z")

    def test_external_authority_always_false(self):
        ledger, reqs, manifest = prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertTrue(packet["external_authority"])
        self.assertFalse(any(packet["external_authority"].values()))


if __name__ == "__main__":
    unittest.main()
