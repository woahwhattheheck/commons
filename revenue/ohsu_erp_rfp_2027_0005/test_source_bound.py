from __future__ import annotations
import copy
import datetime as dt
import json
import pathlib
import subprocess
import sys
import unittest
from revenue.ohsu_erp_rfp_2027_0005 import source_bound as s

ROOT = pathlib.Path(__file__).resolve().parent
A = "1" * 64
B = "2" * 64
C = "3" * 64

def facts(*, route="TEAMING", commitment=False, all_satisfied=False, partner_gates=()):
    partner_gates = set(partner_gates)
    rows = []
    for rid in s.REQUIREMENT_IDS:
        if all_satisfied:
            partner = rid in partner_gates
            rows.append({
                "requirement_id": rid,
                "state": "SATISFIED",
                "basis": "NAMED_COMMITTED_TEAM_PARTNER" if partner else "RESPONDENT",
                "entity_ref": "prime.example" if partner else "token-junkie-labs",
                "evidence_sha256": B if partner else A,
            })
        else:
            rows.append({"requirement_id": rid, "state": "UNKNOWN", "basis": "NONE",
                         "entity_ref": None, "evidence_sha256": None})
    return {
        "schema": s.SCHEMA_FACTS,
        "route": route,
        "source_binding": {"controlling_pack_sha256": s.CONTROLLING_PACK_SHA256,
                           "supplier_qa_sha256": s.SUPPLIER_QA_SHA256},
        "requirements": rows,
        "teaming_commitment": (
            {"status": "CONFIRMED", "partner_ref": "prime.example", "evidence_sha256": C}
            if commitment else
            {"status": "UNCONFIRMED", "partner_ref": None, "evidence_sha256": None}
        ),
        "intent_receipt": None,
        "owner_reviewed": True,
    }

class SourceBoundTests(unittest.TestCase):
    def before_intent(self):
        return dt.datetime(2026, 9, 15, 12, 0, tzinfo=dt.timezone.utc)

    def test_manifest_matches_compiler_constants(self):
        m = json.loads((ROOT / "source_manifest.json").read_text())
        self.assertEqual(m["received_sources"]["controlling_rfp_workbook"]["sha256"], s.CONTROLLING_PACK_SHA256)
        self.assertEqual(m["received_sources"]["supplier_qa_workbook"]["sha256"], s.SUPPLIER_QA_SHA256)
        self.assertEqual({r["requirement_id"] for r in m["normalized_minimum_gates"]}, set(s.REQUIREMENT_IDS))

    def test_unconfirmed_team_route_is_candidate_not_ready(self):
        p = s._compile_at(facts(), self.before_intent())
        self.assertEqual(p["status"], "TEAMING_CANDIDATE")
        self.assertIn("NO_NAMED_COMMITTED_TEAM_PARTNER", p["blockers"])
        self.assertEqual(p["qualification_basis_counts"]["UNSATISFIED"], len(s.REQUIREMENT_IDS))
        self.assertEqual(p["workshare"]["fixed_price_usd"], 12500)
        self.assertEqual(p["workshare"]["commercial_status"], "PROPOSED_NOT_ACCEPTED")
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_wrong_controlling_pack_digest_fails_closed(self):
        f = facts(); f["source_binding"]["controlling_pack_sha256"] = A
        with self.assertRaisesRegex(s.ContractError, "controlling pack digest"):
            s._compile_at(f, self.before_intent())

    def test_wrong_supplier_qa_digest_fails_closed(self):
        f = facts(); f["source_binding"]["supplier_qa_sha256"] = A
        with self.assertRaisesRegex(s.ContractError, "supplier Q&A digest"):
            s._compile_at(f, self.before_intent())

    def test_registry_cannot_omit_minimum_gate(self):
        f = facts(); f["requirements"].pop()
        with self.assertRaisesRegex(s.ContractError, "exact normalized gate set"):
            s._compile_at(f, self.before_intent())

    def test_unconfirmed_target_contributes_zero_qualifications(self):
        f = facts()
        f["requirements"][0].update({
            "state":"SATISFIED","basis":"NAMED_COMMITTED_TEAM_PARTNER",
            "entity_ref":"prime.example","evidence_sha256":A})
        with self.assertRaisesRegex(s.ContractError, "unconfirmed outreach target contributes zero"):
            s._compile_at(f, self.before_intent())

    def test_partner_evidence_must_match_committed_partner(self):
        f = facts(commitment=True, all_satisfied=True, partner_gates={s.REQUIREMENT_IDS[0]})
        f["requirements"][0]["entity_ref"] = "different.prime"
        with self.assertRaisesRegex(s.ContractError, "does not match confirmed partner"):
            s._compile_at(f, self.before_intent())

    def test_prime_route_cannot_inherit_partner_basis(self):
        f = facts(route="PRIME", all_satisfied=True)
        f["requirements"][0].update({
            "basis":"NAMED_COMMITTED_TEAM_PARTNER","entity_ref":"prime.example","evidence_sha256":B})
        with self.assertRaisesRegex(s.ContractError, "forbidden outside TEAMING"):
            s._compile_at(f, self.before_intent())

    def test_confirmed_team_can_compose_qualification(self):
        f = facts(commitment=True, all_satisfied=True,
                  partner_gates={s.REQUIREMENT_IDS[0],s.REQUIREMENT_IDS[1],s.REQUIREMENT_IDS[5]})
        p = s._compile_at(f, self.before_intent())
        self.assertEqual(p["status"], "READY_FOR_OWNER_TEAMING_REVIEW")
        self.assertEqual(p["qualification_basis_counts"]["NAMED_COMMITTED_TEAM_PARTNER"], 3)
        self.assertFalse(p["truth_boundary"]["external_send_authorized"])

    def test_confirmed_team_with_gap_holds(self):
        f = facts(commitment=True, all_satisfied=True, partner_gates={s.REQUIREMENT_IDS[0]})
        f["requirements"][-1] = {"requirement_id":s.REQUIREMENT_IDS[-1],"state":"UNKNOWN",
                                  "basis":"NONE","entity_ref":None,"evidence_sha256":None}
        p = s._compile_at(f, self.before_intent())
        self.assertEqual(p["status"], "HOLD_TEAM_QUALIFICATION")

    def test_direct_prime_gaps_are_explicit_hold(self):
        p = s._compile_at(facts(route="PRIME"), self.before_intent())
        self.assertEqual(p["status"], "HOLD_PRIME_QUALIFICATION")
        self.assertFalse(p["authority"]["prime_eligibility_verified_by_ohsu"])

    def test_direct_prime_all_respondent_evidence_only_owner_review(self):
        p = s._compile_at(facts(route="PRIME", all_satisfied=True), self.before_intent())
        self.assertEqual(p["status"], "READY_FOR_OWNER_PRIME_REVIEW")
        self.assertFalse(p["authority"]["prime_eligibility_verified_by_ohsu"])

    def test_commitment_revocation_invalidates_partner_evidence(self):
        f = facts(commitment=True, all_satisfied=True, partner_gates={s.REQUIREMENT_IDS[0]})
        s._compile_at(f, self.before_intent())
        f["teaming_commitment"] = {"status":"UNCONFIRMED","partner_ref":None,"evidence_sha256":None}
        with self.assertRaisesRegex(s.ContractError, "unconfirmed outreach target contributes zero"):
            s._compile_at(f, self.before_intent())

    def test_exact_intent_deadline_holds_without_receipt(self):
        p = s._compile_at(facts(), dt.datetime(2026,9,17,0,0,tzinfo=dt.timezone.utc))
        self.assertEqual(p["status"], "HOLD_INTENT_DEADLINE")

    def test_after_deadline_receipt_holds_chronology(self):
        f = facts(commitment=True, all_satisfied=True)
        f["intent_receipt"] = {"provider_event_sha256":A,"submitted_at":"2026-09-17T00:00:01Z"}
        p = s._compile_at(f, dt.datetime(2026,9,17,1,0,tzinfo=dt.timezone.utc))
        self.assertEqual(p["status"], "HOLD_INTENT_CHRONOLOGY")

    def test_requirement_order_invariant(self):
        f1 = facts(commitment=True, all_satisfied=True)
        f2 = copy.deepcopy(f1); f2["requirements"] = list(reversed(f2["requirements"]))
        self.assertEqual(s._compile_at(f1,self.before_intent()), s._compile_at(f2,self.before_intent()))

    def test_verify_survives_clock_advance_when_operational_truth_is_unchanged(self):
        f = facts()
        bound = self.before_intent()
        packet = s._compile_at(f, bound)
        original = s._now_utc
        s._now_utc = lambda: bound + dt.timedelta(seconds=1)
        try:
            self.assertTrue(s.verify_current(packet, f))
        finally:
            s._now_utc = original

    def test_verify_stales_packet_when_deadline_crossing_changes_operational_truth(self):
        f = facts()
        just_before = dt.datetime(2026, 9, 16, 23, 59, 59, tzinfo=dt.timezone.utc)
        packet = s._compile_at(f, just_before)
        original = s._now_utc
        s._now_utc = lambda: dt.datetime(2026, 9, 17, 0, 0, 0, tzinfo=dt.timezone.utc)
        try:
            with self.assertRaisesRegex(s.ContractError, "operational state is stale"):
                s.verify_current(packet, f)
        finally:
            s._now_utc = original

    def test_cli_compile_then_verify_does_not_self_stale_on_timestamp_only(self):
        f = facts()
        compile_input = json.dumps({"schema": s.SCHEMA_INPUT, "facts": f}).encode()
        compiled = subprocess.run(
            [sys.executable, "-m", "revenue.ohsu_erp_rfp_2027_0005.source_bound", "compile"],
            input=compile_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT.parents[1])
        self.assertEqual(compiled.returncode, 0, compiled.stderr.decode())
        packet = json.loads(compiled.stdout)
        verify_input = json.dumps({
            "schema": s.SCHEMA_VERIFY_INPUT, "facts": f, "packet": packet
        }).encode()
        verified = subprocess.run(
            [sys.executable, "-m", "revenue.ohsu_erp_rfp_2027_0005.source_bound", "verify"],
            input=verify_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT.parents[1])
        self.assertEqual(verified.returncode, 0, verified.stderr.decode())
        self.assertTrue(json.loads(verified.stdout)["valid"])

    def test_bool_int_alias_rejected(self):
        f = facts(); f["owner_reviewed"] = 1
        with self.assertRaisesRegex(s.ContractError, "must be bool"):
            s._compile_at(f, self.before_intent())

    def test_cli_duplicate_key_controlled_refusal(self):
        raw = ('{"schema":"%s","schema":"%s","facts":{}}' % (s.SCHEMA_INPUT,s.SCHEMA_INPUT)).encode()
        proc = subprocess.run(
            [sys.executable,"-m","revenue.ohsu_erp_rfp_2027_0005.source_bound","compile"],
            input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT.parents[1])
        self.assertEqual(proc.returncode,2)
        self.assertIn(b"duplicate JSON key",proc.stderr)

if __name__ == "__main__":
    unittest.main()
