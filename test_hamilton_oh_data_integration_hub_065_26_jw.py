import copy
import unittest

from opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate import (
    GateError,
    compile_pursuit,
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
        {"id": "integration_engineering", "state": "PROVEN", "evidence": ["x"]},
        {"id": "validation_evidence", "state": "PROVEN", "evidence": ["y"]},
        {"id": "delivery_capacity", "state": "PROVEN", "evidence": ["z"]},
        {"id": "partner_prime", "state": "UNKNOWN", "evidence": []},
    ],
}


def with_official(ledger, *, deadline="2026-10-14T11:00:00-04:00", teaming=True):
    out = copy.deepcopy(ledger)
    out["sources"].append(
        {
            "id": "packet",
            "authority": "OFFICIAL_CONTROLLING_PACKET",
            "retrieved": True,
            "content_sha256": "b" * 64,
            "url": "https://hamiltoncountyohio.gob2g.com/packet",
            "observed_at": "2026-09-18T00:00:00Z",
            "claims": {
                "response_deadline": deadline,
                "teaming_rules": teaming,
                "submission_mechanics": "official portal",
            },
            "controls": ["response_deadline", "teaming_rules", "submission_mechanics"],
        }
    )
    return out


class HamiltonPursuitGateTests(unittest.TestCase):
    def test_baseline_missing_packet_is_hold(self):
        packet = compile_pursuit(BASE_LEDGER, BASE_REQS, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("CONTROLLING_PACKET_NOT_ACQUIRED", packet["reasons"])
        self.assertFalse(packet["authority"]["mirror_can_control_buyer_terms"])
        self.assertTrue(verify_receipt(packet))

    def test_mirror_cannot_control_buyer_fields(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][1]["controls"] = ["response_deadline"]
        with self.assertRaisesRegex(GateError, "cannot control buyer fields"):
            compile_pursuit(bad, BASE_REQS, now="2026-09-17T07:05:00Z")

    def test_mirror_future_deadline_cannot_prevent_hold(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][1]["claims"]["response_deadline"] = "2199-01-01T00:00:00Z"
        packet = compile_pursuit(bad, BASE_REQS, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIsNone(packet["authority"]["response_deadline_source"])

    def test_prime_requires_every_prime_gate(self):
        ledger = with_official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        for row in reqs["requirements"]:
            if row["id"] in {
                "submission_mechanics", "eligibility", "security_compliance",
                "past_performance", "insurance_legal", "pricing",
            }:
                row["state"] = "PROVEN"
                row["evidence"] = ["retained-owner-or-official-evidence"]
        packet = compile_pursuit(ledger, reqs, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "PRIME")
        self.assertEqual(packet["gaps"]["prime"], [])
        self.assertTrue(verify_receipt(packet))

    def test_team_requires_official_permission_partner_and_specialist_evidence(self):
        ledger = with_official(BASE_LEDGER, teaming=True)
        reqs = copy.deepcopy(BASE_REQS)
        for row in reqs["requirements"]:
            if row["id"] == "partner_prime":
                row["state"] = "PROVEN"
                row["evidence"] = ["partner-due-diligence"]
        packet = compile_pursuit(ledger, reqs, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "TEAMING")
        self.assertIn("PRIME_GATES_UNPROVEN", packet["reasons"])

    def test_team_not_allowed_holds(self):
        ledger = with_official(BASE_LEDGER, teaming=False)
        reqs = copy.deepcopy(BASE_REQS)
        for row in reqs["requirements"]:
            if row["id"] == "partner_prime":
                row["state"] = "PROVEN"
                row["evidence"] = ["partner"]
        packet = compile_pursuit(ledger, reqs, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY", packet["reasons"])

    def test_official_deadline_pass_is_no_bid(self):
        ledger = with_official(BASE_LEDGER, deadline="2026-09-17T01:00:00-04:00")
        packet = compile_pursuit(ledger, BASE_REQS, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "NO_BID")
        self.assertIn("OFFICIAL_RESPONSE_DEADLINE_PASSED", packet["reasons"])

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
            compile_pursuit(bad, BASE_REQS, now="2026-09-17T07:05:00Z")

    def test_conflicting_official_authority_fails(self):
        ledger = with_official(BASE_LEDGER)
        other = copy.deepcopy(ledger["sources"][-1])
        other["id"] = "addendum"
        other["authority"] = "OFFICIAL_ADDENDUM"
        other["content_sha256"] = "c" * 64
        other["claims"]["response_deadline"] = "2026-10-15T11:00:00-04:00"
        ledger["sources"].append(other)
        with self.assertRaisesRegex(GateError, "conflicting official authority"):
            compile_pursuit(ledger, BASE_REQS, now="2026-09-18T01:00:00Z")

    def test_receipt_tamper_detected(self):
        packet = compile_pursuit(BASE_LEDGER, BASE_REQS, now="2026-09-17T07:05:00Z")
        packet["decision"] = "PRIME"
        self.assertFalse(verify_receipt(packet))

    def test_external_authority_always_false(self):
        packet = compile_pursuit(with_official(BASE_LEDGER), BASE_REQS, now="2026-09-18T01:00:00Z")
        self.assertTrue(packet["external_authority"])
        self.assertFalse(any(packet["external_authority"].values()))


if __name__ == "__main__":
    unittest.main()
